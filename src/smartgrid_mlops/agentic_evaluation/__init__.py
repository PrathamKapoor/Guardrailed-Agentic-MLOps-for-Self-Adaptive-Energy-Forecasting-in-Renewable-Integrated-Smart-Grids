"""Controlled ablation: deterministic MLOps vs bounded agentic MLOps (Phase 18).

Both systems must produce identical lifecycle outcomes. The experiment measures
operational burden (steps, lookups, estimated time), explanation quality, and
safety equivalence — never model accuracy and never lifecycle changes."""
from .schemas import TaskResult, ComparisonResult

__all__ = ["TaskResult", "ComparisonResult"]
