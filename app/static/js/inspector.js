// Node pop-up (single selection) and sub-population card (multi-selection).
import { COLORS, STATE_COLORS, STATE_NAMES } from './palette.js';
import { LineChart } from './chart.js';

const fmtPct = (x) => `${(100 * x).toFixed(x > 0 && x < 0.1 ? 1 : 0)}%`;
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const mean = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;

// Precomputed per-network lookups shared by both cards
export class NetworkIndex {
  constructor(stat) {
    this.stat = stat;
    const n = stat.n;
    this.contactInc = Array.from({ length: n }, () => []);   // [edgeIdx, neighbor]
    stat.contact_edges.forEach(([a, b], k) => {
      this.contactInc[a].push([k, b]);
      this.contactInc[b].push([k, a]);
    });
    const m = stat.metrics;
    this.socialDeg = m.social_in.map((v, i) => v + m.social_out[i]);
    this.sorted = {};
    for (const key of ['contact_degree', 'contact_core', 'contact_btw', 'social_core', 'social_btw']) {
      this.sorted[key] = [...m[key]].sort((a, b) => a - b);
    }
    this.sorted.social_deg = [...this.socialDeg].sort((a, b) => a - b);
  }

  // Share of nodes with a strictly larger value, as "top X%"
  topPct(key, v) {
    const arr = this.sorted[key];
    let lo = 0, hi = arr.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (arr[mid] <= v) lo = mid + 1; else hi = mid; }
    const above = arr.length - lo;
    return Math.max(1, Math.ceil(100 * (above + 1) / arr.length));
  }
}

function metricCell(idx, key, v, text) {
  return `${text}<span class="pct">top ${idx.topPct(key, v)}%</span>`;
}

function quarantineText(snap, i, config) {
  const days = snap.quarantine_days[i];
  if (days < 0) return null;
  const planned = snap.quarantine_planned ? snap.quarantine_planned[i] : null;
  const q = config.q_mode === 'r' ? ' · until recovery' : planned ? ` of ${planned}` : '';
  return `day ${days}${q}`;
}

export function renderNodeCard(card, ctx) {
  const { stat, snap, history, i, config, idx } = ctx;
  const m = stat.metrics;
  const st = snap.state[i];
  const sinceSteps = snap.t - snap.state_since[i];

  const live = idx.contactInc[i];
  const cutSet = new Set(snap.cut_edges);
  let active = 0, infectedActive = 0;
  for (const [k, nb] of live) {
    if (cutSet.has(k)) continue;
    active++;
    if (snap.state[nb] === 1) infectedActive++;
  }
  const qText = quarantineText(snap, i, config);
  const fj = config.mechanism === 'FJ';

  // Contact layer: the disease process
  const diseaseChips = [
    `<span class="chip"><span class="dot" style="--c:${STATE_COLORS[st]}"></span>${STATE_NAMES[st]}
       <span class="muted">${snap.state_since[i] === 0 ? 'since start' : `${sinceSteps} step${sinceSteps === 1 ? '' : 's'}`}</span></span>`,
    qText
      ? `<span class="chip"><span class="hollow" style="--c:${STATE_COLORS[st]}"></span>Quarantining <span class="muted">${qText}</span></span>`
      : `<span class="chip off">${fj ? 'No node-level quarantine (FJ cuts ties)' : 'Not quarantining'}</span>`,
  ];
  const diseaseKv = [
    ['Active contacts', `${active} of ${live.length}${live.length - active ? ` <span class="muted">(${live.length - active} cut)</span>` : ''}`],
    ['Infected active contacts', infectedActive],
    ['Times infected', snap.times_infected[i]],
    ['Transmissibility β', stat.beta[i].toFixed(3)],
  ];

  // Social layer: the information process
  const infoChips = [
    snap.informed[i]
      ? `<span class="chip"><span class="dot" style="--c:${COLORS.informed}"></span>Informed <span class="muted">since t=${snap.informed_at[i]}</span></span>`
      : `<span class="chip off"><span class="dot" style="--c:${COLORS.uninformed}"></span>Not informed</span>`,
    stat.adheres[i]
      ? `<span class="chip">Adheres</span>`
      : `<span class="chip off"><span class="dot slashed" style="--c:${COLORS.uninformed}"></span>Won't adhere</span>`,
  ];
  const infoKv = [];
  if (snap.belief) infoKv.push(['FJ belief x', snap.belief[i].toFixed(3)]);
  const kvList = (rows) => rows.length ? `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` : '';

  // Per-step state history (last 120 steps), informed marked underneath
  const H = history.slice(-120);
  const strip = H.map(h => `<i class="${h.informed[i] ? 'inf' : ''}" style="background:${STATE_COLORS[h.state[i]]}"></i>`).join('');

  card.innerHTML = `
    <div class="card-head">
      <div><h2>${esc(stat.names[i])}</h2><div class="sub">node ${i}</div></div>
      <button class="close" data-close aria-label="Close">×</button>
    </div>
    <div class="layer-title"><b>Contact</b> · disease</div>
    <div class="chips">${diseaseChips.join('')}</div>
    ${kvList(diseaseKv)}
    <div class="layer-title"><b>Social</b> · information</div>
    <div class="chips">${infoChips.join('')}</div>
    ${kvList(infoKv)}
    <table class="metrics">
      <tr><th></th><th>Contact</th><th>Social <span style="font-weight:400">(in/out)</span></th></tr>
      <tr><td>Degree</td>
          <td>${metricCell(idx, 'contact_degree', m.contact_degree[i], m.contact_degree[i])}</td>
          <td>${metricCell(idx, 'social_deg', idx.socialDeg[i], `${m.social_in[i]}/${m.social_out[i]}`)}</td></tr>
      <tr><td>Coreness</td>
          <td>${metricCell(idx, 'contact_core', m.contact_core[i], m.contact_core[i])}</td>
          <td>${metricCell(idx, 'social_core', m.social_core[i], m.social_core[i])}</td></tr>
      <tr><td>Betweenness</td>
          <td>${metricCell(idx, 'contact_btw', m.contact_btw[i], m.contact_btw[i].toFixed(3))}</td>
          <td>${metricCell(idx, 'social_btw', m.social_btw[i], m.social_btw[i].toFixed(3))}</td></tr>
    </table>
    <div class="sub-title">State history</div>
    <div class="strip-wrap"><div class="strip">${strip}</div></div>
    <div class="strip-axis"><span>t=${H.length ? H[0].t : 0}</span><span>gold underline = informed</span><span>t=${snap.t}</span></div>
  `;
}

