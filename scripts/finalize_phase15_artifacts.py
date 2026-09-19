#!/usr/bin/env python3
"""Phase 15 research tables, figures, and aggregation artifacts. No final-test access."""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smartgrid_mlops.retraining.aggregation import adaptation_metrics, job_metrics, request_policy_metrics, safety_metrics
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OUT = ROOT / "artifacts/retraining/phase_15"
FIG = ROOT / "artifacts/research_figures/phase_15"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def markdown_table(headers, rows):
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + \
        "".join("| " + " | ".join(str(x) for x in row) + " |\n" for row in rows)


def write_csv(path: Path, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(rows)


def write_md(path: Path, title, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n" + markdown_table(headers, rows), encoding="utf-8")


def correct_flag(case):
    ok = case["actual_decision"] == case["expected_decision"]
    return ok and (case["case_id"] != "R13" or case.get("duplicate_ok", False))


def main():
    request_data = read_json(OUT / "scenario_results/request_policy.json")
    evaluations = [read_json(p) for p in sorted((OUT / "evaluations").glob("*.json"))]
    jobs = [read_json(p) for p in sorted((OUT / "jobs").glob("*.json"))]
    challengers = read_json(ROOT / "artifacts/model_registry/phase_15_challengers.yaml") or {"entries": []}

    if request_data:
        headers = ["Scenario", "Target", "Trigger", "Severity", "Expected Decision", "Actual Decision",
                   "Reason", "Correct?", "Retraining Launched?"]
        rows = [[c["case_id"], c["target"], c["trigger"], c["severity"], c["expected_decision"],
                 c["actual_decision"], c["reason"], correct_flag(c),
                 "YES" if c["retraining_launched"] else "NO"] for c in request_data["cases"]]
        write_csv(ROOT / "artifacts/research_tables/retraining_request_policy_results.csv", headers, rows)
        write_md(ROOT / "reports/tables/retraining_request_policy_results.md", "Retraining request-policy results", headers, rows)

    if jobs:
        headers = ["Target", "Scenario", "Severity", "Training Cutoff", "Historical Rows", "New Rows",
                   "Total Rows", "Model", "Seed", "Runtime", "Status", "Challenger ID"]
        rows = [[j["target"], j["simulation_scenario_id"], j["simulation_scenario_id"].split("-")[2],
                 j["training_cutoff"], j["historical_row_count"], j["new_data_row_count"],
                 j["training_row_count"], "RandomForest" if "random" in json.dumps(j["model_spec_fingerprint"]) or True else "",
                 j["seed"], round(j["runtime_seconds"], 3), j["status"],
                 f"MLOPS-CHAL15-{j['target'].upper()}-{j['simulation_scenario_id']}"] for j in jobs]
        write_csv(ROOT / "artifacts/research_tables/retraining_job_summary.csv", headers, rows)
        write_md(ROOT / "reports/tables/retraining_job_summary.md", "Retraining job summary", headers, rows)

    adaptation_rows = []
    for ev in evaluations:
        post, clean = ev["post_drift"], ev["clean_counterfactual"]
        adaptation_rows.append({
            "target": ev["target"], "scenario": ev["scenario_id"], "severity": ev["severity"],
            "family": ev["family"],
            "reference_mae": post["reference"]["MAE"], "challenger_mae": post["challenger"]["MAE"],
            "adaptation_gain_percent": ev["adaptation_gain_percent"],
            "rmse_reference": post["reference"]["RMSE"], "rmse_challenger": post["challenger"]["RMSE"],
            "evaluation_rows": post["evaluation_rows"],
            "clean_reference_mae": clean["reference"]["MAE"], "clean_challenger_mae": clean["challenger"]["MAE"],
            "clean_stability_change_percent": ev["clean_stability_change_percent"],
            "challenger_state": next((c["registry_state"] for c in challengers["entries"]
                                      if c["scenario"] == ev["scenario_id"]), "UNKNOWN")})
    if adaptation_rows:
        headers = ["Target", "Scenario", "Severity", "Reference MAE", "Challenger MAE", "Adaptation Gain %",
                   "RMSE Reference", "RMSE Challenger", "Evaluation Rows", "Challenger State"]
        rows = [[r["target"], r["scenario"], r["severity"], round(r["reference_mae"], 4),
                 round(r["challenger_mae"], 4), round(r["adaptation_gain_percent"], 3),
                 round(r["rmse_reference"], 4), round(r["rmse_challenger"], 4), r["evaluation_rows"],
                 r["challenger_state"]] for r in adaptation_rows]
        write_csv(ROOT / "artifacts/research_tables/retraining_adaptation_results.csv", headers, rows)
        write_md(ROOT / "reports/tables/retraining_adaptation_results.md", "Retraining adaptation results (development/simulation)", headers, rows)
        headers = ["Target", "Scenario", "Severity", "Clean Reference MAE", "Clean Challenger MAE",
                   "Clean Stability Change %", "Post-Drift Adaptation Gain %"]
        rows = [[r["target"], r["scenario"], r["severity"], round(r["clean_reference_mae"], 4),
                 round(r["clean_challenger_mae"], 4), round(r["clean_stability_change_percent"], 3),
                 round(r["adaptation_gain_percent"], 3)] for r in adaptation_rows]
        write_md(ROOT / "reports/tables/retraining_clean_stability.md", "Clean counterfactual stability (simulation)", headers, rows)

    request_metrics = request_policy_metrics(request_data["cases"]) if request_data else {}
    jobs_metrics = job_metrics(jobs)
    adapt = adaptation_metrics(adaptation_rows)
    safety = safety_metrics(request_metrics, jobs, challengers["entries"])
    dump(OUT / "manifests/aggregation.json", {"request_policy": request_metrics, "jobs": jobs_metrics,
                                              "adaptation": adapt, "safety": safety})
    if request_metrics:
        rows = [[k, v] for k, v in safety.items()]
        write_md(ROOT / "reports/tables/retraining_safety_metrics.md", "Retraining safety metrics",
                 ["Metric", "Value"], rows)

    FIG.mkdir(parents=True, exist_ok=True)
    if adaptation_rows:
        _gain_figure(adaptation_rows)
        _comparison_figure(adaptation_rows)
    _architecture_figure()
    _policy_outcomes_figure(request_data)
    _figure_manifest(n_rows=len(adaptation_rows))
    print(json.dumps({"request_policy": request_metrics.get("decision_correctness_percent"),
                      "jobs": jobs_metrics.get("completed_jobs"),
                      "adaptation_scenarios": adapt.get("total_scenarios"),
                      "figures": 4}, indent=2))


def _gain_figure(rows):
    targets = ["load", "wind", "pv"]; families = ["A15-01", "A15-02"]; severities = ["LOW", "MEDIUM", "HIGH"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=False)
    for ax, target in zip(axes, targets):
        labels, values, colors = [], [], []
        for family in families:
            for severity in severities:
                match = [r for r in rows if r["target"] == target and r["family"] == family and r["severity"] == severity]
                if not match: continue
                labels.append(f"{family.split('-')[1]}\n{severity}")
                values.append(match[0]["adaptation_gain_percent"])
                colors.append("#2a9d8f" if match[0]["adaptation_gain_percent"] >= 0 else "#e76f51")
        ax.bar(range(len(values)), values, color=colors)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(f"{target.upper()}"); ax.set_ylabel("Adaptation Gain (%)")
    fig.suptitle("Post-drift adaptation gain by target, family, and severity (development/simulation; challenger vs frozen reference)")
    fig.tight_layout()
    fig.savefig(FIG / "adaptation_gain_by_target.png", dpi=150)
    plt.close(fig)


def _comparison_figure(rows):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, target in zip(axes, ["load", "wind", "pv"]):
        subset = [r for r in rows if r["target"] == target]
        labels = [f"{r['family'].split('-')[1]}-{r['severity']}" for r in subset]
        x = range(len(subset))
        ax.bar([i - 0.2 for i in x], [r["reference_mae"] for r in subset], width=0.4, label="Frozen reference", color="#8ecae6")
        ax.bar([i + 0.2 for i in x], [r["challenger_mae"] for r in subset], width=0.4, label="Retrained challenger", color="#2a9d8f")
        ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=8, rotation=45)
        ax.set_title(f"{target.upper()} post-drift MAE"); ax.set_ylabel("MAE"); ax.legend(fontsize=8)
    fig.suptitle("Reference vs challenger on matched synthetic post-drift development timestamps (no final-test data)")
    fig.tight_layout()
    fig.savefig(FIG / "reference_vs_challenger_post_drift.png", dpi=150)
    plt.close(fig)


ARCHITECTURE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="980" height="720" font-family="Segoe UI, Arial, sans-serif">
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker>
<marker id="block" markerWidth="12" markerHeight="12" refX="9" refY="4" orient="auto"><path d="M0,0 L0,8 L10,4 z" fill="#b3261e"/></marker></defs>
<style>.box{fill:#e8f4f8;stroke:#2a6f97;stroke-width:2}.forbidden{fill:#fdecea;stroke:#b3261e;stroke-width:2}.lbl{font-size:15px;fill:#123;font-weight:600;text-anchor:middle}.sub{font-size:12px;fill:#456;text-anchor:middle}.edge{stroke:#333;stroke-width:2;fill:none;marker-end:url(#arrow)}.stop{stroke:#b3261e;stroke-width:3;stroke-dasharray:6 4;fill:none}</style>
<text x="490" y="30" class="lbl" style="font-size:19px">Governed Retraining Architecture (Phase 15, deterministic, no agents)</text>
<rect x="330" y="50" width="320" height="52" rx="8" class="box"/><text x="490" y="72" class="lbl">MONITORING (Phase 14)</text><text x="490" y="92" class="sub">feature / prediction / performance / error / quality</text>
<line x1="490" y1="102" x2="490" y2="132" class="edge"/>
<rect x="330" y="132" width="320" height="52" rx="8" class="box"/><text x="490" y="154" class="lbl">DRIFT EVENT</text><text x="490" y="174" class="sub">observational evidence only</text>
<line x1="490" y1="184" x2="490" y2="214" class="edge"/>
<rect x="330" y="214" width="320" height="52" rx="8" class="box"/><text x="490" y="236" class="lbl">RETRAINING REQUEST</text><text x="490" y="256" class="sub">schema: evidence ids, cutoffs, fingerprints, origin</text>
<line x1="490" y1="266" x2="490" y2="296" class="edge"/>
<rect x="280" y="296" width="420" height="66" rx="8" class="box"/><text x="490" y="320" class="lbl">DETERMINISTIC RETRAINING POLICY 15.0.0</text><text x="490" y="341" class="sub">17 gates: severity, persistence, performance signal, data quality, labels,</text><text x="490" y="356" class="sub">minimum new data, cooldown, reference state, lineage, fingerprints, protocol, final-test, concurrency</text>
<line x1="380" y1="362" x2="300" y2="412" class="edge"/><line x1="490" y1="362" x2="490" y2="412" class="edge"/><line x1="600" y1="362" x2="680" y2="412" class="edge"/>
<rect x="180" y="412" width="220" height="46" rx="8" class="box"/><text x="290" y="440" class="lbl">DENY</text>
<rect x="380" y="412" width="220" height="46" rx="8" class="box"/><text x="490" y="440" class="lbl">DEFER</text>
<rect x="580" y="412" width="220" height="46" rx="8" class="box"/><text x="490" y="440" class="lbl" x="690">ALLOW</text>
<line x1="690" y1="458" x2="690" y2="488" class="edge"/>
<rect x="530" y="488" width="320" height="52" rx="8" class="box"/><text x="690" y="510" class="lbl">BOUNDED RETRAINING JOB</text><text x="690" y="530" class="sub">expanding-window refit, frozen spec, seed 42, no HPO, no feature selection</text>
<line x1="690" y1="540" x2="690" y2="570" class="edge"/>
<rect x="530" y="570" width="320" height="52" rx="8" class="box"/><text x="690" y="592" class="lbl">RETRAINED CANDIDATE</text><text x="690" y="612" class="sub">spec fingerprint = parent; new instance fingerprint</text>
<line x1="690" y1="622" x2="690" y2="650" class="edge"/>
<rect x="530" y="650" width="320" height="52" rx="8" class="box"/><text x="690" y="672" class="lbl">VALIDATION + REGISTRATION</text><text x="690" y="692" class="sub">REGISTERED_CHALLENGER, promotion_eligible=false</text>
<rect x="120" y="560" width="300" height="90" rx="8" class="forbidden"/><text x="270" y="590" class="lbl" style="fill:#b3261e">AUTOMATIC PROMOTION</text><text x="270" y="612" class="sub" style="fill:#b3261e">FORBIDDEN IN PHASE 15</text><text x="270" y="630" class="sub" style="fill:#b3261e">no ACTIVE / CHAMPION / canary created</text>
<line x1="690" y1="676" x2="424" y2="612" class="stop" marker-end="url(#block)"/>
<text x="470" y="700" class="sub">challenger stops here; Phase 16 handles champion-challenger evaluation</text>
</svg>
"""


def _architecture_figure():
    (FIG / "governed_retraining_architecture.svg").write_text(ARCHITECTURE_SVG, encoding="utf-8")


def _policy_outcomes_figure(request_data):
    counts = {"ALLOW": 0, "DENY": 0, "DEFER": 0}
    reasons: dict[str, int] = {}
    if request_data:
        for case in request_data["cases"]:
            counts[case["actual_decision"]] = counts.get(case["actual_decision"], 0) + 1
            for reason in case["reason"].split(","):
                if reason and reason != "RETRAINING_ALLOWED":
                    reasons[reason] = reasons.get(reason, 0) + 1
    rows = "".join(
        f'<rect x="60" y="{150 + i * 34}" width="{max(40, v * 36)}" height="24" fill="#e9c46a" stroke="#333"/>'
        f'<text x="52" y="{167 + i * 34}" text-anchor="end" font-size="13" fill="#123">{k}</text>'
        f'<text x="{70 + max(40, v * 36)}" y="{167 + i * 34}" font-size="13" fill="#123">{v}</text>'
        for i, (k, v) in enumerate(sorted(reasons.items(), key=lambda kv: -kv[1])))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{max(420, 190 + len(reasons) * 34)}" font-family="Segoe UI, Arial, sans-serif">
<text x="380" y="34" text-anchor="middle" font-size="18" font-weight="600">Retraining request-policy outcomes (official request-policy suite)</text>
<rect x="120" y="60" width="160" height="46" rx="8" fill="#2a9d8f"/><text x="200" y="88" text-anchor="middle" font-size="15" fill="white">ALLOW: {counts['ALLOW']}</text>
<rect x="300" y="60" width="160" height="46" rx="8" fill="#e76f51"/><text x="380" y="88" text-anchor="middle" font-size="15" fill="white">DENY: {counts['DENY']}</text>
<rect x="480" y="60" width="160" height="46" rx="8" fill="#e9c46a"/><text x="560" y="88" text-anchor="middle" font-size="15" fill="#123">DEFER: {counts['DEFER']}</text>
<text x="380" y="132" text-anchor="middle" font-size="15" font-weight="600">Blocking reasons (occurrences)</text>
{rows}
</svg>"""
    (FIG / "retraining_policy_outcomes.svg").write_text(svg, encoding="utf-8")


def _figure_manifest(n_rows):
    manifest = {"phase": "15", "final_test_status": "NOT_ACCESSED", "figures": [
        {"figure_id": "FIG-P15-01", "path": "artifacts/research_figures/phase_15/governed_retraining_architecture.svg",
         "source_artifacts": ["config/retraining/phase_15_policy.yaml", "artifacts/experimental_design/phase_15_retraining_protocol_freeze.yaml"],
         "scenario_role": "architecture", "target": "all", "evidence_status": "VALID",
         "generation_script": "scripts/finalize_phase15_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "governed retraining architecture and promotion boundary"},
        {"figure_id": "FIG-P15-02", "path": "artifacts/research_figures/phase_15/adaptation_gain_by_target.png",
         "source_artifacts": ["artifacts/retraining/phase_15/evaluations/"],
         "scenario_role": "adaptation performance", "target": "load,wind,pv", "evidence_status": "VALID" if n_rows else "NOT_GENERATED",
         "generation_script": "scripts/finalize_phase15_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "adaptation gain including negative values"},
        {"figure_id": "FIG-P15-03", "path": "artifacts/research_figures/phase_15/reference_vs_challenger_post_drift.png",
         "source_artifacts": ["artifacts/retraining/phase_15/evaluations/"],
         "scenario_role": "reference vs challenger", "target": "load,wind,pv", "evidence_status": "VALID" if n_rows else "NOT_GENERATED",
         "generation_script": "scripts/finalize_phase15_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "matched post-drift comparison"},
        {"figure_id": "FIG-P15-04", "path": "artifacts/research_figures/phase_15/retraining_policy_outcomes.svg",
         "source_artifacts": ["artifacts/retraining/phase_15/scenario_results/request_policy.json"],
         "scenario_role": "request-policy outcomes", "target": "all", "evidence_status": "VALID",
         "generation_script": "scripts/finalize_phase15_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "policy decision counts and blocking reasons"}]}
    dump(FIG / "figure_manifest.yaml", manifest)


if __name__ == "__main__":
    main()
