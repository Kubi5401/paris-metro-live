// Carte du métro parisien "en direct".
// - Topologie + coordonnées : /api/network (statique, générée par build_network.py)
// - État du trafic par ligne : /api/traffic (réel, sondé toutes les 30s)
// - Prochains passages par station : /api/passages (réel, à la demande / clic)
// - Position des trains sur la carte : SIMULATION (pas de flux GPS public pour le métro)

// Numéro de version affiché dans le petit badge en coin de carte (voir init()).
// À incrémenter à chaque modification de ce fichier — permet de vérifier en un
// coup d'œil sur le site en ligne si une modification a bien été déployée,
// sans avoir à deviner si le navigateur affiche une version en cache.
const APP_VERSION = "v7";

const SVG_NS = "http://www.w3.org/2000/svg";
const AVG_SPEED_MPS = 6.5; // vitesse commerciale moyenne approximative (arrêts inclus)
const DEFAULT_HEADWAY_S = 240;
const BUSY_LINES = new Set(["1", "4", "6", "9", "13", "14"]);
const HEADWAY_OVERRIDES = { "3bis": 420, "7bis": 420 };

let network = null;
let svg, mapGroup;
let lineMeta = {};      // lineId -> { color, apiLineId, status, messages }
let stationRegistry = {}; // normalizedName -> { name, x, y, lines: [{lineId, monitoringId}] }
let trainPaths = [];    // [{ lineId, points: [{x,y,cum}], totalLenPx, totalLenM, headway, trainsCount }]
let selectedStationKey = null;
let passagesRefreshTimer = null; // ré-interroge le serveur pendant que le panneau est ouvert
let countdownTickTimer = null;   // fait défiler les compte à rebours seconde par seconde
const PASSAGES_REFRESH_MS = 20000;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  svg = document.getElementById("map");
  mapGroup = document.createElementNS(SVG_NS, "g");
  svg.appendChild(mapGroup);

  const versionBadge = document.getElementById("version-badge");
  if (versionBadge) versionBadge.textContent = APP_VERSION;

  setupZoomPan();

  document.getElementById("close-panel").addEventListener("click", () => {
    document.getElementById("station-panel").classList.add("hidden");
    selectedStationKey = null;
    stopPassagesLiveUpdates();
  });

  tickClock();
  setInterval(tickClock, 1000);

  try {
    const res = await fetch("/api/network");
    network = await res.json();
    if (network.error) throw new Error(network.error);
  } catch (e) {
    document.querySelector(".map-wrap").innerHTML =
      `<div style="padding:30px;color:#ff5566;font-size:14px;">Erreur de chargement du réseau : ${e.message}</div>`;
    return;
  }

  buildEverything();
  refreshTraffic();
  setInterval(refreshTraffic, 30000);
  requestAnimationFrame(animateTrains);
}

function tickClock() {
  document.getElementById("clock").textContent =
    new Date().toLocaleTimeString("fr-FR");
}

// ---------- Zoom / déplacement de la carte ----------
// Le <g id="mapGroup"> qui contient toute la carte reçoit un transform
// "translate(x,y) scale(k)" ajusté à la molette, au glisser-déposer et au
// pincement tactile. Le <svg> lui-même garde son viewBox 0..1000 fixe : ce
// repère "vx,vy" (obtenu via getScreenCTM) ne bouge jamais, seul le contenu
// à l'intérieur du groupe se déplace/zoome.
const viewState = { x: 0, y: 0, k: 1 };
const ZOOM_MIN = 1, ZOOM_MAX = 14;
// Distance (en pixels écran) à partir de laquelle un pointerdown->pointerup
// est considéré comme un glisser plutôt qu'un clic. 3px était bien trop
// strict : un vrai clic de souris déplace quasi toujours le curseur de
// quelques pixels (pression du bouton, léger tremblement de la main), donc
// la quasi-totalité des clics étaient à tort traités comme des glissers et
// la sélection de station ne se déclenchait jamais.
const DRAG_THRESHOLD_PX = 8;
let dragMoved = false;

