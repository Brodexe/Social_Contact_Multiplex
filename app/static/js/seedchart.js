// Selected seeds by degree, coreness and betweenness: the figure from
// visualize_adaptive.py (_plot_selected_seed_counts), updated live. Each metric gets
// its own panel and its own equal-width value bins; the colored bar counts selected
// seeds in a bin. Behind it, a gray bar counts every node in that bin: the network's
// own distribution (the Python figure overlays a KDE on a hidden second axis), here
// on the same count axis so "chosen out of available" reads directly.
const NS = 'http://www.w3.org/2000/svg';

export const METRICS = [
  { key: 'degree', label: 'Degree', color: '#3987e5', fmt: v => v.toFixed(0) },
  { key: 'coreness', label: 'Coreness', color: '#d95926', fmt: v => v.toFixed(0) },
  { key: 'betweenness', label: 'Betweenness', color: '#199e70', fmt: v => (v === 0 ? '0' : v < 0.01 ? v.toExponential(1) : v.toFixed(3)) },
];

function el(name, attrs = {}, parent) {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

// Bar with 2px-rounded top corners, flat on the baseline
function barPath(x, y, w, h) {
  if (h <= 0 || w <= 0) return '';
  const r = Math.min(2, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

// np.linspace edges + np.digitize(values, edges[1:-1]) clipped to [0, bins-1], as in the Python
export function binCounts(values, mask, bins) {
  let lo = Infinity, hi = -Infinity;
  for (const v of values) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  const edges = Array.from({ length: bins + 1 }, (_, i) => lo + (hi - lo) * i / bins);
  const all = new Array(bins).fill(0), sel = new Array(bins).fill(0);
  values.forEach((v, i) => {
    let b = 0;
    for (let j = 1; j < bins; j++) if (v >= edges[j]) b = j;
    all[b]++;
    if (mask[i]) sel[b]++;
  });
  return { edges, all, sel };
}

export class SeedMetricChart {
  constructor(host, { height = 128, bins = 10 } = {}) {
    this.host = host;
    this.height = height;
    this.bins = bins;
    this.data = null;
    host.classList.add('seed-chart');
    this.svg = el('svg', { height });
    host.appendChild(this.svg);
    this.tip = document.createElement('div');
    this.tip.className = 'tip';
    this.tip.hidden = true;
    host.appendChild(this.tip);
    this.svg.addEventListener('pointerleave', () => { this.tip.hidden = true; this._highlight(null); });
    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(host);
  }

  // metrics: {degree: [...], coreness: [...], betweenness: [...]} per node; mask: per-node 0/1
  setData(metrics, mask, what) {
    this.data = { metrics, mask, what };
    this.render();
  }

  render() {
    const W = this.host.clientWidth;
    if (!W || !this.data) return;
    const H = this.height;
    this.svg.setAttribute('width', W);
    this.svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    this.svg.replaceChildren();
    this.bars = [];

    const gap = 14, m = { t: 18, b: 18, l: 24 };
    const pw = (W - 2 * gap) / 3;
    const plotH = H - m.t - m.b;
    METRICS.forEach((metric, p) => {
      const x0 = p * (pw + gap);
      const { edges, all, sel } = binCounts(this.data.metrics[metric.key], this.data.mask, this.bins);
      const yMax = Math.max(1, ...all);
      const y = v => m.t + plotH * (1 - v / yMax);
      const px0 = x0 + m.l, pwIn = pw - m.l;
      const slot = pwIn / this.bins;

      const title = el('text', { x: x0, y: 11, fill: '#c3c2b7', 'font-size': 11, 'font-weight': 600 }, this.svg);
      title.textContent = metric.label;
      el('line', { x1: px0, x2: x0 + pw, y1: y(0), y2: y(0), stroke: '#383835' }, this.svg);
      for (const v of [0, yMax]) {
        const lab = el('text', { x: px0 - 5, y: y(v) + 3.5, 'text-anchor': 'end', fill: '#898781', 'font-size': 10 }, this.svg);
        lab.textContent = v;
      }
      for (const [v, anchor, xx] of [[edges[0], 'start', px0], [edges[this.bins], 'end', x0 + pw]]) {
        const lab = el('text', { x: xx, y: H - 4, 'text-anchor': anchor, fill: '#898781', 'font-size': 10 }, this.svg);
        lab.textContent = metric.fmt(v);
      }

      for (let b = 0; b < this.bins; b++) {
        const bx = px0 + b * slot + 1, bw = Math.max(1, slot - 2);  // 2px surface gap between bars
        const ghost = el('path', { d: barPath(bx, y(all[b]), bw, y(0) - y(all[b])), fill: 'rgba(240,239,236,0.13)' }, this.svg);
        const bar = el('path', { d: barPath(bx, y(sel[b]), bw, y(0) - y(sel[b])), fill: metric.color }, this.svg);
        // Hit target: the whole column, taller and wider than the bar
        const hit = el('rect', { x: px0 + b * slot, y: m.t, width: slot, height: plotH, fill: 'transparent' }, this.svg);
        const info = { metric, lo: edges[b], hi: edges[b + 1], sel: sel[b], all: all[b], ghost, bar, cx: px0 + (b + 0.5) * slot };
        this.bars.push(info);
        hit.addEventListener('pointerenter', () => this._show(info));
      }
    });
  }

  _highlight(info) {
    for (const b of this.bars) b.bar.setAttribute('opacity', info && b !== info && b.metric === info.metric ? 0.55 : 1);
  }

  _show(info) {
    this._highlight(info);
    const { metric, lo, hi, sel, all } = info;
    const pct = all ? ` (${Math.round(100 * sel / all)}%)` : '';
    this.tip.innerHTML = `<div class="muted" style="margin-bottom:3px">${metric.label} ${metric.fmt(lo)}–${metric.fmt(hi)}</div>`
      + `<div class="row"><span style="display:flex;align-items:center;gap:6px"><span class="sw" style="--c:${metric.color}"></span>${this.data.what}</span><b>${sel}${pct}</b></div>`
      + `<div class="row"><span style="display:flex;align-items:center;gap:6px"><span class="sw" style="--c:rgba(240,239,236,0.35)"></span>All nodes</span><b>${all}</b></div>`;
    this.tip.hidden = false;
    const W = this.host.clientWidth, tw = this.tip.offsetWidth;
    this.tip.style.left = `${Math.max(0, Math.min(W - tw, info.cx - tw / 2))}px`;
    this.tip.style.top = `${this.height + 4}px`;
  }
}
