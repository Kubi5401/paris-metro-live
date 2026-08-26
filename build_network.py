# -*- coding: utf-8 -*-
"""
build_network.py
-----------------
Construit data/network.json en croisant :
  - la topologie codée en dur dans data/topology.py (ordre des stations, couleurs)
  - les données ouvertes officielles d'Île-de-France Mobilités (coordonnées GPS
    réelles + identifiants techniques nécessaires pour interroger l'API temps réel)

Ce script NE NÉCESSITE PAS de clé API : les 4 jeux de données utilisés ici sont
en open data public (licence ODbL). La clé API PRIM ne sert que plus tard, au
moment d'interroger le temps réel (server.py).

À lancer une fois (puis à relancer si le réseau évolue) :
    python3 build_network.py

Écrit un rapport des stations non reconnues automatiquement : si votre station
préférée manque de coordonnées sur la carte, regardez ce rapport et corrigez
au besoin le nom dans data/topology.py pour qu'il corresponde au nom officiel.
"""
import json
import re
import sys
import unicodedata
import difflib
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from data.topology import LINES as TOPOLOGY

LINES_URL = "https://data.iledefrance-mobilites.fr/explore/dataset/referentiel-des-lignes/download/?format=json&timezone=Europe/Paris&lang=fr"
STOP_AND_LINES_URL = "https://data.iledefrance-mobilites.fr/explore/dataset/arrets-lignes/download/?format=json&timezone=Europe/Paris&lang=fr"
STOP_RELATIONS_URL = "https://data.iledefrance-mobilites.fr/explore/dataset/relations/download/?format=json&timezone=Europe/Paris&lang=fr"

TIMEOUT = 120


def normalize(name: str) -> str:
    """Normalise un nom de station pour permettre le rapprochement malgré les
    différences d'accents, de tirets, d'apostrophes ou de casse."""
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return n.strip()


def normalize_line_code(name_line: str) -> str:
    """Transforme le nom de ligne IDFM (ex: '3 Bis', '3B', '7bis', '14') vers
    nos clés de topologie ('3bis', '7bis', '14'), quel que soit le formatage
    exact utilisé côté IDFM (espace, casse, 'bis' vs 'b')."""
    n = name_line.strip().lower().replace("ligne", "").strip()
    has_bis = "bis" in n or n.endswith("b")
    digits = re.sub(r"[^0-9]", "", n)
    if not digits:
        return re.sub(r"[^a-z0-9]", "", n)
    return f"{digits}bis" if has_bis else digits


def fetch_json(url, label):
    print(f"  téléchargement : {label} ...", flush=True)
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    print(f"    -> {len(data)} lignes reçues")
    return data


