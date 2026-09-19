#!/usr/bin/env python3
"""Phase 16 research tables and figures. No final-test access."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "artifacts/champion_challenger/phase_16"
FIG = ROOT / "artifacts/research_figures/phase_16"


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


def main():
    real = read_json(OUT / "evaluations/real_phase15_challengers.json")
    scenarios = read_json(OUT / "scenario_results/cc_scenarios.json")
    summary = read_json(OUT / "manifests/simulation_summary.json") or {}
    registry = read_json(ROOT / "artifacts/model_registry/phase_16_champion_registry.yaml") or {}

    if real:
        headers = ["Challenger", "Target", "Reference MAE", "Challenger MAE", "Improvement %",
                   "Decision", "Primary Reason", "Unsafe Attempt", "Blocked"]
        rows = [[r["challenger_id"], r["target"], round(r["decision_record"]["metrics"]["reference_mae"], 3),
                 round(r["decision_record"]["metrics"]["challenger_mae"], 3),
                 round(r["relative_mae_improvement_percent"], 3), r["decision"],
                 r["reason_codes"][0], "YES" if r["unsafe_attempt"] else "NO",
                 "YES" if r["blocked"] else "NO"] for r in real["results"]]
        write_csv(ROOT / "artifacts/research_tables/champion_challenger_evaluation_results.csv", headers, rows)
        write_md(ROOT / "reports/tables/champion_challenger_evaluation_results.md",
                 "Champion-challenger evaluation of the 18 registered Phase 15 challengers (development/simulation)", headers, rows)
    if scenarios:
        headers = ["Scenario", "Case", "Decision", "Outcome", "Expected", "Correct", "Reason Codes"]
        from smartgrid_mlops.champion_challenger.simulation import SCENARIO_DESCRIPTIONS
        rows = [[r["scenario_id"], SCENARIO_DESCRIPTIONS[r["scenario_id"]], r["decision"], r["outcome"],
                 r["expected_outcome"], "YES" if r["correct"] else "NO", ",".join(r["reason_codes"])]
                for r in scenarios["results"]]
        write_csv(ROOT / "artifacts/research_tables/promotion_scenario_results.csv", headers, rows)
        write_md(ROOT / "reports/tables/promotion_scenario_results.md", "Frozen promotion and rollback scenarios CC01-CC06", headers, rows)
        rows = [[k, v] for k, v in summary.items()]
        write_md(ROOT / "reports/tables/champion_challenger_safety_metrics.md", "Champion-challenger safety metrics", ["Metric", "Value"], rows)

    FIG.mkdir(parents=True, exist_ok=True)
    _architecture_figure()
    _outcomes_figure(summary)
    dump(FIG / "figure_manifest.yaml", {"phase": "16", "final_test_status": "NOT_ACCESSED", "figures": [
        {"figure_id": "FIG-P16-01", "path": "artifacts/research_figures/phase_16/champion_challenger_architecture.svg",
         "source_artifacts": ["config/governance/phase_16_promotion_policy.yaml"],
         "scenario_role": "architecture", "target": "all", "evidence_status": "VALID",
         "generation_script": "scripts/finalize_phase16_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "governed promotion and rollback paths"},
        {"figure_id": "FIG-P16-02", "path": "artifacts/research_figures/phase_16/promotion_outcomes.svg",
         "source_artifacts": ["artifacts/champion_challenger/phase_16/manifests/simulation_summary.json"],
         "scenario_role": "outcomes", "target": "all", "evidence_status": "VALID",
         "generation_script": "scripts/finalize_phase16_artifacts.py", "final_test_status": "NOT_ACCESSED",
         "paper_relevance": "promotion decision counts and safety metrics"}]})
    print(json.dumps({"tables": 3, "figures": 2, "summary": summary}, indent=2))


ARCHITECTURE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="980" height="640" font-family="Segoe UI, Arial, sans-serif">
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker>
<marker id="b" markerWidth="12" markerHeight="12" refX="9" refY="4" orient="auto"><path d="M0,0 L0,8 L10,4 z" fill="#b3261e"/></marker></defs>
<style>.box{fill:#e8f4f8;stroke:#2a6f97;stroke-width:2}.bad{fill:#fdecea;stroke:#b3261e;stroke-width:2}.lbl{font-size:15px;fill:#123;font-weight:600;text-anchor:middle}.sub{font-size:12px;fill:#456;text-anchor:middle}.edge{stroke:#333;stroke-width:2;fill:none;marker-end:url(#a)}.rb{stroke:#b3261e;stroke-width:3;stroke-dasharray:6 4;fill:none}</style>
<text x="490" y="30" class="lbl" style="font-size:19px">Champion-Challenger Governance (Phase 16, deterministic, simulation only)</text>
<rect x="330" y="50" width="320" height="50" rx="8" class="box"/><text x="490" y="80" class="lbl">REGISTERED_REFERENCE</text>
<line x1="490" y1="100" x2="490" y2="128" class="edge"/>
<rect x="310" y="128" width="360" height="50" rx="8" class="box"/><text x="490" y="150" class="lbl">CHALLENGER EVALUATION</text><text x="490" y="168" class="sub">same timestamps, target, features, protocol; MAE primary</text>
<line x1="490" y1="178" x2="490" y2="206" class="edge"/>
<rect x="250" y="206" width="480" height="64" rx="8" class="box"/><text x="490" y="228" class="lbl">GOVERNANCE POLICY 16.0.0 (13 gates)</text><text x="490" y="247" class="sub">registration, lineage, fingerprints, protocol, metadata, evaluation, performance,</text><text x="490" y="261" class="sub">benchmark, statistics, approval — improved MAE alone is NOT sufficient</text>
<line x1="360" y1="270" x2="230" y2="312" class="edge"/><line x1="490" y1="270" x2="490" y2="312" class="edge"/><line x1="620" y1="270" x2="750" y2="312" class="edge"/>
<rect x="120" y="312" width="200" height="44" rx="8" class="bad"/><text x="220" y="338" class="lbl" style="fill:#b3261e">REJECT</text>
<rect x="390" y="312" width="200" height="44" rx="8" class="box"/><text x="490" y="338" class="lbl">DEFER</text>
<rect x="660" y="312" width="200" height="44" rx="8" class="box"/><text x="760" y="338" class="lbl">APPROVE</text>
<line x1="760" y1="356" x2="760" y2="386" class="edge"/>
<rect x="600" y="386" width="320" height="50" rx="8" class="box"/><text x="760" y="408" class="lbl">CANARY SIMULATION</text><text x="760" y="426" class="sub">guardrail: no MAE regression; failure rolls back before activation</text>
<line x1="760" y1="436" x2="760" y2="464" class="edge"/>
<rect x="600" y="464" width="320" height="50" rx="8" class="box"/><text x="760" y="486" class="lbl">ACTIVE MODEL (PROMOTED, SIMULATION)</text><text x="760" y="504" class="sub">previous reference preserved (artifact + fingerprint + lineage)</text>
<path d="M700 514 C 560 560, 400 560, 300 520" class="rb" marker-end="url(#b)"/>
<rect x="140" y="520" width="320" height="76" rx="8" class="bad"/><text x="300" y="546" class="lbl" style="fill:#b3261e">ROLLBACK (verified restoration)</text><text x="300" y="566" class="sub" style="fill:#b3261e">degradation detected -&gt; artifact, fingerprint, lineage, load checks</text><text x="300" y="582" class="sub" style="fill:#b3261e">verification failure -&gt; ROLLBACK_BLOCKED; previous model restored</text>
<text x="490" y="628" class="sub">Phase 13 lifecycle registry unchanged; promotion states are simulation-scoped; AUTOMATIC PROMOTION = FORBIDDEN</text>
</svg>
"""


