"""Read-only queries over Phase 15 decision/job/challenger artifacts."""
from __future__ import annotations
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists(): return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_json(path: Path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def decisions(out_dir: Path) -> list[dict]:
    return read_jsonl(Path(out_dir) / "decisions/retraining_decisions.jsonl")


def jobs(out_dir: Path) -> list[dict]:
    return [read_json(p) for p in sorted((Path(out_dir) / "jobs").glob("*.json")) if p]


def evaluations(out_dir: Path) -> list[dict]:
    return [read_json(p) for p in sorted((Path(out_dir) / "evaluations").glob("*.json")) if p]


def challengers(project_root: Path) -> list[dict]:
    document = read_json(Path(project_root) / "artifacts/model_registry/phase_15_challengers.yaml")
    return document["entries"] if document else []


def known_evidence_ids(out_dir: Path) -> set[str]:
    return {e["event_id"] for e in read_jsonl(Path(out_dir) / "evidence/drift_events.jsonl")}
