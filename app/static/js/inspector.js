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
    // Social edge indices into / out of each node (for the tie-weight table)
    this.socialIn = Array.from({ length: n }, () => []);
    this.socialOut = Array.from({ length: n }, () => []);
    stat.social_edges.forEach(([a, b], k) => { this.socialOut[a].push(k); this.socialIn[b].push(k); });
    // Louvain community sizes per layer
    this.commSize = {};
    for (const layer of ['contact', 'social']) {
      const size = this.commSize[layer] = [];
      for (const c of stat.communities[layer]) size[c] = (size[c] ?? 0) + 1;
    }
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

// Hill-climb utility of seed i, and its rank among this batch's seeds (1 = highest).
// HillClimb._propose drops a seed with probability softmax(-utility), so the
// lowest-ranked seeds are the likeliest to be swapped out next.
function utilityText(snap, i) {
  const u = snap.policy?.utilities;
  if (!u) return null;
  const rank = 1 + snap.seeds.filter(j => u[j] > u[i]).length;
  return `${u[i].toFixed(3)}<span class="pct">rank ${rank} of ${snap.seeds.length} seeds</span>`;
}

// Reality Commons survey ties into and out of person i, by relationship type, with
// the weight each type carries and why (networks.RC_TIE_TYPES / RC_TIE_NOTE)
function tieTable(stat, idx, i, config) {
  if (!stat.social_weights) return '';
  const use = config.mechanism === 'ic' && config.ic_tie_weights
    ? 'This run spreads information with each tie\u2019s weight as its cascade probability.'
    : config.mechanism === 'ic'
      ? `This run uses one cascade probability, p = ${config.mech_val}, on every tie; turn on per-tie probabilities under Dynamics to use these weights.`
      : 'This run spreads information by a threshold / opinion model, which does not use these weights.';
  const w = stat.social_weights;
  const rows = stat.tie_types.map(tt => {
    const match = (k) => Math.abs(w[k] - tt.weight) < 1e-6;
    return { ...tt, in: idx.socialIn[i].filter(match).length, out: idx.socialOut[i].filter(match).length };
  });
  return `
    <table class="metrics ties">
      <tr><th>Relationship</th><th>Weight</th><th title="Ties into this person: people whose news reaches them (they named these people)">In</th><th title="Ties out of this person: people they reach (these people named them)">Out</th></tr>
      ${rows.map(r => `<tr class="${r.in || r.out ? '' : 'none'}"><td>${esc(r.label)}</td><td>${r.weight.toFixed(2)}</td><td>${r.in}</td><td>${r.out}</td></tr>`).join('')}
    </table>
    <div class="note">${esc(stat.tie_note)} <b>${use}</b></div>`;
}

