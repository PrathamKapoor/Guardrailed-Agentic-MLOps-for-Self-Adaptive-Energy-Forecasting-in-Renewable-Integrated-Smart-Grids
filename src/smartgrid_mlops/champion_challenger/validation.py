"""Phase 16 guardrails: final-test denial, no-automatic-promotion invariant,
forbidden runner flags, prior-freeze protection."""
from __future__ import annotations
import hashlib
from pathlib import Path

FINAL_TEST_FORBIDDEN = ("final_test", "final-test", "november", "december")
FORBIDDEN_RUNNER_FLAGS = ("--final-test", "--final", "--hpo", "--hyperparameter")


def assert_no_final_test_access(path=None) -> None:
    if path and any(x in str(path).lower() for x in FINAL_TEST_FORBIDDEN):
        raise ValueError("FINAL_TEST_POLICY_VIOLATION")


def assert_no_forbidden_runner_flags(source: str) -> None:
    for flag in FORBIDDEN_RUNNER_FLAGS:
        if f'"{flag}"' in source or f"'{flag}'" in source:
            raise ValueError(f"Forbidden runner flag {flag}")


def assert_no_automatic_promotion(decision, canary, promoted: bool) -> None:
    """A promotion may exist only after a governed APPROVE plus a passing canary."""
    if promoted and not (decision.decision == "APPROVE" and canary is not None and canary.passed):
        raise ValueError("AUTOMATIC_PROMOTION_FORBIDDEN: promotion without governed approval and canary")


def assert_prior_freezes_unchanged(project_root: Path, expected: dict[str, str]) -> None:
    for relative, checksum in expected.items():
        actual = hashlib.sha256((project_root / relative).read_bytes()).hexdigest()
        if actual != checksum:
            raise ValueError(f"PRIOR_FREEZE_MODIFIED: {relative}")
