import { MultiplexScene } from './scene.js';
import { LineChart } from './chart.js';
import { COLORS, STATE_NAMES } from './palette.js';
import { NetworkIndex, renderNodeCard, renderGroupCard } from './inspector.js';

const $ = (sel) => document.querySelector(sel);

// Two backends answer the same /api/* calls. Served by app/server.py, it's HTTP,
// with one server-side simulation per tab so concurrent visitors don't step each
// other's runs. Served as static files (the hosted build), there is no /api/, so
// boot() falls back to running app/browser_api.py in a Pyodide web worker.
const SESSION_ID = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
let worker = null;
const pending = new Map();
let nextCallId = 0;

function startWorker(onStatus) {
  worker = new Worker(new URL('./pyodide-worker.js', import.meta.url), { type: 'module' });
  worker.onerror = (e) => {  // e.g. the Pyodide CDN is unreachable
    e.preventDefault();
    for (const { reject } of pending.values()) reject(new Error(e.message || 'Python runtime failed to load'));
    pending.clear();
  };
  worker.onmessage = ({ data }) => {
    if (data.type === 'status') return onStatus(data.text);
    const { resolve, reject } = pending.get(data.id);
    pending.delete(data.id);
    const res = JSON.parse(data.response);
    if (res.ok) resolve(res.data); else reject(new Error(res.detail));
  };
  worker.postMessage({ type: 'init', bundleUrl: new URL('py-bundle.zip', document.baseURI).href });
}

function call(method, path, body) {
  if (!worker) return httpCall(method, path, body);
  return new Promise((resolve, reject) => {
    const id = nextCallId++;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, method, path, body });
  });
}

