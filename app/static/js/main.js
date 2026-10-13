import { MultiplexScene } from './scene.js';
import { LineChart } from './chart.js';
import { COLORS, STATE_NAMES, SLOT_COLORS, SLOT_NAMES } from './palette.js';
import { NetworkIndex, renderNodeCard, renderGroupCard } from './inspector.js';
import { SeedMetricChart } from './seedchart.js';

const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// Two backends answer the same /api/* calls. Served by app/server.py, it's HTTP,
// with one server-side workspace per tab so concurrent visitors don't step each
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
// Only for a multiplex with misinformation on; its own dash keeps it apart from the
// other lines without relying on color (see palette.js)
const MISINFO_SERIES = { key: 'misinformed', label: 'Misinformed', color: COLORS.misinformed, dash: '7 2 1.5 2' };
const seriesFor = (S) => (S?.config.misinfo ? [...SERIES.slice(0, 4), MISINFO_SERIES, SERIES[4]] : SERIES);
// Cost per batch: the total plus each term the scenario counts (one shared cost axis)
const COST_SERIES = {
  cost: { key: 'cost', label: 'Total', color: COLORS.text },
  infections: { key: 'infections', label: 'Infections', color: COLORS.I, dash: '5 3' },
  edges: { key: 'edges', label: 'Edge removals', color: COLORS.quarantine, dash: '1.5 3' },
  seeds: { key: 'seeds', label: 'Seeds', color: COLORS.informed, dash: '8 3 2 3' },
};
// No-quarantine baseline runs: per-tick worst case (what normalizes the infection term) and mean
const BASELINE_SERIES = [
  { key: 'max', label: 'Max over runs (used)', color: COLORS.text },
  { key: 'mean', label: 'Mean over runs', color: COLORS.muted, dash: '4 3' },
];
const ALGO_HINTS = {
  none: 'The Seeds count above is drawn once at begin q, with probability ∝ social degree², and information spreads from them.',
  hill: 'Starts from K random seeds. Each batch tests the kept set with one swap and keeps the swap if the batch cost did not rise (adaptive_seed_selection.hill2).',
  degree: 'Each batch: the K people with the highest degree in the current, quarantine-pruned contact network.',
  cob: 'Each batch: the top K by normalized coreness ÷ normalized betweenness in the current contact network.',
  random: 'Each batch: K people chosen uniformly at random.',
  milp: 'Each batch: a mixed-integer program picks up to K seeds and which contacts to remove, minimizing the chosen cost terms with a linear exposure proxy (milp.py). Removed contacts show as cut.',
};
const ALGO_COMMON = ' Seeds are re-chosen every batch from t = 0, and each batch restarts with only its seeds informed and all quarantine cuts lifted, as in the research scripts. Seeds and Begin q above are not used.'
  + ' Before the first batch, the baseline runs are collected (no quarantine, Baseline T ticks each, as the research initialize() does over T); their per-tick worst case sets the infection weight α_w = 1/g.';
const COST_HINTS = {
  hill: 'Swaps are kept or rejected on these terms. A swap keeps the seed count at K, so the seeds term is the same for every candidate.',
  milp: 'The MILP minimizes these terms, so they change which seeds and cuts it picks.',
  other: 'These terms are only reported; they do not change which seeds are chosen.',
};

const MECH = {
  ic: { label: 'p (edge prob.)', value: 0.02, step: 'any' },
  lt: { label: 'Threshold', value: 1, step: 1 },
  FJ: { label: 'κ (hazard shape)', value: 1.25, step: 'any' },
};
const BASELINE_STEP_MS = 160;  // pace of baseline collection, so its progress is visible

// One multiplex: its scenario, network, live state and seed-selection records
function newSlotState(slot, res) {
  const stat = res.static;
  return {
    slot,
    config: res.config,
    stat,
    snap: res.snapshot,
    idx: new NetworkIndex(stat),
    history: [compact(res.snapshot)],
    policy: stat.policy ?? null,
    phase: res.snapshot.policy?.phase ?? 'run',
    costRows: [],                       // one per completed batch
    seedCounts: new Uint32Array(stat.n), // per node: batches it was a seed in
    batches: 0,
    baselineRuns: (stat.policy?.baseline.counts ?? []).slice(),  // per collected run: newly infected per tick
  };
}

const app = {
  slots: new Map(),      // slot -> slot state (see newSlotState)
  active: 0,             // slot the panel shows and the scenario form edits
  maxSlots: 3,
  selection: { slot: null, ids: [] },
  anchor: null,          // {slot, i, layer} the single-node pop-up follows
  seedView: 'ever',      // seed metric chart: picks across all batches ('ever') or this 'batch'
  metricLayer: 'social',
  playing: false,
  busy: false,
  speed: 3,
};
const activeSlot = () => app.slots.get(app.active);
const collecting = () => [...app.slots.values()].filter(S => S.phase === 'baseline');

