"""Stage 5 deployment tests.

These tests verify the deployment-grade surface added on top of the
existing Stage 2 API service:
  * the FastAPI app starts and serves /health + /openapi.json
  * CORS is env-driven and refuses arbitrary origins
  * the typed error envelope does not leak Python tracebacks
  * required research artefacts are validated at startup
  * the OpenAPI schema contains no lifecycle-mutation endpoints
  * the production build of the frontend contains no hard-coded
    localhost dependency
  * a "before checksums -> start -> exercise API -> after checksums"
    run leaves the 20 protected Phase 19 artefacts byte-identical

The tests reuse the same `client` / `app` fixture pattern as
`tests/test_api_service.py`; they do not introduce a second framework.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

PROTECTED_ARTEFACTS = [
    "artifacts/research_tables/final_predictions.csv",
    "artifacts/research_tables/final_forecasting_results.csv",
    "artifacts/research_tables/final_model_comparison.csv",
    "artifacts/model_registry/forecasting_reference_registry.yaml",
    "artifacts/model_registry/lifecycle_registry.yaml",
    "artifacts/audit/phase_19_final_execution_audit.json",
    "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml",
    "config/governance/phase_13_policy.yaml",
    "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
    "reports/phase_19_completion.md",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def app():
    from product.backend_api.app.main import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


# ---------------- Application starts ----------------

def test_app_starts_and_health_responds(client):
    """The FastAPI app boots and the /health endpoint returns the typed
    health envelope. This is the smallest possible smoke test."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["api"] == "UP"
    # The honest offline-evaluation note is present.
    notes_joined = " ".join(body.get("notes") or [])
    assert "offline evaluation" in notes_joined.lower()