function applyMapTransform() {
  mapGroup.setAttribute("transform", `translate(${viewState.x},${viewState.y}) scale(${viewState.k})`);
}

function clientToViewboxPoint(clientX, clientY) {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function zoomAt(vx, vy, factor) {
  const newK = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, viewState.k * factor));
  if (newK === viewState.k) return;
  const dataX = (vx - viewState.x) / viewState.k;
  const dataY = (vy - viewState.y) / viewState.k;
  viewState.k = newK;
  viewState.x = vx - dataX * newK;
  viewState.y = vy - dataY * newK;
  applyMapTransform();
}

function resetMapView() {
  viewState.x = 0;
  viewState.y = 0;
  viewState.k = 1;
  applyMapTransform();
}

function setupZoomPan() {
  // Molette : zoom centré sur le curseur.
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const p = clientToViewboxPoint(e.clientX, e.clientY);
    zoomAt(p.x, p.y, e.deltaY < 0 ? 1.15 : 1 / 1.15);
  }, { passive: false });

  // Glisser (souris) / glisser & pincer (tactile), via Pointer Events pour
  // gérer les deux avec le même code — chaque doigt/pointeur a son propre
  // pointerId, ce qui permet de détecter un pincement à deux doigts sans
  // avoir besoin d'écouteurs "touch" séparés.
  const activePointers = new Map();
  let panState = null;
  let pinchState = null;

  function startPan(clientX, clientY) {
    panState = { lastX: clientX, lastY: clientY };
    pinchState = null;
  }

  svg.addEventListener("pointerdown", (e) => {
    svg.setPointerCapture(e.pointerId);
    activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    dragMoved = false;
    if (activePointers.size === 1) {
      svg.classList.add("panning");
      startPan(e.clientX, e.clientY);
    } else if (activePointers.size === 2) {
      svg.classList.remove("panning");
      panState = null;
      const [a, b] = [...activePointers.values()];
      pinchState = {
        startDist: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        startK: viewState.k,
        center: clientToViewboxPoint((a.x + b.x) / 2, (a.y + b.y) / 2),
      };
    }
  });

  svg.addEventListener("pointermove", (e) => {
    if (!activePointers.has(e.pointerId)) return;
    activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pinchState && activePointers.size === 2) {
      const [a, b] = [...activePointers.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (dist > 0) {
        const newK = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, pinchState.startK * (dist / pinchState.startDist)));
        const dataX = (pinchState.center.x - viewState.x) / viewState.k;
        const dataY = (pinchState.center.y - viewState.y) / viewState.k;
        viewState.k = newK;
        viewState.x = pinchState.center.x - dataX * newK;
        viewState.y = pinchState.center.y - dataY * newK;
        applyMapTransform();
        dragMoved = true;
      }
      return;
    }

    if (panState) {
      const dx = e.clientX - panState.lastX;
      const dy = e.clientY - panState.lastY;
      if (Math.hypot(dx, dy) > DRAG_THRESHOLD_PX) dragMoved = true;
      if (!dragMoved) return;
      const ctm = svg.getScreenCTM();
      viewState.x += dx / ctm.a;
      viewState.y += dy / ctm.d;
      applyMapTransform();
      panState.lastX = e.clientX;
      panState.lastY = e.clientY;
    }
  });

  function endPointer(e) {
    // Important : pour un pointeur souris, le navigateur ne relâche jamais la
    // capture tout seul (contrairement au tactile, où elle est libérée quand
    // le doigt se lève). Sans ce relâchement explicite, TOUS les clics suivants
    // seraient redirigés vers le <svg> lui-même au lieu de l'élément réellement
    // sous le curseur (les cercles <circle> des stations) — ce qui rend les
    // stations définitivement impossibles à cliquer après le tout premier
    // pointerdown. On le relâche donc systématiquement ici.
    try { svg.releasePointerCapture(e.pointerId); } catch (err) { /* déjà relâché */ }
    activePointers.delete(e.pointerId);
    svg.classList.remove("panning");
    if (activePointers.size === 1) {
      const [[, p]] = activePointers;
      startPan(p.x, p.y);
    } else {
      panState = null;
      pinchState = null;
    }
  }
  svg.addEventListener("pointerup", endPointer);
  svg.addEventListener("pointercancel", endPointer);

  // Empêche qu'un glisser se termine par la sélection accidentelle de la
  // station survolée au moment du relâchement.
  svg.addEventListener("click", (e) => {
    if (dragMoved) {
      e.stopPropagation();
      dragMoved = false;
    }
  }, true);

  document.getElementById("zoom-in").addEventListener("click", () => zoomAt(500, 500, 1.3));
  document.getElementById("zoom-out").addEventListener("click", () => zoomAt(500, 500, 1 / 1.3));
  document.getElementById("zoom-reset").addEventListener("click", resetMapView);
}

