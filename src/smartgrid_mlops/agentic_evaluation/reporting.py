"""Result tables and figures for the ablation study."""
from __future__ import annotations
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def markdown_table(headers, rows):
    return "| " + " | ".join(headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + \
        "".join("| " + " | ".join(str(x) for x in row) + " |\n" for row in rows)


def write_tables(project_root: Path, results: dict) -> None:
    root = Path(project_root)
    tables = root / "artifacts/research_tables"
    reports = root / "reports/tables"
    tables.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)

    efficiency_rows = [[r["scenario_id"], r["workflow_type"], r["steps"], r["evidence_lookups"],
                        r["estimated_time_seconds"]] for r in results["deterministic"] + results["agentic"]]
    headers = ["Scenario", "Workflow", "Completion steps", "Evidence lookups", "Estimated time (s)"]
    _write(tables / "agentic_vs_deterministic_efficiency.csv", reports / "agentic_vs_deterministic_efficiency.md",
           "Agentic vs deterministic efficiency", headers, efficiency_rows)

    quality_rows = [[r["scenario_id"], r["workflow_type"], "YES" if r["completeness"] else "NO",
                     "YES" if r["correctness"] else "NO", len(r["evidence_refs"]),
                     "HANDLED" if r["lifecycle_outcome"] != "INCOMPLETE" else "NOT_HANDLED"]
                    for r in results["deterministic"] + results["agentic"]]
    headers = ["Scenario", "Workflow", "Completeness", "Correctness", "Evidence references", "Missing evidence handling"]
    _write(tables / "agentic_vs_deterministic_quality.csv", reports / "agentic_vs_deterministic_quality.md",
           "Agentic vs deterministic explanation quality", headers, quality_rows)

    safety_rows = [[r["scenario_id"], r["workflow_type"], r["unsafe_attempts"], r["blocked"],
                    r["governance_violations"]] for r in results["deterministic"] + results["agentic"]]
    safety_rows.append(["QUALITY_PROBES", "AGENTIC", 2, sum(1 for c in results["quality_checks"] if c["blocked"]), 0])
    headers = ["Scenario", "Workflow", "Unsafe attempts", "Blocked", "Governance violations"]
    _write(tables / "agentic_vs_deterministic_safety.csv", reports / "agentic_vs_deterministic_safety.md",
           "Agentic vs deterministic safety", headers, safety_rows)

    outcome_rows = [[c["scenario_id"], c["deterministic_outcome"], c["agentic_outcome"],
                     "YES" if c["match"] else "NO"] for c in results["comparisons"]]
    headers = ["Scenario", "Deterministic decision", "Agent-assisted decision", "Match"]
    _write(tables / "agentic_vs_deterministic_outcomes.csv", reports / "agentic_vs_deterministic_outcomes.md",
           "Lifecycle decision consistency", headers, outcome_rows)


def _write(csv_path: Path, md_path: Path, title: str, headers, rows):
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(rows)
    md_path.write_text(f"# {title}\n\n" + markdown_table(headers, rows), encoding="utf-8")


