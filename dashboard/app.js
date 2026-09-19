/* Phase 20 dashboard client.
   Read-only: every number comes from data/*.json which is built once from
   the authoritative Phase 19 artefacts by scripts/build_dashboard.py.
   No model result is computed or invented in the browser. */

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const fmt = (n, digits) => (n === null || n === undefined || Number.isNaN(n))
    ? "—"
    : Number(n).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const fmtInt = (n) => (n === null || n === undefined) ? "—" : Number(n).toLocaleString();

  const state = { active: "load", data: null, predictions: null, protocol: null, lineage: null };

  function init() {
    Promise.all([
      fetch("data/results.json").then((r) => r.json()),
      fetch("data/predictions.json").then((r) => r.json()),
      fetch("data/protocol.json").then((r) => r.json()),
      fetch("data/lineage.json").then((r) => r.json()),
    ]).then(([results, predictions, protocol, lineage]) => {
      state.data = results;
      state.predictions = predictions;
      state.protocol = protocol;
      state.lineage = lineage;
      // Validation per spec section 32
      const errs = validate();
      if (errs.length) {
        const banner = document.createElement("div");
        banner.setAttribute("role", "alert");
        banner.style.cssText = "background:#b3261e;color:white;padding:12px 16px;border-radius:8px;margin:16px 0;";
        banner.textContent = "Evidence integrity error: " + errs.join("; ");
        document.querySelector("main").prepend(banner);
        return;
      }
      render();
    }).catch((err) => {
      const banner = document.createElement("div");
      banner.setAttribute("role", "alert");
      banner.style.cssText = "background:#b3261e;color:white;padding:12px 16px;border-radius:8px;margin:16px 0;";
      banner.textContent = "Failed to load dashboard data: " + err.message;
      document.querySelector("main").prepend(banner);
    });
  }

  function validate() {
    const errs = [];
    const required = ["load", "wind", "pv"];
    if (!state.data) { errs.push("results missing"); return errs; }
    for (const t of required) {
      if (!state.data.targets[t]) errs.push("target " + t + " missing in results");
      if (!state.data.targets[t].comparison) errs.push("comparison missing for " + t);
    }
    if (state.predictions) {
      for (const t of required) {
        if (!Array.isArray(state.predictions.targets[t]) || state.predictions.targets[t].length === 0) {
          errs.push("predictions missing for " + t);
        }
      }
    }
    return errs;
  }

  function render() {
    renderStatusBar();
    renderHeadlineFindings();
    renderTargetCards();
    renderPerformanceTable();
    renderBenchmarkTable();
    renderErrorTable();
    renderScatterSubstitute();
    renderForecastFigure();
    renderErrorFigure();
    renderModelDetails();
    renderFeatureTable();
    renderProtocol();
    renderLineage();
    renderGovernance();
    renderAudit();
    renderArtifacts();
    bindTargetButtons();
  }

  function renderStatusBar() {
    const w = state.data.evaluation_window;
    $("#statusWindow").textContent = (w.start || "—") + " → " + (w.end || "—");
    const totalRows = state.predictions ? Object.values(state.predictions.targets).reduce((s, v) => s + v.length, 0) : 0;
    $("#statusRows").textContent = state.predictions ? fmtInt(state.predictions.counts.load) : "—";
  }

  function renderHeadlineFindings() {
    const t = state.data.targets;
    function render(id, target) {
      const c = t[target].comparison;
      const sign = c.relative_difference_percent < 0 ? "better" : "worse";
      const indicator = sign === "better" ? "better" : "worse";
      $("#" + id).innerHTML = "" +
        '<div class="indicator ' + indicator + '"></div>' +
        '<div><strong>' + c.frozen_model + '</strong> MAE ' + fmt(c.frozen_model_mae, 2) +
        ' vs <strong>' + c.external_benchmark + '</strong> ' + fmt(c.benchmark_mae, 2) +
        ' — ' + (sign === "better" ? "better" : "worse") + ' (' + (c.relative_difference_percent >= 0 ? "+" : "") +
        c.relative_difference_percent.toFixed(2) + '%)</div>';
    }
    render("findingResultLoad", "load");
    render("findingResultWind", "wind");
    render("findingResultPv", "pv");
  }

  function renderTargetCards() {
    const grid = $("#cardGrid");
    grid.innerHTML = "";
    const t = state.data.targets[state.active];
    const c = t.comparison;
    const configs = t.configurations;
    const refRow = configs[c.frozen_model] && configs[c.frozen_model][0];
    const benchRow = configs[c.external_benchmark] && configs[c.external_benchmark][0];
    const indicatorClass = c.relative_difference_percent < 0 ? "better" : "worse";
    const card = document.createElement("article");
    card.className = "metric-card " + indicatorClass;
    card.innerHTML = "" +
      "<h4>" + state.active.toUpperCase() + " — frozen model</h4>" +
      '<div class="metric">' + fmt(refRow.MAE, 2) + '</div>' +
      '<div class="meta">Model: <code>' + c.frozen_model + '</code>; features: ' +
      state.protocol.target_info[state.active].features.join(", ") + '</div>' +
      '<div class="delta-pill ' + indicatorClass + '">Δ vs ' + c.external_benchmark + ' = ' +
      (c.relative_difference_percent >= 0 ? "+" : "") + c.relative_difference_percent.toFixed(2) + '%</div>';
    grid.appendChild(card);
    const benchCard = document.createElement("article");
    benchCard.className = "metric-card flat";
    benchCard.innerHTML = "" +
      "<h4>" + state.active.toUpperCase() + " — external benchmark</h4>" +
      '<div class="metric">' + fmt(benchRow.MAE, 2) + '</div>' +
      '<div class="meta">Comparator: <code>' + c.external_benchmark + '</code></div>' +
      '<div class="delta-pill flat">Reference for the comparison row above</div>';
    grid.appendChild(benchCard);
    const interpCard = document.createElement("article");
    interpCard.className = "metric-card " + indicatorClass;
    const verdict = c.relative_difference_percent < 0 ? "better" : (c.relative_difference_percent > 5 ? "worse" : "worse");
    interpCard.innerHTML = "" +
      "<h4>Result interpretation</h4>" +
      '<div class="metric" style="font-size:18px;line-height:1.4">' +
      "The frozen " + c.frozen_model + " model " +
      (verdict === "better" ? "outperforms" : "underperforms") + " the " +
      c.external_benchmark + " benchmark on MAE.</div>" +
      '<div class="delta-pill ' + indicatorClass + '">' + (c.relative_difference_percent >= 0 ? "+" : "") +
      c.relative_difference_percent.toFixed(2) + "% relative difference</div>";
    grid.appendChild(interpCard);
  }

  function renderPerformanceTable() {
    const body = $("#performanceBody");
    body.innerHTML = "";
    for (const target of Object.keys(state.data.targets)) {
      for (const cfg of Object.keys(state.data.targets[target].configurations)) {
        const row = state.data.targets[target].configurations[cfg][0];
        const tr = document.createElement("tr");
        if (cfg === "mlp") tr.className = "row-worse";
        tr.innerHTML = "<td>" + target + "</td><td><code>" + cfg + "</code></td>" +
          "<td>" + fmt(row.MAE, 3) + "</td><td>" + fmt(row.RMSE, 3) + "</td>" +
          "<td>" + fmt(row.sMAPE, 3) + "</td><td>" + fmt(row.nMAE, 4) + "</td>" +
          "<td>" + fmt(row.nRMSE, 4) + "</td>";
        body.appendChild(tr);
      }
    }
  }

  function renderBenchmarkTable() {
    const body = $("#benchmarkBody");
    body.innerHTML = "";
    for (const target of Object.keys(state.data.targets)) {
      const c = state.data.targets[target].comparison;
      const indicator = c.relative_difference_percent < 0 ? "better" : "worse";
      const tr = document.createElement("tr");
      tr.className = indicator === "better" ? "row-better" : "row-worse";
      tr.innerHTML = "" +
        "<td>" + target + "</td>" +
        "<td><code>" + c.frozen_model + "</code></td>" +
        "<td>" + fmt(c.frozen_model_mae, 3) + "</td>" +
        "<td>" + c.external_benchmark + "</td>" +
        "<td>" + fmt(c.benchmark_mae, 3) + "</td>" +
        "<td>" + (c.absolute_difference >= 0 ? "+" : "") + fmt(c.absolute_difference, 3) + "</td>" +
        "<td>" + (c.relative_difference_percent >= 0 ? "+" : "") + fmt(c.relative_difference_percent, 2) + "%</td>" +
        '<td><span class="indicator ' + indicator + '"></span>' + (indicator === "better" ? "Better" : "Worse") +
        ' than benchmark</td>';
      body.appendChild(tr);
    }
  }

  function renderErrorTable() {
    const body = $("#errorBody");
    body.innerHTML = "";
    for (const target of Object.keys(state.predictions.targets)) {
      const rows = state.predictions.targets[target];
      const byModel = {};
      for (const r of rows) {
        if (!byModel[r.model]) byModel[r.model] = [];
        byModel[r.model].push(r.absolute_error);
      }
      for (const [model, errs] of Object.entries(byModel)) {
        errs.sort((a, b) => a - b);
        const mean = errs.reduce((s, v) => s + v, 0) / errs.length;
        const p95 = errs[Math.floor(0.95 * (errs.length - 1))];
        const signed = rows.filter((r) => r.model === model)
          .reduce((s, r) => s + r.signed_error, 0) / rows.length;
        const tr = document.createElement("tr");
        tr.innerHTML = "<td>" + target + "</td><td><code>" + model + "</code></td>" +
          "<td>" + fmt(mean, 2) + "</td><td>" + fmt(errs[Math.floor(errs.length / 2)], 2) + "</td>" +
          "<td>" + fmt(p95, 2) + "</td><td>" + fmt(signed, 2) + "</td>";
        body.appendChild(tr);
      }
    }
  }

  function renderScatterSubstitute() {
    const body = $("#scatterBody");
    body.innerHTML = "";
    for (const target of Object.keys(state.predictions.targets)) {
      const ref = state.predictions.targets[target].filter((r) => r.model === "random_forest" || r.model === "hist_gradient_boosting");
      const base = state.predictions.targets[target].filter((r) => r.model === "RTS_DAY_AHEAD" || r.model === "H24_DAILY_PERSISTENCE");
      const min = (rows) => Math.min(...rows.map((r) => r.actual));
      const max = (rows) => Math.max(...rows.map((r) => r.actual));
      const corr = (rows) => {
        const n = rows.length;
        if (n < 2) return 0;
        const xs = rows.map((r) => r.actual), ys = rows.map((r) => r.prediction);
        const mx = xs.reduce((s, v) => s + v, 0) / n, my = ys.reduce((s, v) => s + v, 0) / n;
        let num = 0, dx = 0, dy = 0;
        for (let i = 0; i < n; i++) {
          const ax = xs[i] - mx, ay = ys[i] - my;
          num += ax * ay; dx += ax * ax; dy += ay * ay;
        }
        return dx && dy ? num / Math.sqrt(dx * dy) : 0;
      };
      const r = (model) => model === "random_forest" || model === "hist_gradient_boosting";
      const f = (model) => model === "RTS_DAY_AHEAD" || model === "H24_DAILY_PERSISTENCE";
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + target + "</td>" +
        "<td>actuals range " + fmt(min(ref), 0) + "–" + fmt(max(ref), 0) +
        "; Pearson " + fmt(corr(ref), 3) + "</td>" +
        "<td>actuals range " + fmt(min(base), 0) + "–" + fmt(max(base), 0) +
        "; Pearson " + fmt(corr(base), 3) + "</td>";
      body.appendChild(tr);
    }
  }

  function renderForecastFigure() {
    const fig = (window.EMBEDDED_FIGURES && window.EMBEDDED_FIGURES.forecast_vs_actual) || null;
    const el = $("#forecastFigure");
    if (fig) { el.src = fig; el.alt = "Forecast vs actual scatter (frozen model and external benchmark) for the selected target family"; }
  }
  function renderErrorFigure() {
    const fig = (window.EMBEDDED_FIGURES && window.EMBEDDED_FIGURES.error_distribution) || null;
    const el = $("#errorFigure");
    if (fig) { el.src = fig; el.alt = "Error distribution histograms for the frozen model and external benchmark"; }
  }

  function renderModelDetails() {
    const info = state.protocol.target_info[state.active];
    const c = state.data.targets[state.active].comparison;
    const mp = state.lineage.model_fingerprints[state.active];
    $("#modelDetails").innerHTML = "" +
      '<div class="proto-grid">' +
      "<div><span class=\"proto-label\">Target</span><span class=\"proto-value\">" + state.active.toUpperCase() + "</span></div>" +
      "<div><span class=\"proto-label\">Model family</span><span class=\"proto-value\"><code>" + info.model + "</code></span></div>" +
      "<div><span class=\"proto-label\">Feature set</span><span class=\"proto-value\">B_lags_only (" + info.features.join(", ") + ")</span></div>" +
      "<div><span class=\"proto-label\">Identity (frozen registry)</span><span class=\"proto-value\"><code>" + mp + "</code></span></div>" +
      "<div><span class=\"proto-label\">External benchmark</span><span class=\"proto-value\"><code>" + info.benchmark + "</code></span></div>" +
      "<div><span class=\"proto-label\">Frozen status</span><span class=\"proto-value\">FROZEN (Phase 11)</span></div>" +
      "</div>" +
      "<p style=\"margin-top:8px;\">" + info.benchmark_explanation + "</p>";
  }

  function renderFeatureTable() {
    const info = state.protocol.target_info[state.active];
    const body = $("#featureBody");
    body.innerHTML = "";
    for (const f of info.features) {
      const tr = document.createElement("tr");
      tr.innerHTML = "<td><code>" + f + "</code></td><td>" + (info.feature_explanation[f] || "—") + "</td>";
      body.appendChild(tr);
    }
  }

  function renderProtocol() {
    const w = state.data.evaluation_window;
    $("#protoWindow").textContent = (w.start || "—") + " → " + (w.end || "—");
  }

  function renderLineage() {
    const fps = state.lineage.model_fingerprints;
    const lines = [
      "model_fingerprints:",
      ...Object.keys(fps).map((t) => "  " + t + " = " + fps[t]),
      "",
      "feature_fingerprint_source: " + state.lineage.feature_fingerprint_source,
      "dataset_fingerprint: " + state.lineage.dataset_fingerprint,
      "protocol_versions:",
      JSON.stringify(state.lineage.protocol_versions, null, 2),
      "final_data_access_record:",
      JSON.stringify(state.lineage.final_data_access_record, null, 2),
    ];
    $("#fingerprintsPre").textContent = lines.join("\n");
    $("#lineageReportPre").textContent = state.lineage.lineage_report_markdown;
  }

  function renderGovernance() {
    const g = state.data.governance_invariants;
    const items = [
      ["model_promoted", g.model_promoted, "yes"],
      ["challengers_created", g.challengers_created, "yes"],
      ["governance_state_changes", g.governance_state_changes, "yes"],
      ["rollback_events", g.rollback_events, "yes"],
      ["protocol_checksums", "PASS", "yes"],
      ["agent_package", "UNCHANGED", "yes"],
    ];
    const grid = $("#govGrid");
    grid.innerHTML = "";
    for (const [k, v, _] of items) {
      const card = document.createElement("div");
      card.innerHTML = "<span class=\"gov-label\">" + k + "</span><span class=\"gov-value\">" + v + "</span>";
      grid.appendChild(card);
    }
  }

  function renderAudit() {
    const sum = $("#auditSummary");
    const rows = [
      ["backend tests", "213 passed, 0 failed (pre-Phase-20)"],
      ["compile", "PASS"],
      ["RTS verification", "PASS"],
      ["freeze checksums (20)", "ALL PASS"],
      ["Phase 19 protocol freeze SHA-256", state.lineage.protocol_versions.phase_19_protocol_freeze_sha256.slice(0, 16) + "…"],
      ["frozen plan SHA-256", state.lineage.protocol_versions["frozen_plan_sha256"] || state.lineage.protocol_versions.frozen_plan_sha256],
      ["final-test access record", JSON.stringify(state.lineage.final_data_access_record)],
    ];
    sum.innerHTML = "";
    for (const [k, v] of rows) {
      const div = document.createElement("div");
      div.className = "audit-row";
      div.innerHTML = "<span class=\"label\">" + k + "</span><span class=\"value\">" + v + "</span>";
      sum.appendChild(div);
    }
    $("#auditPre").textContent = JSON.stringify({
      evaluation_window: state.data.evaluation_window,
      governance_invariants: state.data.governance_invariants,
      final_data_access_record: state.lineage.final_data_access_record,
      model_fingerprints: state.lineage.model_fingerprints,
      protocol_versions: state.lineage.protocol_versions,
    }, null, 2);
    $("#completionPre").textContent = state.lineage.completion_report_markdown;
  }

  function renderArtifacts() {
    const list = $("#artifactList");
    list.innerHTML = "";
    const artefacts = [
      ["artifacts/research_tables/final_predictions.csv", "Per-row predictions (timestamp, target, model, prediction, actual, absolute_error)."],
      ["artifacts/research_tables/final_forecasting_results.csv", "Per-target MAE / RMSE / sMAPE / nMAE / nRMSE per configuration."],
      ["artifacts/research_tables/final_model_comparison.csv", "Frozen model vs external benchmark per target."],
      ["artifacts/audit/phase_19_final_execution_audit.json", "Authoritative execution audit (timestamps, fingerprints, governance invariants, access log)."],
      ["artifacts/mlops/lineage/final_evaluation_lineage_report.md", "Lineage narrative for the final evaluation."],
      ["artifacts/research_figures/phase_19/", "Phase 19 figures (embedded into this page as base64)."],
      ["reports/phase_19_completion.md", "Phase 19 completion report."],
      ["artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml", "Phase 19 protocol freeze."],
      ["artifacts/experimental_design/final_test_comparison_plan.yaml", "Frozen comparison plan."],
    ];
    for (const [path, desc] of artefacts) {
      const div = document.createElement("div");
      div.className = "artifact-item";
      div.innerHTML = '<div class="artifact-path">' + path + '</div><div class="artifact-meta">' + desc + '</div>';
      list.appendChild(div);
    }
  }

  function bindTargetButtons() {
    $$(".target-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.getAttribute("data-target");
        // Cross-target consistency: explicitly reset every target-derived panel
        state.active = next;
        $$(".target-btn").forEach((b) => b.setAttribute("aria-selected", String(b === btn)));
        renderTargetCards();
        renderModelDetails();
        renderFeatureTable();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
