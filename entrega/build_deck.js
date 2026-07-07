// Conjecture Hunters — submission deck. Palette: spectral indigo/violet + mint accent.
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                 // 13.3 x 7.5
const W = 13.3, H = 7.5;
pres.author = "Conjecture Hunters";
pres.title = "Conjecture Hunters";

const C = {
  bg:     "141229",   // near-black indigo (dark slides)
  bg2:    "1E1B3A",
  ink:    "241B4A",   // dark violet (titles on light)
  violet: "6C5CE7",
  vlt:    "A29BFE",
  mint:   "16C79A",   // accent success (on light)
  mintlt: "31E6C0",   // accent on dark
  amber:  "F5A623",
  white:  "FFFFFF",
  body:   "3A3654",
  muted:  "8A86A6",
  mutedL: "B9B4D6",   // muted on dark
  card:   "F4F3FB",   // light violet tint card
  line:   "E4E1F3",
};

const S = () => ({ type: "outer", color: "1B1740", blur: 9, offset: 3, angle: 90, opacity: 0.16 });

function edge(sl, x1, y1, x2, y2, color, width) {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
              line: { color, width } };
  if ((x2 - x1) * (y2 - y1) < 0) o.flipV = true;
  sl.addShape(pres.shapes.LINE, o);
}
function node(sl, cx, cy, d, color, ring) {
  if (ring) sl.addShape(pres.shapes.OVAL, { x: cx - d/2 - 0.03, y: cy - d/2 - 0.03, w: d + 0.06, h: d + 0.06, fill: { color: ring } });
  sl.addShape(pres.shapes.OVAL, { x: cx - d/2, y: cy - d/2, w: d, h: d, fill: { color } });
}
// friendship graph F2 (two triangles sharing the hub)
function friendship(sl, cx, cy, s, edgeColor, nodeColor, hubColor) {
  const H_ = [cx, cy];
  const A = [cx - 1.05*s, cy - 0.62*s], B = [cx - 1.05*s, cy + 0.62*s];
  const D = [cx + 1.05*s, cy - 0.62*s], E = [cx + 1.05*s, cy + 0.62*s];
  const ew = Math.max(1.25, 2.2*s);
  [[H_,A],[H_,B],[A,B],[H_,D],[H_,E],[D,E]].forEach(([p,q]) => edge(sl, p[0],p[1],q[0],q[1], edgeColor, ew));
  const d = 0.30*s;
  [A,B,D,E].forEach(p => node(sl, p[0], p[1], d, nodeColor));
  node(sl, H_[0], H_[1], d*1.15, hubColor || nodeColor);
}
function card(sl, x, y, w, h, fill) {
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.10, fill: { color: fill || C.card }, shadow: S() });
}
function chip(sl, x, y, w, txt, fill, color) {
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.42, rectRadius: 0.21, fill: { color: fill } });
  sl.addText(txt, { x, y, w, h: 0.42, align: "center", valign: "middle", margin: 0, fontFace: "Arial", fontSize: 12, bold: true, color });
}
function kicker(sl, txt, color) {
  sl.addText(txt.toUpperCase(), { x: 0.7, y: 0.5, w: 11.9, h: 0.32, margin: 0, fontFace: "Arial",
    fontSize: 12.5, bold: true, color: color || C.violet, charSpacing: 3 });
}
function title(sl, txt, color) {
  sl.addText(txt, { x: 0.7, y: 0.82, w: 11.9, h: 0.8, margin: 0, fontFace: "Georgia", fontSize: 30, bold: true, color: color || C.ink });
}

