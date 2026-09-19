SIGNIFICANCE_LEVEL = 0.05
MULTIPLE_COMPARISON_METHOD = "Holm-Bonferroni"

def relative_improvement(baseline: float, model: float) -> float:
    if baseline == 0: raise ValueError("baseline metric must be nonzero")
    return 100 * (baseline-model) / baseline
