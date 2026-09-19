"""Bounded agent memory: structured summaries only.

Never stores chain-of-thought, private reasoning traces, or prompts. Every
record is field-filtered to the frozen memory schema before persistence."""
from __future__ import annotations
import json
from pathlib import Path
from .schemas import MEMORY_FIELDS


class MemoryStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / "agent_memory.jsonl"

    def store(self, record: dict) -> dict:
        filtered = {k: record.get(k) for k in MEMORY_FIELDS if k in record}
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(filtered, sort_keys=True) + "\n")
        return filtered

    def read(self) -> list[dict]:
        if not self.path.exists(): return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def by_agent(self, agent_id: str) -> list[dict]:
        return [r for r in self.read() if r.get("agent_id") == agent_id]