// ---------------------------------------------------------------- Slide 1 — title
let s = pres.addSlide(); s.background = { color: C.bg };
// faint constellation
[[11.6,1.5],[12.4,2.5],[10.9,2.9],[12.7,4.6],[11.4,5.4],[10.4,4.2]].forEach((p,i,a)=>{
  if(i>0){const q=a[i-1]; edge(s,p[0],p[1],q[0],q[1], "33305C", 1.2);}
});
[[11.6,1.5],[12.4,2.5],[10.9,2.9],[12.7,4.6],[11.4,5.4],[10.4,4.2]].forEach(p=>node(s,p[0],p[1],0.16,"4A4680"));
// hero friendship graph
friendship(s, 10.9, 4.0, 1.15, C.violet, C.vlt, C.mintlt);
s.addText("CONJECTURE HUNTERS", { x: 0.8, y: 1.7, w: 8.6, h: 0.5, margin: 0, fontFace: "Arial", fontSize: 15, bold: true, color: C.mintlt, charSpacing: 4 });
s.addText("Evolving graphs that\nrefute open conjectures.", { x: 0.72, y: 2.2, w: 8.7, h: 2.0, margin: 0, fontFace: "Georgia", fontSize: 46, bold: true, color: C.white, lineSpacingMultiple: 0.98 });
s.addText("An evolutionary engine for spectral graph theory — LLM (Gemma) mutations, a Rust search core, and exact, un-gameable certificates. Running on AMD.",
  { x: 0.74, y: 4.5, w: 8.5, h: 1.0, margin: 0, fontFace: "Arial", fontSize: 16, color: C.mutedL, lineSpacingMultiple: 1.1 });
s.addText([
  { text: "AMD Developer Hackathon · ACT II", options: { color: C.vlt } },
  { text: "     Track 3 Unicorn  ·  Best AMD-Hosted Gemma", options: { color: C.muted } },
], { x: 0.74, y: 6.6, w: 11, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 12.5, bold: true });

// ---------------------------------------------------------------- Slide 2 — the idea
s = pres.addSlide(); s.background = { color: C.white };
kicker(s, "Why this is tractable");
title(s, "Refute = find one counterexample, then prove it");
s.addText([
  { text: "A conjecture claims ", options: {} },
  { text: "“for every graph G, P(G) holds.”", options: { italic: true, color: C.ink } },
  { text: "  Refuting it needs exactly ", options: {} },
  { text: "one", options: { bold: true, color: C.violet } },
  { text: " graph where P fails — plus a check that the failure is real. That asymmetry is a search problem with cheap, exact verification: ideal for evolution paired with an un-gameable certificate.", options: {} },
], { x: 0.72, y: 1.75, w: 11.9, h: 0.95, margin: 0, fontFace: "Arial", fontSize: 15.5, color: C.body, lineSpacingMultiple: 1.12 });

const steps = [
  ["1", "SEARCH", "Gemma (LLM) + parallel GA propose programs that print graphs.", C.violet],
  ["2", "EVALUATE", "A frozen exact evaluator scores the gap.  gap > 0  ⇔  counterexample.", C.mint],
  ["3", "CERTIFY", "Exact arithmetic proves the gap — immune to floating-point error.", C.amber],
];
let cx = 0.72, cw = 3.86, gap = 0.35, cy = 3.0, ch = 3.2;
steps.forEach((st, i) => {
  const x = cx + i * (cw + gap);
  card(s, x, cy, cw, ch, C.card);
  s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: cy + 0.38, w: 0.72, h: 0.72, fill: { color: st[3] } });
  s.addText(st[0], { x: x + 0.35, y: cy + 0.38, w: 0.72, h: 0.72, align: "center", valign: "middle", margin: 0, fontFace: "Georgia", fontSize: 26, bold: true, color: C.white });
  s.addText(st[1], { x: x + 0.35, y: cy + 1.32, w: cw - 0.7, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 17, bold: true, color: C.ink });
  s.addText(st[2], { x: x + 0.35, y: cy + 1.78, w: cw - 0.7, h: 1.2, margin: 0, fontFace: "Arial", fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.1 });
  if (i < 2) s.addText("→", { x: x + cw - 0.02, y: cy + 1.0, w: gap + 0.04, h: 0.6, align: "center", valign: "middle", margin: 0, fontFace: "Arial", fontSize: 22, bold: true, color: C.vlt });
});