const scene = new MultiplexScene($('#canvas-host'));
let chartSeries = SERIES;
let chart = new LineChart($('#chart'), chartSeries, { height: 150 });
const seedChart = new SeedMetricChart($('#seed-chart'));
const baselineChart = new LineChart($('#baseline-chart'), BASELINE_SERIES, {
  height: 110, minT: 10, yMax: 'auto', format: v => v.toFixed(1),
});
let costChart = null;

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

function buildTiles(series = SERIES) {
  // Six tiles (with misinformation) don't fit one row: two even rows of three
  $('#tiles').style.setProperty('--cols', series.length > 5 ? 3 : 5);
  $('#tiles').innerHTML = series.map(s => `
    <div class="tile" data-key="${s.key}">
      <div class="lab"><span class="sw ${s.dashed ? 'dashed' : ''}" style="--c:${s.color}"></span>${s.label}</div>
      <div class="val">0</div><div class="pct">0%</div>
    </div>`).join('');
}

function compact(snap) {
  return { t: snap.t, state: snap.state, informed: snap.informed, misinformed: snap.misinformed, counts: snap.counts };
}

// Tiles and population chart carry a Misinformed series only while the active
// multiplex has misinformation on
function syncSeries() {
  const want = seriesFor(activeSlot());
  if (want.length === chartSeries.length) return;
  chartSeries = want;
  chart.destroy();
  $('#chart').replaceChildren();
  chart = new LineChart($('#chart'), chartSeries, { height: 150 });
  buildTiles(chartSeries);
}

const slotBadge = (slot) => `<span class="slot-badge" style="--slot:${SLOT_COLORS[slot]}">${SLOT_NAMES[slot]}</span>`;

function slotSummary(S) {
  const mis = S.config.misinfo ? ' · misinformation' : '';
  if (!S.policy) return `no strategy${mis}`;
  return S.phase === 'baseline'
    ? `${S.policy.label} · baselines ${S.baselineRuns.length}/${S.policy.baseline.runs}${mis}`
    : S.policy.label + mis;
}

// Tabs, one per multiplex, plus "add"
function renderTabs() {
  const tabs = [...app.slots.values()].sort((a, b) => a.slot - b.slot).map(S => `
    <div class="slot-tab ${S.slot === app.active ? 'on' : ''}" style="--slot:${SLOT_COLORS[S.slot]}" data-slot="${S.slot}" role="tab" tabindex="0" aria-selected="${S.slot === app.active}">
      ${slotBadge(S.slot)}
      <span class="slot-meta"><b>t = ${S.snap.t}</b><span class="muted">${esc(slotSummary(S))}</span></span>
      ${app.slots.size > 1 ? `<button class="slot-remove" data-remove="${S.slot}" title="Remove multiplex ${SLOT_NAMES[S.slot]}" aria-label="Remove multiplex ${SLOT_NAMES[S.slot]}">×</button>` : ''}
    </div>`).join('');
  const add = app.slots.size < app.maxSlots
    ? `<button class="slot-add" id="btn-add-slot" title="Add another multiplex (copies this one's scenario; change it below)">+ Add multiplex</button>` : '';
  $('#slot-tabs').innerHTML = tabs + add;
}

function refreshPanel() {
  const S = activeSlot();
  if (!S) return;
  const { snap, stat } = S;
  syncSeries();
  $('#t-value').textContent = snap.t;
  $('#active-badge').innerHTML = slotBadge(S.slot);
  // Legend entries for misinformation, while any multiplex on screen has it
  const anyMisinfo = [...app.slots.values()].some(M => M.config.misinfo);
  for (const el of document.querySelectorAll('[data-misinfo]')) el.hidden = !anyMisinfo;
  for (const s of chartSeries) {
    const tile = $(`.tile[data-key="${s.key}"]`);
    const v = snap.counts[s.key];
    tile.querySelector('.val').textContent = v;
    tile.querySelector('.pct').textContent = `${(100 * v / stat.n).toFixed(0)}%`;
  }
  chart.setRows(S.history.map(h => ({
    t: h.t,
    values: Object.fromEntries(chartSeries.map(s => [s.key, h.counts[s.key] / stat.n])),
  })));
  refreshPolicy();
  renderTabs();
  refreshPhaseBanner();
}

function showNetworkInfo() {
  const S = activeSlot();
  const sm = S.stat.summary;
  $('#network-name').textContent = `${S.stat.label} · ${S.stat.n} people`;
  $('#network-stats').textContent = `Contact: ${sm.contact_edges} edges, clustering ${sm.contact_clustering}`
    + ` · Social: ${sm.social_ties} ties, clustering ${sm.social_clustering}, ${Math.round(100 * sm.overlap)}% also contacts`;
}