async function httpCall(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { 'X-Session-Id': SESSION_ID, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* non-JSON error body */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const SERIES = [
  { key: 'S', label: 'Susceptible', color: COLORS.S },
  { key: 'I', label: 'Infected', color: COLORS.I },
  { key: 'R', label: 'Recovered', color: COLORS.R },
  { key: 'informed', label: 'Informed', color: COLORS.informed },
  { key: 'quarantining', label: 'Quarantining', color: COLORS.quarantine, dashed: true },
];
const MECH = {
  ic: { label: 'p (edge prob.)', value: 0.02, step: 'any' },
  lt: { label: 'Threshold', value: 1, step: 1 },
  FJ: { label: 'κ (hazard shape)', value: 1.25, step: 'any' },
};

const app = {
  stat: null, snap: null, idx: null, config: null,
  history: [],
  selection: [],
  anchor: null,          // {i, layer} the single-node pop-up follows
  playing: false,
  busy: false,
  speed: 3,
};

const scene = new MultiplexScene($('#canvas-host'));
const chart = new LineChart($('#chart'), SERIES, { height: 150 });

// ------------------------------------------------------------------ UI bits ---

let toastTimer = null;
function toast(msg, { error = false, ms = 2200 } = {}) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.toggle('error', error);
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

function buildTiles() {
  $('#tiles').innerHTML = SERIES.map(s => `
    <div class="tile" data-key="${s.key}">
      <div class="lab"><span class="sw ${s.dashed ? 'dashed' : ''}" style="--c:${s.color}"></span>${s.label}</div>
      <div class="val">0</div><div class="pct">0%</div>
    </div>`).join('');
}

function compact(snap) {
  return { t: snap.t, state: snap.state, informed: snap.informed, counts: snap.counts };
}

function refreshPanel() {
  const { snap, stat } = app;
  $('#t-value').textContent = snap.t;
  for (const s of SERIES) {
    const tile = $(`.tile[data-key="${s.key}"]`);
    const v = snap.counts[s.key];
    tile.querySelector('.val').textContent = v;
    tile.querySelector('.pct').textContent = `${(100 * v / stat.n).toFixed(0)}%`;
  }
  chart.setRows(app.history.map(h => ({
    t: h.t,
    values: Object.fromEntries(SERIES.map(s => [s.key, h.counts[s.key] / stat.n])),
  })));
}

function refreshInspector() {
  const nodeCard = $('#node-card'), groupCard = $('#group-card');
  const ctx = { stat: app.stat, snap: app.snap, history: app.history, config: app.config, idx: app.idx };
  if (app.selection.length === 1) {
    renderNodeCard(nodeCard, { ...ctx, i: app.selection[0] });
    nodeCard.hidden = false;
    groupCard.hidden = true;
    positionNodeCard();
  } else if (app.selection.length > 1) {
    renderGroupCard(groupCard, { ...ctx, ids: app.selection });
    groupCard.hidden = false;
    nodeCard.hidden = true;
  } else {
    nodeCard.hidden = true;
    groupCard.hidden = true;
  }
}

// Keep the single-node pop-up beside its node as the camera moves
function positionNodeCard() {
  const card = $('#node-card');
  if (card.hidden || !app.anchor) return;
  const stage = $('#stage');
  const p = scene.screenPos(app.anchor.i, app.anchor.layer);
  const W = stage.clientWidth, H = stage.clientHeight;
  const cw = card.offsetWidth, ch = card.offsetHeight;
  let x = p.x + 22, y = p.y - 30;
  if (x + cw > W - 10) x = p.x - 22 - cw;
  x = Math.max(10, Math.min(W - cw - 10, x));
  y = Math.max(54, Math.min(H - ch - 34, y));
  card.style.left = `${x}px`;
  card.style.top = `${y}px`;
  card.style.opacity = p.visible ? 1 : 0;
}
scene.onFrame = positionNodeCard;

function setSelection(ids, anchor = null) {
  app.selection = [...new Set(ids)];
  if (app.selection.length === 1) {
    app.anchor = anchor && anchor.i === app.selection[0] ? anchor : { i: app.selection[0], layer: 'contact' };
  } else {
    app.anchor = null;
  }
  scene.setSelection(app.selection);
  refreshInspector();
}

// -------------------------------------------------------------- simulation ---

async function restart(config) {
  setPlaying(false);
  $('#loading').hidden = false;
  try {
    const res = await call('POST', '/api/reset', config);
    app.config = res.config;
    app.stat = res.static;
    app.snap = res.snapshot;
    app.idx = new NetworkIndex(app.stat);
    app.history = [compact(res.snapshot)];
    scene.load(app.stat);
    scene.applySnapshot(app.snap, { animate: false });
    $('#network-name').textContent = `${NETWORK_NAMES[app.config.network] ?? app.config.network} · ${app.stat.n} people`;
    setSelection([]);
    refreshPanel();
  } catch (err) {
    console.error(err);
    toast(`Could not start scenario: ${err.message}`, { error: true, ms: 6000 });
  } finally {
    $('#loading').hidden = true;
  }
}

async function stepOnce() {
  if (app.busy || !app.stat) return;
  app.busy = true;
  try {
    const snap = await call('POST', '/api/step');
    app.snap = snap;
    app.history.push(compact(snap));
    scene.applySnapshot(snap);
    refreshPanel();
    if (app.selection.length) refreshInspector();
  } catch (err) {
    console.error(err);
    setPlaying(false);
    toast(`Step failed: ${err.message}`, { error: true, ms: 6000 });
  } finally {
    app.busy = false;
  }
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function playLoop() {
  while (app.playing) {
    const t0 = performance.now();
    await stepOnce();
    const wait = 1000 / app.speed - (performance.now() - t0);
    if (wait > 0) await sleep(wait);
  }
}

function setPlaying(on) {
  if (on === app.playing) return;
  app.playing = on;
  const btn = $('#btn-play');
  btn.classList.toggle('playing', on);
  btn.setAttribute('aria-label', on ? 'Pause' : 'Play');
  $('#play-label').textContent = on ? 'Pause' : 'Play';
  $('#btn-step').disabled = on;
  if (on) {
    scene.setHover(null);
    $('#hover-tip').hidden = true;
    playLoop();
  }
}

// ------------------------------------------------------------- interaction ---

const host = $('#canvas-host');
const marquee = $('#marquee');
const hoverTip = $('#hover-tip');
let press = null;

// Capture phase so a shift-drag can switch off OrbitControls before it sees the event
host.addEventListener('pointerdown', (e) => {
  press = { x: e.clientX, y: e.clientY, button: e.button, shift: e.shiftKey, marquee: false };
  if (e.button === 0 && e.shiftKey && !app.playing) {
    press.marquee = true;
    scene.controls.enabled = false;
    host.setPointerCapture(e.pointerId);
  }
  hoverTip.hidden = true;
}, { capture: true });

host.addEventListener('pointermove', (e) => {
  if (press?.marquee) {
    const r = $('#stage').getBoundingClientRect();
    const x0 = Math.min(press.x, e.clientX) - r.left, y0 = Math.min(press.y, e.clientY) - r.top;
    Object.assign(marquee.style, {
      left: `${x0}px`, top: `${y0}px`,
      width: `${Math.abs(e.clientX - press.x)}px`, height: `${Math.abs(e.clientY - press.y)}px`,
    });
    marquee.hidden = Math.hypot(e.clientX - press.x, e.clientY - press.y) < 5;
    return;
  }
  if (e.buttons || !app.stat) return;
  const hit = scene.pick(e.clientX, e.clientY);
  scene.setHover(hit ? hit.i : null);
  host.style.cursor = hit ? (app.playing ? 'default' : 'pointer') : '';
  if (hit) {
    const r = $('#stage').getBoundingClientRect();
    hoverTip.innerHTML = hoverText(hit.i, hit.layer);
    hoverTip.style.left = `${e.clientX - r.left + 14}px`;
    hoverTip.style.top = `${e.clientY - r.top + 12}px`;
    hoverTip.hidden = false;
  } else {
    hoverTip.hidden = true;
  }
});

// Hover shows only the hovered layer's process; clicking opens the full profile
function hoverText(i, layer) {
  const { snap, stat, config } = app;
  const parts = [];
  if (layer === 'contact') {
    parts.push(STATE_NAMES[snap.state[i]]);
    if (snap.quarantine_days[i] >= 0) parts.push(`quarantining, day ${snap.quarantine_days[i]}`);
  } else {
    parts.push(snap.informed[i] ? `Informed since t=${snap.informed_at[i]}` : 'Not informed');
    parts.push(stat.adheres[i] ? 'adheres' : "won't adhere");
    if (config.mechanism === 'FJ' && snap.belief) parts.push(`belief ${snap.belief[i].toFixed(2)}`);
  }
  return `<b>${stat.names[i]}</b> <span class="muted">· ${parts.join(' · ')}</span>`;
}

host.addEventListener('pointerleave', () => {
  scene.setHover(null);
  hoverTip.hidden = true;
});

host.addEventListener('pointerup', (e) => {
  if (!press) return;
  const moved = Math.hypot(e.clientX - press.x, e.clientY - press.y);
  if (press.marquee) {
    scene.controls.enabled = true;
    marquee.hidden = true;
    if (moved >= 5) {
      const ids = scene.nodesInRect(press.x, press.y, e.clientX, e.clientY);
      if (ids.length) setSelection([...app.selection, ...ids]);
      press = null;
      return;
    }
  }
  if (moved < 5 && press.button === 0) handleClick(e.clientX, e.clientY, press.shift);
  press = null;
});

function handleClick(x, y, shift) {
  if (!app.stat) return;
  const hit = scene.pick(x, y);
  if (app.playing) {
    if (hit) toast('Pause the simulation to select people');
    return;
  }
  if (!hit) {
    if (!shift) setSelection([]);
    return;
  }
  const anchor = { i: hit.i, layer: hit.layer };
  if (shift) {
    const has = app.selection.includes(hit.i);
    setSelection(has ? app.selection.filter(i => i !== hit.i) : [...app.selection, hit.i], anchor);
  } else if (app.selection.length === 1 && app.selection[0] === hit.i) {
    setSelection([]);
  } else {
    setSelection([hit.i], anchor);
  }
}

for (const id of ['#node-card', '#group-card']) {
  $(id).addEventListener('click', (e) => { if (e.target.closest('[data-close]')) setSelection([]); });
}

document.addEventListener('keydown', (e) => {
  if (e.target.closest('input, select, textarea')) return;
  if (e.code === 'Space') { e.preventDefault(); setPlaying(!app.playing); }
  else if (e.key === 'ArrowRight' && !app.playing) { e.preventDefault(); stepOnce(); }
  else if (e.key === 'Escape') setSelection([]);
});

$('#btn-play').addEventListener('click', () => setPlaying(!app.playing));
$('#btn-step').addEventListener('click', () => stepOnce());
$('#btn-reset').addEventListener('click', () => app.config && restart(app.config));
$('#speed').addEventListener('input', (e) => {
  app.speed = Number(e.target.value);
  $('#speed-value').textContent = `${app.speed}/s`;
});

for (const btn of document.querySelectorAll('[data-arrange]')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-arrange]').forEach(b => b.classList.toggle('on', b === btn));
    scene.setArrangement(btn.dataset.arrange);
  });
}
for (const btn of document.querySelectorAll('[data-layout]')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-layout]').forEach(b => b.classList.toggle('on', b === btn));
    scene.setLayout(btn.dataset.layout);
  });
}
$('#btn-camera').addEventListener('click', () => scene.resetCamera(true));
$('#show-cut').addEventListener('change', (e) => scene.setShowCut(e.target.checked));