// ---------- Construction géométrique ----------

function normalize(name) {
  return (name || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function metersXY(lat, lon, lat0) {
  const R = 6371000;
  const x = R * (lon * Math.PI / 180) * Math.cos(lat0 * Math.PI / 180);
  const y = R * (lat * Math.PI / 180);
  return { x, y };
}

function buildEverything() {
  // 1. collecter tous les points valides pour la projection
  const allStations = [];
  for (const line of network.lines) {
    for (const s of line.stations) allStations.push(s);
    for (const b of line.branches || []) for (const s of b.stations) allStations.push(s);
  }
  const valid = allStations.filter(s => s.lat != null && s.lon != null);
  const lat0 = valid.reduce((a, s) => a + s.lat, 0) / valid.length;

  const merc = valid.map(s => metersXY(s.lat, s.lon, lat0));
  const minX = Math.min(...merc.map(p => p.x));
  const maxX = Math.max(...merc.map(p => p.x));
  const minY = Math.min(...merc.map(p => p.y));
  const maxY = Math.max(...merc.map(p => p.y));

  const PAD = 60, VB = 1000;
  const scale = Math.min((VB - 2 * PAD) / (maxX - minX), (VB - 2 * PAD) / (maxY - minY));

  function project(lat, lon) {
    if (lat == null || lon == null) return null;
    const { x, y } = metersXY(lat, lon, lat0);
    return {
      x: PAD + (x - minX) * scale,
      y: VB - (PAD + (y - minY) * scale), // flip Y (nord = y plus petit en SVG)
    };
  }

  // 2. registre des stations (fusion des lignes partageant une station)
  stationRegistry = {};
  function registerStation(s, lineId, apiLineId) {
    if (s.lat == null || s.lon == null) return;
    const key = normalize(s.name);
    const p = project(s.lat, s.lon);
    if (!stationRegistry[key]) {
      stationRegistry[key] = { name: s.name, x: p.x, y: p.y, lines: [] };
    }
    stationRegistry[key].lines.push({ lineId, apiLineId, monitoringId: s.monitoring_id });
  }

  trainPaths = [];
  lineMeta = {};

  // 3. tracer les lignes + préparer les chemins d'animation
  for (const line of network.lines) {
    lineMeta[line.id] = { color: line.color, apiLineId: line.api_line_id, status: "unknown", messages: [] };

    const trunkPts = line.stations.map(s => ({ s, p: project(s.lat, s.lon) }));
    trunkPts.forEach(({ s }) => registerStation(s, line.id, line.api_line_id));
    drawPolyline(trunkPts.map(o => o.p).filter(Boolean), line.color, line.id);
    addTrainPath(line.id, trunkPts.map(o => o.p).filter(Boolean));

    for (const branch of line.branches || []) {
      const branchPts = branch.stations.map(s => ({ s, p: project(s.lat, s.lon) }));
      branchPts.forEach(({ s }) => registerStation(s, line.id, line.api_line_id));
      const lastTrunk = [...trunkPts].reverse().find(o => o.p);
      const full = (lastTrunk ? [lastTrunk] : []).concat(branchPts);
      drawPolyline(full.map(o => o.p).filter(Boolean), line.color, line.id);
      addTrainPath(line.id, full.map(o => o.p).filter(Boolean));
    }
  }

  // 4. dessiner les stations (une fois, par-dessus les lignes)
  const interchangeKeys = new Set((network.interchanges || []).map(i => normalize(i.name)));
  // Le point visuel (r=3, ou 5 pour les correspondances) ne fait que 4-9px
  // de diamètre une fois affiché à l'écran : bien trop petit pour être visé
  // de façon fiable à la souris, surtout au milieu des ~300 stations de la
  // carte. On superpose donc, sous chaque point, un cercle invisible plus
  // large qui reçoit réellement le clic (le point visuel reste petit et net,
  // seule sa zone cliquable est agrandie).
  const HIT_RADIUS_PAD = 6;
  for (const key in stationRegistry) {
    const st = stationRegistry[key];
    const isInterchange = interchangeKeys.has(key) || st.lines.length > 1;
    const visualR = isInterchange ? 5 : 3;

    const hitArea = document.createElementNS(SVG_NS, "circle");
    hitArea.setAttribute("cx", st.x);
    hitArea.setAttribute("cy", st.y);
    hitArea.setAttribute("r", visualR + HIT_RADIUS_PAD);
    hitArea.setAttribute("class", "station-hit");
    hitArea.addEventListener("click", () => selectStation(key));
    mapGroup.appendChild(hitArea);

    const circle = document.createElementNS(SVG_NS, "circle");
    circle.setAttribute("cx", st.x);
    circle.setAttribute("cy", st.y);
    circle.setAttribute("r", visualR);
    circle.setAttribute("class", "station-dot" + (isInterchange ? " interchange" : ""));
    // Sans ça, le contour blanc grossit avec le zoom (il vit dans le même
    // groupe SVG transformé que toute la carte) : à fort zoom, un contour de
    // 2px devient un anneau énorme et disproportionné. "non-scaling-stroke"
    // garde l'épaisseur du trait fixe à l'écran quel que soit le zoom.
    circle.setAttribute("vector-effect", "non-scaling-stroke");
    circle.addEventListener("click", () => selectStation(key));
    mapGroup.appendChild(circle);
  }

  buildLegend();
}

function drawPolyline(points, color, lineId) {
  if (points.length < 2) return;
  const d = "M " + points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" L ");

  const base = document.createElementNS(SVG_NS, "path");
  base.setAttribute("d", d);
  base.setAttribute("stroke", color);
  base.setAttribute("class", "metro-line metro-line-base");
  base.dataset.lineId = lineId;
  mapGroup.appendChild(base);

  const overlay = document.createElementNS(SVG_NS, "path");
  overlay.setAttribute("d", d);
  overlay.setAttribute("stroke", color);
  overlay.setAttribute("class", "metro-line metro-line-perturbed");
  overlay.dataset.lineId = lineId;
  overlay.style.display = "none";
  mapGroup.appendChild(overlay);
}

function addTrainPath(lineId, points) {
  if (points.length < 2) return;
  let cum = 0;
  const withCum = points.map((p, i) => {
    if (i > 0) cum += Math.hypot(p.x - points[i - 1].x, p.y - points[i - 1].y);
    return { ...p, cum };
  });
  const totalLenPx = cum;
  // longueur réelle approx : on reprojette la distance px -> mètres via le ratio
  // moyen (suffisant pour une simulation, pas besoin d'exactitude ici)
  const headway = HEADWAY_OVERRIDES[lineId] || (BUSY_LINES.has(lineId) ? 120 : DEFAULT_HEADWAY_S);
  trainPaths.push({ lineId, points: withCum, totalLenPx, headway });

  for (let d = 0; d < 2; d++) {
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("r", 4.2);
    dot.setAttribute("fill", lineMeta[lineId] ? lineMeta[lineId].color : "#fff");
    dot.setAttribute("class", "train-dot");
    dot.dataset.pathIndex = trainPaths.length - 1;
    dot.dataset.direction = d;
    mapGroup.appendChild(dot);
  }
}

function pointAt(path, fraction) {
  const target = fraction * path.totalLenPx;
  const pts = path.points;
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].cum >= target) {
      const prev = pts[i - 1], cur = pts[i];
      const segLen = cur.cum - prev.cum || 1;
      const t = (target - prev.cum) / segLen;
      return { x: prev.x + (cur.x - prev.x) * t, y: prev.y + (cur.y - prev.y) * t };
    }
  }
  return pts[pts.length - 1];
}

