// Small SVG line chart (share of population over time by default) with crosshair + tooltip.
// series: [{key, label, color, dashed?, dash?}]; rows: [{t, values: {key: number}}]
// Values are fractions 0..1 shown as percentages unless yMax: 'auto' (domain fitted to
// the data) and a format function are given.
const NS = 'http://www.w3.org/2000/svg';

function el(name, attrs = {}, parent) {
  const e = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

function niceStep(span, target) {
  const raw = span / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  return (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
}

export class LineChart {
  constructor(host, series, { height = 150, minT = 20, compact = false, yMax = 1,
                              format = v => `${(v * 100).toFixed(1)}%` } = {}) {
    this.host = host;
    this.series = series;
    this.height = height;
    this.minT = minT;
    this.compact = compact;
    this.yMaxOpt = yMax;
    this.format = format;
    this.rows = [];
    this.m = compact ? { l: 26, r: 6, t: 6, b: 16 } : { l: 32, r: 8, t: 8, b: 20 };

    this.svg = el('svg', { height });
    host.appendChild(this.svg);
    this.gGrid = el('g', {}, this.svg);
    this.gLines = el('g', {}, this.svg);
    this.gHover = el('g', { visibility: 'hidden' }, this.svg);
    this.cross = el('line', { stroke: '#898781', 'stroke-width': 1, 'stroke-dasharray': '2 3' }, this.gHover);
    this.dots = series.map(s => el('circle', { r: 4, fill: s.color, stroke: '#1a1a19', 'stroke-width': 2 }, this.gHover));
    this.paths = series.map(s => el('path', {
      fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
      ...(s.dash || s.dashed ? { 'stroke-dasharray': s.dash ?? '5 3' } : {}),
    }, this.gLines));
    this.hit = el('rect', { fill: 'transparent' }, this.svg);

    host.classList.add('line-chart');
    this.tip = document.createElement('div');
    this.tip.className = 'tip';
    this.tip.hidden = true;
    host.appendChild(this.tip);
    this.hit.addEventListener('pointermove', e => this._hover(e));
    this.hit.addEventListener('pointerleave', () => this._unhover());
    this.resizeObserver = new ResizeObserver(() => this.render());
    this.resizeObserver.observe(host);
  }

  destroy() {
    this.resizeObserver.disconnect();
  }

  setRows(rows) {
    this.rows = rows;
    this.render();
  }

  render() {
    const W = this.host.clientWidth;
    if (!W) return;
    const H = this.height, m = this.m;
    this.W = W;
    this.svg.setAttribute('width', W);
    this.svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const tMax = Math.max(this.minT, this.rows.length ? this.rows[this.rows.length - 1].t : 0);
    let yMax = 1, yTicks = this.compact ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1];
    let tickText = v => `${Math.round(v * 100)}%`;
    if (this.yMaxOpt === 'auto') {
      const top = Math.max(0, ...this.rows.flatMap(r => this.series.map(s => r.values[s.key] ?? 0)));
      const yStep = niceStep(top > 0 ? top : 1, this.compact ? 2 : 4);
      yMax = Math.max(yStep, Math.ceil(top / yStep - 1e-9) * yStep);
      yTicks = [];
      for (let v = 0; v <= yMax + 1e-9; v += yStep) yTicks.push(v);
      const dp = Math.max(0, -Math.floor(Math.log10(yStep) + 1e-9));
      tickText = v => v.toFixed(dp);
    }
    this.x = t => m.l + (t / tMax) * (W - m.l - m.r);
    this.y = v => m.t + (1 - v / yMax) * (H - m.t - m.b);
    this.tMax = tMax;

    this.gGrid.replaceChildren();
    for (const v of yTicks) {
      el('line', { x1: m.l, x2: W - m.r, y1: this.y(v), y2: this.y(v), stroke: v === 0 ? '#383835' : '#2c2c2a', 'stroke-width': 1 }, this.gGrid);
      const lab = el('text', { x: m.l - 6, y: this.y(v) + 3.5, 'text-anchor': 'end', fill: '#898781', 'font-size': 10 }, this.gGrid);
      lab.textContent = tickText(v);
    }
    const step = niceStep(tMax, this.compact ? 3 : 5);
    for (let t = 0; t <= tMax + 1e-9; t += step) {
      const lab = el('text', { x: this.x(t), y: H - 4, 'text-anchor': 'middle', fill: '#898781', 'font-size': 10 }, this.gGrid);
      lab.textContent = t;
    }

    this.series.forEach((s, k) => {
      let d = this.rows.map((r, j) => `${j ? 'L' : 'M'}${this.x(r.t).toFixed(1)},${this.y(r.values[s.key]).toFixed(1)}`).join('');
      if (this.rows.length === 1) d += 'h0.01';  // a lone point still shows as a round-capped dot
      this.paths[k].setAttribute('d', d);
    });

    this.hit.setAttribute('x', m.l);
    this.hit.setAttribute('y', 0);
    this.hit.setAttribute('width', Math.max(0, W - m.l - m.r));
    this.hit.setAttribute('height', H);
    if (this.hoverT != null) this._showAt(this.hoverT);
  }

  _hover(e) {
    if (!this.rows.length) return;
    const rect = this.svg.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const t = ((px - this.m.l) / (this.W - this.m.l - this.m.r)) * this.tMax;
    // Nearest row (rows needn't be one per tick, e.g. one per batch)
    let best = this.rows[0];
    for (const r of this.rows) if (Math.abs(r.t - t) < Math.abs(best.t - t)) best = r;
    this.hoverT = best.t;
    this._showAt(this.hoverT);
  }

  _unhover() {
    this.hoverT = null;
    this.gHover.setAttribute('visibility', 'hidden');
    this.tip.hidden = true;
  }

  _showAt(t) {
    const row = this.rows.find(r => r.t === t);
    if (!row) return;
    const x = this.x(t);
    this.gHover.setAttribute('visibility', 'visible');
    this.cross.setAttribute('x1', x); this.cross.setAttribute('x2', x);
    this.cross.setAttribute('y1', this.m.t); this.cross.setAttribute('y2', this.height - this.m.b);
    this.series.forEach((s, k) => {
      this.dots[k].setAttribute('cx', x);
      this.dots[k].setAttribute('cy', this.y(row.values[s.key]));
    });
    this.tip.innerHTML = `<div class="muted" style="margin-bottom:3px">t = ${t}</div>` + this.series.map(s =>
      `<div class="row"><span style="display:flex;align-items:center;gap:6px"><span class="sw" style="--c:${s.color}"></span>${s.label}</span><b>${this.format(row.values[s.key])}</b></div>`).join('');
    this.tip.hidden = false;
    const tipW = this.tip.offsetWidth;
    const left = x + 12 + tipW > this.W ? x - 12 - tipW : x + 12;
    this.tip.style.left = `${left}px`;
    this.tip.style.top = `4px`;
  }
}
