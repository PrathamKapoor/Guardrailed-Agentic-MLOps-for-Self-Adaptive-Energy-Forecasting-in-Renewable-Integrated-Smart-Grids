"""Source metadata inspection helpers."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def profile_metadata(path: Path, categorical_columns: list[str]) -> dict[str, Any]:
    fields, rows = read_table(path)
    return {
        "rows": len(rows), "columns": len(fields), "column_names": fields,
        "missing_values": {field: sum(not row.get(field, "").strip() or row.get(field, "").strip() == "NA" for row in rows) for field in fields},
        "categorical_values": {field: dict(sorted(Counter(row.get(field, "") for row in rows).items())) for field in categorical_columns},
    }
