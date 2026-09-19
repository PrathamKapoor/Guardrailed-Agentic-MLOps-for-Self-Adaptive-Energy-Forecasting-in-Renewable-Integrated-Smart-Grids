"""Operational task workload D01-D08 built from real Phase 13-17 evidence.

Each task represents "an operator must understand this event" — a deterministic
task over recorded evidence. No humans are simulated with LMs."""
from __future__ import annotations
import json
from pathlib import Path


def _jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def load_workload(project_root: Path) -> dict[str, dict]:
    root = Path(project_root)
    drift = _jsonl(root / "artifacts/retraining/phase_15/evidence/drift_events.jsonl")
    decisions = _jsonl(root / "artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl")
    evaluations = [json.loads(p.read_text(encoding="utf-8"))
                   for p in sorted((root / "artifacts/retraining/phase_15/evaluations").glob("*.json"))]
    promotion = json.loads((root / "artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json").read_text())["results"]
    champion = json.loads((root / "artifacts/model_registry/phase_16_champion_registry.yaml").read_text())
    audit = _jsonl(root / "artifacts/mlops/audit/events.jsonl")

    drift_event = next((e for e in drift if e.get("severity") == "CRITICAL"), drift[0] if drift else {})
    deny = next((d for d in decisions if d.get("decision") == "DENY" and "DATA_QUALITY_BLOCK" in d.get("reason_codes", [])), {})
    allow = next((d for d in reversed(decisions) if d.get("decision") == "ALLOW" and d.get("simulation_scenario_id")), {})
    evaluation = evaluations[0] if evaluations else {}
    rejection = next((r for r in promotion if "BENCHMARK_REQUIREMENT_NOT_SATISFIED" in r["reason_codes"]), promotion[0])
    rollback = next((r for r in champion["rollbacks"] if r["outcome"] == "ROLLBACK_COMPLETED"), {})
    audit_subject = rollback.get("promoted_model_id", "SIM-CHAL-CC05")
    subject_events = [e for e in audit if e.get("subject_id") == audit_subject]

    return {
        "D01": {"description": "drift investigation",
                "agent_query": ("EXPLAIN_DRIFT", {"drift_event": drift_event,
                                                  "evidence_refs": ["artifacts/retraining/phase_15/evidence/drift_events.jsonl"]}),
                "sources": ["artifacts/retraining/phase_15/evidence/drift_events.jsonl"],
                "records_scanned": max(len(drift), 1),
                "expected_facts": {"target": drift_event.get("target"), "severity": drift_event.get("severity")},
                "expected_outcome": "NO_ACTION_EVIDENCE_ONLY",
                "correctness_substrings": [str(drift_event.get("target")), str(drift_event.get("severity"))]},
        "D02": {"description": "retraining decision explanation",
                "agent_query": ("EXPLAIN_RETRAINING", {"retraining_decision": deny,
                                                       "evidence_refs": ["artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl"]}),
                "sources": ["artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl"],
                "records_scanned": max(len(decisions), 1),
                "expected_facts": {"decision": "DENY", "primary_reason": "DATA_QUALITY_BLOCK"},
                "expected_outcome": "RETRAINING_DENIED",
                "correctness_substrings": ["denied", "DATA_QUALITY_BLOCK"]},
        "D03": {"description": "challenger comparison",
                "agent_query": ("GENERATE_REPORT", {"report_kind": "MODEL_COMPARISON",
                                                    "challenger_evaluations": [{"challenger_id": r["challenger_id"],
                                                                                "decision": r["decision"],
                                                                                "reason_codes": r["reason_codes"]}
                                                                               for r in promotion[:3]],
                                                    "evidence_refs": ["artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json"]}),
                "sources": ["artifacts/model_registry/phase_15_challengers.yaml",
                            "artifacts/retraining/phase_15/evaluations"],
                "verification_ref": "artifacts/model_registry/phase_15_challengers.yaml",
                "records_scanned": 18,
                "expected_facts": {"challengers_registered": 18, "promotion_eligible": False},
                "expected_outcome": "REGISTERED_CHALLENGER_NO_PROMOTION",
                "correctness_substrings": ["promotion", "not sufficient"]},
        "D04": {"description": "promotion rejection explanation",
                "agent_query": ("EXPLAIN_PROMOTION", {"promotion_decision": rejection["decision_record"],
                                                      "evidence_refs": ["artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json"]}),
                "sources": ["artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json"],
                "records_scanned": len(promotion),
                "expected_facts": {"decision": "REJECT", "failed_gate": "BENCHMARK_GATE"},
                "expected_outcome": "PROMOTION_REJECTED",
                "correctness_substrings": ["REJECT", "BENCHMARK"]},
        "D05": {"description": "rollback investigation",
                "agent_query": ("EXPLAIN_ROLLBACK", {"rollback_record": rollback,
                                                     "evidence_refs": ["artifacts/model_registry/phase_16_champion_registry.yaml"]}),
                "sources": ["artifacts/model_registry/phase_16_champion_registry.yaml"],
                "records_scanned": len(champion.get("promotions", [])) + len(champion.get("rollbacks", [])),
                "expected_facts": {"outcome": "ROLLBACK_COMPLETED", "previous_model_restored": True},
                "expected_outcome": "ROLLBACK_COMPLETED_REFERENCE_RESTORED",
                "correctness_substrings": ["ROLLBACK_COMPLETED", "verification"]},
        "D06": {"description": "audit preparation",
                "agent_query": ("GENERATE_REPORT", {"report_kind": "AUDIT_EXPLANATION",
                                                    "audit_events": subject_events[:10],
                                                    "evidence_refs": ["artifacts/mlops/audit/events.jsonl"]}),
                "sources": ["artifacts/mlops/audit/events.jsonl"],
                "records_scanned": max(len(audit), 1),
                "expected_facts": {"events_for_subject": len(subject_events)},
                "expected_outcome": "AUDIT_REPORT_PRODUCED_NO_ACTION",
                "correctness_substrings": ["audited actions"]},
        "D07": {"description": "model lineage investigation",
                "agent_query": ("RETRIEVE_EVIDENCE", {"source": "lineage_index",
                                                      "subject_id": "MLOPS-REF-LOAD-H24-V1"}),
                "sources": ["artifacts/mlops/lineage/lineage_index.yaml"],
                "records_scanned": 18,
                "expected_facts": {"trace_reaches_dataset": True},
                "expected_outcome": "LINEAGE_VERIFIED_NO_ACTION",
                "correctness_substrings": ["retrieved", "structured records"]},
        "D08": {"description": "incident summary generation",
                "agent_query": ("GENERATE_REPORT", {"report_kind": "INCIDENT_REPORT",
                                                    "drift_event": drift_event, "retraining_decision": deny,
                                                    "evidence_refs": ["artifacts/retraining/phase_15/evidence/drift_events.jsonl",
                                                                      "artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl"]}),
                "sources": ["artifacts/retraining/phase_15/evidence/drift_events.jsonl",
                            "artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl"],
                "records_scanned": max(len(drift), 1) + max(len(decisions), 1),
                "expected_facts": {"drift_severity": drift_event.get("severity"), "retraining_decision": "DENY"},
                "expected_outcome": "INCIDENT_SUMMARY_NO_ACTION",
                "correctness_substrings": ["Drift incident", "DENY"]},
    }