function animateTrains() {
  const now = performance.now() / 1000;
  const dots = mapGroup.querySelectorAll(".train-dot");
  dots.forEach(dot => {
    const path = trainPaths[+dot.dataset.pathIndex];
    if (!path) return;
    // vitesse ~constante quel que soit le zoom : on calibre le temps de parcours
    // sur la longueur du tracé projeté (approximation raisonnable, tout le
    // réseau étant projeté avec la même échelle mètres -> px).
    const travelTime = Math.max(30, path.totalLenPx / 4.2); // 4.2 px/s ~ vitesse relative constante
    const direction = +dot.dataset.direction;
    const phase = direction === 0 ? 0 : 0.5;
    let frac = ((now / travelTime) + phase) % 1;
    if (direction === 1) frac = 1 - frac;
    const pos = pointAt(path, frac);
    dot.setAttribute("cx", pos.x);
    dot.setAttribute("cy", pos.y);
  });
  requestAnimationFrame(animateTrains);
}

// ---------- Légende + trafic ----------

function buildLegend() {
  const ul = document.getElementById("legend-list");
  ul.innerHTML = "";
  for (const line of network.lines) {
    const li = document.createElement("li");
    li.id = `legend-${line.id}`;
    li.innerHTML = `
      <span class="line-chip" style="background:${line.color}">${line.name}</span>
      <span class="line-label">Ligne ${line.name}</span>
      <span class="status-dot status-unknown" id="status-dot-${line.id}"></span>
    `;
    ul.appendChild(li);
    const msg = document.createElement("div");
    msg.className = "line-messages";
    msg.id = `messages-${line.id}`;
    msg.style.display = "none";
    ul.appendChild(msg);
  }
}