// Banner over the stage while seed strategies still need their baseline runs, so the
// preliminary collection is never mistaken for the experiment itself
function refreshPhaseBanner() {
  const banner = $('#phase-banner');
  const C = collecting();
  if (!C.length) { banner.hidden = true; return; }
  const who = C.map(S => `${slotBadge(S.slot)} ${esc(S.policy.label)} <span class="muted">(${S.baselineRuns.length}/${S.policy.baseline.runs} runs)</span>`).join(' · ');
  const waiting = [...app.slots.values()].filter(S => S.phase !== 'baseline');
  const running = app.playing || app.busy;
  banner.innerHTML = `<div class="phase-title">${running ? '<span class="spinner small"></span>' : ''}Preliminary · no-quarantine baseline runs</div>`
    + `<div>${who}</div>`
    + `<div class="muted small">${running ? 'Collecting' : 'Press Play or Step to collect'} ${C.length === 1 ? 'these' : 'each multiplex’s'} reference runs first (no quarantine, ${C[0].policy.baseline.horizon} ticks each). `
    + `This is not the experiment: it only sets the infection weight α_w. The experiment starts at t = 0 once they are in.`
    + (waiting.length ? ` ${waiting.map(S => SLOT_NAMES[S.slot]).join(', ')} wait${waiting.length === 1 ? 's' : ''} meanwhile.` : '') + '</div>';
  banner.hidden = false;
}

// ------------------------------------------------------- seed selection ---

function setupPolicy() {
  const S = activeSlot();
  const pol = S?.policy ?? null;
  $('#policy-panel').hidden = !pol;
  if (!pol) return;
  const bi = pol.batch_interval;
  $('#policy-label').textContent = `· ${pol.label}, K = ${pol.k}, batches of ${bi} tick${bi === 1 ? '' : 's'}`;
  const series = [COST_SERIES.cost, ...pol.terms.map(k => COST_SERIES[k])];
  costChart?.destroy();
  $('#cost-chart').replaceChildren();
  costChart = new LineChart($('#cost-chart'), series, { height: 130, minT: 10, yMax: 'auto', format: v => v.toFixed(3) });
  $('#cost-legend').innerHTML = series.map(s => `<span><svg width="18" height="4" aria-hidden="true"><line x1="0" x2="18" y1="2" y2="2" stroke="${s.color}" stroke-width="2" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''}/></svg>${s.label}</span>`).join('');
  $('#baseline-legend').innerHTML = BASELINE_SERIES.map(s => `<span><svg width="18" height="4" aria-hidden="true"><line x1="0" x2="18" y1="2" y2="2" stroke="${s.color}" stroke-width="2" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''}/></svg>${s.label}</span>`).join('');
  $('#cost-sub').textContent = `· ${pol.terms.length} term${pol.terms.length === 1 ? '' : 's'}, each capped at 1`;
}

function recordSnapshot(S, snap) {
  const p = snap.policy;
  if (p?.baseline?.latest && p.baseline.done > S.baselineRuns.length) S.baselineRuns.push(p.baseline.latest);
  const wasCollecting = S.phase === 'baseline';
  S.phase = p?.phase ?? 'run';
  // A baseline step leaves t where it was: refresh that entry rather than adding one
  if (snap.t === S.snap.t) S.history[S.history.length - 1] = compact(snap);
  else S.history.push(compact(snap));
  S.snap = snap;
  if (wasCollecting && S.phase === 'run') {
    toast(`${SLOT_NAMES[S.slot]}: baselines collected. ${S.policy.label} starts at t = 0.`, { ms: 3500 });
  }
  if (!p) return;
  if (p.new_batch) {
    S.batches++;
    for (const u of snap.seeds) S.seedCounts[u]++;
  }
  if (p.cost) S.costRows.push({ t: p.cost.t, values: { cost: p.cost.cost, ...p.cost.terms }, weights: p.cost.weights });
}

