from smartgrid_mlops.reporting.phase09_evidence import select_official_evidence


def test_official_aggregation_excludes_invalid_and_non_evidence_statuses():
    classical = {"id": "A", "evidence_status": "VALID", "framework": "sklearn", "implementation_id": "RANDOM_FOREST"}
    pytorch = {"id": "B", "evidence_status": "VALID", "framework": "pytorch", "implementation_id": "PYTORCH_MLP_V1"}
    invalid = {"id": "C", "evidence_status": "INVALIDATED", "framework": "sklearn", "implementation_id": "MLPRegressor", "deviation_id": "P9-DEV-001"}
    smoke = {"id": "E", "evidence_status": "NON_EVIDENCE_SMOKE"}
    audit = {"id": "F", "evidence_status": "AUDIT_ONLY"}
    included, rejected = select_official_evidence([classical, pytorch, invalid, smoke, audit])
    assert [record["id"] for record in included] == ["A", "B"]
    assert {item["record"]["id"] for item in rejected} == {"C", "E", "F"}


def test_neural_aggregation_requires_pytorch_identity_in_depth():
    pytorch = {"id": "B", "evidence_status": "VALID", "framework": "pytorch", "implementation_id": "PYTORCH_MLP_V1"}
    wrong_identity = {"id": "D", "evidence_status": "VALID", "framework": "sklearn", "implementation_id": "MLPRegressor"}
    included, rejected = select_official_evidence([pytorch, wrong_identity], neural_only=True)
    assert [record["id"] for record in included] == ["B"]
    assert rejected[0]["record"]["id"] == "D"
    assert "neural identity" in rejected[0]["reason"]
