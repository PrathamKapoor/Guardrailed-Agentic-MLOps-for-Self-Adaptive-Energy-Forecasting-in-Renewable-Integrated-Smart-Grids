from __future__ import annotations

import json
from pathlib import Path

from .schemas import AuditEvent


def append_audit_event(path: Path, event: AuditEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


def read_audit_events(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