// ---------------------------------------------------------------- Slide 3 — architecture
s = pres.addSlide(); s.background = { color: C.white };
kicker(s, "How it is built");
title(s, "One evolutionary loop, an exact backstop");
const bullets = [
  ["Gemma is the mutation operator", "It edits programs that print graphs, inside an OpenEvolve loop (best-of-N, ordinal ranking)."],
  ["Rust search core (rayon + faer)", "31× faster than Python, bit-parity to 1e-9 vs the frozen oracle — 3,212 graphs, 0 misclassifications."],
  ["Islands + Thompson bandit", "Discounted bandit steers effort across conjecture lanes; MAP-Elites keeps novelty."],
];
let by = 1.95;
bullets.forEach((b) => {
  s.addShape(pres.shapes.OVAL, { x: 0.75, y: by + 0.04, w: 0.16, h: 0.16, fill: { color: C.violet } });
  s.addText([
    { text: b[0] + "   ", options: { bold: true, color: C.ink } },
    { text: b[1], options: { color: C.body } },
  ], { x: 1.05, y: by - 0.12, w: 6.7, h: 0.9, margin: 0, fontFace: "Arial", fontSize: 14.5, lineSpacingMultiple: 1.08 });
  by += 1.15;
});
// evaluation cascade diagram (right)
const casc = [
  ["T1  ·  Validity", "reject malformed graphs fast", C.violet],
  ["T2  ·  Rust batch eval", "gap over thousands of graphs, in parallel", C.mint],
  ["T3  ·  Exact certificate", "the final, un-gameable verdict", C.amber],
];
let dx = 8.15, dw = 4.4, dy = 2.08, dh = 1.15, dg = 0.28;
s.addText("EVALUATION CASCADE", { x: dx, y: 1.66, w: dw, h: 0.3, margin: 0, fontFace: "Arial", fontSize: 12, bold: true, color: C.muted, charSpacing: 2 });
casc.forEach((t, i) => {
  const y = dy + i * (dh + dg);
  card(s, dx, y, dw, dh, C.card);
  s.addShape(pres.shapes.OVAL, { x: dx + 0.28, y: y + dh/2 - 0.16, w: 0.32, h: 0.32, fill: { color: t[2] } });
  s.addText(t[0], { x: dx + 0.78, y: y + 0.16, w: dw - 1.0, h: 0.42, margin: 0, fontFace: "Arial", fontSize: 15.5, bold: true, color: C.ink });
  s.addText(t[1], { x: dx + 0.78, y: y + 0.58, w: dw - 1.0, h: 0.42, margin: 0, fontFace: "Arial", fontSize: 12.5, color: C.body });
  if (i < 2) s.addText("▼", { x: dx + dw/2 - 0.2, y: y + dh - 0.04, w: 0.4, h: dg + 0.06, align: "center", valign: "middle", margin: 0, fontSize: 11, color: C.vlt });
});

// ---------------------------------------------------------------- Slide 4 — calibration
s = pres.addSlide(); s.background = { color: C.white };
kicker(s, "It works — calibration vertical", C.mint);
title(s, "Re-discovers SOTA in seconds; 86 tests green");
const stats = [
  ["0.6 s", "re-find the CAL-1 counterexample", "AMCS reference: 46 s", C.violet],
  ["< 1 s", "re-discover the n = 203 benchmark", "then certify it exactly", C.mint],
  ["86", "tests green", "exhaustive oracle, all 994 graphs n≤7", C.amber],
  ["10,056", "evaluations / second", "exact evaluator, parallel · 31.5× vs Python", C.violet],
];
let gx = 0.72, gw = 5.9, ggap = 0.36, gy = 2.0, gh = 1.9, gvy = 0.34;
stats.forEach((st, i) => {
  const x = gx + (i % 2) * (gw + ggap);
  const y = gy + Math.floor(i / 2) * (gh + gvy);
  card(s, x, y, gw, gh, C.card);
  s.addText(st[0], { x: x + 0.4, y: y + 0.28, w: gw - 0.8, h: 0.95, margin: 0, fontFace: "Georgia", fontSize: 44, bold: true, color: st[3] });
  s.addText(st[1], { x: x + 0.42, y: y + 1.18, w: gw - 0.8, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 15, bold: true, color: C.ink });
  s.addText(st[2], { x: x + 0.42, y: y + 1.5, w: gw - 0.8, h: 0.34, margin: 0, fontFace: "Arial", fontSize: 12, italic: true, color: C.muted });
});
s.addText("Every capability is re-runnable via a 7/7 scorecard — we always know if a change improves or regresses.",
  { x: 0.72, y: 6.55, w: 11.9, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 13, italic: true, color: C.body });

