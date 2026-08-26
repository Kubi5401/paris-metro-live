# -*- coding: utf-8 -*-
"""
server.py — petit serveur local qui :
  1. sert la carte (dossier static/)
  2. sert la topologie du réseau (data/network.json, générée par build_network.py)
  3. relaie en direct les deux API temps réel officielles PRIM (Île-de-France
     Mobilités), en y ajoutant votre clé API côté serveur (jamais exposée au
     navigateur) et un petit cache pour rester loin des quotas :
       - état du trafic par ligne (line_reports)
       - prochains passages par station (stop-monitoring)

Lancement :  python3 server.py
Puis ouvrez http://127.0.0.1:8000
"""
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

load_dotenv()

API_KEY = os.environ.get("PRIM_API_KEY", "").strip()
BASE = "https://prim.iledefrance-mobilites.fr/marketplace"
ROOT = Path(__file__).parent

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="")

# Construction automatique des données réseau si elles n'existent pas encore
# (pratique pour un hébergeur en ligne : un simple "python3 server.py" au
# démarrage suffit, pas besoin d'une étape séparée).
_network_path = ROOT / "data" / "network.json"
if not _network_path.exists():
    print("data/network.json introuvable : construction automatique en cours (1-2 min)...")
    try:
        import build_network
        build_network.main()
    except Exception as exc:
        print(f"ÉCHEC de la construction automatique : {exc}")
        print("Vous pouvez la relancer manuellement avec : python3 build_network.py")

TRAFFIC_TTL = 45     # secondes de cache pour l'état du trafic
PASSAGES_TTL = 15    # secondes de cache pour les prochains passages
_cache = {}


def cached(key, ttl, fetch_fn):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit["t"] < ttl:
        return hit["v"]
    value = fetch_fn()
    _cache[key] = {"t": now, "v": value}
    return value


def prim_get(url):
    if not API_KEY:
        raise RuntimeError(
            "Aucune clé API définie. Créez un fichier .env (voir .env.example) "
            "avec PRIM_API_KEY=votre_cle, obtenue gratuitement sur "
            "https://prim.iledefrance-mobilites.fr/fr/mon-jeton-api"
        )
    resp = requests.get(
        url,
        headers={"apiKey": API_KEY, "Accept": "application/json"},
        timeout=20,
    )
    if resp.status_code >= 400:
        # on inclut le corps de la réponse : PRIM y met souvent le vrai motif
        # du rejet (paramètre invalide, identifiant inconnu...), bien plus
        # utile que le générique "400 Bad Request".
        raise RuntimeError(f"{resp.status_code} sur {url} -> {resp.text[:500]}")
    return resp.json()


def parse_iso(value):
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        # certaines réponses n'ont pas de microsecondes
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            return None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/network")
def api_network():
    network_path = ROOT / "data" / "network.json"
    if not network_path.exists():
        return jsonify({
            "error": "data/network.json est introuvable. "
                     "Lancez d'abord : python3 build_network.py"
        }), 500
    return jsonify(json.loads(network_path.read_text(encoding="utf-8")))


