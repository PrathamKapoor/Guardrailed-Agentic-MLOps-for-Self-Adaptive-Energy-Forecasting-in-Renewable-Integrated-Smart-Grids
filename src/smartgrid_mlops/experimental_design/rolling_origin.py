from __future__ import annotations

from datetime import datetime

VALIDATION_MONTHS = tuple(range(5, 11))

def fold_boundaries() -> list[dict]:
    folds=[]
    for index, month in enumerate(VALIDATION_MONTHS, 1):
        next_month=datetime(2020,month+1,1) if month<12 else datetime(2021,1,1)
        folds.append({"fold_id":f"F{index:02d}","training_start":datetime(2020,1,1),"training_end_exclusive":datetime(2020,month,1),"validation_start":datetime(2020,month,1),"validation_end_exclusive":next_month})
    return folds

def fold_membership(rows: list[dict], boundary: dict) -> tuple[list[dict],list[dict]]:
    train=[r for r in rows if boundary["training_start"] <= r["target_timestamp"] < boundary["training_end_exclusive"]]
    validation=[r for r in rows if boundary["validation_start"] <= r["target_timestamp"] < boundary["validation_end_exclusive"]]
    return train,validation