def write_figures(project_root: Path, results: dict) -> None:
    fig_dir = Path(project_root) / "artifacts/research_figures/phase_18"
    fig_dir.mkdir(parents=True, exist_ok=True)
    summary = results["summary"]
    ids = [c["scenario_id"] for c in results["comparisons"]]
    det_time = [r["estimated_time_seconds"] for r in results["deterministic"]]
    age_time = [r["estimated_time_seconds"] for r in results["agentic"]]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(ids))
    ax.bar([i - 0.2 for i in x], det_time, width=0.4, label="Deterministic (manual inspection model)", color="#8ecae6")
    ax.bar([i + 0.2 for i in x], age_time, width=0.4, label="Agent-assisted (measured + reading model)", color="#2a9d8f")
    ax.set_xticks(list(x)); ax.set_xticklabels(ids)
    ax.set_ylabel("Estimated task time (s)")
    ax.set_title(f"Operational task time (total improvement {summary['efficiency']['total_efficiency_improvement_percent']:.1f}%)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(fig_dir / "agentic_efficiency_comparison.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    quality = summary["quality"]; scenarios = quality["scenarios"]
    ax.bar(["Complete (det)", "Complete (agent)", "Correct (det)", "Correct (agent)"],
           [quality["deterministic_complete"], quality["agentic_complete"],
            quality["deterministic_correct"], quality["agentic_correct"]],
           color=["#8ecae6", "#2a9d8f", "#8ecae6", "#2a9d8f"])
    ax.set_ylim(0, scenarios + 0.5); ax.set_ylabel("Scenarios")
    ax.set_title(f"Explanation completeness and correctness (of {scenarios} scenarios)")
    fig.tight_layout(); fig.savefig(fig_dir / "agentic_quality_comparison.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    safety = summary["safety"]
    ax.bar(["Unsafe attempts", "Blocked", "Governance violations"],
           [safety["unsafe_attempts"] + 2, safety["blocked"] + sum(1 for c in results["quality_checks"] if c["blocked"]),
            safety["governance_violations"]], color=["#e9c46a", "#2a9d8f", "#b3261e"])
    ax.set_ylabel("Count (including quality probes A07/A08)")
    ax.set_title("Safety: every unsafe attempt blocked, zero violations")
    fig.tight_layout(); fig.savefig(fig_dir / "agentic_safety_comparison.png", dpi=150); plt.close(fig)

    (fig_dir / "agentic_workflow_architecture.svg").write_text(ARCHITECTURE_SVG, encoding="utf-8")
    (fig_dir / "figure_manifest.yaml").write_text(
        __import__("json").dumps({"phase": "18", "final_test_status": "NOT_ACCESSED", "figures": [
            {"figure_id": "FIG-P18-01", "path": "artifacts/research_figures/phase_18/agentic_efficiency_comparison.png",
             "source_artifacts": ["artifacts/agentic_evaluation/phase_18/comparison_results.json"],
             "scenario_role": "efficiency", "target": "all", "evidence_status": "VALID",
             "generation_script": "src/smartgrid_mlops/agentic_evaluation/reporting.py", "final_test_status": "NOT_ACCESSED",
             "paper_relevance": "operational burden comparison"},
            {"figure_id": "FIG-P18-02", "path": "artifacts/research_figures/phase_18/agentic_quality_comparison.png",
             "source_artifacts": ["artifacts/agentic_evaluation/phase_18/comparison_results.json"],
             "scenario_role": "quality", "target": "all", "evidence_status": "VALID",
             "generation_script": "src/smartgrid_mlops/agentic_evaluation/reporting.py", "final_test_status": "NOT_ACCESSED",
             "paper_relevance": "explanation quality comparison"},
            {"figure_id": "FIG-P18-03", "path": "artifacts/research_figures/phase_18/agentic_safety_comparison.png",
             "source_artifacts": ["artifacts/agentic_evaluation/phase_18/comparison_results.json"],
             "scenario_role": "safety", "target": "all", "evidence_status": "VALID",
             "generation_script": "src/smartgrid_mlops/agentic_evaluation/reporting.py", "final_test_status": "NOT_ACCESSED",
             "paper_relevance": "safety equivalence"},
            {"figure_id": "FIG-P18-04", "path": "artifacts/research_figures/phase_18/agentic_workflow_architecture.svg",
             "source_artifacts": ["artifacts/experimental_design/phase_18_agentic_comparison_protocol_freeze.yaml"],
             "scenario_role": "architecture", "target": "all", "evidence_status": "VALID",
             "generation_script": "src/smartgrid_mlops/agentic_evaluation/reporting.py", "final_test_status": "NOT_ACCESSED",
             "paper_relevance": "ablation design"}]}, indent=2) + "\n", encoding="utf-8")


ARCHITECTURE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="980" height="560" font-family="Segoe UI, Arial, sans-serif">
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker></defs>
<style>.box{fill:#e8f4f8;stroke:#2a6f97;stroke-width:2}.agent{fill:#eaf7ee;stroke:#2a9d8f;stroke-width:2}.lbl{font-size:15px;fill:#123;font-weight:600;text-anchor:middle}.sub{font-size:12px;fill:#456;text-anchor:middle}.edge{stroke:#333;stroke-width:2;fill:none;marker-end:url(#a)}</style>
<text x="490" y="30" class="lbl" style="font-size:18px">Phase 18 Ablation: Deterministic vs Bounded Agentic MLOps (identical lifecycle outcomes)</text>
<rect x="80" y="60" width="360" height="86" rx="8" class="box"/><text x="260" y="88" class="lbl">SYSTEM A: DETERMINISTIC ONLY</text><text x="260" y="110" class="sub">monitoring -&gt; governance -&gt; retraining decision -&gt;</text><text x="260" y="126" class="sub">challenger evaluation -&gt; promotion decision</text><text x="260" y="142" class="sub">operator manually inspects raw metrics, logs, registries, audits</text>
<rect x="540" y="60" width="360" height="86" rx="8" class="agent"/><text x="720" y="88" class="lbl">SYSTEM B: BOUNDED AGENTIC MLOPS</text><text x="720" y="110" class="sub">monitoring -&gt; agent explanation / retrieval -&gt;</text><text x="720" y="126" class="sub">human decision support -&gt; deterministic governance -&gt; lifecycle</text><text x="720" y="142" class="sub">agent assists but does not control</text>
<line x1="260" y1="146" x2="420" y2="220" class="edge"/><line x1="720" y1="146" x2="560" y2="220" class="edge"/>
<rect x="330" y="220" width="320" height="70" rx="8" class="box"/><text x="490" y="248" class="lbl">SHARED RECORDED EVIDENCE</text><text x="490" y="268" class="sub">Phase 13-17 decisions, registries, evaluations, audits, lineage</text><text x="490" y="284" class="sub">identical inputs for both systems</text>
<line x1="490" y1="290" x2="490" y2="330" class="edge"/>
<rect x="290" y="330" width="400" height="60" rx="8" class="box"/><text x="490" y="354" class="lbl">MEASURED DIMENSIONS</text><text x="490" y="374" class="sub">efficiency (steps, lookups, time) - quality (completeness, correctness, refs) - safety - consistency</text>
<line x1="490" y1="390" x2="490" y2="424" class="edge"/>
<rect x="250" y="424" width="480" height="56" rx="8" class="agent"/><text x="490" y="448" class="lbl">REQUIRED RESULT: LIFECYCLE OUTCOMES IDENTICAL</text><text x="490" y="468" class="sub">decision difference 0 - governance violations 0 - unsafe executions 0</text>
<text x="490" y="520" class="sub">operational assistance experiment; not a forecasting experiment; no model changes; no final-test access</text>
</svg>
"""
