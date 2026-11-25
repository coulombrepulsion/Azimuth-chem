/* Ball-and-stick molecule picture with a per-pixel depth test (Atlas v2). §1 THEORY A bond must visibly leave one
   atom and enter the other, as in Chemcraft and in Azimuth's Compass. Painting flat circles over flat lines cannot show
   that: the junction of a rod and a sphere is their intersection curve, and which surface is in front changes along it.
   Here every pixel shows the surface nearest to the viewer. With orthographic rays along the view axis: sphere (c, r):
   z(p) = c_z + sqrt(r^2 - |p - c|^2) rod A->B, radius rho: the larger root t of |w_perp + t e_perp|^2 = rho^2, w =
   (p_x, p_y, 0) - A, k = (B - A)/|B - A|, e_perp = e_z - k_z k, w_perp = w - (w.k) k, accepted for 0 <= u = (w.k + t
   k_z)/|B - A| <= 1. A rod leaving its sphere in the screen plane meets it along the straight line x0 = sqrt(r^2 -
   rho^2) from the centre (both surfaces have equal depth there); no outline is drawn there, so the bond seems to grow
   out of the atom. Shading: I = AMBIENT + DIFFUSE * max(L.N, 0) with DIFFUSE = (1 - AMBIENT)/L_z, so a surface facing
   the viewer keeps its colour (I = 1 for N = e_z); a plateau |I - 1| < FLAT shows the exact element colour in the
   middle of a rod; a white Blinn-Phong highlight on rods only (atoms matte since 2026-10-23); a darker contour on the
   farther pixel wherever the depth jumps between two objects (one passes in front of another). §2 ALGORITHM 1. Scale
   the scene to device pixels (k = shown CSS width / viewBox width x devicePixelRatio) and by the supersampling factor
   ss. 2. For each object, for each pixel centre of its bounding box: the 2D test (inside the disk; within rho of the
   projected segment), then the analytic depth above; keep it if nearer than the depth buffer (owner, normal, colour).
   3. Shade the hit pixels; contour pixels x CONTOUR; average ss x ss blocks (premultiplied), divide by coverage for the
   canvas (straight alpha). 4. Draw the picture into a <canvas> held in a <foreignObject> of the SVG, at the place in
   the SVG where draw() is called (so SVG items before it lie behind the molecule and items after it in front). This is
   a JavaScript port of modules/compass/raster.py (Azimuth), same constants; it is tested against that file
   (tests/test_atlas_ballstick.py). §3 APPLICATIONS The model of the symmetry page (draw) and the before/after
   comparison (drawCompare): atom labels are drawn afterwards only for atoms whose centre is visible (result.visible),
   so a hidden atom's letter is not shown on top. §4 SPECIFICATION BallStick.rasterize(W, H, spheres, rods, ss) ->
   {rgba: Uint8ClampedArray (w*h*4, straight alpha) of the region x0..x0+w, y0..y0+h of the output that holds all
   objects (1 pixel of margin), owner: Int32Array (w*h*ss*ss: sphere index, -2 for a rod, -1 for nothing), x0, y0, w, h,
   ss} BallStick.rasterizeFull(W, H, spheres, rods, ss) -> Uint8ClampedArray W*H*4. spheres: [{x, y, z, r, c}] - pixels
   of the output, y down, z towards the viewer (same units), r > 0, c = CSS colour '#rrggbb' or [R, G, B]; rods: [{a:
   [x, y, z], b: [x, y, z], rho, ca, cb, u0, u1}] - colour ca below u0 and cb above u1 along the rod, linear blend
   between (u0 = u1: split). W, H positive integers, ss in {1, 2}; W*H*ss*ss <= MAX_PIXELS. Throws RangeError for a bad
   size, TypeError for non-finite coordinates. BallStick.draw(svg, spheres, rods, opts) -> {visible: Set of sphere
   indices} spheres and rods in viewBox units; opts.fast: true during animation and dragging (no supersampling now, a
   refined picture follows when idle). BallStick.ghost(svg, old, now, colours, radii, bonds, ink): the previous
   positions as in Compass (pale dashed atoms, dashed bonds, dotted trails), SVG elements. BallStick.scene(atoms, bonds,
   opts) -> {spheres, rods}: atoms [{x, y, z, r, c}], bonds [[i, j]]; one rod per bond from centre to centre, split into
   the atom colours with a blend over 0.4..0.6; rod radius opts.rho (default: r of the smaller atom of the pair x 0.27,
   at least 1.2 viewBox units). §5 CODE - below. §6 NOTES No dependency. The canvas is reused per SVG (a WeakMap), so
   draw() may clear the SVG with innerHTML = '' every frame. pointer-events: none on the canvas keeps rotation by
   dragging on the SVG. §7 TESTS tests/test_atlas_ballstick.py (Azimuth): analytic depth, the intersection line, a rod
   in front of / behind a sphere, colour of a viewer-facing surface, and pixel-for-pixel agreement with raster.py up to
   1 unit of rounding. §8' ROBUSTNESS Degenerate objects (r <= 0, zero-length or end-on rods) are skipped. Objects
   outside the picture are clipped. A hidden SVG (zero width) is drawn at the viewBox size x devicePixelRatio. */
