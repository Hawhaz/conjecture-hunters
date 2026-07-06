#!/usr/bin/env python3
"""
build_dashboard.py

Lee un CSV de logs del GA (esquema: corrida,gen,best_gap,best_g6,n,evento,epoch)
y genera dashboard/dashboard_baked.html: un HTML único, autocontenido, con los
datos incrustados como JSON. Se puede abrir directamente desde el disco (file://)
sin servidor ni fetch.

Uso:
    python build_dashboard.py
    python build_dashboard.py --csv ruta/a/otro_log.csv
    python build_dashboard.py --csv ruta/a/otro_log.csv --out ruta/salida.html

Solo usa la biblioteca estándar (csv, json, argparse, pathlib).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REQUIRED_HEADER = ["corrida", "gen", "best_gap", "best_g6", "n", "evento", "epoch"]

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = SCRIPT_DIR.parent / "calibracion" / "runs" / "ga_log_sin_seeds.csv"
DEFAULT_OUT = SCRIPT_DIR / "dashboard_baked.html"

COUNTEREXAMPLE_THRESHOLD = 1e-9


def parse_args():
    p = argparse.ArgumentParser(
        description="Genera un dashboard HTML autocontenido con los datos de un CSV del GA incrustados."
    )
    p.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV),
        help=f"Ruta al CSV de logs del GA (default: {DEFAULT_CSV})",
    )
    p.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_OUT),
        help=f"Ruta de salida del HTML generado (default: {DEFAULT_OUT})",
    )
    return p.parse_args()


def load_rows(csv_path: Path):
    """Lee el CSV y devuelve una lista de dicts con los tipos ya convertidos."""
    if not csv_path.exists():
        print(f"ERROR: no existe el archivo CSV: {csv_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print(f"ERROR: el CSV está vacío: {csv_path}", file=sys.stderr)
            sys.exit(1)

        header = [h.strip() for h in header]
        missing = [c for c in REQUIRED_HEADER if c not in header]
        if missing:
            print(
                f"ERROR: el CSV no tiene el header esperado. Faltan columnas: {missing}\n"
                f"Header encontrado: {header}\n"
                f"Header esperado:   {REQUIRED_HEADER}",
                file=sys.stderr,
            )
            sys.exit(1)

        idx = {name: header.index(name) for name in REQUIRED_HEADER}
        line_no = 1
        skipped = 0
        for raw in reader:
            line_no += 1
            if not raw or (len(raw) == 1 and raw[0].strip() == ""):
                continue
            if len(raw) < len(header):
                skipped += 1
                continue
            try:
                corrida = int(raw[idx["corrida"]])
                gen = int(raw[idx["gen"]])
                best_gap = float(raw[idx["best_gap"]])
                n = int(raw[idx["n"]]) if raw[idx["n"]].strip() != "" else None
                epoch = int(raw[idx["epoch"]]) if raw[idx["epoch"]].strip() != "" else None
            except ValueError:
                skipped += 1
                continue

            rows.append(
                {
                    "corrida": corrida,
                    "gen": gen,
                    "best_gap": best_gap,
                    "best_g6": raw[idx["best_g6"]].strip(),
                    "n": n,
                    "evento": raw[idx["evento"]].strip(),
                    "epoch": epoch,
                }
            )

        if skipped:
            print(f"Aviso: se omitieron {skipped} filas malformadas.", file=sys.stderr)

    return rows


def build_summary(rows):
    """Calcula el resumen por carril (corrida) y las KPIs globales, en Python,
    como sanity-check adicional (el HTML también las recalcula en JS a partir
    de los datos crudos, pero dejamos esto para validar en consola)."""
    by_lane = {}
    for r in rows:
        by_lane.setdefault(r["corrida"], []).append(r)
    for arr in by_lane.values():
        arr.sort(key=lambda r: r["gen"])

    summary = []
    for corrida, arr in sorted(by_lane.items()):
        best_row = max(arr, key=lambda r: r["best_gap"])
        first_cross = next((r for r in arr if r["best_gap"] > COUNTEREXAMPLE_THRESHOLD), None)
        last = arr[-1]
        summary.append(
            {
                "corrida": corrida,
                "bestGap": best_row["best_gap"],
                "finalGap": last["best_gap"],
                "firstGen": first_cross["gen"] if first_cross else None,
                "n": best_row["n"],
                "bestG6": best_row["best_g6"],
                "counterexample": first_cross is not None,
            }
        )

    lanes_crossed = [s for s in summary if s["counterexample"]]
    kpi = {
        "lanes": len(summary),
        "bestOverall": max((s["bestGap"] for s in summary), default=None),
        "laneCrossedCount": len(lanes_crossed),
        "firstGenAny": min((s["firstGen"] for s in lanes_crossed), default=None),
        "minN": min((s["n"] for s in lanes_crossed if s["n"] is not None), default=None),
    }
    return summary, kpi


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard GA (baked) — Cazador de contraejemplos</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#0b0f14;
    --bg-panel:#121821;
    --bg-panel-2:#0f151d;
    --border:#232d3a;
    --text:#e6edf3;
    --text-dim:#8b98a9;
    --accent:#4fa8ff;
    --accent-2:#7ee2b8;
    --green:#28c76f;
    --green-bg:rgba(40,199,111,0.14);
    --green-border:rgba(40,199,111,0.55);
    --red:#ff6b6b;
    --yellow:#f2c94c;
    --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  *{box-sizing:border-box;}
  html,body{
    margin:0; padding:0;
    background:var(--bg);
    color:var(--text);
    font-family:var(--sans);
    min-height:100vh;
  }
  body{ padding:20px; }
  h1{ font-size:1.4rem; margin:0 0 4px 0; font-weight:600; letter-spacing:0.2px; }
  .subtitle{ color:var(--text-dim); font-size:0.85rem; margin:0 0 18px 0; }
  .layout{ display:flex; flex-direction:column; gap:16px; max-width:1500px; margin:0 auto; }

  .loader{
    border:2px dashed var(--border);
    border-radius:10px;
    padding:16px 18px;
    background:var(--bg-panel);
    display:flex;
    align-items:center;
    gap:14px;
    flex-wrap:wrap;
  }
  .loader .drop-label{ color:var(--text-dim); font-size:0.85rem; flex:1 1 260px; }
  .loader .drop-label b{ color:var(--text); }
  .file-btn{
    background:var(--accent); color:#04101f; border:none;
    padding:9px 16px; border-radius:7px; font-weight:600; font-size:0.85rem; cursor:pointer;
  }
  .file-btn:hover{ filter:brightness(1.08); }
  #fileInput{ display:none; }
  .status-pill{
    font-family:var(--mono); font-size:0.75rem; padding:5px 10px; border-radius:20px;
    background:var(--bg-panel-2); border:1px solid var(--border); color:var(--text-dim); white-space:nowrap;
  }
  .status-pill.ok{ color:var(--green); border-color:var(--green-border); }
  .status-pill.err{ color:var(--red); border-color:rgba(255,107,107,.5); }

  .kpi-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }
  .kpi-card{ background:var(--bg-panel); border:1px solid var(--border); border-radius:10px; padding:14px 16px; position:relative; overflow:hidden; }
  .kpi-card .label{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.6px; color:var(--text-dim); margin-bottom:6px; }
  .kpi-card .value{ font-size:1.6rem; font-weight:700; font-family:var(--mono); line-height:1.15; }
  .kpi-card .sub{ font-size:0.72rem; color:var(--text-dim); margin-top:4px; }
  .kpi-card.highlight{ border-color:var(--green-border); background:linear-gradient(180deg, var(--green-bg), var(--bg-panel)); }
  .kpi-card.highlight .value{ color:var(--green); }
  .kpi-card.neutral .value{ color:var(--accent); }

  .panel{ background:var(--bg-panel); border:1px solid var(--border); border-radius:10px; padding:16px; }
  .panel h2{ font-size:0.95rem; margin:0 0 12px 0; font-weight:600; display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap; }
  .panel h2 .hint{ font-weight:400; font-size:0.72rem; color:var(--text-dim); }
  .chart-wrap{ position:relative; height:420px; }

  .table-scroll{ overflow-x:auto; }
  table{ width:100%; border-collapse:collapse; font-size:0.82rem; }
  thead th{
    text-align:left; padding:9px 10px; background:var(--bg-panel-2); color:var(--text-dim);
    font-weight:600; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.5px;
    border-bottom:1px solid var(--border); cursor:pointer; white-space:nowrap; user-select:none;
  }
  thead th:hover{ color:var(--text); }
  thead th .arrow{ display:inline-block; margin-left:4px; opacity:0.5; font-size:0.65rem; }
  thead th.sorted .arrow{ opacity:1; color:var(--accent); }
  tbody td{ padding:8px 10px; border-bottom:1px solid var(--border); font-family:var(--mono); white-space:nowrap; }
  tbody tr:hover{ background:rgba(255,255,255,0.03); }
  tbody tr.counterexample{ background:var(--green-bg); }
  tbody tr.counterexample:hover{ background:rgba(40,199,111,0.22); }
  tbody tr.counterexample td:first-child{ border-left:3px solid var(--green); }
  td.g6-cell{ max-width:220px; overflow:hidden; text-overflow:ellipsis; cursor:pointer; position:relative; }
  td.g6-cell:hover{ color:var(--accent); }
  td.g6-cell.copied::after{
    content:"copiado!"; position:absolute; right:6px; top:50%; transform:translateY(-50%);
    background:var(--green); color:#04160d; font-family:var(--sans); font-size:0.65rem; font-weight:700;
    padding:2px 6px; border-radius:4px;
  }
  .badge{ display:inline-block; padding:2px 7px; border-radius:4px; font-size:0.72rem; font-weight:700; }
  .badge.yes{ background:var(--green); color:#04160d; }
  .badge.no{ background:var(--bg-panel-2); color:var(--text-dim); border:1px solid var(--border); }

  .empty-state{ color:var(--text-dim); font-size:0.85rem; text-align:center; padding:40px 20px; }
  footer{ text-align:center; color:var(--text-dim); font-size:0.72rem; margin-top:6px; padding-bottom:10px; }
  ::-webkit-scrollbar{ height:8px; width:8px; }
  ::-webkit-scrollbar-track{ background:var(--bg-panel-2); }
  ::-webkit-scrollbar-thumb{ background:var(--border); border-radius:4px; }

  @media (max-width: 640px){
    .chart-wrap{ height:320px; }
    h1{ font-size:1.15rem; }
  }
</style>
</head>
<body>
<div class="layout">
  <div>
    <h1>Dashboard GA (baked) — Cazador de contraejemplos</h1>
    <p class="subtitle">Datos incrustados desde <b>__CSV_NAME__</b> al momento de generar este archivo. gap &gt; 0 ⇔ contraejemplo encontrado.</p>
  </div>

  <div class="loader" id="loader">
    <input type="file" id="fileInput" accept=".csv,text/csv">
    <button class="file-btn" id="pickBtn">Cargar otro CSV…</button>
    <span class="drop-label">o arrastrá un <b>ga_log*.csv</b> aquí para reemplazar los datos incrustados (mismo esquema de columnas).</span>
    <span class="status-pill ok" id="statusPill">datos incrustados listos</span>
  </div>

  <div class="kpi-grid" id="kpiGrid"></div>

  <div class="panel">
    <h2>Evolución de best_gap por carril (corrida) <span class="hint">línea gruesa en gap = 0 → umbral de contraejemplo</span></h2>
    <div class="chart-wrap">
      <canvas id="gapChart"></canvas>
    </div>
    <div class="empty-state" id="chartEmpty" style="display:none;">Sin datos todavía. Cargá un CSV para ver el gráfico.</div>
  </div>

  <div class="panel">
    <h2>Resumen por carril <span class="hint">click en encabezado para ordenar · click en best_g6 para copiar</span></h2>
    <div class="table-scroll">
      <table id="summaryTable">
        <thead>
          <tr>
            <th data-key="corrida">corrida<span class="arrow">▲▼</span></th>
            <th data-key="bestGap">mejor gap<span class="arrow">▲▼</span></th>
            <th data-key="finalGap">gap final<span class="arrow">▲▼</span></th>
            <th data-key="firstGen">1ª gen contraejemplo<span class="arrow">▲▼</span></th>
            <th data-key="n">n<span class="arrow">▲▼</span></th>
            <th data-key="counterexample">contraejemplo<span class="arrow">▲▼</span></th>
            <th data-key="bestG6">best_g6<span class="arrow">▲▼</span></th>
          </tr>
        </thead>
        <tbody id="summaryBody"></tbody>
      </table>
    </div>
    <div class="empty-state" id="tableEmpty" style="display:none;">Sin datos todavía.</div>
  </div>

  <footer>Dashboard estático (baked) · Chart.js vía cdnjs · sin almacenamiento local · generado por build_dashboard.py</footer>
</div>

<script>
// ---------------------------------------------------------------------
// Datos incrustados al momento de build (bake). No requiere fetch ni servidor.
// ---------------------------------------------------------------------
var BAKED_ROWS = __ROWS_JSON__;

(function(){
  "use strict";

  var COUNTEREXAMPLE_THRESHOLD = 1e-9;

  var state = {
    rows: [],
    byLane: new Map(),
    summary: [],
    sortKey: "corrida",
    sortDir: 1,
    chart: null
  };

  var LANE_COLORS = [
    "#4fa8ff", "#7ee2b8", "#f2c94c", "#ff6b6b", "#c792ea",
    "#ff9f43", "#54a0ff", "#1dd1a1", "#ee5a6f", "#a29bfe",
    "#00d2d3", "#feca57", "#48dbfb", "#ff6b81", "#576574",
    "#00b894", "#e17055", "#0984e3", "#fdcb6e", "#6c5ce7"
  ];

  function laneColor(corrida){
    var idx = Math.abs(parseInt(corrida, 10)) % LANE_COLORS.length;
    return LANE_COLORS[idx];
  }

  // ---------- CSV parsing (used only if the user drags in a replacement file) ----------
  function parseCSV(text){
    var rows = [];
    var i = 0, len = text.length;
    var field = "", row = [];
    var inQuotes = false;

    function pushField(){ row.push(field); field = ""; }
    function pushRow(){ pushField(); rows.push(row); row = []; }

    while (i < len){
      var c = text[i];
      if (inQuotes){
        if (c === '"'){
          if (text[i+1] === '"'){ field += '"'; i += 2; continue; }
          inQuotes = false; i++; continue;
        } else { field += c; i++; continue; }
      } else {
        if (c === '"'){ inQuotes = true; i++; continue; }
        if (c === ','){ pushField(); i++; continue; }
        if (c === '\\r'){ i++; continue; }
        if (c === '\\n'){ pushRow(); i++; continue; }
        field += c; i++; continue;
      }
    }
    if (field.length > 0 || row.length > 0){ pushRow(); }
    rows = rows.filter(function(r){ return !(r.length === 1 && r[0] === ""); });
    return rows;
  }

  function rowsToObjects(rows){
    if (rows.length === 0) return [];
    var header = rows[0].map(function(h){ return h.trim(); });
    var idx = {
      corrida: header.indexOf("corrida"),
      gen: header.indexOf("gen"),
      best_gap: header.indexOf("best_gap"),
      best_g6: header.indexOf("best_g6"),
      n: header.indexOf("n"),
      evento: header.indexOf("evento"),
      epoch: header.indexOf("epoch")
    };
    var missing = Object.keys(idx).filter(function(k){ return idx[k] === -1; });
    if (missing.length){
      throw new Error("Header inválido. Faltan columnas: " + missing.join(", "));
    }
    var out = [];
    for (var i = 1; i < rows.length; i++){
      var r = rows[i];
      if (r.length < header.length) continue;
      var corrida = parseInt(r[idx.corrida], 10);
      var gen = parseInt(r[idx.gen], 10);
      var best_gap = parseFloat(r[idx.best_gap]);
      if (isNaN(corrida) || isNaN(gen) || isNaN(best_gap)) continue;
      out.push({
        corrida: corrida,
        gen: gen,
        best_gap: best_gap,
        best_g6: (r[idx.best_g6] || "").trim(),
        n: parseInt(r[idx.n], 10),
        evento: (r[idx.evento] || "").trim(),
        epoch: parseInt(r[idx.epoch], 10)
      });
    }
    return out;
  }

  // ---------- Data processing ----------
  function buildLanes(rows){
    var byLane = new Map();
    rows.forEach(function(r){
      if (!byLane.has(r.corrida)) byLane.set(r.corrida, []);
      byLane.get(r.corrida).push(r);
    });
    byLane.forEach(function(arr){ arr.sort(function(a,b){ return a.gen - b.gen; }); });
    return byLane;
  }

  function buildSummary(byLane){
    var summary = [];
    byLane.forEach(function(arr, corrida){
      var bestGap = -Infinity;
      var bestRow = null;
      var firstCross = null;
      arr.forEach(function(r){
        if (r.best_gap > bestGap){ bestGap = r.best_gap; bestRow = r; }
        if (firstCross === null && r.best_gap > COUNTEREXAMPLE_THRESHOLD){
          firstCross = r;
        }
      });
      var last = arr[arr.length - 1];
      summary.push({
        corrida: corrida,
        bestGap: bestGap,
        finalGap: last ? last.best_gap : null,
        firstGen: firstCross ? firstCross.gen : null,
        n: bestRow ? bestRow.n : (last ? last.n : null),
        bestG6: bestRow ? bestRow.best_g6 : (last ? last.best_g6 : ""),
        counterexample: firstCross !== null,
        rowCount: arr.length
      });
    });
    return summary;
  }

  function computeKPIs(rows, summary){
    var lanes = summary.length;
    var bestOverall = -Infinity;
    summary.forEach(function(s){ if (s.bestGap > bestOverall) bestOverall = s.bestGap; });
    var laneCrossed = summary.filter(function(s){ return s.counterexample; });
    var firstGenAny = null;
    laneCrossed.forEach(function(s){
      if (firstGenAny === null || s.firstGen < firstGenAny) firstGenAny = s.firstGen;
    });
    var minN = null;
    laneCrossed.forEach(function(s){
      if (s.n !== null && (minN === null || s.n < minN)) minN = s.n;
    });
    return {
      lanes: lanes,
      bestOverall: bestOverall,
      laneCrossedCount: laneCrossed.length,
      firstGenAny: firstGenAny,
      minN: minN
    };
  }

  // ---------- Rendering: KPI cards ----------
  function fmtGap(v){
    if (v === null || v === undefined || !isFinite(v)) return "—";
    return v.toFixed(10);
  }
  function fmtInt(v){
    return (v === null || v === undefined) ? "—" : String(v);
  }

  function renderKPIs(kpi){
    var grid = document.getElementById("kpiGrid");
    var foundAny = kpi.laneCrossedCount > 0;
    grid.innerHTML = "";

    var cards = [
      { label: "Carriles (corridas)", value: fmtInt(kpi.lanes), sub: "total de lanes en el CSV", cls: "neutral" },
      { label: "Mejor gap global", value: fmtGap(kpi.bestOverall), sub: kpi.bestOverall > COUNTEREXAMPLE_THRESHOLD ? "contraejemplo confirmado" : "aún sin cruzar 0", cls: kpi.bestOverall > COUNTEREXAMPLE_THRESHOLD ? "highlight" : "" },
      { label: "Carriles con contraejemplo", value: fmtInt(kpi.laneCrossedCount) + " / " + fmtInt(kpi.lanes), sub: "lanes con gap > 1e-9", cls: foundAny ? "highlight" : "" },
      { label: "1ª generación cruzada", value: fmtInt(kpi.firstGenAny), sub: "gen más temprana con gap > 0", cls: foundAny ? "highlight" : "" },
      { label: "Mín. n en contraejemplos", value: fmtInt(kpi.minN), sub: "vértices del contraejemplo más chico", cls: foundAny ? "highlight" : "" }
    ];

    cards.forEach(function(c){
      var div = document.createElement("div");
      div.className = "kpi-card" + (c.cls ? " " + c.cls : "");
      div.innerHTML =
        '<div class="label">' + c.label + '</div>' +
        '<div class="value">' + c.value + '</div>' +
        '<div class="sub">' + c.sub + '</div>';
      grid.appendChild(div);
    });
  }

  // ---------- Rendering: chart ----------
  function renderChart(byLane){
    var ctx = document.getElementById("gapChart").getContext("2d");
    var chartEmpty = document.getElementById("chartEmpty");

    if (byLane.size === 0){
      chartEmpty.style.display = "block";
      if (state.chart){ state.chart.destroy(); state.chart = null; }
      return;
    }
    chartEmpty.style.display = "none";

    var datasets = [];
    var lanesSorted = Array.from(byLane.keys()).sort(function(a,b){ return a-b; });

    lanesSorted.forEach(function(corrida){
      var arr = byLane.get(corrida);
      var color = laneColor(corrida);
      datasets.push({
        label: "carril " + corrida,
        data: arr.map(function(r){ return { x: r.gen, y: r.best_gap }; }),
        borderColor: color,
        backgroundColor: color,
        borderWidth: 1.75,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.15,
        spanGaps: true
      });
    });

    var allGens = [];
    lanesSorted.forEach(function(corrida){
      byLane.get(corrida).forEach(function(r){ allGens.push(r.gen); });
    });
    var minGen = Math.min.apply(null, allGens);
    var maxGen = Math.max.apply(null, allGens);
    datasets.push({
      label: "umbral gap = 0",
      data: [{x: minGen, y: 0}, {x: maxGen, y: 0}],
      borderColor: "#ffffff",
      borderWidth: 2.5,
      borderDash: [6, 4],
      pointRadius: 0,
      pointHoverRadius: 0,
      tension: 0,
      order: 0
    });

    if (state.chart){ state.chart.destroy(); }

    state.chart = new Chart(ctx, {
      type: "line",
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: "nearest", axis: "x", intersect: false },
        plugins: {
          legend: { labels: { color: "#8b98a9", boxWidth: 12, font: { size: 10 } } },
          tooltip: {
            backgroundColor: "#121821",
            borderColor: "#232d3a",
            borderWidth: 1,
            titleColor: "#e6edf3",
            bodyColor: "#e6edf3",
            callbacks: {
              label: function(ctx){
                var v = ctx.parsed.y;
                return ctx.dataset.label + ": " + (typeof v === "number" ? v.toFixed(10) : v);
              }
            }
          }
        },
        scales: {
          x: { type: "linear", title: { display: true, text: "gen", color: "#8b98a9" }, ticks: { color: "#8b98a9" }, grid: { color: "#1a222c" } },
          y: { title: { display: true, text: "best_gap", color: "#8b98a9" }, ticks: { color: "#8b98a9" }, grid: { color: "#1a222c" } }
        }
      }
    });
  }

  // ---------- Rendering: table ----------
  function sortSummary(){
    var key = state.sortKey;
    var dir = state.sortDir;
    var withVal = state.summary.slice();
    withVal.sort(function(a, b){
      var av = a[key], bv = b[key];
      var aNull = (av === null || av === undefined);
      var bNull = (bv === null || bv === undefined);
      if (aNull && bNull) return 0;
      if (aNull) return 1;
      if (bNull) return -1;
      if (typeof av === "boolean"){ av = av ? 1 : 0; bv = bv ? 1 : 0; }
      if (typeof av === "string"){ return dir * av.localeCompare(bv); }
      return dir * (av - bv);
    });
    return withVal;
  }

  function renderTable(){
    var tbody = document.getElementById("summaryBody");
    var tableEmpty = document.getElementById("tableEmpty");
    tbody.innerHTML = "";

    if (state.summary.length === 0){
      tableEmpty.style.display = "block";
      return;
    }
    tableEmpty.style.display = "none";

    var sorted = sortSummary();

    sorted.forEach(function(s){
      var tr = document.createElement("tr");
      if (s.counterexample) tr.className = "counterexample";

      var g6full = s.bestG6 || "";
      var g6short = g6full.length > 28 ? g6full.slice(0, 28) + "…" : g6full;

      tr.innerHTML =
        '<td>' + s.corrida + '</td>' +
        '<td>' + fmtGap(s.bestGap) + '</td>' +
        '<td>' + fmtGap(s.finalGap) + '</td>' +
        '<td>' + (s.firstGen === null ? "—" : s.firstGen) + '</td>' +
        '<td>' + (s.n === null ? "—" : s.n) + '</td>' +
        '<td>' + (s.counterexample ? '<span class="badge yes">sí</span>' : '<span class="badge no">no</span>') + '</td>' +
        '<td class="g6-cell" title="click para copiar el string completo" data-full="' + escapeAttr(g6full) + '">' + escapeHtml(g6short || "—") + '</td>';

      tbody.appendChild(tr);
    });

    tbody.querySelectorAll(".g6-cell").forEach(function(td){
      td.addEventListener("click", function(){
        var full = td.getAttribute("data-full");
        if (!full) return;
        copyToClipboard(full).then(function(){
          td.classList.add("copied");
          setTimeout(function(){ td.classList.remove("copied"); }, 1100);
        });
      });
    });
  }

  function escapeHtml(str){
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function escapeAttr(str){
    return escapeHtml(str).replace(/"/g, "&quot;");
  }

  function copyToClipboard(text){
    if (navigator.clipboard && navigator.clipboard.writeText){
      return navigator.clipboard.writeText(text).catch(function(){ return fallbackCopy(text); });
    }
    return fallbackCopy(text);
  }
  function fallbackCopy(text){
    return new Promise(function(resolve){
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      try { document.execCommand("copy"); } catch(e){ /* ignore */ }
      document.body.removeChild(ta);
      resolve();
    });
  }

  document.querySelectorAll("#summaryTable thead th").forEach(function(th){
    th.addEventListener("click", function(){
      var key = th.getAttribute("data-key");
      if (state.sortKey === key){ state.sortDir *= -1; }
      else { state.sortKey = key; state.sortDir = 1; }
      document.querySelectorAll("#summaryTable thead th").forEach(function(h){ h.classList.remove("sorted"); });
      th.classList.add("sorted");
      renderTable();
    });
  });

  function setStatus(text, cls){
    var pill = document.getElementById("statusPill");
    pill.textContent = text;
    pill.className = "status-pill" + (cls ? " " + cls : "");
  }

  function loadFromObjects(objs, sourceLabel){
    if (objs.length === 0){
      setStatus("CSV vacío o sin filas válidas (" + sourceLabel + ")", "err");
      return;
    }
    state.rows = objs;
    state.byLane = buildLanes(objs);
    state.summary = buildSummary(state.byLane);
    var kpi = computeKPIs(objs, state.summary);

    renderKPIs(kpi);
    renderChart(state.byLane);
    renderTable();

    setStatus(objs.length + " filas · " + state.byLane.size + " carriles cargados (" + sourceLabel + ")", "ok");
  }

  function loadCSVText(text, sourceLabel){
    try {
      var rawRows = parseCSV(text);
      var objs = rowsToObjects(rawRows);
      loadFromObjects(objs, sourceLabel);
    } catch (err){
      setStatus("Error al parsear CSV: " + err.message, "err");
    }
  }

  function handleFile(file){
    var reader = new FileReader();
    reader.onload = function(e){ loadCSVText(e.target.result, file.name); };
    reader.onerror = function(){ setStatus("No se pudo leer el archivo " + file.name, "err"); };
    reader.readAsText(file);
  }

  var fileInput = document.getElementById("fileInput");
  var pickBtn = document.getElementById("pickBtn");
  pickBtn.addEventListener("click", function(){ fileInput.click(); });
  fileInput.addEventListener("change", function(e){
    if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
  });

  var loader = document.getElementById("loader");
  ["dragenter", "dragover"].forEach(function(evt){
    loader.addEventListener(evt, function(e){ e.preventDefault(); e.stopPropagation(); loader.classList.add("dragover"); });
  });
  ["dragleave", "drop"].forEach(function(evt){
    loader.addEventListener(evt, function(e){ e.preventDefault(); e.stopPropagation(); loader.classList.remove("dragover"); });
  });
  loader.addEventListener("drop", function(e){
    var files = e.dataTransfer && e.dataTransfer.files;
    if (files && files[0]) handleFile(files[0]);
  });

  // Render immediately using the data baked in at build time.
  loadFromObjects(BAKED_ROWS, "incrustado en build");
})();
</script>
</body>
</html>
"""


def render_html(rows, csv_name):
    rows_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__ROWS_JSON__", rows_json)
    html = html.replace("__CSV_NAME__", csv_name)
    return html


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    out_path = Path(args.out)

    print(f"Leyendo CSV: {csv_path}")
    rows = load_rows(csv_path)
    print(f"  -> {len(rows)} filas válidas cargadas.")

    summary, kpi = build_summary(rows)
    print(f"  -> {kpi['lanes']} carriles detectados.")
    print(f"  -> mejor gap global: {kpi['bestOverall']}")
    print(f"  -> carriles con contraejemplo: {kpi['laneCrossedCount']} / {kpi['lanes']}")
    print(f"  -> primera generación cruzada: {kpi['firstGenAny']}")
    print(f"  -> n mínimo entre contraejemplos: {kpi['minN']}")

    html = render_html(rows, csv_path.name)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_bytes = out_path.stat().st_size
    print(f"\nOK: escribí {out_path} ({size_bytes:,} bytes)")


if __name__ == "__main__":
    main()
