"""Deterministic-only baseline: the manual evidence-inspection workflow.

The operator receives raw metrics, logs, registry information, and audit
events, and must open each artifact to derive the required facts. Steps,
lookups, and records scanned are counted; time is estimated with the frozen
human-inspection cost model (no real operators are measured)."""
from __future__ import annotations
import json
from pathlib import Path
from .schemas import COST_MODEL, TaskResult


def _extract_facts(scenario_id: str, project_root: Path, spec: dict) -> tuple[dict, bool, list[str]]:
    """Derive the task's required facts by inspecting the raw sources."""
    root = Path(project_root)
    facts: dict = {}
    refs: list[str] = []
    for source in spec["sources"]:
        refs.append(source)
        path = root / source
        if not path.exists():
            continue
        if path.suffix == ".jsonl":
            records = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        elif path.is_dir():
            records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(path.glob("*.json"))]
        else:
            records = [json.loads(path.read_text(encoding="utf-8"))]
        facts = _merge_facts(scenario_id, facts, records, source)
    expected = spec["expected_facts"]
    complete = all(facts.get(k) == v for k, v in expected.items())
    return facts, complete, refs


def _merge_facts(scenario_id: str, facts: dict, records: list, source: str) -> dict:
    import json as _json
    if scenario_id == "D01":
        event = next((r for r in records if r.get("severity") == "CRITICAL"), records[0] if records else {})
        facts.update({"target": event.get("target"), "severity": event.get("severity")})
    elif scenario_id == "D02":
        deny = next((r for r in records if r.get("decision") == "DENY"
                     and "DATA_QUALITY_BLOCK" in r.get("reason_codes", [])), {})
        facts.update({"decision": deny.get("decision"), "primary_reason": (deny.get("reason_codes") or [""])[0]})
    elif scenario_id == "D03":
        if source.endswith("phase_15_challengers.yaml") and records:
            facts.update({"challengers_registered": len(records[0].get("entries", [])),
                          "promotion_eligible": any(e.get("promotion_eligible") for e in records[0].get("entries", []))})
    elif scenario_id == "D04":
        results = records[0].get("results", []) if records and isinstance(records[0], dict) else []
        rejection = next((r for r in results if "BENCHMARK_REQUIREMENT_NOT_SATISFIED" in r.get("reason_codes", [])),
                         results[0] if results else {})
        record = rejection.get("decision_record", {})
        failed = [g["gate"] for g in record.get("gate_results", []) if not g.get("passed")]
        facts.update({"decision": record.get("decision"), "failed_gate": failed[0] if failed else None})
    elif scenario_id == "D05":
        rollbacks = records[0].get("rollbacks", []) if records and isinstance(records[0], dict) else []
        rollback = next((r for r in rollbacks if r.get("outcome") == "ROLLBACK_COMPLETED"), {})
        facts.update({"outcome": rollback.get("outcome"),
                      "previous_model_restored": rollback.get("outcome") == "ROLLBACK_COMPLETED"})
    elif scenario_id == "D06":
        subject = "SIM-CHAL-CC05"
        facts.update({"events_for_subject": sum(1 for r in records if r.get("subject_id") == subject)})
    elif scenario_id == "D07":
        document = records[0] if records else {}
        nodes = {n["id"] for n in document.get("nodes", [])}
        reachable = "MLOPS-REF-LOAD-H24-V1" in nodes and "dataset:rts-gmlc-v2.0" in nodes
        facts.update({"trace_reaches_dataset": reachable})
    elif scenario_id == "D08":
        event = next((r for r in records if isinstance(r, dict) and r.get("severity") == "CRITICAL"),
                     next((r for r in records if isinstance(r, dict) and r.get("decision")), {}))
        if "severity" in event:
            facts.update({"drift_severity": event.get("severity")})
        if "decision" in event:
            facts.update({"retraining_decision": event.get("decision")})
    return facts


def run_deterministic(scenario_id: str, spec: dict, project_root: Path) -> TaskResult:
    facts, complete, refs = _extract_facts(scenario_id, project_root, spec)
    expected = spec["expected_facts"]
    correct = complete and all(facts.get(k) == v for k, v in expected.items())
    steps = len(spec["sources"])
    lookups = steps
    scanned = int(spec["records_scanned"])
    estimated = steps * COST_MODEL["per_artifact_inspection_seconds"] + scanned * COST_MODEL["per_record_scan_seconds"]
    return TaskResult(
        scenario_id=scenario_id, workflow_type="DETERMINISTIC", steps=steps, evidence_lookups=lookups,
        estimated_time_seconds=round(estimated, 4), completeness=complete, correctness=correct,
        evidence_refs=refs, derived_facts=facts, lifecycle_outcome=spec["expected_outcome"] if correct else "INCOMPLETE",
        unsafe_attempts=0, blocked=0, governance_violations=0)