function refreshPolicy() {
  const S = activeSlot();
  const pol = S?.policy;
  if (!pol) return;
  const { snap, stat } = S;
  const base = pol.baseline;
  const runs = S.baselineRuns;

  // Baselines: progress while collecting, then the curves they produced
  const coll = S.phase === 'baseline';
  $('#baseline-status').innerHTML = coll
    ? `<b>Collecting</b> · run ${runs.length} of ${base.runs}, ${base.horizon} ticks each, no quarantine. <span class="muted">Preliminary, not the ${esc(pol.label)} experiment.</span>`
    : `${base.runs} run${base.runs === 1 ? '' : 's'} × ${base.horizon} ticks, no quarantine. <span class="muted">g sums the per-tick max over each batch window; α_w = 1/g.</span>`;
  $('#baseline-progress').hidden = !coll;
  $('#baseline-progress span').style.width = `${100 * runs.length / base.runs}%`;
  $('#baseline-wrap').classList.toggle('collecting', coll);
  const horizon = runs.length ? runs[0].length : 0;
  baselineChart.setRows(Array.from({ length: horizon }, (_, t) => {
    const vals = runs.map(r => r[t]);
    return { t, values: { max: Math.max(...vals), mean: vals.reduce((a, b) => a + b, 0) / vals.length } };
  }));
  // Experiment sections stay hidden until the baselines are in
  $('#experiment-wrap').hidden = coll;
  if (coll) return;

  const last = S.costRows[S.costRows.length - 1];
  const ever = S.seedCounts.reduce((a, c) => a + (c > 0), 0);
  const seedSet = new Set(snap.seeds);
  const bySpread = snap.informed.reduce((a, v, i) => a + (v && !seedSet.has(i)), 0);
  const fmtW = (w) => (w === undefined ? '–' : w < 0.001 ? w.toExponential(2) : w.toFixed(4));
  const cells = [
    [S.batches || '–', 'batch'],
    [snap.seeds.length, S.batches ? 'seeds this batch' : 'seeds, first batch'],
    [`${ever}<span class="muted" style="font-size:12px">/${stat.n}</span>`, 'ever chosen'],
    [last ? last.values.cost.toFixed(3) : '–', 'last batch cost'],
    [bySpread, 'informed by spread'],
    pol.algorithm === 'milp' ? [snap.policy.milp_removed, 'contacts cut by MILP'] : [snap.counts.cut_edges, 'contacts cut'],
    [fmtW(last?.weights.alpha_w), 'α_w = 1/g (infections)'],
    [fmtW(last?.weights.beta_w), 'β_w (edge removals)'],
  ];
  $('#policy-stats').innerHTML = cells.map(([v, l]) => `<div><b>${v}</b><span>${l}</span></div>`).join('');

  const showCost = $('#show-cost').checked, showMetrics = $('#show-metrics').checked;
  $('#cost-wrap').hidden = !showCost;
  $('#metrics-wrap').hidden = !showMetrics;
  if (showCost) costChart.setRows(S.costRows);
  if (showMetrics) {
    const weights = app.seedView === 'ever'
      ? Array.from(S.seedCounts)
      : Array.from({ length: stat.n }, (_, i) => (seedSet.has(i) ? 1 : 0));
    seedChart.setData(pol.metrics[app.metricLayer], weights,
      app.seedView === 'ever' ? 'Seed picks, all batches' : 'This batch’s seeds');
  }
}

// ------------------------------------------------------------ inspection ---

function refreshInspector() {
  const nodeCard = $('#node-card'), groupCard = $('#group-card');
  const { slot, ids } = app.selection;
  const S = app.slots.get(slot);
  if (!S || !ids.length) {
    nodeCard.hidden = true;
    groupCard.hidden = true;
    return;
  }
  const ctx = { stat: S.stat, snap: S.snap, history: S.history, config: S.config, idx: S.idx,
                policy: S.policy, seedCounts: S.seedCounts, batches: S.batches, slot };
  if (ids.length === 1) {
    renderNodeCard(nodeCard, { ...ctx, i: ids[0] });
    nodeCard.style.setProperty('--slot', SLOT_COLORS[slot]);
    nodeCard.hidden = false;
    groupCard.hidden = true;
    positionNodeCard();
  } else {
    renderGroupCard(groupCard, { ...ctx, ids });
    groupCard.style.setProperty('--slot', SLOT_COLORS[slot]);
    groupCard.hidden = false;
    nodeCard.hidden = true;
  }
}

