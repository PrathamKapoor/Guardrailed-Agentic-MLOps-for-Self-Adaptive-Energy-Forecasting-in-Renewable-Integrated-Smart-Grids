"""Reference-vs-challenger metric comparison on matched timestamps."""
from __future__ import annotations
from smartgrid_mlops.experimental_design.statistics import relative_improvement

METRIC_KEYS = ("MAE", "RMSE", "sMAPE", "nMAE", "nRMSE")


def comparison_record(*, reference_metrics: dict, challenger_metrics: dict, matched_rows: int,
                      same_target: bool = True, same_feature_representation: bool = True,
                      same_evaluation_protocol: bool = True) -> dict:
    if not same_target or not same_feature_representation or not same_evaluation_protocol:
        raise ValueError("challenger evaluation requires same target, feature representation, and protocol")
    if matched_rows <= 0:
        raise ValueError("challenger evaluation requires matched timestamps")
    record = {"matched_rows": matched_rows,
              "protocol_match": True,
              "reference": {k: float(reference_metrics[k]) for k in METRIC_KEYS},
              "challenger": {k: float(challenger_metrics[k]) for k in METRIC_KEYS}}
    record["relative_mae_improvement_percent"] = relative_improvement(reference_metrics["MAE"], challenger_metrics["MAE"])
    record["challenger_better"] = challenger_metrics["MAE"] < reference_metrics["MAE"]
    return record