async function refreshTraffic() {
  const ids = network.lines.map(l => l.api_line_id).filter(Boolean).join(",");
  const indicator = document.getElementById("live-indicator");
  try {
    const res = await fetch(`/api/traffic?lines=${encodeURIComponent(ids)}`);
    const data = await res.json();
    indicator.classList.remove("stale");

    for (const line of network.lines) {
      const info = data[line.api_line_id];
      const dot = document.getElementById(`status-dot-${line.id}`);
      const msgBox = document.getElementById(`messages-${line.id}`);
      if (!info) continue;
      lineMeta[line.id].status = info.status;
      lineMeta[line.id].messages = info.messages || [];
      dot.className = "status-dot status-" + (info.status || "unknown");

      document.querySelectorAll(`.metro-line-perturbed[data-line-id="${line.id}"]`)
        .forEach(el => el.style.display = info.status === "normal" ? "none" : "block");

      if (info.messages && info.messages.length) {
        msgBox.style.display = "block";
        msgBox.textContent = info.messages.map(m => m.title || m.text).filter(Boolean).join(" · ");
      } else {
        msgBox.style.display = "none";
      }
    }
  } catch (e) {
    indicator.classList.add("stale");
  }
}

// ---------- Panneau station ----------

function selectStation(key) {
  selectedStationKey = key;
  const st = stationRegistry[key];
  const panel = document.getElementById("station-panel");
  panel.classList.remove("hidden");
  document.getElementById("station-name").textContent = st.name;

  const linesBox = document.getElementById("station-lines");
  linesBox.innerHTML = st.lines
    .map(l => `<span class="mini-chip" style="background:${lineMeta[l.lineId].color}">${network.lines.find(x => x.id === l.lineId).name}</span>`)
    .join("");

  document.getElementById("station-passages").innerHTML = `<div class="passages-empty">Chargement…</div>`;

  stopPassagesLiveUpdates();
  loadPassages(key);                                        // chargement immédiat
  passagesRefreshTimer = setInterval(() => loadPassages(key), PASSAGES_REFRESH_MS); // + rafraîchi en direct
  countdownTickTimer = setInterval(tickCountdowns, 1000);    // + décompte seconde par seconde entre deux rafraîchissements
}

