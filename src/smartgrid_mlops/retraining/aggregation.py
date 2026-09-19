"""Aggregation of request-policy correctness, adaptation performance, and safety metrics."""
from __future__ import annotations


def request_policy_metrics(cases: list[dict]) -> dict:
    total = len(cases)
    expected = {d: sum(1 for c in cases if c["expected_decision"] == d) for d in ("ALLOW", "DENY", "DEFER")}
    correct = sum(1 for c in cases if c["actual_decision"] == c["expected_decision"])
    false_allows = sum(1 for c in cases if c["expected_decision"] != "ALLOW" and c["actual_decision"] == "ALLOW")
    false_denies = sum(1 for c in cases if c["expected_decision"] != "DENY" and c["actual_decision"] == "DENY")
    false_defers = sum(1 for c in cases if c["expected_decision"] != "DEFER" and c["actual_decision"] == "DEFER")
    unsafe = [c for c in cases if c.get("unsafe_attempt")]
    unsafe_blocked = [c for c in unsafe if c["actual_decision"] != "ALLOW"]
    unnecessary = [c for c in cases if c.get("unnecessary_attempt")]
    unnecessary_prevented = [c for c in unnecessary if c["actual_decision"] != "ALLOW"]
    return {
        "total_request_scenarios": total, "expected_allow": expected["ALLOW"],
        "expected_deny": expected["DENY"], "expected_defer": expected["DEFER"],
        "correct_decisions": correct, "decision_correctness_percent": 100.0 * correct / total if total else 0.0,
        "false_allows": false_allows, "false_denies": false_denies, "false_defers": false_defers,
        "unsafe_retraining_attempts": len(unsafe), "unsafe_retraining_attempts_blocked": len(unsafe_blocked),
        "unsafe_retraining_prevention_rate_percent": 100.0 * len(unsafe_blocked) / len(unsafe) if unsafe else None,
        "unnecessary_retraining_attempts": len(unnecessary),
        "unnecessary_retraining_prevented": len(unnecessary_prevented),
        "data_quality_blocked_requests": sum(1 for c in cases if "DATA_QUALITY_BLOCK" in c.get("reason", "")),
        "final_test_violations_blocked": sum(1 for c in cases if "FINAL_TEST_POLICY_VIOLATION" in c.get("reason", "")),
    }


def adaptation_metrics(results: list[dict]) -> dict:
    by_target: dict[str, dict] = {}
    for r in results:
        bucket = by_target.setdefault(r["target"], {"gains": [], "improved": 0, "degraded": 0, "no_change": 0,
                                                    "ref_mae": [], "chal_mae": [], "scenarios": 0})
        bucket["scenarios"] += 1
        bucket["ref_mae"].append(r["reference_mae"]); bucket["chal_mae"].append(r["challenger_mae"])
        bucket["gains"].append(r["adaptation_gain_percent"])
        if r["adaptation_gain_percent"] > 1e-9: bucket["improved"] += 1
        elif r["adaptation_gain_percent"] < -1e-9: bucket["degraded"] += 1
        else: bucket["no_change"] += 1
    summary = {}
    for target, b in by_target.items():
        n = len(b["gains"]) or 1
        summary[target] = {"scenarios": b["scenarios"],
                           "mean_reference_post_drift_mae": sum(b["ref_mae"]) / n,
                           "mean_challenger_post_drift_mae": sum(b["chal_mae"]) / n,
                           "mean_adaptation_gain_percent": sum(b["gains"]) / n,
                           "improved_cases": b["improved"], "degraded_cases": b["degraded"],
                           "no_material_change_cases": b["no_change"]}
    by_severity: dict[str, list[float]] = {}
    for r in results: by_severity.setdefault(r["severity"], []).append(r["adaptation_gain_percent"])
    severity_summary = {s: {"mean_adaptation_gain_percent": sum(v) / len(v), "cases": len(v)}
                        for s, v in by_severity.items()}
    return {"by_target": summary, "by_severity": severity_summary, "total_scenarios": len(results)}


def job_metrics(jobs: list[dict]) -> dict:
    completed = [j for j in jobs if j["status"] == "COMPLETED"]
    runtimes = sorted(j["runtime_seconds"] for j in completed)
    n = len(runtimes) or 1
    return {"planned_jobs": len(jobs), "started_jobs": len(jobs), "completed_jobs": len(completed),
            "failed_jobs": sum(1 for j in jobs if j["status"] == "FAILED"),
            "mean_runtime_seconds": sum(runtimes) / n,
            "median_runtime_seconds": runtimes[len(runtimes) // 2] if runtimes else 0.0,
            "total_new_data_rows": sum(j["new_data_row_count"] for j in completed),
            "total_training_rows": sum(j["training_row_count"] for j in completed)}


def safety_metrics(request_metrics: dict, jobs: list[dict], challengers: list[dict]) -> dict:
    return {
        "drift_alerts_considered": request_metrics["total_request_scenarios"],
        "retraining_requests_generated": request_metrics["total_request_scenarios"],
        "allow": request_metrics["expected_allow"], "deny": request_metrics["expected_deny"],
        "defer": request_metrics["expected_defer"],
        "unsafe_retraining_attempts": request_metrics["unsafe_retraining_attempts"],
        "unsafe_retraining_attempts_blocked": request_metrics["unsafe_retraining_attempts_blocked"],
        "unsafe_retraining_prevention_rate_percent": request_metrics["unsafe_retraining_prevention_rate_percent"],
        "unnecessary_retraining_attempts": request_metrics["unnecessary_retraining_attempts"],
        "unnecessary_retraining_prevented": request_metrics["unnecessary_retraining_prevented"],
        "data_quality_blocked_requests": request_metrics["data_quality_blocked_requests"],
        "final_test_violations_blocked": request_metrics["final_test_violations_blocked"],
        "actual_retraining_jobs": len(jobs),
        "automatic_promotions": 0, "reference_replacements": 0, "governance_bypasses": 0,
        "challengers_registered": len(challengers),
        "challenger_terminal_state": "REGISTERED_CHALLENGER",
    }
