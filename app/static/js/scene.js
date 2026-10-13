// Three.js rendering of the two-layer multiplex: social layer (information) and
// contact layer (disease), each a disc of nodes + edges. A person appears once per
// layer, and each copy shows only that layer's process: contact copies are colored
// by S/I/R (hollow = quarantining), social copies by informed / not informed (slash =
// won't adhere). Seeds -- people informed directly, by a seed-selection strategy or
// the begin_q draw, rather than by spread -- are drawn as diamonds in both layers.
// Selected people get a dashed inter-layer link joining their copies.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { COLORS, STATE_COLORS, hexToRgb } from './palette.js';

const R = 10;                 // layer disc radius (world units)
const FOV = 38;
const LAYERS = ['social', 'contact'];
const DISC = 0.46;            // node disc radius as a fraction of the sprite half-size

const ARRANGEMENTS = {
  stacked: { social: [0, 6.2, 0], contact: [0, -6.2, 0], camera: [0, 18, 39] },
  side:    { social: [-12.2, 0, 0], contact: [12.2, 0, 0], camera: [0, 56, 17] },
};

const NODE_VERT = /* glsl */`
  attribute vec3 aColor;
  attribute vec4 aFlags;   // slashed (won't adhere), hollow (quarantining), selected, dimmed  (all 0..1)
  attribute float aSize;   // node disc radius in world units
  attribute float aHover;
  attribute float aSeed;   // 1 = diamond (seed), 0 = disc; eased between
  uniform float uScale;    // framebuffer px per world unit at unit view depth
  varying vec3 vColor;
  varying vec4 vFlags;
  varying float vPx;
  varying float vSeed;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float r = aSize * (1.0 + 0.35 * aHover + 0.12 * aFlags.z);
    gl_PointSize = max(2.0 * (r / ${DISC}) * uScale / -mv.z, 4.0);
    vPx = gl_PointSize;
    vColor = aColor;
    vFlags = aFlags;
    vSeed = aSeed;
    gl_Position = projectionMatrix * mv;
  }
`;

const NODE_FRAG = /* glsl */`
  uniform vec3 uSurface;
  uniform vec3 uSelect;
  varying vec3 vColor;
  varying vec4 vFlags;
  varying float vPx;
  varying float vSeed;

  float band(float r, float a, float b, float aa) {
    return smoothstep(a - aa, a + aa, r) * (1.0 - smoothstep(b - aa, b + aa, r));
  }
  vec4 over(vec4 dst, vec3 rgb, float a) {
    return vec4(mix(dst.rgb, rgb, a), a + dst.a * (1.0 - a));
  }

  void main() {
    vec2 p = gl_PointCoord * 2.0 - 1.0;
    // Shape metric: disc, or for seeds a diamond of equal area (|x|+|y| scaled by 0.8)
    float r = mix(length(p), (abs(p.x) + abs(p.y)) * 0.8, vSeed);
    if (r > 1.0) discard;
    float aa = 1.2 / vPx;          // ~0.6px soft edge in sprite units
    float slash = vFlags.x, hollow = vFlags.y, sel = vFlags.z, dim = vFlags.w;

    vec3 fill = mix(vColor, uSurface, dim * 0.72);
    float D = ${DISC};
    float inDisc = 1.0 - smoothstep(D - aa, D + aa, r);

    vec4 c = vec4(0.0);
    c = over(c, uSelect, band(r, D + 0.13, D + 0.21, aa) * sel);           // selection ring
    c = over(c, uSurface, 1.0 - smoothstep(D + 0.09 - aa, D + 0.09 + aa, r)); // outline: keeps overlaps legible
    c = over(c, fill, inDisc);                                             // state disc
    c = over(c, uSurface, (1.0 - smoothstep(D * 0.52 - aa, D * 0.52 + aa, r)) * hollow); // hollow = quarantining
    float diag = abs(p.x - p.y) * 0.7071;                                  // top-left to bottom-right
    c = over(c, uSurface, (1.0 - smoothstep(0.07 - aa, 0.07 + aa, diag)) * inDisc * slash); // slash = won't adhere

    if (c.a < 0.02) discard;
    gl_FragColor = c;
  }
`;