// ---------------------------------------------------------------- scenario ---

const form = $('#scenario-form');
let NETWORK_NAMES = {};

function fillForm(cfg) {
  for (const [k, v] of Object.entries(cfg)) {
    const input = form.elements[k];
    if (!input) continue;
    if (input.type === 'checkbox') input.checked = !!v;
    else input.value = v ?? '';
  }
  syncFormState();
}

function syncFormState() {
  const mech = MECH[form.elements.mechanism.value];
  $('#mech-label').textContent = mech.label;
  form.elements.mech_val.step = mech.step;
  form.elements.q_period.disabled = form.elements.q_mode.value !== 'fixed';
  form.elements.beta.disabled = form.elements.heterogeneous_beta.checked;
}

function readForm() {
  const f = form.elements;
  const num = (name) => Number(f[name].value);
  return {
    network: f.network.value,
    mechanism: f.mechanism.value,
    mech_val: num('mech_val'),
    q_mode: f.q_mode.value,
    q_period: num('q_period'),
    adherence: num('adherence'),
    seeds: num('seeds'),
    begin_q: num('begin_q'),
    init: num('init'),
    gamma: num('gamma'),
    mu: num('mu'),
    heterogeneous_beta: f.heterogeneous_beta.checked,
    beta: num('beta'),
    rng_seed: f.rng_seed.value === '' ? null : num('rng_seed'),
    mc: num('mc'),
  };
}

form.elements.mechanism.addEventListener('change', () => {
  form.elements.mech_val.value = MECH[form.elements.mechanism.value].value;
  syncFormState();
});
form.addEventListener('change', syncFormState);
form.addEventListener('submit', (e) => {
  e.preventDefault();
  restart(readForm());
});

// -------------------------------------------------------------------- boot ---

(async function boot() {
  buildTiles();
  try {
    let opts;
    try {
      opts = await call('GET', '/api/options');
    } catch {
      const label = $('#loading span');
      startWorker((text) => { label.textContent = text; });
      opts = await call('GET', '/api/options');
    }
    NETWORK_NAMES = opts.networks;
    form.elements.network.innerHTML = Object.entries(opts.networks)
      .map(([k, v]) => `<option value="${k}">${v}</option>`).join('');
    fillForm(opts.defaults);
    await restart(opts.defaults);
  } catch (err) {
    $('#loading').hidden = true;
    toast(`Could not start the simulation: ${err.message}`, { error: true, ms: 10000 });
  }
})();

// Handle for poking at the live app from the browser devtools console
window.multiplex = { app, scene };
