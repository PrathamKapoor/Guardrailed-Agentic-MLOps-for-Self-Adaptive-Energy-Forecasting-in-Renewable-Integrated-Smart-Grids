from __future__ import annotations

def select_feature_set(scores: dict[str, float], counts: dict[str, int], tie_threshold_percent: float) -> str:
    """Use development MAE only; practically tied sets prefer fewer features."""
    best=min(scores.values())
    eligible=[name for name,value in scores.items() if 100*(value-best)/best <= tie_threshold_percent]
    return min(eligible,key=lambda name:(counts[name],name))

def relative_mae_change(reference: float, candidate: float) -> float:
    return 100*(reference-candidate)/reference