function stopPassagesLiveUpdates() {
  if (passagesRefreshTimer) clearInterval(passagesRefreshTimer);
  if (countdownTickTimer) clearInterval(countdownTickTimer);
  passagesRefreshTimer = null;
  countdownTickTimer = null;
}

async function loadPassages(key) {
  const st = stationRegistry[key];
  const passagesBox = document.getElementById("station-passages");
  const fetchedAt = Date.now();

  const sections = [];
  for (const l of st.lines) {
    if (!l.monitoringId) continue;
    const lineName = network.lines.find(x => x.id === l.lineId).name;
    try {
      const res = await fetch(`/api/passages?monitoring_id=${encodeURIComponent(l.monitoringId)}&line_id=${encodeURIComponent(l.apiLineId || "")}`);
      const data = await res.json();
      const chip = `<span class="siel-line-chip" style="background:${lineMeta[l.lineId].color}">${lineName}</span>`;
      const head = `<div class="siel-board-head">${chip}<span class="siel-board-title">Prochains départs</span></div>`;

      if (data.error) {
        sections.push(`<div class="siel-board siel-board-error">${head}<div class="siel-empty">${data.error}</div></div>`);
        continue;
      }
      if (!data.passages || !data.passages.length) {
        sections.push(`<div class="siel-board siel-board-empty">${head}<div class="siel-empty">Aucun passage annoncé</div></div>`);
        continue;
      }
      // target = horodatage absolu du passage, pour pouvoir faire défiler le
      // compte à rebours côté client sans re-solliciter le serveur chaque seconde
      const rows = data.passages.slice(0, 4).map(p => {
        const targetMs = fetchedAt + p.seconds * 1000;
        return `
        <div class="siel-row">
          <span class="siel-dest">${p.destination}</span>
          <span class="siel-time" data-at-stop="${p.at_stop ? "1" : "0"}" data-target-ms="${targetMs}">${p.at_stop ? "à quai" : formatCountdown(p.seconds)}</span>
        </div>`;
      }).join("");
      sections.push(`<div class="siel-board">${head}<div class="siel-rows">${rows}</div></div>`);
    } catch (e) {
      sections.push(`<div class="siel-board siel-board-error"><div class="siel-board-head"><span class="siel-line-chip" style="background:${lineMeta[l.lineId].color}">${lineName}</span><span class="siel-board-title">Prochains départs</span></div><div class="siel-empty">Erreur réseau</div></div>`);
    }
  }
  // ne remplace que si la sélection n'a pas changé entre-temps (l'utilisateur
  // a peut-être cliqué ailleurs pendant que les requêtes étaient en vol)
  if (selectedStationKey === key) {
    passagesBox.innerHTML = sections.join("") || `<div class="passages-empty">Pas de données disponibles</div>`;
  }
}

function tickCountdowns() {
  document.querySelectorAll(".siel-time[data-target-ms]").forEach(el => {
    if (el.dataset.atStop === "1") return;
    const remaining = Math.round((+el.dataset.targetMs - Date.now()) / 1000);
    el.textContent = remaining <= 0 ? "à quai" : formatCountdown(remaining);
  });
}

function formatCountdown(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m} min` : `${s} s`;
}
