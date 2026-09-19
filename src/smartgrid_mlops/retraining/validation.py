"""Phase 15 guardrails: final-test denial, forbidden-flag absence, frozen-spec preservation."""
from __future__ import annotations

FINAL_TEST_FORBIDDEN = ("final_test", "final-test", "november", "december")
FORBIDDEN_RUNNER_FLAGS = ("--final-test", "--final", "--hpo", "--hyperparameter")


def assert_no_final_test_access(path=None) -> None:
    if path and any(x in str(path).lower() for x in FINAL_TEST_FORBIDDEN):
        raise ValueError("FINAL_TEST_POLICY_VIOLATION")


def assert_no_forbidden_runner_flags(source: str) -> None:
    for flag in FORBIDDEN_RUNNER_FLAGS:
        if f'"{flag}"' in source or f"'{flag}'" in source:
            raise ValueError(f"Forbidden runner flag {flag}")


def assert_spec_frozen(model_family: str, hyperparameters: dict, feature_names: list[str],
                       expected_family: str, expected_hyperparameters: dict,
                       expected_feature_names: list[str]) -> None:
    if model_family != expected_family:
        raise ValueError("MODEL_FAMILY_CHANGED: retraining must reuse the frozen family")
    if hyperparameters != expected_hyperparameters:
        raise ValueError("HYPERPARAMETERS_CHANGED: retraining must reuse frozen hyperparameters (no HPO)")
    if list(feature_names) != list(expected_feature_names):
        raise ValueError("FEATURES_CHANGED: retraining must reuse the frozen feature set (no selection)")