// Keep the single-node pop-up beside its node as the camera moves
function positionNodeCard() {
  const card = $('#node-card');
  if (card.hidden || !app.anchor) return;
  const stage = $('#stage');
  const p = scene.screenPos(app.anchor.slot, app.anchor.i, app.anchor.layer);
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

// Select people in one multiplex (which becomes the active one)
function setSelection(slot, ids, anchor = null) {
  ids = [...new Set(ids)];
  app.selection = { slot: ids.length ? slot : null, ids };
  app.anchor = ids.length === 1
    ? (anchor && anchor.i === ids[0] ? anchor : { slot, i: ids[0], layer: 'contact' })
    : null;
  scene.setSelection(slot, ids);
  if (ids.length && slot !== app.active) setActive(slot);
  refreshInspector();
}
const clearSelection = () => setSelection(null, []);

function setActive(slot) {
  if (!app.slots.has(slot)) return;
  const changed = slot !== app.active;
  app.active = slot;
  if (app.selection.slot !== null && app.selection.slot !== slot) clearSelection();
  if (changed) {
    fillForm(activeSlot().config);
    setupPolicy();
    showNetworkInfo();
    $('#form-error').hidden = true;
  }
  refreshPanel();
}

// -------------------------------------------------------------- simulation ---

async function restart(slot, config) {
  setPlaying(false);
  $('#loading').hidden = false;
  $('#form-error').hidden = true;
  try {
    const res = await call('POST', `/api/reset?slot=${slot}`, config);
    const S = newSlotState(slot, res);
    app.slots.set(slot, S);
    scene.load(slot, S.stat);
    scene.applySnapshot(slot, S.snap, { animate: false });
    if (app.selection.slot === slot) clearSelection();
    app.active = slot;
    fillForm(S.config);
    setupPolicy();
    showNetworkInfo();
    refreshPanel();
    return true;
  } catch (err) {
    console.error(err);
    // Strip the Python exception name; the message is written for the user
    const msg = err.message.replace(/^\w+Error: /, '');
    $('#form-error').textContent = msg;
    $('#form-error').hidden = false;
    toast(`Could not start scenario: ${msg}`, { error: true, ms: 6000 });
    return false;
  } finally {
    $('#loading').hidden = true;
  }
}

async function restartAll() {
  const active = app.active;
  for (const S of [...app.slots.values()].sort((a, b) => a.slot - b.slot)) await restart(S.slot, S.config);
  setActive(active);
}

async function addSlot() {
  const free = [...Array(app.maxSlots).keys()].find(k => !app.slots.has(k));
  if (free === undefined) return;
  // Start from the active multiplex's scenario with a fresh random draw; edit it below
  const source = app.active;
  const cfg = { ...activeSlot().config, rng_seed: null };
  if (await restart(free, cfg)) {
    $('#scenario').open = true;
    toast(`Added multiplex ${SLOT_NAMES[free]}, a copy of ${SLOT_NAMES[source]}’s scenario. Change it under Scenario, then Apply.`, { ms: 4500 });
  }
}

async function removeSlot(slot) {
  if (app.slots.size <= 1) return;
  setPlaying(false);
  try {
    await call('POST', `/api/remove?slot=${slot}`);
  } catch (err) {
    toast(`Could not remove multiplex: ${err.message}`, { error: true });
    return;
  }
  if (app.selection.slot === slot) clearSelection();
  app.slots.delete(slot);
  scene.remove(slot);
  if (app.active === slot) {
    app.active = Math.min(...app.slots.keys());
    fillForm(activeSlot().config);
    setupPolicy();
    showNetworkInfo();
  }
  refreshPanel();
}

// One step for every multiplex. Returns the phase ('baseline' while any multiplex is
// still collecting its baseline runs, else 'run'), or null on failure.
async function stepOnce() {
  if (app.busy || !app.slots.size) return null;
  app.busy = true;
  try {
    const res = await call('POST', '/api/step');
    for (const [k, snap] of Object.entries(res.snapshots)) {
      const S = app.slots.get(Number(k));
      if (!snap || !S) continue;
      recordSnapshot(S, snap);
      scene.applySnapshot(S.slot, snap);
    }
    refreshPanel();
    if (app.selection.ids.length) refreshInspector();
    return res.phase;
  } catch (err) {
    console.error(err);
    setPlaying(false);
    toast(`Step failed: ${err.message}`, { error: true, ms: 6000 });
    return null;
  } finally {
    app.busy = false;
  }
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function playLoop() {
  while (app.playing) {
    const t0 = performance.now();
    const phase = await stepOnce();
    if (phase === null) break;
    const wait = (phase === 'baseline' ? BASELINE_STEP_MS : 1000 / app.speed) - (performance.now() - t0);
    if (wait > 0) await sleep(wait);
  }
}

// Step: one tick. If baselines are still owed, collect them all first and stop there,
// so the next Step is the experiment's first tick.
let stepping = false;
async function stepButton() {
  if (stepping || app.playing) return;
  if (!collecting().length) { await stepOnce(); return; }
  stepping = true;
  $('#btn-step').disabled = true;
  try {
    while (collecting().length && !app.playing) {
      if (await stepOnce() === null) break;
      await sleep(BASELINE_STEP_MS);
    }
  } finally {
    stepping = false;
    $('#btn-step').disabled = app.playing;
    refreshPhaseBanner();
  }
}

function setPlaying(on) {
  if (on === app.playing) return;
  app.playing = on;
  const btn = $('#btn-play');
  btn.classList.toggle('playing', on);
  btn.setAttribute('aria-label', on ? 'Pause' : 'Play');
  $('#play-label').textContent = on ? 'Pause' : 'Play';
  $('#btn-step').disabled = on || stepping;
  if (on) {
    scene.setHover(null, null);
    $('#hover-tip').hidden = true;
    playLoop();
  }
  refreshPhaseBanner();
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
  if (e.buttons || !app.slots.size) return;
  const hit = scene.pick(e.clientX, e.clientY);
  scene.setHover(hit ? hit.slot : null, hit ? hit.i : null);
  host.style.cursor = hit ? (app.playing ? 'default' : 'pointer') : '';
  if (hit) {
    const r = $('#stage').getBoundingClientRect();
    hoverTip.innerHTML = hoverText(hit.slot, hit.i, hit.layer);
    hoverTip.style.left = `${e.clientX - r.left + 14}px`;
    hoverTip.style.top = `${e.clientY - r.top + 12}px`;
    hoverTip.hidden = false;
  } else {
    hoverTip.hidden = true;
  }
});

// Hover shows only the hovered layer's process; clicking opens the full profile
function hoverText(slot, i, layer) {
  const { snap, stat, config, policy } = app.slots.get(slot);
  const parts = [];
  const mis = snap.misinformed;
  if (snap.seeds.includes(i)) parts.push(policy ? `seed, ${policy.label}` : 'seed');
  if (snap.misinfo_seeds?.includes(i)) parts.push('misinformation seed');
  if (layer === 'contact') {
    parts.push(STATE_NAMES[snap.state[i]]);
    if (snap.quarantine_days[i] >= 0) parts.push(`quarantining, day ${snap.quarantine_days[i]}`);
  } else {
    parts.push(mis?.[i] ? `Misinformed since t=${snap.misinformed_at[i]}`
      : snap.informed[i] ? `Informed since t=${snap.informed_at[i]}` : mis ? 'Neither informed nor misinformed' : 'Not informed');
    parts.push((mis ? !mis[i] : stat.adheres[i]) ? 'adheres' : "won't adhere");
    if (config.mechanism === 'FJ' && snap.belief) parts.push(`belief ${snap.belief[i].toFixed(2)}`);
  }
  return `${slotBadge(slot)} <b>${esc(stat.names[i])}</b> <span class="muted">· ${parts.join(' · ')}</span>`;
}

host.addEventListener('pointerleave', () => {
  scene.setHover(null, null);
  hoverTip.hidden = true;
});

host.addEventListener('pointerup', (e) => {
  if (!press) return;
  const moved = Math.hypot(e.clientX - press.x, e.clientY - press.y);
  if (press.marquee) {
    scene.controls.enabled = true;
    marquee.hidden = true;
    if (moved >= 5) {
      const hits = scene.nodesInRect(press.x, press.y, e.clientX, e.clientY);
      // One multiplex at a time: extend the current selection's, else the one with most hits
      let slot = hits.has(app.selection.slot) ? app.selection.slot : null;
      if (slot === null) for (const [s, ids] of hits) if (slot === null || ids.length > hits.get(slot).length) slot = s;
      if (slot !== null) setSelection(slot, [...(slot === app.selection.slot ? app.selection.ids : []), ...hits.get(slot)]);
      press = null;
      return;
    }
  }
  if (moved < 5 && press.button === 0) handleClick(e.clientX, e.clientY, press.shift);
  press = null;
});

function handleClick(x, y, shift) {
  if (!app.slots.size) return;
  const hit = scene.pick(x, y);
  if (app.playing) {
    if (hit) toast('Pause the simulation to select people');
    return;
  }
  if (!hit) {
    if (!shift) clearSelection();
    return;
  }
  const anchor = { slot: hit.slot, i: hit.i, layer: hit.layer };
  const sel = app.selection;
  const same = sel.slot === hit.slot;
  if (shift && same) {
    const has = sel.ids.includes(hit.i);
    setSelection(hit.slot, has ? sel.ids.filter(i => i !== hit.i) : [...sel.ids, hit.i], anchor);
  } else if (same && sel.ids.length === 1 && sel.ids[0] === hit.i) {
    clearSelection();
  } else {
    setSelection(hit.slot, [hit.i], anchor);
  }
}

for (const id of ['#node-card', '#group-card']) {
  $(id).addEventListener('click', (e) => { if (e.target.closest('[data-close]')) clearSelection(); });
}

document.addEventListener('keydown', (e) => {
  if (e.target.closest('input, select, textarea')) return;
  if (e.code === 'Space') { e.preventDefault(); setPlaying(!app.playing); }
  else if (e.key === 'ArrowRight' && !app.playing) { e.preventDefault(); stepButton(); }
  else if (e.key === 'Escape') clearSelection();
});

$('#btn-play').addEventListener('click', () => setPlaying(!app.playing));
$('#btn-step').addEventListener('click', () => stepButton());
$('#btn-reset').addEventListener('click', () => app.slots.size && restartAll());
$('#speed').addEventListener('input', (e) => {
  app.speed = Number(e.target.value);
  $('#speed-value').textContent = `${app.speed}/s`;
});

$('#slot-tabs').addEventListener('click', (e) => {
  const rm = e.target.closest('[data-remove]');
  if (rm) { e.stopPropagation(); removeSlot(Number(rm.dataset.remove)); return; }
  if (e.target.closest('#btn-add-slot')) { addSlot(); return; }
  const tab = e.target.closest('[data-slot]');
  if (tab) setActive(Number(tab.dataset.slot));
});
$('#slot-tabs').addEventListener('keydown', (e) => {
  const tab = e.target.closest('[data-slot]');
  if (tab && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setActive(Number(tab.dataset.slot)); }
});

for (const btn of document.querySelectorAll('[data-arrange]')) {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-arrange]').forEach(b => b.classList.toggle('on', b === btn));
    scene.setArrangement(btn.dataset.arrange);
  });
}
// Layout: style (force / cluster / grid) and mode (own per layer / aligned), both layers of every multiplex
for (const [attr, key] of [['layoutstyle', 'style'], ['layoutmode', 'mode']]) {
  const btns = document.querySelectorAll(`[data-${attr}]`);
  for (const btn of btns) {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.toggle('on', b === btn));
      scene.setLayout({ [key]: btn.dataset[attr] });
    });
  }
}
$('#btn-camera').addEventListener('click', () => scene.resetCamera(true));
$('#show-cut').addEventListener('change', (e) => scene.setShowCut(e.target.checked));
$('#btn-labels').addEventListener('click', (e) => {
  const on = !scene.showLabels;
  scene.setShowLabels(on);
  e.currentTarget.classList.toggle('on', on);
  e.currentTarget.setAttribute('aria-pressed', String(on));
});
for (const id of ['#show-cost', '#show-metrics']) {
  $(id).addEventListener('change', () => refreshPolicy());
}
for (const [attr, prop] of [['seedset', 'seedView'], ['metriclayer', 'metricLayer']]) {
  const btns = document.querySelectorAll(`[data-${attr}]`);
  for (const btn of btns) {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.toggle('on', b === btn));
      app[prop] = btn.dataset[attr];
      refreshPolicy();
    });
  }
}

