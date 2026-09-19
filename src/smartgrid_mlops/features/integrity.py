"""Binary and logical integrity helpers for feature artifacts.

Logical hashes intentionally encode field order, names, types, row order, and
canonical values, while excluding Parquet writer metadata.  They therefore
detect scientific-data changes independently of byte serialization changes.
"""
from __future__ import annotations

import hashlib
import math
import struct
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

INTEGRITY_AUDIT = "INTEGRITY_AUDIT"


def binary_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _value_bytes(value: Any) -> bytes:
    if value is None:
        return b"N"
    if isinstance(value, float):
        if math.isnan(value):
            return b"Fnan"
        return b"F" + struct.pack("!d", value)
    if isinstance(value, int):
        return b"I" + str(value).encode("ascii")
    if isinstance(value, (datetime, date)):
        return b"T" + value.isoformat().encode("utf-8")
    if isinstance(value, bytes):
        return b"B" + len(value).to_bytes(8, "big") + value
    text = str(value).encode("utf-8")
    return b"S" + len(text).to_bytes(8, "big") + text


def logical_content_sha256(table: pa.Table) -> str:
    """Hash ordered logical content, excluding non-scientific schema metadata."""
    digest = hashlib.sha256()
    digest.update(b"smartgrid-logical-content-v1\0")
    digest.update(str(table.num_rows).encode("ascii") + b"\0")
    for field, column in zip(table.schema, table.columns):
        digest.update(field.name.encode("utf-8") + b"\0" + str(field.type).encode("utf-8") + b"\0")
        for value in column.to_pylist():
            encoded = _value_bytes(value)
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
    return digest.hexdigest()


def parquet_logical_content_sha256(path: str | Path) -> str:
    return logical_content_sha256(pq.read_table(path))