def _architecture_figure():
    (FIG / "champion_challenger_architecture.svg").write_text(ARCHITECTURE_SVG, encoding="utf-8")


def _outcomes_figure(summary: dict):
    items = [("Approved", summary.get("approved", 0), "#2a9d8f"),
             ("Rejected", summary.get("rejected", 0), "#e76f51"),
             ("Deferred", summary.get("deferred", 0), "#e9c46a"),
             ("Unsafe blocked", summary.get("blocked_unsafe_promotions", 0), "#264653"),
             ("Rollbacks OK", summary.get("successful_rollback", 0), "#2a9d8f"),
             ("Rollbacks blocked", summary.get("failed_rollback", 0), "#b3261e")]
    bars = "".join(
        f'<rect x="200" y="{70 + i * 44}" width="{max(30, v * 55)}" height="30" fill="{c}" stroke="#333"/>'
        f'<text x="190" y="{91 + i * 44}" text-anchor="end" font-size="14" fill="#123">{n}</text>'
        f'<text x="{210 + max(30, v * 55)}" y="{91 + i * 44}" font-size="14" fill="#123">{v}</text>'
        for i, (n, v, c) in enumerate(items))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="400" font-family="Segoe UI, Arial, sans-serif">
<text x="380" y="36" text-anchor="middle" font-size="18" font-weight="600">Promotion and rollback outcomes (24 governed decisions; 18 real + 6 frozen scenarios)</text>
{bars}
<text x="380" y="380" text-anchor="middle" font-size="13" fill="#456">automatic promotions: 0 — every promotion required policy evaluation, approval, and canary</text>
</svg>"""
    (FIG / "promotion_outcomes.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