// ---------------------------------------------------------------- scenario ---

const form = $('#scenario-form');
// Real-data bin sizes, from /api/options
let HS = { bins: [], survey_n: 0 };
let RC = { bins: [], survey_n: 0, tie_types: [], tie_note: '' };

function fillForm(cfg) {
  for (const [k, v] of Object.entries(cfg)) {
    const input = form.elements[k];
    if (!input) continue;
    if (input.type === 'checkbox') input.checked = !!v;
    else input.value = v ?? '';
  }
  syncFormState();
}

function tieTypesHtml() {
  return `<table class="metrics ties"><tr><th>Relationship (survey)</th><th>Weight</th></tr>`
    + RC.tie_types.map(t => `<tr><td>${esc(t.label)} <span class="muted">${esc(t.type)}</span></td><td>${t.weight.toFixed(2)}</td></tr>`).join('')
    + `</table><div class="note">${esc(RC.tie_note)}</div>`;
}

function syncFormState() {
  const f = form.elements;
  const mech = MECH[f.mechanism.value];
  $('#mech-label').textContent = mech.label;
  f.mech_val.step = mech.step;
  f.q_period.disabled = f.q_mode.value !== 'fixed';
  // Per-tie cascade probabilities: IC on the weighted Reality Commons survey only
  const tieWeights = f.mechanism.value === 'ic' && f.social_model.value === 'rc_survey';
  $('#tie-weights-row').hidden = !tieWeights;
  f.mech_val.disabled = tieWeights && f.ic_tie_weights.checked;
  f.beta.disabled = f.heterogeneous_beta.checked;
  $('#misinfo-fields').hidden = !f.misinfo.checked;
  $('#misinfo-val-label').textContent = `${mech.label.split(' (')[0]} (misinfo)`;
  f.misinfo_val.step = mech.step;

  // Show only the fields the chosen contact / social models use
  for (const el of form.querySelectorAll('[data-when]')) {
    const [name, values] = el.dataset.when.split('=');
    el.hidden = !values.split(',').includes(f[name].value);
  }

  // Node counts the two layers must agree on, spelled out as the user edits
  const contact = f.contact_model.value, social = f.social_model.value;
  const real = contact === 'hs_bin' ? HS : contact === 'rc_bin' ? RC : null;
  const bin = real?.bins.find(b => b.bin === Number(contact === 'hs_bin' ? f.hs_bin.value : f.rc_bin.value));
  const ownSurvey = (contact === 'hs_bin' && social === 'hs_survey') || (contact === 'rc_bin' && social === 'rc_survey');
  const survey = social === 'hs_survey' ? HS : social === 'rc_survey' ? RC : null;
  const contactN = real ? bin?.n : Number(f.contact_n.value);
  const nodes = ownSurvey ? bin?.n_with_survey : survey ? survey.survey_n : contactN;

  const algo = f.seed_algo.value, policy = algo !== 'none';
  f.seeds.disabled = policy;
  f.begin_q.disabled = policy;
  f.seed_k.placeholder = nodes ? `¾·n = ${Math.floor(0.75 * nodes)}` : '¾·n';
  $('#algo-hint').textContent = ALGO_HINTS[algo] + (policy ? ALGO_COMMON : '');
  $('#cost-hint').textContent = COST_HINTS[algo] ?? COST_HINTS.other;

  let contactHint = '';
  if (contact === 'hs_bin' && bin) {
    contactHint = `Bin ${bin.bin}: <b>${bin.n}</b> students, ${bin.edges} contacts (${bin.n_with_survey} also in the survey).`;
  } else if (contact === 'rc_bin' && bin) {
    contactHint = `Bin ${bin.bin} (30 days of Bluetooth proximity): <b>${bin.n}</b> participants with a contact, ${bin.edges} contacts (${bin.n_with_survey} also in the survey).`
      + ' A contact’s weight is the share of the other bins that also contain it, so habitual contacts cost more to cut.';
  } else if (contact === 'sbm') {
    contactHint = 'Stochastic block model at the same density as random. <b>Clusters</b> sets how many communities there are; '
      + '<b>Between-cluster share</b> how separated they are (0 = none between; 1 − 1/clusters = no structure). '
      + '<b>Closure</b> sets the clustering coefficient separately: the share of edges that close a triangle (how likely a person’s contacts know each other).';
  }
  $('#contact-hint').innerHTML = contactHint;

  let socialHint;
  if (survey) {
    const what = social === 'hs_survey' ? 'friendship survey' : 'relationship survey';
    socialHint = ownSurvey
      ? `${what[0].toUpperCase() + what.slice(1)} of ${survey.survey_n} people, aligned with the bin on the <b>${bin?.n_with_survey}</b> people in both.`
      : `The ${what} has <b>${survey.survey_n}</b> people, so the contact network needs ${survey.survey_n} nodes.`;
    if (social === 'rc_survey') socialHint += tieTypesHtml();
  } else {
    socialHint = `Nodes must match the contact network (<b>${contactN ?? '?'}</b>).` + (social === 'khop'
      ? ' Ties are sampled by how much people\'s k-hop contact neighbourhoods overlap; density is the share of all pairs that are ties.'
      : ' c = 1 copies the contact edges, c = −1 takes every pair that isn\'t a contact, c = 0 is independent.');
  }
  $('#social-hint').innerHTML = socialHint;

  if (f.misinfo.checked) {
    const nonAdh = nodes ? nodes - Math.floor(Number(f.adherence.value) * nodes) : null;
    $('#misinfo-hint').innerHTML = 'Misinformers start at begin q just like informers: the extra seeds above plus <b>every non-adherer</b>'
      + (nonAdh !== null ? ` (adherence ${f.adherence.value} leaves <b>${nonAdh}</b> of ${nodes})` : '')
      + ', who all spread it. Misinformed people never adhere, so they never quarantine (anyone mid-quarantine breaks it off); '
      + 'with misinformation on, adherence simply means not misinformed. It spreads by the same mechanism as information, '
      + 'with its own value (blank = the same). '
      + (f.misinfo_mode.value === 'takeover'
        ? '<b>Takeover</b>: either side can win over the other’s people (seeds never switch).'
        : '<b>Collide</b>: only people with neither can be reached; whoever reaches them first keeps them.')
      + (policy ? ' With a seed strategy, misinformation restarts from its seeds every batch, as information does.' : '');
  }
}

