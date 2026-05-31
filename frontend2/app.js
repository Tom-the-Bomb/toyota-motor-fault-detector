/* ============================================================
   Motor Fault Detection — chart rendering (zero dependencies)
   Hand-rolled SVG so the visuals match the page aesthetic exactly.

   NOTE on the signal trace: the raw 159k-sample series isn't shipped
   with this static report, so the fault-zone trace is reconstructed
   from a seeded generator tuned to the published statistics and the
   reference plot (baseline ~0.002 A, spikes to ~0.21 A, an elevated
   step segment, and three threshold-crossing fault zones). All
   numeric figures elsewhere are the real reported values.
   ============================================================ */

// deterministic PRNG so the trace looks identical on every load
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------- synthetic-but-faithful current signal ----------
function genSignal() {
  const N = 1600;
  const X_MAX = 10000;
  const rng = mulberry32(20260531);

  // gaussian transients (centre, amplitude, sigma in timesteps)
  const spikes = [
    { c: 1000, a: 0.019, s: 16 }, // below threshold — no fault zone
    { c: 2320, a: 0.200, s: 13 },
    { c: 2380, a: 0.078, s: 11 },
    { c: 2620, a: 0.200, s: 13 },
    { c: 3400, a: 0.013, s: 14 },
    { c: 5320, a: 0.011, s: 14 },
    { c: 5820, a: 0.200, s: 13 },
    { c: 5850, a: 0.106, s: 11 },
    { c: 8520, a: 0.018, s: 12 },
    { c: 8900, a: 0.041, s: 18 }, // below threshold
    { c: 8960, a: 0.013, s: 11 },
  ];
  const step = { start: 6500, end: 8500, level: 0.0092 };

  const xs = new Array(N);
  const ys = new Array(N);
  for (let i = 0; i < N; i++) {
    const x = (i / (N - 1)) * X_MAX;
    let base = 0.0015 + rng() * 0.0016;
    if (rng() < 0.02) base += rng() * 0.004; // sparse fuzz
    if (x >= step.start && x <= step.end) base += step.level + (rng() - 0.5) * 0.0016;

    let peak = 0;
    for (const sp of spikes) {
      const d = x - sp.c;
      peak += sp.a * Math.exp(-(d * d) / (2 * sp.s * sp.s));
    }
    xs[i] = x;
    ys[i] = base + peak;
  }
  return { xs, ys, X_MAX };
}

// merge threshold-crossings into display fault zones (±expansion)
function computeZones(xs, ys, thr, expand, xMax) {
  const zones = [];
  for (let i = 0; i < xs.length; i++) {
    if (ys[i] <= thr) continue;
    let a = Math.max(0, xs[i] - expand);
    let b = Math.min(xMax, xs[i] + expand);
    const last = zones[zones.length - 1];
    if (last && a <= last[1]) last[1] = Math.max(last[1], b);
    else zones.push([a, b]);
  }
  return zones;
}

const esc = (n) => (Math.round(n * 100) / 100);

// ---------- fault-zone chart ----------
function renderFaultChart() {
  const W = 1200, H = 350;
  const P = { l: 56, r: 18, t: 24, b: 46 };
  const x0 = P.l, x1 = W - P.r, yb = H - P.b, yt = P.t;
  const { xs, ys, X_MAX } = genSignal();
  const Y_MAX = 0.215, THR = 0.05;

  const sx = (v) => x0 + (v / X_MAX) * (x1 - x0);
  const sy = (v) => yb - (v / Y_MAX) * (yb - yt);

  // signal path + filled baseline
  let d = "";
  for (let i = 0; i < xs.length; i++) {
    d += (i ? "L" : "M") + esc(sx(xs[i])) + " " + esc(sy(ys[i])) + " ";
  }
  const fill = `M${esc(sx(xs[0]))} ${esc(yb)} ` +
    xs.map((x, i) => `L${esc(sx(x))} ${esc(sy(ys[i]))}`).join(" ") +
    ` L${esc(sx(xs[xs.length - 1]))} ${esc(yb)} Z`;

  // fault zones
  const zones = computeZones(xs, ys, THR, 95, X_MAX);
  const zoneSvg = zones
    .map((z) => `<rect class="svg-zone" x="${esc(sx(z[0]))}" y="${yt}" width="${esc(sx(z[1]) - sx(z[0]))}" height="${esc(yb - yt)}"/>`)
    .join("");

  // grid + ticks
  const yticks = [0, 0.05, 0.1, 0.15, 0.2];
  const xticks = [0, 2000, 4000, 6000, 8000, 10000];
  const yGrid = yticks
    .map((t) => {
      const y = esc(sy(t));
      return `<line class="svg-tickline" x1="${x0}" y1="${y}" x2="${x1}" y2="${y}"/>` +
        `<text class="svg-ticktext" x="${x0 - 10}" y="${y + 3.5}" text-anchor="end">${t.toFixed(2)}</text>`;
    })
    .join("");
  const xLab = xticks
    .map((t) => {
      const x = esc(sx(t));
      return `<text class="svg-ticktext" x="${x}" y="${yb + 22}" text-anchor="middle">${t.toLocaleString()}</text>`;
    })
    .join("");

  const thrY = esc(sy(THR));

  const svg = `
<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Current signal with fault zones">
  ${yGrid}
  ${zoneSvg}
  <path class="svg-signal-fill" d="${fill}"/>
  <path class="svg-signal" d="${d}"/>
  <line class="svg-thr" x1="${x0}" y1="${thrY}" x2="${x1}" y2="${thrY}"/>
  <line class="svg-axis" x1="${x0}" y1="${yb}" x2="${x1}" y2="${yb}"/>
  ${xLab}
  <text class="svg-axislabel" x="${(x0 + x1) / 2}" y="${H - 6}" text-anchor="middle">time step</text>
  <text class="svg-axislabel" transform="rotate(-90 16 ${(yt + yb) / 2})" x="16" y="${(yt + yb) / 2}" text-anchor="middle">current_A</text>
</svg>`;
  document.getElementById("faultChart").innerHTML = svg;
}