// ---------------------------------------------------------------- Slide 5 — HEADLINE
s = pres.addSlide(); s.background = { color: C.bg };
s.addText("THE RESULT", { x: 0.7, y: 0.55, w: 11.9, h: 0.32, margin: 0, fontFace: "Arial", fontSize: 12.5, bold: true, color: C.mintlt, charSpacing: 3 });
s.addText("We refuted an OPEN conjecture — and improved it", { x: 0.7, y: 0.92, w: 11.9, h: 0.7, margin: 0, fontFace: "Georgia", fontSize: 30, bold: true, color: C.white });
s.addText([
  { text: "Jia–Song (2018), Conjecture 3.8", options: { bold: true, color: C.vlt } },
  { text: "  — catalogued open in the Aouchiche–Rather 2024 survey.", options: { color: C.mutedL } },
], { x: 0.72, y: 1.75, w: 11.9, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 15 });
// claim card
card(s, 0.72, 2.4, 7.3, 3.9, C.bg2);
s.addText([
  { text: "ρ + ∂₂  ≥  ", options: { color: C.white } },
  { text: "n/(n−1) + (n−1 − √((n−1)²+8))/2", options: { color: C.vlt } },
], { x: 1.05, y: 2.75, w: 6.7, h: 0.6, margin: 0, fontFace: "Cambria", fontSize: 20, bold: true });
chip(s, 1.05, 3.45, 2.35, "✗  REFUTED", C.mint, "07231C");
s.addText([
  { text: "Counterexample: the infinite family  ", options: { color: C.mutedL } },
  { text: "K₁ ∨ 2Kᵣ", options: { color: C.mintlt, bold: true } },
  { text: ".  Smallest = the friendship graph  ", options: { color: C.mutedL } },
  { text: "F₂ (n=5)", options: { color: C.white, bold: true } },
  { text: ".", options: { color: C.mutedL } },
], { x: 1.05, y: 4.15, w: 6.6, h: 0.8, margin: 0, fontFace: "Arial", fontSize: 14.5, lineSpacingMultiple: 1.1 });
s.addText([
  { text: "ρ+∂₂(F₂) = 0.79844  <  0.80051 = B(5)", options: { breakLine: true, color: C.white, bold: true } },
  { text: "integer certificate:  59² = 3481 > 3456", options: { color: C.mintlt } },
], { x: 1.05, y: 5.05, w: 6.7, h: 1.0, margin: 0, fontFace: "Cambria", fontSize: 16, lineSpacingMultiple: 1.15 });
// F2 drawing on the right
s.addText("F₂  ·  the counterexample", { x: 8.4, y: 2.5, w: 4.2, h: 0.35, align: "center", margin: 0, fontFace: "Arial", fontSize: 13, bold: true, color: C.mutedL });
friendship(s, 10.5, 4.35, 1.35, C.violet, C.vlt, C.mintlt);
chip(s, 8.7, 6.35, 1.95, "exact proof", "2A2650", C.mintlt);
chip(s, 10.75, 6.35, 2.15, "independently verified", "2A2650", C.mintlt);

// ---------------------------------------------------------------- Slide 6 — rigor & honesty
s = pres.addSlide(); s.background = { color: C.white };
kicker(s, "Why you can trust it");
title(s, "Un-gameable — and honestly scoped");
card(s, 0.72, 1.95, 5.9, 4.4, C.card);
s.addText("UN-GAMEABLE", { x: 1.05, y: 2.2, w: 5.2, h: 0.34, margin: 0, fontFace: "Arial", fontSize: 13, bold: true, color: C.violet, charSpacing: 2 });
[
  "Exact arithmetic — zero floating-point in the verdict (sympy Sturm / mpmath + Weyl residual).",
  "An independent second method reproduces ρ+∂₂ < B(n).",
  "Reading the primary source exposed a transcription error in the published equality case (Kₙ−2e vs Kₙ−e) — documented.",
].forEach((t, i) => {
  const y = 2.66 + i * 1.12;
  s.addShape(pres.shapes.OVAL, { x: 1.05, y: y + 0.04, w: 0.15, h: 0.15, fill: { color: C.violet } });
  s.addText(t, { x: 1.33, y: y - 0.05, w: 5.0, h: 0.92, valign: "top", margin: 0, fontFace: "Arial", fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.08 });
});
card(s, 6.98, 1.95, 5.6, 4.4, C.card);
s.addText("HONEST SCOPE  +  IMPROVEMENT", { x: 7.31, y: 2.2, w: 5.0, h: 0.34, margin: 0, fontFace: "Arial", fontSize: 13, bold: true, color: C.mint, charSpacing: 2 });
[
  "Novelty stated as strong evidence, not certainty — a literature search is never exhaustive.",
  "Not just broken — improved: a corrected sharp bound B′(n); true minimizer = the balanced two-clique join.",
  "We state exactly where it fails: {n odd ≥ 5} ∪ {n even ≥ 10}.",
].forEach((t, i) => {
  const y = 2.66 + i * 1.12;
  s.addShape(pres.shapes.OVAL, { x: 7.31, y: y + 0.04, w: 0.15, h: 0.15, fill: { color: C.mint } });
  s.addText(t, { x: 7.59, y: y - 0.05, w: 4.7, h: 0.92, valign: "top", margin: 0, fontFace: "Arial", fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.08 });
});

