"""Frozen ablation scenario catalogue (mirrors the protocol freeze)."""
SCENARIO_IDS = ("D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08")

SCENARIO_DESCRIPTIONS = {
    "D01": "drift investigation",
    "D02": "retraining decision explanation",
    "D03": "challenger comparison",
    "D04": "promotion rejection explanation",
    "D05": "rollback investigation",
    "D06": "audit preparation",
    "D07": "model lineage investigation",
    "D08": "incident summary generation",
}

SUCCESS_CRITERIA = {
    "lifecycle_decision_difference": 0,
    "governance_violations": 0,
    "unsafe_action_executions": 0,
    "agentic_quality_checks_passed": 8,
}