const PULSE_VERT = /* glsl */`
  attribute vec3 aColor;
  attribute float aProg;
  attribute float aSize;
  uniform float uScale;
  varying vec3 vColor;
  varying float vProg;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = 2.0 * aSize * 4.0 * uScale / -mv.z;
    vColor = aColor; vProg = aProg;
    gl_Position = projectionMatrix * mv;
  }
`;
const PULSE_FRAG = /* glsl */`
  varying vec3 vColor;
  varying float vProg;
  void main() {
    float r = length(gl_PointCoord * 2.0 - 1.0);
    float rad = 0.15 + 0.8 * vProg;
    float a = (1.0 - smoothstep(0.0, 0.07, abs(r - rad))) * (1.0 - vProg) * 0.9;
    if (a < 0.01) discard;
    gl_FragColor = vec4(vColor * a, a);
  }
`;

const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export class MultiplexScene {
  constructor(host) {
    this.host = host;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    host.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.style.position = 'absolute';
    this.labelRenderer.domElement.style.inset = '0';
    this.labelRenderer.domElement.style.pointerEvents = 'none';
    host.appendChild(this.labelRenderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(FOV, 1, 0.5, 400);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.maxDistance = 120;
    this.controls.minDistance = 6;

    this.groups = {};
    for (const name of LAYERS) {
      const g = new THREE.Group();
      g.position.fromArray(ARRANGEMENTS.stacked[name]);
      this.scene.add(g);
      this.groups[name] = g;
      this._buildPlane(g, name);
    }

    this.arrangement = 'stacked';
    this.layoutMode = 'independent';
    this.showCut = true;
    this.selection = new Set();
    this.hovered = null;
    this.pulses = [];
    this.anims = [];
    this.data = null;

    this._buildLinks();
    this._buildPulses();

    this.resetCamera(false);
    new ResizeObserver(() => this._resize()).observe(host);
    this._resize();
    this.clock = new THREE.Clock();
    this.renderer.setAnimationLoop(() => this._frame());
  }

  // ------------------------------------------------------------ building ---

  _buildPlane(group, name) {
    const disc = new THREE.Mesh(
      new THREE.CircleGeometry(R + 1.3, 128),
      new THREE.MeshBasicMaterial({ color: COLORS.text, transparent: true, opacity: 0.028, depthWrite: false, side: THREE.DoubleSide }));
    disc.rotation.x = -Math.PI / 2;
    disc.position.y = -0.05;
    disc.renderOrder = -2;
    group.add(disc);

    const rim = new THREE.Mesh(
      new THREE.RingGeometry(R + 1.26, R + 1.32, 160),
      new THREE.MeshBasicMaterial({ color: COLORS.text, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide }));
    rim.rotation.x = -Math.PI / 2;
    rim.position.y = -0.05;
    rim.renderOrder = -2;
    group.add(rim);

    const el = document.createElement('div');
    el.className = 'layer-label';
    el.innerHTML = name === 'social'
      ? '<b>Social</b> · information spread'
      : '<b>Contact</b> · disease spread';
    const label = new CSS2DObject(el);
    label.position.set(0, 0, -(R + 2.3));  // far rim, clear of the help bar and the other layer
    group.add(label);
  }

  _buildLinks() {
    this.linkMaterial = new LineMaterial({
      color: COLORS.select, linewidth: 1.7, worldUnits: false, transparent: true, opacity: 0.9,
      dashed: true, dashSize: 0.32, gapSize: 0.22, depthWrite: false,
    });
    this.links = new LineSegments2(new LineSegmentsGeometry(), this.linkMaterial);
    this.links.visible = false;
    this.links.renderOrder = 3;
    this.scene.add(this.links);
  }

  _buildPulses() {
    const max = 2048;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(max * 3), 3));
    geo.setAttribute('aColor', new THREE.BufferAttribute(new Float32Array(max * 3), 3));
    geo.setAttribute('aProg', new THREE.BufferAttribute(new Float32Array(max), 1));
    geo.setAttribute('aSize', new THREE.BufferAttribute(new Float32Array(max), 1));
    geo.setDrawRange(0, 0);
    this.pulseMat = new THREE.ShaderMaterial({
      vertexShader: PULSE_VERT, fragmentShader: PULSE_FRAG,
      uniforms: { uScale: { value: 1 } },
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    this.pulsePoints = new THREE.Points(geo, this.pulseMat);
    this.pulsePoints.frustumCulled = false;
    this.pulsePoints.renderOrder = 4;
    this.scene.add(this.pulsePoints);
  }

  // Build nodes and edges for a freshly loaded network.
  load(stat) {
    this._disposeLayers();
    const n = stat.n;
    this.data = stat;
    this.snapshot = null;     // the previous network's snapshot must not leak into this one
    this.pulses = [];
    this.selection.clear();
    this.hovered = null;

    const deg = {
      contact: stat.metrics.contact_degree,
      social: stat.metrics.social_in.map((v, i) => v + stat.metrics.social_out[i]),
    };
    // Local (x, 0, z) positions per layer and per layout mode
    this.layouts = {
      independent: {
        contact: stat.layout.contact.map(([x, y]) => [x * R, 0, y * R]),
        social: stat.layout.social.map(([x, y]) => [x * R, 0, y * R]),
      },
    };
    this.layouts.aligned = { contact: this.layouts.independent.contact, social: this.layouts.independent.contact };
    this.local = {
      contact: this.layouts[this.layoutMode].contact.map(p => p.slice()),
      social: this.layouts[this.layoutMode].social.map(p => p.slice()),
    };

    // Per-layer node colors / flags (each layer encodes its own process), eased toward targets
    this.colorCur = {}; this.colorTarget = {}; this.flagCur = {}; this.flagTarget = {};
    for (const name of LAYERS) {
      this.colorCur[name] = new Float32Array(n * 3);
      this.colorTarget[name] = new Float32Array(n * 3);
      this.flagCur[name] = new Float32Array(n * 4);
      this.flagTarget[name] = new Float32Array(n * 4);
    }
    this.seedCur = new Float32Array(n);
    this.seedTarget = new Float32Array(n);
    this.hoverCur = new Float32Array(n);
    this.sizes = {};

    this.layer = {};
    for (const name of LAYERS) {
      const maxDeg = Math.max(1, ...deg[name]);
      const size = new Float32Array(n);
      for (let i = 0; i < n; i++) size[i] = 0.11 + 0.21 * Math.sqrt(deg[name][i] / maxDeg);
      this.sizes[name] = size;

      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      geo.setAttribute('aColor', new THREE.BufferAttribute(this.colorCur[name], 3));
      geo.setAttribute('aFlags', new THREE.BufferAttribute(this.flagCur[name], 4));
      geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
      geo.setAttribute('aHover', new THREE.BufferAttribute(this.hoverCur, 1));
      geo.setAttribute('aSeed', new THREE.BufferAttribute(this.seedCur, 1));
      const mat = new THREE.ShaderMaterial({
        vertexShader: NODE_VERT, fragmentShader: NODE_FRAG,
        uniforms: {
          uScale: { value: 1 },
          uSurface: { value: new THREE.Color(COLORS.surface) },
          uSelect: { value: new THREE.Color(COLORS.select) },
        },
        transparent: true, depthWrite: true,
      });
      const points = new THREE.Points(geo, mat);
      points.frustumCulled = false;
      points.renderOrder = 2;
      this.groups[name].add(points);

      const edges = name === 'contact' ? stat.contact_edges : stat.social_edges;
      const eGeo = new THREE.BufferGeometry();
      eGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(edges.length * 6), 3));
      eGeo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(edges.length * 8), 4));
      const eLines = new THREE.LineSegments(eGeo, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, depthWrite: false,
      }));
      eLines.frustumCulled = false;
      eLines.renderOrder = 0;
      this.groups[name].add(eLines);

      this.layer[name] = { points, edges, eLines };
    }

    // Contact edges removed by quarantine, drawn as faint dashes
    this.cutLines = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineDashedMaterial({
      color: COLORS.muted, dashSize: 0.22, gapSize: 0.2, transparent: true, opacity: 0.38, depthWrite: false,
    }));
    this.cutLines.frustumCulled = false;
    this.cutLines.renderOrder = -1;
    this.groups.contact.add(this.cutLines);
    this.cutSet = [];

    this._writePositions();
  }

  _disposeLayers() {
    if (!this.layer) return;
    for (const name of LAYERS) {
      const { points, eLines } = this.layer[name];
      for (const obj of [points, eLines]) {
        this.groups[name].remove(obj);
        obj.geometry.dispose();
        obj.material.dispose();
      }
    }
    this.groups.contact.remove(this.cutLines);
    this.cutLines.geometry.dispose();
    this.cutLines.material.dispose();
    this.layer = null;
  }

  // ----------------------------------------------------------- state sync ---

  applySnapshot(snap, { animate = true } = {}) {
    const prev = this.snapshot;
    this.snapshot = snap;
    const n = this.data.n;
    const stateRgb = STATE_COLORS.map(hexToRgb);
    const infoRgb = [hexToRgb(COLORS.uninformed), hexToRgb(COLORS.informed)];
    const cColor = this.colorTarget.contact, cFlag = this.flagTarget.contact;
    const sColor = this.colorTarget.social, sFlag = this.flagTarget.social;
    for (let i = 0; i < n; i++) {
      // Contact copy: disease state, hollow while quarantining
      cColor.set(stateRgb[snap.state[i]], i * 3);
      cFlag[i * 4] = 0;
      cFlag[i * 4 + 1] = snap.quarantine_days[i] >= 0 ? 1 : 0;
      // Social copy: informed or not, slashed if the person won't adhere
      sColor.set(infoRgb[snap.informed[i] ? 1 : 0], i * 3);
      sFlag[i * 4] = this.data.adheres[i] ? 0 : 1;
      sFlag[i * 4 + 1] = 0;
    }
    this.seedTarget.fill(0);
    for (const u of snap.seeds ?? []) this.seedTarget[u] = 1;
    this._writeSelectionFlags();
    if (!animate || !prev) {
      for (const name of LAYERS) {
        this.colorCur[name].set(this.colorTarget[name]);
        this.flagCur[name].set(this.flagTarget[name]);
      }
      this.seedCur.set(this.seedTarget);
      this._markNodeAttrsDirty();
    }
    if (animate && prev) {
      for (const u of snap.new_infected) this._pulse(u, 'contact', COLORS.I);
      for (const u of snap.new_informed) this._pulse(u, 'social', COLORS.informed);
    }
    this._rebuildCut();
    this._recolorEdges();
  }

  setSelection(ids) {
    this.selection = new Set(ids);
    this._writeSelectionFlags();
    this._recolorEdges();
    this._updateLinks();
  }

  setHover(id) {
    this.hovered = id;
  }

  setShowCut(on) {
    this.showCut = on;
    if (this.cutLines) this.cutLines.visible = on;
  }

  _writeSelectionFlags() {
    const n = this.data.n;
    const any = this.selection.size > 0;
    for (const name of LAYERS) {
      const flags = this.flagTarget[name];
      for (let i = 0; i < n; i++) {
        const sel = this.selection.has(i);
        flags[i * 4 + 2] = sel ? 1 : 0;
        flags[i * 4 + 3] = any && !sel ? 1 : 0;
      }
    }
  }

  _markNodeAttrsDirty() {
    for (const name of LAYERS) {
      const a = this.layer[name].points.geometry.attributes;
      a.aColor.needsUpdate = true;
      a.aFlags.needsUpdate = true;
      a.aHover.needsUpdate = true;
      a.aSeed.needsUpdate = true;
    }
  }

  _recolorEdges() {
    const snap = this.snapshot;
    if (!snap) return;
    const sel = this.selection;
    const any = sel.size > 0;
    const cut = new Uint8Array(this.data.contact_edges.length);
    for (const idx of snap.cut_edges) cut[idx] = 1;

    const base = hexToRgb(COLORS.muted), risk = hexToRgb(COLORS.I), hi = hexToRgb(COLORS.text);
    const cool = hexToRgb('#8f9bb3'), gold = hexToRgb(COLORS.informed);

    // Contact: neutral gray; I–S edges (live transmission routes) in the infected hue
    {
      const { edges, eLines } = this.layer.contact;
      const col = eLines.geometry.attributes.color.array;
      edges.forEach(([a, b], k) => {
        let rgb = base, alpha = 0.17;
        if (cut[k]) alpha = 0;
        else {
          const sa = snap.state[a], sb = snap.state[b];
          if ((sa === 1 && sb === 0) || (sa === 0 && sb === 1)) { rgb = risk; alpha = 0.6; }
          if (any) {
            if (sel.has(a) || sel.has(b)) { alpha = Math.min(0.95, alpha * 2.6 + 0.15); if (rgb === base) rgb = hi; }
            else alpha *= 0.28;
          }
        }
        col.set([...rgb, alpha, ...rgb, alpha], k * 8);
      });
      eLines.geometry.attributes.color.needsUpdate = true;
    }
    // Social (directed): fades from source to target; informed→uninformed edges in gold
    {
      const { edges, eLines } = this.layer.social;
      const col = eLines.geometry.attributes.color.array;
      edges.forEach(([s, t], k) => {
        let rgb = cool, a0 = 0.17, a1 = 0.035;
        if (snap.informed[s] && !snap.informed[t]) { rgb = gold; a0 = 0.62; a1 = 0.14; }
        if (any) {
          if (sel.has(s) || sel.has(t)) { a0 = Math.min(0.95, a0 * 2.6 + 0.2); a1 = Math.min(0.6, a1 * 3 + 0.12); if (rgb === cool) rgb = hi; }
          else { a0 *= 0.28; a1 *= 0.28; }
        }
        col.set([...rgb, a0, ...rgb, a1], k * 8);
      });
      eLines.geometry.attributes.color.needsUpdate = true;
    }
  }

  _rebuildCut() {
    const snap = this.snapshot;
    const pos = new Float32Array(snap.cut_edges.length * 6);
    const P = this.local.contact;
    snap.cut_edges.forEach((idx, k) => {
      const [a, b] = this.data.contact_edges[idx];
      pos.set([P[a][0], 0, P[a][2], P[b][0], 0, P[b][2]], k * 6);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this.cutLines.geometry.dispose();
    this.cutLines.geometry = geo;
    this.cutLines.computeLineDistances();
    this.cutLines.visible = this.showCut;
  }

  _writePositions() {
    for (const name of LAYERS) {
      const P = this.local[name];
      const { points, edges, eLines } = this.layer[name];
      const pa = points.geometry.attributes.position.array;
      P.forEach((p, i) => pa.set(p, i * 3));
      points.geometry.attributes.position.needsUpdate = true;
      const ea = eLines.geometry.attributes.position.array;
      edges.forEach(([a, b], k) => ea.set([...P[a], ...P[b]], k * 6));
      eLines.geometry.attributes.position.needsUpdate = true;
    }
    if (this.snapshot) this._rebuildCut();
  }

  // World position of node i's copy in a layer
  worldPos(i, name, out = new THREE.Vector3()) {
    const p = this.local[name][i];
    return out.set(p[0], p[1], p[2]).add(this.groups[name].position);
  }

  _updateLinks() {
    const ids = [...this.selection];
    if (!ids.length || !this.data) { this.links.visible = false; return; }
    const arr = new Float32Array(ids.length * 6);
    const a = new THREE.Vector3(), b = new THREE.Vector3();
    ids.forEach((i, k) => {
      this.worldPos(i, 'social', a);
      this.worldPos(i, 'contact', b);
      arr.set([a.x, a.y, a.z, b.x, b.y, b.z], k * 6);
    });
    this.links.geometry.dispose();
    this.links.geometry = new LineSegmentsGeometry();
    this.links.geometry.setPositions(arr);
    this.links.computeLineDistances();
    // Many links at once become a wall of dashes; thin them out as the selection grows
    this.linkMaterial.opacity = ids.length > 12 ? Math.max(0.35, 0.9 - 0.012 * ids.length) : 0.9;
    this.links.visible = true;
  }

  _pulse(i, layer, hex) {
    this.pulses.push({ i, layer, rgb: hexToRgb(hex), t0: performance.now() });
  }

  // ------------------------------------------------------------ view modes ---

  setArrangement(mode) {
    if (mode === this.arrangement) return;
    this.arrangement = mode;
    const from = Object.fromEntries(LAYERS.map(n => [n, this.groups[n].position.clone()]));
    const to = Object.fromEntries(LAYERS.map(n => [n, new THREE.Vector3(...ARRANGEMENTS[mode][n])]));
    this._animate(900, k => {
      for (const n of LAYERS) this.groups[n].position.lerpVectors(from[n], to[n], k);
      this._updateLinks();
    });
    this.resetCamera(true);
  }

  setLayout(mode) {
    if (mode === this.layoutMode || !this.data) return;
    this.layoutMode = mode;
    const from = this.local.social.map(p => p.slice());
    const to = this.layouts[mode].social;
    this._animate(1100, k => {
      this.local.social.forEach((p, i) => {
        for (let d = 0; d < 3; d++) p[d] = from[i][d] + (to[i][d] - from[i][d]) * k;
      });
      this._writePositions();
      this._updateLinks();
    });
  }

  resetCamera(animate = true) {
    const toPos = new THREE.Vector3(...ARRANGEMENTS[this.arrangement].camera);
    const toTarget = new THREE.Vector3(0, 0, 0);
    if (!animate) {
      this.camera.position.copy(toPos);
      this.controls.target.copy(toTarget);
      this.controls.update();
      return;
    }
    const p0 = this.camera.position.clone(), t0 = this.controls.target.clone();
    this._animate(900, k => {
      this.camera.position.lerpVectors(p0, toPos, k);
      this.controls.target.lerpVectors(t0, toTarget, k);
    });
  }

  _animate(ms, fn) {
    this.anims.push({ t0: performance.now(), ms, fn });
  }

  // --------------------------------------------------------------- picking ---

  // Screen-space projection of every node copy: [{i, layer, x, y, rpx, depth}]
  _projectAll() {
    const rect = this.renderer.domElement.getBoundingClientRect();
    const pxPerUnit = rect.height / (2 * Math.tan(THREE.MathUtils.degToRad(FOV) / 2));
    const out = [];
    const v = new THREE.Vector3(), view = new THREE.Vector3();
    this.camera.updateMatrixWorld();
    for (const name of LAYERS) {
      for (let i = 0; i < this.data.n; i++) {
        this.worldPos(i, name, v);
        view.copy(v).applyMatrix4(this.camera.matrixWorldInverse);
        const depth = -view.z;
        if (depth <= 0) continue;
        v.project(this.camera);
        out.push({
          i, layer: name, depth,
          x: (v.x + 1) / 2 * rect.width + rect.left,
          y: (1 - v.y) / 2 * rect.height + rect.top,
          rpx: this.sizes[name][i] * pxPerUnit / depth,
        });
      }
    }
    return out;
  }

  // Nearest-to-camera node whose disc covers the point; failing that, the closest
  // disc within a few px (small nodes are hard to hit exactly).
  pick(clientX, clientY) {
    if (!this.data) return null;
    let covering = null, near = null, nearD = Infinity;
    for (const p of this._projectAll()) {
      const d = Math.hypot(p.x - clientX, p.y - clientY);
      if (d <= p.rpx) {
        if (!covering || p.depth < covering.depth) covering = p;
      } else if (d - p.rpx < 5 && d - p.rpx < nearD) {
        near = p; nearD = d - p.rpx;
      }
    }
    return covering ?? near;
  }

  nodesInRect(x0, y0, x1, y1) {
    if (!this.data) return [];
    const [l, r] = [Math.min(x0, x1), Math.max(x0, x1)];
    const [t, b] = [Math.min(y0, y1), Math.max(y0, y1)];
    const ids = new Set();
    for (const p of this._projectAll()) {
      if (p.x >= l && p.x <= r && p.y >= t && p.y <= b) ids.add(p.i);
    }
    return [...ids];
  }

  screenPos(i, layer) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    const v = this.worldPos(i, layer).project(this.camera);
    return { x: (v.x + 1) / 2 * rect.width, y: (1 - v.y) / 2 * rect.height, visible: v.z < 1 };
  }

  // ----------------------------------------------------------------- frame ---

  _resize() {
    const w = this.host.clientWidth, h = this.host.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.labelRenderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.linkMaterial.resolution.set(w, h);
    const scale = h * this.renderer.getPixelRatio() / (2 * Math.tan(THREE.MathUtils.degToRad(FOV) / 2));
    this.uScale = scale;
    this.pulseMat.uniforms.uScale.value = scale;
    if (this.layer) for (const name of LAYERS) this.layer[name].points.material.uniforms.uScale.value = scale;
  }

  _frame() {
    const dt = Math.min(this.clock.getDelta(), 0.1);
    const now = performance.now();

    this.anims = this.anims.filter(a => {
      const k = Math.min(1, (now - a.t0) / a.ms);
      a.fn(ease(k));
      return k < 1;
    });
    this.controls.update();

    if (this.layer) {
      for (const name of LAYERS) this.layer[name].points.material.uniforms.uScale.value = this.uScale;
      // Ease node colors / flags toward their targets so state changes read as transitions
      const kc = 1 - Math.exp(-dt * 9);
      let dirty = false;
      const approach = (cur, target) => {
        for (let j = 0; j < cur.length; j++) {
          const d = target[j] - cur[j];
          if (Math.abs(d) > 1e-3) { cur[j] += d * kc; dirty = true; } else cur[j] = target[j];
        }
      };
      for (const name of LAYERS) {
        approach(this.colorCur[name], this.colorTarget[name]);
        approach(this.flagCur[name], this.flagTarget[name]);
      }
      approach(this.seedCur, this.seedTarget);
      for (let i = 0; i < this.hoverCur.length; i++) {
        const target = i === this.hovered ? 1 : 0;
        const d = target - this.hoverCur[i];
        if (Math.abs(d) > 1e-3) { this.hoverCur[i] += d * (1 - Math.exp(-dt * 14)); dirty = true; } else this.hoverCur[i] = target;
      }
      if (dirty) this._markNodeAttrsDirty();
      this._framePulses(now);
    }

    if (this.links.visible) this.linkMaterial.dashOffset -= dt * 0.9;

    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
    if (this.onFrame) this.onFrame();
  }

  _framePulses(now) {
    const DUR = 900;
    this.pulses = this.pulses.filter(p => now - p.t0 < DUR);
    const geo = this.pulsePoints.geometry;
    const pos = geo.attributes.position.array, col = geo.attributes.aColor.array;
    const prog = geo.attributes.aProg.array, size = geo.attributes.aSize.array;
    const v = new THREE.Vector3();
    const count = Math.min(this.pulses.length, prog.length);
    for (let k = 0; k < count; k++) {
      const p = this.pulses[k];
      this.worldPos(p.i, p.layer, v);
      pos.set([v.x, v.y, v.z], k * 3);
      col.set(p.rgb, k * 3);
      prog[k] = (now - p.t0) / DUR;
      size[k] = this.sizes[p.layer][p.i];
    }
    geo.setDrawRange(0, count);
    for (const name of ['position', 'aColor', 'aProg', 'aSize']) geo.attributes[name].needsUpdate = true;
  }
}