@app.get("/api/traffic")
def api_traffic():
    """État de trafic pour toutes les lignes passées en paramètre
    (?lines=C01371,C01372,...). Résultat mis en cache par ligne."""
    line_ids = [l for l in request.args.get("lines", "").split(",") if l]
    result = {}
    for line_id in line_ids:
        def fetch(line_id=line_id):
            url = (
                f"{BASE}/v2/navitia/lines%2Fline%3AIDFM%3A"
                f"{urllib.parse.quote(line_id, safe='')}/line_reports"
            )
            try:
                data = prim_get(url)
            except Exception as exc:
                return {"status": "unknown", "messages": [], "error": str(exc)}

            disruptions = (data or {}).get("disruptions", [])
            status = "normal"
            messages = []
            seen = set()
            # Mots-clés d'équipement (ascenseur, escalator...) : ce sont des
            # pannes d'accessibilité, pas des perturbations de circulation —
            # elles sont très nombreuses et polluent complètement l'affichage
            # si on ne les met pas de côté.
            EQUIPMENT_KEYWORDS = ("ascenseur", "escalator", "escalier méc", "equipement", "équipement")

            def is_equipment_issue(d, title, text):
                tags = d.get("tags") or []
                tag_text = " ".join(
                    (t if isinstance(t, str) else t.get("name", "")) for t in tags
                ).lower()
                blob = f"{tag_text} {title} {text}".lower()
                return any(kw in blob for kw in EQUIPMENT_KEYWORDS)

            for d in disruptions:
                effect = (d.get("severity") or {}).get("effect", "")
                title = ""
                text = ""
                for m in d.get("messages", []):
                    channel = (m.get("channel") or {}).get("name", "")
                    if channel == "titre":
                        title = m.get("text", "")
                    elif channel == "moteur":
                        text = m.get("text", "")

                if is_equipment_issue(d, title, text):
                    continue  # on ignore les pannes d'ascenseur/escalator

                if effect in ("NO_SERVICE",):
                    status = "interrompu"
                elif status != "interrompu":
                    status = "perturbe"

                key = (title, text)
                if (title or text) and key not in seen:
                    seen.add(key)
                    messages.append({"title": title, "text": text, "effect": effect})

            MAX_MESSAGES = 5
            truncated = len(messages) - MAX_MESSAGES
            messages = messages[:MAX_MESSAGES]
            if truncated > 0:
                messages.append({"title": f"+ {truncated} autre(s) message(s)", "text": "", "effect": ""})

            return {"status": status, "messages": messages}

        result[line_id] = cached(f"traffic:{line_id}", TRAFFIC_TTL, fetch)
    return jsonify(result)


@app.get("/api/passages")
def api_passages():
    """Prochains passages pour une station donnée.
    ?monitoring_id=STIF:StopPoint:Q:xxxx:&line_id=C01371 (line_id optionnel)"""
    monitoring_id = request.args.get("monitoring_id", "")
    line_id = request.args.get("line_id", "")
    if not monitoring_id:
        return jsonify({"error": "monitoring_id manquant"}), 400

    def fetch():
        url = f"{BASE}/stop-monitoring?MonitoringRef={urllib.parse.quote(monitoring_id, safe=':')}"
        if line_id:
            url += f"&LineRef={urllib.parse.quote(f'STIF:Line::{line_id}:', safe=':')}"
        try:
            data = prim_get(url)
        except Exception as exc:
            return {"passages": [], "error": str(exc)}

        try:
            delivery = data["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]
            visits = delivery.get("MonitoredStopVisit", [])
        except (KeyError, IndexError):
            visits = []

        now = datetime.now(timezone.utc)
        passages = []
        for v in visits:
            try:
                mvj = v["MonitoredVehicleJourney"]
                call = mvj["MonitoredCall"]
                dest = mvj.get("DestinationName", [{}])[0].get("value", "?")
                try:
                    direction = mvj["DirectionName"][0]["value"]
                except (KeyError, IndexError):
                    direction = dest
                when = call.get("ExpectedArrivalTime") or call.get("ExpectedDepartureTime")
                dt = parse_iso(when)
                if dt is None:
                    continue
                seconds = max(0, int((dt - now).total_seconds()))
                passages.append({
                    "destination": dest,
                    "direction": direction,
                    "seconds": seconds,
                    "at_stop": call.get("VehicleAtStop", False),
                })
            except (KeyError, IndexError):
                continue

        passages.sort(key=lambda p: p["seconds"])
        return {"passages": passages}

    return jsonify(cached(f"passages:{monitoring_id}:{line_id}", PASSAGES_TTL, fetch))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    # host 0.0.0.0 : fonctionne aussi bien en local (accessible via 127.0.0.1)
    # que sur un hébergeur en ligne (Render, etc.) qui a besoin d'écouter sur
    # toutes les interfaces.
    print(f"\nCarte du métro parisien en direct : http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