// ---------------------------------------------------------------- Slide 7 — AMD + Gemma
s = pres.addSlide(); s.background = { color: C.white };
kicker(s, "The AMD + Gemma story", C.amber);
title(s, "Built to scale on MI300X");
const rows = [
  ["Parallelism", "MI300X runs 20+ conjecture lanes at once — the throughput that makes evolutionary search over graphs practical.", C.violet],
  ["Gemma in the loop", "Gemma is the mutation operator: Fireworks today, AMD-hosted MI300X for the prize (one line of config).", C.mint],
  ["Self-improvement", "LoRA (PatternBoost) fine-tunes Gemma on 6,100 harvested gap-improving edits — the system learns to mutate better.", C.amber],
];
let ry = 2.0, rh = 1.35, rgap = 0.28;
rows.forEach((r, i) => {
  const y = ry + i * (rh + rgap);
  card(s, 0.72, y, 11.86, rh, C.card);
  s.addShape(pres.shapes.OVAL, { x: 1.05, y: y + rh/2 - 0.28, w: 0.56, h: 0.56, fill: { color: r[2] } });
  s.addText(r[0], { x: 1.9, y: y + 0.2, w: 3.0, h: rh - 0.4, valign: "middle", margin: 0, fontFace: "Georgia", fontSize: 18, bold: true, color: C.ink });
  s.addText(r[1], { x: 5.0, y: y + 0.18, w: 7.3, h: rh - 0.36, valign: "middle", margin: 0, fontFace: "Arial", fontSize: 14, color: C.body, lineSpacingMultiple: 1.08 });
});

// ---------------------------------------------------------------- Slide 8 — closing
s = pres.addSlide(); s.background = { color: C.bg };
[[10.9,0.7],[11.8,1.15],[12.6,0.75],[12.0,1.7]].forEach((p,i,a)=>{ if(i>0){const q=a[i-1]; edge(s,p[0],p[1],q[0],q[1],"33305C",1.2);} });
[[10.9,0.7],[11.8,1.15],[12.6,0.75],[12.0,1.7]].forEach(p=>node(s,p[0],p[1],0.15,"4A4680"));
s.addText("Search finds it.\nExact arithmetic proves it.", { x: 0.9, y: 2.5, w: 11.6, h: 1.9, margin: 0, fontFace: "Georgia", fontSize: 40, bold: true, color: C.white, lineSpacingMultiple: 1.0 });
s.addText([
  { text: "One open conjecture refuted   ·   SOTA re-discovered in seconds   ·   86 tests   ·   exact certificates", options: { color: C.mutedL } },
], { x: 0.92, y: 4.55, w: 11.6, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 15 });
chip(s, 0.92, 5.35, 5.2, "github.com/Hawhaz/conjecture-hunters", C.violet, C.white);
s.addText("Conjecture Hunters  ·  AMD Developer Hackathon ACT II  ·  July 2026",
  { x: 0.92, y: 6.7, w: 11.6, h: 0.4, margin: 0, fontFace: "Arial", fontSize: 12.5, color: C.muted });

pres.writeFile({ fileName: process.argv[2] || "Conjecture_Hunters.pptx" }).then(f => console.log("WROTE", f));