export function renderGroupCard(card, ctx) {
  const { stat, snap, history, ids, idx } = ctx;
  const m = stat.metrics;
  const k = ids.length;
  const inSel = new Uint8Array(stat.n);
  ids.forEach(i => { inSel[i] = 1; });

  const cnt = [0, 0, 0];
  let informed = 0, quar = 0, adh = 0, liveDeg = 0, origDeg = 0;
  for (const i of ids) {
    cnt[snap.state[i]]++;
    informed += snap.informed[i];
    quar += snap.quarantine_days[i] >= 0 ? 1 : 0;
    adh += stat.adheres[i];
    liveDeg += snap.live_degree[i];
    origDeg += m.contact_degree[i];
  }
  const cutSet = new Set(snap.cut_edges);
  let cInt = 0, cIntLive = 0;
  stat.contact_edges.forEach(([a, b], e) => {
    if (inSel[a] && inSel[b]) { cInt++; if (!cutSet.has(e)) cIntLive++; }
  });
  let sInt = 0;
  for (const [a, b] of stat.social_edges) if (inSel[a] && inSel[b]) sInt++;

  const seg = (c, x) => x ? `<span style="background:${c};flex:${x}"></span>` : '';
  const names = ids.slice(0, 10).map(i => esc(stat.names[i])).join(', ') + (k > 10 ? ` +${k - 10} more` : '');

  const all = [...Array(stat.n).keys()];
  const rows = [
    ['Contact degree', i => m.contact_degree[i], 1],
    ['Social degree', i => idx.socialDeg[i], 1],
    ['Contact coreness', i => m.contact_core[i], 1],
    ['Social coreness', i => m.social_core[i], 1],
    ['Contact betweenness', i => m.contact_btw[i], 3],
    ['Social betweenness', i => m.social_btw[i], 3],
  ];

  card.innerHTML = `
    <div class="card-head">
      <div><h2>${k} people selected</h2><div class="sub">${names}</div></div>
      <button class="close" data-close aria-label="Clear selection">×</button>
    </div>
    <div class="stack">${seg(COLORS.S, cnt[0])}${seg(COLORS.I, cnt[1])}${seg(COLORS.R, cnt[2])}</div>
    <div class="stack-labels">
      <span><span class="sw" style="--c:${COLORS.S}"></span>S <b>${cnt[0]}</b></span>
      <span><span class="sw" style="--c:${COLORS.I}"></span>I <b>${cnt[1]}</b></span>
      <span><span class="sw" style="--c:${COLORS.R}"></span>R <b>${cnt[2]}</b></span>
    </div>
    <div class="stat-grid">
      <div><b>${fmtPct(informed / k)}</b><span>informed</span></div>
      <div><b>${fmtPct(quar / k)}</b><span>quarantining</span></div>
      <div><b>${fmtPct(adh / k)}</b><span>adhere</span></div>
      <div><b>${origDeg ? fmtPct(1 - liveDeg / origDeg) : '–'}</b><span>contacts cut</span></div>
      <div><b>${cIntLive}<span class="muted" style="font-size:12px">/${cInt}</span></b><span>internal contacts live</span></div>
      <div><b>${sInt}</b><span>internal social ties</span></div>
    </div>
    <div class="sub-title">Infected &amp; informed over time</div>
    <div class="spark"></div>
    <div class="stack-labels small" style="margin-top:4px">
      <span><span class="sw" style="--c:${COLORS.I}"></span>Selection infected</span>
      <span><span class="sw" style="--c:${COLORS.muted}"></span>Everyone infected</span>
      <span><span class="sw" style="--c:${COLORS.informed}"></span>Selection informed</span>
    </div>
    <table class="metrics" style="margin-top:10px">
      <tr><th>Mean</th><th>Selection</th><th>Everyone</th></tr>
      ${rows.map(([lab, f, dp]) => `<tr><td>${lab}</td><td>${mean(ids.map(f)).toFixed(dp)}</td><td class="muted">${mean(all.map(f)).toFixed(dp)}</td></tr>`).join('')}
    </table>
  `;

  card._chart?.destroy();
  const chart = card._chart = new LineChart(card.querySelector('.spark'), [
    { key: 'gi', label: 'Selection infected', color: COLORS.I },
    { key: 'pi', label: 'Everyone infected', color: COLORS.muted, dashed: true },
    { key: 'gf', label: 'Selection informed', color: COLORS.informed },
  ], { height: 96, compact: true });
  chart.setRows(history.map(h => {
    let gi = 0, gf = 0;
    for (const i of ids) { gi += h.state[i] === 1; gf += h.informed[i]; }
    return { t: h.t, values: { gi: gi / k, gf: gf / k, pi: h.counts.I / stat.n } };
  }));
}