(() => {
  'use strict';
  const MAX_PIXELS = 12e6;
  const n3 = Math.hypot(-1, -1, 1.6);
  const LIGHT = [-1 / n3, -1 / n3, 1.6 / n3];
  const hl = Math.hypot(LIGHT[0], LIGHT[1], LIGHT[2] + 1);
  const HALF = [LIGHT[0] / hl, LIGHT[1] / hl, (LIGHT[2] + 1) / hl];
  const AMBIENT = 0.42, DIFFUSE = (1 - AMBIENT) / LIGHT[2];
  const SPECULAR = 0.55, SHININESS = 60, FLAT = 0.05;
  const CONTOUR = 0.62, CONTOUR_STEP = 1.5;

  function rgb(c) {
    if (Array.isArray(c)) return c;
    const h = String(c).trim().replace('#', '');
    const s = h.length === 3 ? h.split('').map(x => x + x).join('') : h;
    return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
  }
  const finite = (...v) => v.every(Number.isFinite);

  /* Bounding box (in supersampled pixels) of everything, aligned to whole output pixels. */
  function bounds(W, H, ss, spheres, rods) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const grow = (x, y, r) => { x0 = Math.min(x0, x - r); y0 = Math.min(y0, y - r); x1 = Math.max(x1, x + r); y1 = Math.max(y1, y + r); };
    spheres.forEach(s => { if (s.r > 0) grow(s.x, s.y, s.r); });
    rods.forEach(r => { grow(r.a[0], r.a[1], r.rho); grow(r.b[0], r.b[1], r.rho); });
    if (!(x1 >= x0)) return null;
    const X0 = Math.max(0, Math.floor(x0) - 1), Y0 = Math.max(0, Math.floor(y0) - 1);
    const X1 = Math.min(W, Math.ceil(x1) + 2), Y1 = Math.min(H, Math.ceil(y1) + 2);
    return X1 > X0 && Y1 > Y0 ? [X0, Y0, X1, Y1] : null;
  }

  /* The picture of the region [X0, X1) x [Y0, Y1) of the output (see §2). */
  function rasterize(W, H, spheres, rods, ss) {
    if (!Number.isInteger(W) || !Number.isInteger(H) || W < 1 || H < 1 || !(ss === 1 || ss === 2))
      throw new RangeError('rasterize: bad size');
    if (W * H * ss * ss > MAX_PIXELS) throw new RangeError('rasterize: picture too large');
    spheres.forEach(s => { if (!finite(s.x, s.y, s.z, s.r)) throw new TypeError('rasterize: non-finite sphere'); });
    rods.forEach(r => { if (!finite(...r.a, ...r.b, r.rho)) throw new TypeError('rasterize: non-finite rod'); });
    const box = bounds(W, H, ss, spheres, rods);
    if (!box) return { rgba: new Uint8ClampedArray(0), x0: 0, y0: 0, w: 0, h: 0, owner: new Int32Array(0), ss };
    const [X0, Y0, X1, Y1] = box, BW = X1 - X0, BH = Y1 - Y0;
    const w = BW * ss, h = BH * ss, n = w * h, ox = X0 * ss, oy = Y0 * ss; // region in supersampled pixels
    const depth = new Float32Array(n).fill(-1e30), size = new Float32Array(n);
    const nx = new Float32Array(n), ny = new Float32Array(n), nz = new Float32Array(n);
    const cr = new Float32Array(n), cg = new Float32Array(n), cb = new Float32Array(n);
    const owner = new Int32Array(n).fill(-1), oid = new Int32Array(n).fill(-1);
    let id = 0;
    // -- spheres: front surface z = c_z + sqrt(r^2 - d^2)
    spheres.forEach((s, index) => {
      id++;
      const x = s.x * ss - ox, y = s.y * ss - oy, z = s.z * ss, r = s.r * ss, c = rgb(s.c);
      if (r <= 0) return;
      const i0 = Math.max(0, Math.floor(x - r)), i1 = Math.min(w, Math.ceil(x + r) + 1);
      const j0 = Math.max(0, Math.floor(y - r)), j1 = Math.min(h, Math.ceil(y + r) + 1);
      for (let j = j0; j < j1; j++) {
        const dy = j + 0.5 - y;
        for (let i = i0; i < i1; i++) {
          const dx = i + 0.5 - x, h2 = r * r - dx * dx - dy * dy;
          if (h2 <= 0) continue;
          const hz = Math.sqrt(h2), zz = z + hz, p = j * w + i;
          if (zz <= depth[p]) continue;
          depth[p] = zz; nx[p] = dx / r; ny[p] = dy / r; nz[p] = hz / r;
          cr[p] = c[0]; cg[p] = c[1]; cb[p] = c[2]; owner[p] = index; oid[p] = id; size[p] = r;
        }
      }
    });
    // -- rods: the nearer root of the ray-cylinder quadratic, 0 <= u <= 1
    rods.forEach(rd => {
      id++;
      const A = [rd.a[0] * ss - ox, rd.a[1] * ss - oy, rd.a[2] * ss], B = [rd.b[0] * ss - ox, rd.b[1] * ss - oy, rd.b[2] * ss], rho = rd.rho * ss;
      const ax = B[0] - A[0], ay = B[1] - A[1], az = B[2] - A[2], len = Math.hypot(ax, ay, az);
      if (rho <= 0 || len < 1e-9) return;
      const k = [ax / len, ay / len, az / len];
      const e = [-k[2] * k[0], -k[2] * k[1], 1 - k[2] * k[2]], qa = e[0] * e[0] + e[1] * e[1] + e[2] * e[2];
      if (qa < 1e-9) return; // end-on: covered by its atoms
      const ca = rgb(rd.ca), cbb = rgb(rd.cb), u0 = rd.u0 ?? 0.5, u1 = rd.u1 ?? 0.5;
      const ex = ax, ey = ay, e2 = ex * ex + ey * ey;
      const i0 = Math.max(0, Math.floor(Math.min(A[0], B[0]) - rho)), i1 = Math.min(w, Math.ceil(Math.max(A[0], B[0]) + rho) + 1);
      const j0 = Math.max(0, Math.floor(Math.min(A[1], B[1]) - rho)), j1 = Math.min(h, Math.ceil(Math.max(A[1], B[1]) + rho) + 1);
      for (let j = j0; j < j1; j++) {
        const py = j + 0.5;
        for (let i = i0; i < i1; i++) {
          const px = i + 0.5;
          // 2D: within rho of the projected segment (the rod's silhouette)
          const s = Math.min(1, Math.max(0, ((px - A[0]) * ex + (py - A[1]) * ey) / e2));
          const qx = px - A[0] - s * ex, qy = py - A[1] - s * ey;
          if (qx * qx + qy * qy > rho * rho) continue;
          const w0 = px - A[0], w1 = py - A[1], w2 = -A[2];
          const along = w0 * k[0] + w1 * k[1] + w2 * k[2];
          const p0 = w0 - along * k[0], p1 = w1 - along * k[1], p2 = w2 - along * k[2];
          const qb = p0 * e[0] + p1 * e[1] + p2 * e[2], qc = p0 * p0 + p1 * p1 + p2 * p2 - rho * rho;
          const disc = qb * qb - qa * qc;
          if (disc < 0) continue;
          const t = (-qb + Math.sqrt(disc)) / qa, u = (along + t * k[2]) / len;
          if (u < 0 || u > 1) continue;
          const p = j * w + i;
          if (t <= depth[p]) continue;
          const f = u1 > u0 ? Math.min(1, Math.max(0, (u - u0) / (u1 - u0))) : (u >= u0 ? 1 : 0);
          depth[p] = t; nx[p] = (p0 + t * e[0]) / rho; ny[p] = (p1 + t * e[1]) / rho; nz[p] = (p2 + t * e[2]) / rho;
          cr[p] = ca[0] * (1 - f) + cbb[0] * f; cg[p] = ca[1] * (1 - f) + cbb[1] * f; cb[p] = ca[2] * (1 - f) + cbb[2] * f;
          owner[p] = -2; oid[p] = id; size[p] = rho;
        }
      }
    });
    // -- contour: the farther pixel of a depth jump between two objects
    const dark = new Uint8Array(n);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const p = j * w + i;
      if (oid[p] < 0) continue;
      for (const q of [i + 1 < w ? p + 1 : -1, j + 1 < h ? p + w : -1]) {
        if (q < 0 || oid[q] < 0 || oid[q] === oid[p]) continue;
        const near = depth[p] > depth[q] ? size[p] : size[q];
        if (Math.abs(depth[p] - depth[q]) > Math.max(CONTOUR_STEP * ss, 0.25 * near)) dark[depth[p] < depth[q] ? p : q] = 1;
      }
    }
    // -- shading of each hit sample and averaging of ss x ss blocks (straight alpha for the canvas)
    const rgba = new Uint8ClampedArray(BW * BH * 4), a2 = ss * ss;
    for (let J = 0; J < BH; J++) for (let I = 0; I < BW; I++) {
      let r = 0, g = 0, b = 0, cov = 0;
      for (let dj = 0; dj < ss; dj++) for (let di = 0; di < ss; di++) {
        const p = (J * ss + dj) * w + I * ss + di;
        if (oid[p] < 0) continue;
        const lam = Math.max(0, nx[p] * LIGHT[0] + ny[p] * LIGHT[1] + nz[p] * LIGHT[2]);
        let shade = AMBIENT + DIFFUSE * lam - 1;
        shade = Math.sign(shade) * Math.max(Math.abs(shade) - FLAT, 0);
        const sp = owner[p] !== -2 ? 0 // atoms are matte: the highlight is on rods only
          : 255 * SPECULAR * Math.pow(Math.max(0, nx[p] * HALF[0] + ny[p] * HALF[1] + nz[p] * HALF[2]), SHININESS);
        const m = dark[p] ? CONTOUR : 1;
        r += Math.min(255, Math.max(0, (cr[p] * (1 + shade) + sp) * m));
        g += Math.min(255, Math.max(0, (cg[p] * (1 + shade) + sp) * m));
        b += Math.min(255, Math.max(0, (cb[p] * (1 + shade) + sp) * m));
        cov++;
      }
      if (!cov) continue;
      const o = (J * BW + I) * 4;
      rgba[o] = r / cov; rgba[o + 1] = g / cov; rgba[o + 2] = b / cov; rgba[o + 3] = Math.round(255 * cov / a2);
    }
    return { rgba, x0: X0, y0: Y0, w: BW, h: BH, owner, ss };
  }

  /* The whole W x H picture (tests and comparisons): the region placed into a transparent frame. */
  function rasterizeFull(W, H, spheres, rods, ss) {
    const res = rasterize(W, H, spheres, rods, ss), out = new Uint8ClampedArray(W * H * 4);
    for (let j = 0; j < res.h; j++) out.set(res.rgba.subarray(j * res.w * 4, (j + 1) * res.w * 4), ((res.y0 + j) * W + res.x0) * 4);
    return out;
  }

  function scene(atoms, bonds, opts = {}) {
    const spheres = atoms.map(a => ({ x: a.x, y: a.y, z: a.z, r: a.r, c: a.c }));
    const rods = bonds.map(([i, j]) => {
      const A = atoms[i], B = atoms[j];
      const rho = opts.rho ?? Math.max(1.2, Math.min(A.r, B.r) * 0.27);
      return { a: [A.x, A.y, A.z], b: [B.x, B.y, B.z], rho, ca: A.c, cb: B.c, u0: 0.4, u1: 0.6 };
    });
    return { spheres, rods };
  }

  const holders = new WeakMap(); // svg -> {fo, canvas, timer}
  function draw(svg, spheres, rods, opts = {}) {
    const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : { x: 0, y: 0, width: 460, height: 420 };
    let hold = holders.get(svg);
    if (!hold) {
      const fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
      const canvas = document.createElementNS('http://www.w3.org/1999/xhtml', 'canvas');
      canvas.style.cssText = 'display:block;width:100%;height:100%;pointer-events:none';
      fo.appendChild(canvas);
      hold = { fo, canvas, timer: 0 };
      holders.set(svg, hold);
    }
    const { fo, canvas } = hold;
    for (const [k, v] of Object.entries({ x: vb.x, y: vb.y, width: vb.width, height: vb.height })) fo.setAttribute(k, v);
    fo.setAttribute('pointer-events', 'none');
    svg.appendChild(fo);
    const shown = svg.getBoundingClientRect().width;
    const k = (shown > 0 ? shown / vb.width : 1) * (window.devicePixelRatio || 1);
    const W = Math.max(1, Math.round(vb.width * k)), H = Math.max(1, Math.round(vb.height * k));
    const px = s => ({ ...s, x: (s.x - vb.x) * k, y: (s.y - vb.y) * k, z: s.z * k, r: s.r * k });
    const sp = spheres.map(px);
    const rd = rods.map(r => ({ ...r, a: [(r.a[0] - vb.x) * k, (r.a[1] - vb.y) * k, r.a[2] * k], b: [(r.b[0] - vb.x) * k, (r.b[1] - vb.y) * k, r.b[2] * k], rho: r.rho * k }));
    const paint = ss => {
      const res = rasterize(W, H, sp, rd, ss);
      if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, W, H);
      if (res.w) ctx.putImageData(new ImageData(res.rgba, res.w, res.h), res.x0, res.y0);
      return res;
    };
    clearTimeout(hold.timer);
    const now = performance.now(), fast = opts.fast || now - (hold.last || -1e9) < 120; // animation or drag
    hold.last = now;
    const hiDpi = (window.devicePixelRatio || 1) >= 2;
    // while turning, smoothed too when the picture is small enough
    // to be painted twice as fine in time (≤ 0.6 Mpx after supersampling); a large one is refined once idle as before
    const small = W * H * 4 <= 600000;
    const res = paint(hiDpi ? 1 : fast && !small ? 1 : 2);
    if (fast && !hiDpi && !small) hold.timer = setTimeout(() => paint(2), 160); // refined once idle
    // atoms whose centre pixel shows the atom itself
    const visible = new Set();
    sp.forEach((s, i) => {
      const x = Math.floor(s.x * res.ss) - res.x0 * res.ss, y = Math.floor(s.y * res.ss) - res.y0 * res.ss, rw = res.w * res.ss;
      if (x >= 0 && y >= 0 && x < rw && y < res.h * res.ss && res.owner[y * rw + x] === i) visible.add(i);
    });
    return { visible };
  }

  /* The previous positions, in the style of Compass's optimization steps: pale atoms
     (fill 22 %, dashed edge 67 %, radius x 0.85), dashed bonds, thin dotted lines from
     each old position to the new one. old, now: [{x, y}] (viewBox units), colours: CSS
     colours of the atoms, radii: their radii, bonds: [[i, j]], ink: colour of the lines. */
  function ghost(svg, old, now, colours, radii, bonds, ink) {
    const NS = 'http://www.w3.org/2000/svg';
    const add = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); svg.appendChild(e); return e; };
    bonds.forEach(([i, j]) => add('line', { x1: old[i].x, y1: old[i].y, x2: old[j].x, y2: old[j].y, stroke: ink, 'stroke-width': 1.6,
      'stroke-dasharray': '5 4', 'stroke-linecap': 'round' }));
    old.forEach((a, i) => { const b = now[i]; if (b && Math.hypot(b.x - a.x, b.y - a.y) > 0.5)
      add('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: ink, 'stroke-opacity': 0.43, 'stroke-width': 1, 'stroke-dasharray': '1 3' }); });
    old.forEach((a, i) => add('circle', { cx: a.x, cy: a.y, r: radii[i] * 0.85, fill: colours[i], 'fill-opacity': 0.22, stroke: colours[i],
      'stroke-opacity': 0.67, 'stroke-width': 1.2, 'stroke-dasharray': '4 3' }));
  }

  const api = { rasterize, rasterizeFull, scene, draw, ghost, constants: { AMBIENT, DIFFUSE, SPECULAR, SHININESS, FLAT, CONTOUR, CONTOUR_STEP, LIGHT } };
  if (typeof window !== 'undefined') window.BallStick = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
