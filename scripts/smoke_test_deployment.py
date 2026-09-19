#!/usr/bin/env python3
"""Deployment smoke test.

Boots the FastAPI app (in-process via the existing TestClient fixture path
is NOT used here — this script exercises a real HTTP server) and hits
one endpoint per router to confirm the deployment is wired correctly. It
reuses the same product code as the test suite; it does not introduce a
second test framework.

Usage:
    .venv\\Scripts\\python.exe scripts/smoke_test_deployment.py [--host HOST] [--port PORT]

Environment:
    QSMLOPS_PROJECT_ROOT  Override the project root (matches the API).
    QSMLOPS_ALLOWED_ORIGINS  Defaults to the loopback origin for the loop.

Exit codes:
    0   all probes pass
    1   one or more probes failed
    2   app failed to import or start
"""
from __future__ import annotations
import argparse
import http.client
import os
import socket
import sys
import threading
import time
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """Poll a TCP port until the server accepts a connection or the timeout
    elapses. Returns True on success."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _probe(host: str, port: int, path: str, method: str = "GET",
           body: dict | None = None,
           expected_status: tuple[int, ...] = (200,)) -> tuple[bool, str]:
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            import json
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        body_bytes = resp.read()
        if status not in expected_status:
            return False, f"{method} {path} -> {status} (expected one of {expected_status}); body={body_bytes[:200]!r}"
        return True, f"{method} {path} -> {status} OK"
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.environ.get("QSMLOPS_API_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("QSMLOPS_API_PORT", "8765")))
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    # Default CORS origin to the loopback for this probe. The smoke test
    # never sets credentials, so the most permissive dev default works.
    os.environ.setdefault("QSMLOPS_ALLOWED_ORIGINS", f"http://{args.host}:{args.port}")
    os.environ.setdefault("QSMLOPS_APP_ENV", "development")

    try:
        import uvicorn
    except ImportError:
        LOGGER.info("FAIL: uvicorn is not installed. Run `.venv\\Scripts\\python.exe -m pip install uvicorn`.",
              file=sys.stderr)
        return 2
    try:
        from product.backend_api.app.main import create_app
    except Exception as e:  # pragma: no cover - reported via exit code
        LOGGER.error(f"FAIL: cannot import the FastAPI app: {e!r}")
        return 2

    app = create_app()
    config = uvicorn.Config(app, host=args.host, port=args.port, log_level="warning",
                            access_log=False, lifespan="on")
    server = uvicorn.Server(config)

    # Run the server in a worker thread. uvicorn's Server.run is blocking,
    # so we hand off to a thread and let the main thread run the probes.
    server_thread = threading.Thread(target=server.run, daemon=True, name="uvicorn-smoke")
    server_thread.start()
    try:
        if not _wait_for_port(args.host, args.port, timeout=args.timeout):
            LOGGER.info(f"FAIL: server did not accept connections on {args.host}:{args.port} within {args.timeout}s",
                  file=sys.stderr)
            return 2
        # Probe one endpoint per router plus the /openapi.json self-check.
        probes: list[tuple[str, dict | None, tuple[int, ...]]] = [
            ("GET", "/health", None, (200,)),
            ("GET", "/api/forecasts", None, (200,)),
            ("GET", "/api/models", None, (200,)),
            ("GET", "/api/monitoring/events", None, (200,)),
            ("GET", "/api/governance/policy", None, (200,)),
            ("GET", "/api/agents/types", None, (200,)),
            ("GET", "/api/audit/events", None, (200,)),
            ("GET", "/openapi.json", None, (200,)),
            # Governance evaluation: a known-unsafe request returns 4xx
            # with a typed error envelope (DENY is not a server error).
            ("POST", "/api/governance/decisions",
             {"subject_id": "MLOPS-REF-LOAD-H24-V1",
              "current_state": "PROMOTION_ELIGIBLE",
              "proposed_state": "APPROVAL_PENDING",
              "actor_type": "AGENT", "simulation": True,
              "benchmark_gate": "BENCHMARK_GATE_FAIL"},
             (200, 400, 422)),
        ]
        ok = 0
        for method, path, body, expected in probes:
            passed, msg = _probe(args.host, args.port, path, method=method, body=body,
                                 expected_status=expected)
            prefix = "OK  " if passed else "FAIL"
            LOGGER.info(f"{prefix}: {msg}")
            if passed:
                ok += 1
        total = len(probes)
        LOGGER.info(f"\nsmoke test: {ok}/{total} probes passed")
        return 0 if ok == total else 1
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