function readForm() {
  const f = form.elements;
  const num = (name) => Number(f[name].value);
  return {
    contact_model: f.contact_model.value,
    contact_n: num('contact_n'),
    contact_p: num('contact_p'),
    sbm_blocks: num('sbm_blocks'),
    sbm_mixing: num('sbm_mixing'),
    clustering: num('clustering'),
    hs_bin: num('hs_bin'),
    rc_bin: num('rc_bin'),
    social_model: f.social_model.value,
    social_n: num('social_n'),
    khop_k: num('khop_k'),
    social_density: num('social_density'),
    correlation: num('correlation'),
    net_seed: num('net_seed'),
    mechanism: f.mechanism.value,
    mech_val: num('mech_val'),
    ic_tie_weights: f.ic_tie_weights.checked && f.mechanism.value === 'ic' && f.social_model.value === 'rc_survey',
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
    misinfo: f.misinfo.checked,
    misinfo_seeds: num('misinfo_seeds'),
    misinfo_mode: f.misinfo_mode.value,
    misinfo_val: f.misinfo_val.value === '' ? null : num('misinfo_val'),
    seed_algo: f.seed_algo.value,
    seed_k: f.seed_k.value === '' ? null : num('seed_k'),
    batch_interval: num('batch_interval'),
    info_spread: f.info_spread.checked,
    cost_infections: f.cost_infections.checked,
    cost_edges: f.cost_edges.checked,
    cost_seeds: f.cost_seeds.checked,
    cost_baselines: num('cost_baselines'),
    baseline_horizon: num('baseline_horizon'),
  };
}