export function renderNodeCard(card, ctx) {
  const { stat, snap, history, i, config, idx, policy, seedCounts, batches } = ctx;
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

  // Social layer: the information process (and misinformation, if on: then adherence
  // is simply "not misinformed")
  const mis = snap.misinformed;
  const adheres = mis ? !mis[i] : stat.adheres[i];
  const infoChips = [
    mis?.[i]
      ? `<span class="chip"><span class="dot slashed" style="--c:${COLORS.misinformed}"></span>Misinformed <span class="muted">since t=${snap.misinformed_at[i]}</span></span>`
      : snap.informed[i]
        ? `<span class="chip"><span class="dot" style="--c:${COLORS.informed}"></span>Informed <span class="muted">since t=${snap.informed_at[i]}</span></span>`
        : `<span class="chip off"><span class="dot" style="--c:${COLORS.uninformed}"></span>${mis ? 'Neither informed nor misinformed' : 'Not informed'}</span>`,
    adheres
      ? `<span class="chip">Adheres</span>`
      : `<span class="chip off"><span class="dot slashed" style="--c:${mis ? COLORS.misinformed : COLORS.uninformed}"></span>Won't adhere${mis ? ' <span class="muted">misinformed</span>' : ''}</span>`,
  ];
  // Seeds are informed directly (diamonds in the scene), not by spread
  if (snap.seeds.includes(i)) {
    const when = policy ? (batches ? 'this batch' : 'first batch') : `chosen at t=${config.begin_q}`;
    infoChips.push(`<span class="chip"><span class="dot diamond" style="--c:${COLORS.informed}"></span>Seed <span class="muted">${when}</span></span>`);
  }
  if (snap.misinfo_seeds?.includes(i)) {
    const why = stat.adheres[i] ? 'drawn' : 'non-adherer';
    infoChips.push(`<span class="chip"><span class="dot diamond" style="--c:${COLORS.misinformed}"></span>Misinformation seed <span class="muted">${why}</span></span>`);
  }
  const infoKv = [];
  if (policy) infoKv.push([`Seed under ${esc(policy.label)}`, `${seedCounts[i]} of ${batches} batch${batches === 1 ? '' : 'es'}`]);
  const util = snap.seeds.includes(i) ? utilityText(snap, i) : null;
  if (util) infoKv.push(['Hill-climb utility', util]);
  if (snap.belief) infoKv.push(['FJ belief x', snap.belief[i].toFixed(3)]);
  if (snap.misbelief) infoKv.push(['FJ misinformation belief', snap.misbelief[i].toFixed(3)]);
  const kvList = (rows) => rows.length ? `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` : '';

  // Per-step state history (last 120 steps), informed marked underneath
  const H = history.slice(-120);
  const strip = H.map(h => `<i class="${h.misinformed?.[i] ? 'mis' : h.informed[i] ? 'inf' : ''}" style="background:${STATE_COLORS[h.state[i]]}"></i>`).join('');

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
    ${util ? '<div class="note">Utility is the EWMA of batch-cost improvement. When a swap adds a seed, the one dropped is drawn with probability ∝ e<sup>−utility</sup>, so low-utility seeds go first.</div>' : ''}
    ${tieTable(stat, idx, i, config)}
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
      <tr><td title="Louvain community (the Cluster layout's islands)">Cluster</td>
          <td>#${stat.communities.contact[i] + 1}<span class="pct">${idx.commSize.contact[stat.communities.contact[i]]} people</span></td>
          <td>#${stat.communities.social[i] + 1}<span class="pct">${idx.commSize.social[stat.communities.social[i]]} people</span></td></tr>
    </table>
    <div class="sub-title">State history</div>
    <div class="strip-wrap"><div class="strip">${strip}</div></div>
    <div class="strip-axis"><span>t=${H.length ? H[0].t : 0}</span><span>gold underline = informed${mis ? ', magenta = misinformed' : ''}</span><span>t=${snap.t}</span></div>
  `;
}

export function renderGroupCard(card, ctx) {
  const { stat, snap, history, ids, idx } = ctx;
  const m = stat.metrics;
  const k = ids.length;
  const inSel = new Uint8Array(stat.n);
  ids.forEach(i => { inSel[i] = 1; });

  const cnt = [0, 0, 0];
  const mis = snap.misinformed;
  let informed = 0, misinformed = 0, quar = 0, adh = 0, liveDeg = 0, origDeg = 0;
  for (const i of ids) {
    cnt[snap.state[i]]++;
    informed += snap.informed[i];
    misinformed += mis ? mis[i] : 0;
    quar += snap.quarantine_days[i] >= 0 ? 1 : 0;
    adh += mis ? 1 - mis[i] : stat.adheres[i];
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
      ${mis ? `<div><b>${fmtPct(misinformed / k)}</b><span>misinformed</span></div>` : ''}
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
      ${mis ? `<span><span class="sw" style="--c:${COLORS.misinformed}"></span>Selection misinformed</span>` : ''}
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
    ...(mis ? [{ key: 'gm', label: 'Selection misinformed', color: COLORS.misinformed, dash: '7 2 1.5 2' }] : []),
  ], { height: 96, compact: true });
  chart.setRows(history.map(h => {
    let gi = 0, gf = 0, gm = 0;
    for (const i of ids) { gi += h.state[i] === 1; gf += h.informed[i]; gm += h.misinformed?.[i] ?? 0; }
    return { t: h.t, values: { gi: gi / k, gf: gf / k, gm: gm / k, pi: h.counts.I / stat.n } };
  }));
}