def main():
    print("1/4 Référentiel des lignes")
    lines_raw = fetch_json(LINES_URL, "referentiel-des-lignes")

    metro_id_to_code = {}   # id_line (IDFM) -> "1", "3bis", ...
    unrecognized = []
    for row in lines_raw:
        f = row.get("fields", {})
        if f.get("transportmode") != "metro":
            continue
        code = normalize_line_code(f.get("name_line", ""))
        if code in TOPOLOGY:
            metro_id_to_code[f["id_line"]] = code
        else:
            unrecognized.append(f.get("name_line", ""))

    missing_lines = set(TOPOLOGY.keys()) - set(metro_id_to_code.values())
    if missing_lines:
        print(f"  ATTENTION : lignes non retrouvées dans le référentiel : {sorted(missing_lines)}")
        print(f"  (noms de lignes métro vus mais non reconnus : {unrecognized})")
    print(f"  {len(metro_id_to_code)} lignes de métro identifiées")

    print("2/4 Relations d'arrêts (ArRId -> ZdAId)")
    relations_raw = fetch_json(STOP_RELATIONS_URL, "relations")
    arid_to_zdaid = {}
    for row in relations_raw:
        f = row.get("fields", {})
        if "arrid" in f and "zdaid" in f:
            arid_to_zdaid[str(f["arrid"])] = str(f["zdaid"])

    print("3/4 Arrêts et lignes associées (gros fichier, patience...)")
    stops_raw = fetch_json(STOP_AND_LINES_URL, "arrets-lignes")

    # per_line[code] = { normalized_name: {"name":..., "lat":..., "lon":..., "monitoring_id":...} }
    per_line = {code: {} for code in TOPOLOGY}

    for row in stops_raw:
        f = row.get("fields", {})
        raw_id_field = f.get("id", "")
        if ":" not in raw_id_field:
            continue
        line_id = raw_id_field.split(":")[1]
        code = metro_id_to_code.get(line_id)
        if code is None:
            continue

        stop_name = f.get("stop_name")
        lat = f.get("stop_lat")
        lon = f.get("stop_lon")
        if not stop_name or lat is None or lon is None:
            continue

        raw_stop_id = f.get("stop_id", "")
        if "monomodalStopPlace" in raw_stop_id:
            resolved = raw_stop_id[24:].rstrip(":")
        else:
            arid = raw_stop_id.split(":")[-2] if raw_stop_id.endswith(":") else raw_stop_id.split(":")[-1]
            resolved = arid_to_zdaid.get(arid, arid)
        monitoring_id = f"STIF:StopPoint:Q:{resolved}:"

        key = normalize(stop_name)
        if key not in per_line[code]:
            per_line[code][key] = {
                "name": stop_name,
                "lat": float(lat),
                "lon": float(lon),
                "monitoring_id": monitoring_id,
            }

    print("4/4 Rapprochement topologie <-> données officielles")
    code_to_line_id = {v: k for k, v in metro_id_to_code.items()}
    output_lines = []
    unmatched = []

    for code, line_def in TOPOLOGY.items():
        available = per_line.get(code, {})
        # Empêche deux stations DIFFÉRENTES de la même ligne de se faire
        # rapprocher du même arrêt réel : dès qu'une clé a servi (match exact
        # ou approximatif), elle est retirée des candidats pour les stations
        # suivantes. Sans ça, une station manquante du jeu de données ouvert
        # (typiquement une extension récente comme "Fort d'Aubervilliers" sur
        # la ligne 12) se fait absorber par la station homonyme la plus
        # proche déjà attribuée (ex: "Mairie d'Aubervilliers"), et les deux
        # stations se retrouvent avec des coordonnées et un identifiant
        # temps réel identiques — silencieusement faux plutôt que signalé.
        claimed_keys = set()

        def resolve_station(station_name):
            key = normalize(station_name)
            hit = None
            matched_key = None
            if key in available:
                hit = available[key]
                matched_key = key
            else:
                candidates = [k for k in available if k not in claimed_keys]
                close = difflib.get_close_matches(key, candidates, n=1, cutoff=0.6)
                if close:
                    matched_key = close[0]
                    hit = available[matched_key]
            if hit is None:
                unmatched.append(f"  ligne {code} : « {station_name} »")
                return {"name": station_name, "lat": None, "lon": None, "monitoring_id": None}
            claimed_keys.add(matched_key)
            return {
                "name": station_name,
                "lat": hit["lat"],
                "lon": hit["lon"],
                "monitoring_id": hit["monitoring_id"],
            }

        entry = {
            "id": code,
            "name": line_def["name"],
            "color": line_def["color"],
            "api_line_id": code_to_line_id.get(code),
            "stations": [resolve_station(s) for s in line_def["trunk"]],
            "branches": [],
        }
        for branch in line_def.get("branches", []):
            entry["branches"].append({
                "name": branch["name"],
                "stations": [resolve_station(s) for s in branch["stations"]],
            })
        output_lines.append(entry)

    # Détection des correspondances : une station (par nom normalisé) présente
    # sur au moins 2 lignes différentes.
    name_to_lines = {}
    for entry in output_lines:
        all_stations = list(entry["stations"]) + [s for b in entry["branches"] for s in b["stations"]]
        for st in all_stations:
            key = normalize(st["name"])
            name_to_lines.setdefault(key, {"name": st["name"], "lines": set()})
            name_to_lines[key]["lines"].add(entry["id"])
    interchanges = [
        {"name": v["name"], "lines": sorted(v["lines"])}
        for v in name_to_lines.values() if len(v["lines"]) > 1
    ]

    result = {
        "lines": output_lines,
        "interchanges": interchanges,
    }

    out_path = Path(__file__).parent / "data" / "network.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK -> {out_path} ({len(output_lines)} lignes, {len(interchanges)} correspondances)")

    if unmatched:
        print(f"\n{len(unmatched)} station(s) non rapprochées automatiquement (coordonnées manquantes) :")
        for line in unmatched:
            print(line)
        print("\n-> Vérifiez l'orthographe dans data/topology.py si besoin, puis relancez ce script.")
    else:
        print("\nToutes les stations ont été rapprochées avec succès.")


if __name__ == "__main__":
    main()