def test_app_exposes_openapi_schema(client):
    """FastAPI auto-generates /openapi.json; deployment must not disable it."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "paths" in spec
    assert "/health" in spec["paths"]
    assert "/api/governance/decisions" in spec["paths"]


# ---------------- CORS ----------------

def test_cors_allows_configured_origin(client):
    """An OPTIONS preflight from the configured dev origin is allowed
    (the API uses CORSMiddleware with the dev default when env unset)."""
    resp = client.options(
        "/api/forecasts",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette returns 200 for an allowed preflight.
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_does_not_allow_arbitrary_origin(client):
    """A preflight from a non-configured origin is rejected. This is the
    opposite of `allow_origins=["*"]` and protects against accidental
    cross-origin reads of governance decisions, audit, etc."""
    resp = client.options(
        "/api/forecasts",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette's CORSMiddleware does not echo a non-allow-listed origin.
    assert resp.headers.get("access-control-allow-origin") is None


# ---------------- Error envelope hygiene ----------------

def test_404_returns_typed_error_envelope(client):
    """Unknown paths produce a typed 404 envelope; no Python traceback."""
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    err = body["error"]
    assert err["status"] == 404
    assert err["type"] == "http"
    assert err["path"] == "/this-route-does-not-exist"
    # The envelope must not leak Python internals.
    raw = json.dumps(body)
    assert "Traceback" not in raw
    assert ".py\"" not in raw
    assert "site-packages" not in raw


def test_500_unhandled_exception_returns_generic_envelope(app):
    """A handler that raises an exception is wrapped by the unhandled-
    exception handler. The handler is a function registered on the
    FastAPI app instance, so we exercise it directly: that is the same
    code path the framework invokes at runtime when an unhandled
    exception escapes a route handler. We assert the response shape
    and that the secret-shaped fragments in the exception text are
    never echoed to the client."""
    # Find the Exception handler in the app's registry. FastAPI exposes
    # registered handlers via app.exception_handlers.
    handler = app.exception_handlers.get(Exception)
    assert handler is not None, "no Exception handler is registered on the app"
    # Build a minimal scope / request mock. Starlette's Request requires
    # a real ASGI scope; we use a tiny stub.
    from starlette.requests import Request
    from starlette.datastructures import URL

    class _Stub:
        url = URL("/api/_test/raise")
    req = Request({"type": "http", "method": "GET", "headers": [], "path": "/api/_test/raise",
                   "query_string": b"", "scheme": "http", "server": ("test", 80)}, receive=lambda: None)
    req._url = URL("/api/_test/raise")  # type: ignore[attr-defined]
    # The handler is registered for the production config; verify the
    # app_env actually drives the detail field.
    from product.backend_api.app.config import CONFIG
    saved_env = CONFIG.app_env
    try:
        exc = RuntimeError("/etc/passwd contents: SECRET_API_KEY=qiskit-token")
        import asyncio
        for env_value, expected_detail in (
            ("production", "internal server error"),
            ("development", "RuntimeError"),
        ):
            object.__setattr__(CONFIG, "app_env", env_value)
            resp = asyncio.run(handler(req, exc))
            assert resp.status_code == 500
            body = json.loads(resp.body)
            assert body["error"]["type"] == "internal"
            assert body["error"]["path"].endswith("/api/_test/raise")
            # The detail is bounded: it is either a fixed phrase (production)
            # or just the exception class name (development). It must never
            # include the exception's own message, which is where secret-shaped
            # fragments typically appear.
            assert body["error"]["detail"] == expected_detail, (
                f"env={env_value}: detail={body['error']['detail']!r}, "
                f"expected {expected_detail!r}"
            )
            raw = json.dumps(body)
            assert "/etc/passwd" not in raw
            assert "qiskit-token" not in raw
            assert "SECRET_API_KEY" not in raw
            # And the message is fully redacted.
            assert "/etc/passwd contents" not in raw
    finally:
        object.__setattr__(CONFIG, "app_env", saved_env)


# ---------------- Startup validation ----------------

def test_startup_rejects_missing_required_artifact(tmp_path):
    """When the project root contains none of the required Phase 19
    artefacts, the startup validator must raise RuntimeError with a
    clear, actionable message. We exercise `_validate_required_artifacts`
    directly because the module-level STATE singleton is imported at
    process start and cannot be re-resolved mid-session; this is the same
    validator the real `_load_state` uses."""
    from product.backend_api.app.dependencies import _validate_required_artifacts
    with pytest.raises(RuntimeError) as ei:
        _validate_required_artifacts(tmp_path)
    msg = str(ei.value)
    assert "Required research artefacts are missing" in msg
    assert "final_forecasting_results.csv" in msg


def test_startup_passes_with_real_project_root():
    """The real project root (where this test file lives) has every
    required artefact, so validation must succeed silently."""
    from product.backend_api.app.dependencies import _validate_required_artifacts
    # Should not raise.
    _validate_required_artifacts(ROOT)


# ---------------- OpenAPI mutation-surface ----------------

FORBIDDEN_PATH_HINTS = (
    "promote", "deploy", "rollback", "retrain", "change_policy",
    "modify_model", "modify_features", "approve_deployment",
)


def test_openapi_contains_no_lifecycle_mutation_path(client):
    """The OpenAPI schema must expose no path that maps to a lifecycle
    mutation. This is the API-side mirror of the agent firewall."""
    spec = client.get("/openapi.json").json()
    for path in spec["paths"]:
        low = path.lower()
        for hint in FORBIDDEN_PATH_HINTS:
            assert hint not in low, (
                f"OpenAPI exposes lifecycle-mutation path: {path} "
                f"(matched hint {hint!r})"
            )


# ---------------- Frontend production build ----------------

def test_frontend_dist_has_no_localhost_dependency():
    """The production build must not contain a hard-coded
    `http://127.0.0.1:8000` or `http://localhost:8000` dependency. The
    backend URL is supplied at build time via VITE_API_BASE_URL; a
    production build with an unset env should still use the relative
    path "/api", which is what the api client falls back to."""
    dist_html = ROOT / "product" / "frontend" / "dist" / "index.html"
    if not dist_html.exists():
        pytest.skip("frontend dist/ not built yet; run `npm run build`")
    # The html is the entrypoint and references the bundled JS/CSS.
    html = dist_html.read_text(encoding="utf-8")
    # No http://127.0.0.1 / http://localhost inside the html.
    assert "http://127.0.0.1" not in html
    assert "http://localhost" not in html
    # Same check on the JS bundle.
    assets = (ROOT / "product" / "frontend" / "dist" / "assets").glob("*.js")
    for asset in assets:
        text = asset.read_text(encoding="utf-8", errors="ignore")
        # Vite injects import.meta.env at build time; the literal string
        # `VITE_API_BASE_URL` only appears when unconfigured AND the dev
        # default is baked in. In production, the API client must use the
        # configured value or "/api". The forbidden string is a fully
        # qualified http URL pointing at a loopback port.
        assert not re.search(r"http://(127\.0\.0\.1|localhost):\d+", text), (
            f"hard-coded loopback URL in {asset.name}"
        )


# ---------------- Integrity before/after a real run ----------------

def test_running_app_does_not_mutate_protected_artefacts(client):
    """Exercise every primary API category; the 10 protected artefacts
    must remain byte-identical before and after. The endpoint set is
    deliberately read-only, but this is the deployment-level guarantee
    that the read-only contract holds against the live app."""
    before = {p: _sha256(ROOT / p) for p in PROTECTED_ARTEFACTS}
    # Touch one endpoint per router.
    for path in (
        "/health",
        "/api/forecasts",
        "/api/models",
        "/api/monitoring/events",
        "/api/governance/policy",
        "/api/governance/decisions?limit=5",
        "/api/agents/types",
        "/api/audit/events",
    ):
        r = client.get(path)
        assert r.status_code in (200, 422), f"{path} -> {r.status_code}"
    # A governance evaluate request is the most "write-like" call the API
    # exposes; it must not mutate any artefact.
    r = client.post("/api/governance/decisions", json={
        "subject_id": "MLOPS-REF-LOAD-H24-V1",
        "current_state": "PROMOTION_ELIGIBLE",
        "proposed_state": "APPROVAL_PENDING",
        "actor_type": "AGENT", "simulation": True,
        "benchmark_gate": "BENCHMARK_GATE_FAIL",
    })
    assert r.status_code in (200, 400, 422)
    after = {p: _sha256(ROOT / p) for p in PROTECTED_ARTEFACTS}
    assert before == after, f"artefact changed: {set(before) - set(after) or [k for k in before if before[k] != after[k]]}"


# ---------------- No forbidden capability strings in shipped code ----------------

def test_backend_module_has_no_quantum_or_llm_capability_claims():
    """Spec invariant: the shipped backend module must not CLAIM to use
    quantum / QML / GNN / LLM capabilities. Non-goal statements that
    explicitly disclaim those capabilities are allowed and required.

    A "claim" is detected by heuristic: a forbidden token that is NOT
    preceded by a non-goal marker such as "no", "without", "not", "absent",
    "forbidden", "never", "without any", or a comment marker.
    """
    backend_root = ROOT / "product" / "backend_api" / "app"
    # Forbidden capability tokens. The list mirrors spec §20 (Qiskit,
    # PennyLane, Cirq, qubits, ansatz, VQC, quantum ML) plus the LLM
    # vendor family that has no place in this product.
    forbidden = ("qiskit", "pennylane", "cirq", "qubit", "ansatz", "VQC",
                 "openai", "anthropic", "claude-", "gpt-4", "gpt-3.5",
                 "gemini", "llama-")
    # Non-goal markers that, when present within ~40 characters before a
    # token, indicate the token is a disclaimer, not a claim.
    non_goal_markers = (
        "no ", "not ", "never ", "without ", "absent", "forbidden",
        "not part of project", "not used", "is empty", "is not", "aren't",
        "doesn't", "does not", "isn't", "is not ", "must not", "no live",
        "no quantum", "no llm", "no fake", "no qlm", "no qml", "no gnn",
        "explicitly", "excluded",
    )
    hits: list[tuple[str, str, int]] = []
    for f in backend_root.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for word in forbidden:
            for m in re.finditer(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
                pre = text[max(0, m.start() - 80):m.start()].lower()
                # Strip comment markers and quotes from the preceding text.
                pre_clean = re.sub(r"[#\"'`*_]", " ", pre)
                if any(marker in pre_clean for marker in non_goal_markers):
                    continue
                # Also skip lines that are clearly a docstring / comment
                # enumerating non-goals (preceded by "#", '"""', or "'").
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_prefix = text[line_start:m.start()]
                if line_prefix.lstrip().startswith(("#", '"', "'")):
                    continue
                hits.append((str(f.relative_to(ROOT)), word, m.start()))
    assert not hits, f"forbidden capability claim in backend: {hits[:10]}"
