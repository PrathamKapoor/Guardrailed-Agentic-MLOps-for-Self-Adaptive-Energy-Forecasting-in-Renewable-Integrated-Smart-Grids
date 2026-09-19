from __future__ import annotations


def metadata(model) -> dict:
    return {"estimator_class": type(model).__name__, "has_fit": hasattr(model, "fit"), "has_predict": hasattr(model, "predict")}