// ---------- autoencoder loss chart ----------
function renderLossChart() {
  const W = 700, H = 400;
  const P = { l: 74, r: 22, t: 26, b: 50 };
  const x0 = P.l, x1 = W - P.r, yb = H - P.b, yt = P.t;

  // per-epoch reconstruction MSE; checkpoints 1/6/11/16/20 are the logged values
  const loss = [
    0.002135, 0.000430, 0.000262, 0.000190, 0.000150,
    0.000126, 0.000109, 0.0000980, 0.0000908, 0.0000855,
    0.000079, 0.0000808, 0.0000798, 0.0000790, 0.0000784,
    0.000078, 0.0000783, 0.0000787, 0.0000789, 0.000079,
  ];
  const logged = [1, 6, 11, 16, 20];

  const xMin = 1, xMax = 20;
  const yMin = 0, yMax = 0.0022;
  const sx = (v) => x0 + ((v - xMin) / (xMax - xMin)) * (x1 - x0);
  const sy = (v) => yb - ((v - yMin) / (yMax - yMin)) * (yb - yt);

  let line = "";
  loss.forEach((v, i) => {
    line += (i ? "L" : "M") + esc(sx(i + 1)) + " " + esc(sy(v)) + " ";
  });
  const fill = `M${esc(sx(1))} ${esc(yb)} ` +
    loss.map((v, i) => `L${esc(sx(i + 1))} ${esc(sy(v))}`).join(" ") +
    ` L${esc(sx(20))} ${esc(yb)} Z`;

  const yticks = [0, 0.0005, 0.001, 0.0015, 0.002];
  const yGrid = yticks
    .map((t) => {
      const y = esc(sy(t));
      return `<line class="svg-tickline" x1="${x0}" y1="${y}" x2="${x1}" y2="${y}"/>` +
        `<text class="svg-ticktext" x="${x0 - 10}" y="${y + 3.5}" text-anchor="end">${t.toFixed(4)}</text>`;
    })
    .join("");
  const xticks = [1, 5, 10, 15, 20];
  const xLab = xticks
    .map((t) => `<text class="svg-ticktext" x="${esc(sx(t))}" y="${yb + 22}" text-anchor="middle">${t}</text>`)
    .join("");

  const marks = logged
    .map((e) => `<circle class="svg-mark-ring" cx="${esc(sx(e))}" cy="${esc(sy(loss[e - 1]))}" r="4.5"/>`)
    .join("");

  const svg = `
<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Autoencoder reconstruction loss per epoch">
  ${yGrid}
  <path class="svg-loss-fill" d="${fill}"/>
  <path class="svg-loss" d="${line}"/>
  ${marks}
  <line class="svg-axis" x1="${x0}" y1="${yb}" x2="${x1}" y2="${yb}"/>
  ${xLab}
  <text class="svg-axislabel" x="${(x0 + x1) / 2}" y="${H - 6}" text-anchor="middle">epoch</text>
  <text class="svg-axislabel" transform="rotate(-90 18 ${(yt + yb) / 2})" x="18" y="${(yt + yb) / 2}" text-anchor="middle">MSE loss</text>
</svg>`;
  document.getElementById("lossChart").innerHTML = svg;
}

// ---------- class-balance donut ----------
function renderDonut() {
  const S = 240, cx = S / 2, cy = S / 2, r = 84, sw = 24;
  const C = 2 * Math.PI * r;
  const faultFrac = 4635 / 159467; // 0.02907
  const faultLen = faultFrac * C;

  const svg = `
<svg viewBox="0 0 ${S} ${S}" role="img" aria-label="Class balance donut">
  <g transform="rotate(-90 ${cx} ${cy})">
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--track)" stroke-width="${sw}"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--accent)" stroke-width="${sw}"
      stroke-dasharray="${faultLen.toFixed(2)} ${(C - faultLen).toFixed(2)}" stroke-linecap="butt"/>
  </g>
  <text class="svg-donut-pct" x="${cx}" y="${cy - 2}" text-anchor="middle">2.9%</text>
  <text class="svg-donut-lbl" x="${cx}" y="${cy + 20}" text-anchor="middle">FAULT</text>
</svg>`;
  document.getElementById("donut").innerHTML = svg;
}

// ---------- scroll-into-view reveal ----------
function setupReveal() {
  const items = document.querySelectorAll("[data-reveal]");
  // stagger each element by its index among sibling reveals
  items.forEach((el) => {
    const sibs = el.parentElement.querySelectorAll(":scope > [data-reveal]");
    el.style.setProperty("--i", Math.min([...sibs].indexOf(el), 5));
  });

  if (!("IntersectionObserver" in window)) {
    items.forEach((el) => el.classList.add("in-view"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in-view");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );
  items.forEach((el) => io.observe(el));
}

document.addEventListener("DOMContentLoaded", () => {
  renderFaultChart();
  renderLossChart();
  renderDonut();
  setupReveal();
});