form.elements.mechanism.addEventListener('change', () => {
  form.elements.mech_val.value = MECH[form.elements.mechanism.value].value;
  form.elements.misinfo_val.value = '';  // a different mechanism's scale: back to "same as info"
  syncFormState();
});
form.addEventListener('change', syncFormState);
form.addEventListener('input', syncFormState);
form.addEventListener('submit', (e) => {
  e.preventDefault();
  restart(app.active, readForm());
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
    HS = opts.high_school;
    RC = opts.reality_commons;
    app.maxSlots = opts.max_multiplexes ?? 3;
    form.elements.hs_bin.innerHTML = HS.bins
      .map(b => `<option value="${b.bin}">Bin ${b.bin} · ${b.n} students</option>`).join('');
    form.elements.rc_bin.innerHTML = RC.bins
      .map(b => `<option value="${b.bin}">Bin ${b.bin} · ${b.n} participants</option>`).join('');
    for (const name of ['contact_n', 'social_n', 'seed_k', 'misinfo_seeds']) form.elements[name].max = opts.max_nodes;
    fillForm(opts.defaults);
    await restart(0, opts.defaults);
  } catch (err) {
    $('#loading').hidden = true;
    toast(`Could not start the simulation: ${err.message}`, { error: true, ms: 10000 });
  }
})();

// Handle for poking at the live app from the browser devtools console
window.multiplex = { app, scene };
