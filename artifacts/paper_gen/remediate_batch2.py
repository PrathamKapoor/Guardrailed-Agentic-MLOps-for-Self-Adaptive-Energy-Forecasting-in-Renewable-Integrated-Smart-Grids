# -*- coding: utf-8 -*-
"""Audit remediation batch 2: stubs, docstring, Docker, CI, auth, LICENSE,
CHANGELOG, .gitignore, sourcemaps, HPO trials env, cleanup."""
import io, os, shutil, glob

ROOT = r"C:\Projects\guardrailed-agentic-mlops-smart-grid_trial"

def w(path, content):
    full = ROOT + "\\" + path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    io.open(full, "w", encoding="utf-8", newline="\n").write(content)
    print("wrote", path)

def patch(path, old, new):
    full = ROOT + "\\" + path
    s = io.open(full, encoding="utf-8").read()
    assert old in s, f"anchor missing in {path}"
    io.open(full, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("patched", path)

# ---- 23) typed external-validation errors get real messages ----
w(r"src\smartgrid_mlops\external_validation\validation.py", None) if False else None
p = ROOT + r"\src\smartgrid_mlops\external_validation\validation.py"
s = io.open(p, encoding="utf-8").read()
old = '''class ExternalValidationError(RuntimeError):
    pass


class DatasetNotAvailableError(ExternalValidationError):
    pass


class ProvenanceError(ExternalValidationError):
    pass


class FeatureCompatibilityError(ExternalValidationError):
    pass


class TemporalCoverageError(ExternalValidationError):
    pass


class FrozenModelError(ExternalValidationError):
    pass'''
new = '''class ExternalValidationError(RuntimeError):
    """Base for external-dataset validation failures.

    Subclasses carry a default message so a raised error is self-describing;
    callers may still override with a more specific message.
    """

    default_message = "external validation failed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class DatasetNotAvailableError(ExternalValidationError):
    default_message = "external dataset not found or not provisioned"


class ProvenanceError(ExternalValidationError):
    default_message = "external dataset provenance could not be verified (missing checksums or manifest)"


class FeatureCompatibilityError(ExternalValidationError):
    default_message = "external dataset features are incompatible with the frozen feature specification"


class TemporalCoverageError(ExternalValidationError):
    default_message = "external dataset temporal coverage does not satisfy the evaluation window"


class FrozenModelError(ExternalValidationError):
    default_message = "frozen model unavailable or mismatched for external validation"'''
assert old in s
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("patched external_validation/validation.py stubs")

# ---- 24) ProtocolAccessError stub ----
p = ROOT + r"\src\smartgrid_mlops\experimental_design\protocol.py"
s = io.open(p, encoding="utf-8").read()
old = '''class ProtocolAccessError(PermissionError):
    pass'''
new = '''class ProtocolAccessError(PermissionError):
    """Raised when an access mode attempts to touch a partition it may not see.

    Enforces the protocol-freeze boundary: development modes cannot read the
    TEST partition; only FINAL_EVALUATION mode may, after the candidate is
    frozen and the protocol unsealed.
    """

    default_detail = "protocol access violation: partition not visible in this access mode"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.default_detail)'''
assert old in s
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("patched experimental_design/protocol.py stub")

# ---- 10) stale package docstring ----
w(r"src\smartgrid_mlops\__init__.py",
  '''"""Guardrailed agentic MLOps research package for smart-grid forecasting.

Offline evaluation platform: RTS-GMLC forecasting with frozen finalists,
chronological protocol-frozen partitions, observational drift monitoring
(PSI / Wasserstein / rolling MAE), a bounded deterministic agent layer, and
a deterministic governance engine (13-state lifecycle, 12 ordered gates).
No live telemetry, no production deployment, no quantum / GNN / LLM components.
"""
''')

# ---- 25) HPO trials configurable (default preserved) ----
p = ROOT + r"\scripts\run_pytorch_mlp_hpo.py"
s = io.open(p, encoding="utf-8").read()
old = "study.optimize(obj,n_trials=max(0,5-len(study.trials)));return study"
new = ('_trials = int(os.environ.get("SMARTGRID_MLOPS_HPO_TRIALS", "5"))\n'
       ' study.optimize(obj,n_trials=max(0,_trials-len(study.trials)));return study')
assert old in s
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("patched scripts/run_pytorch_mlp_hpo.py (SMARTGRID_MLOPS_HPO_TRIALS, default 5)")

# ---- 5) Docker ----
w(r"docker\Dockerfile",
'''# Guardrailed agentic MLOps - offline research API.
# Builds the repository into a container serving the FastAPI evidence API.
# The API is read-only with respect to the lifecycle; research endpoints write
# only under artifacts/research_ui/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    SMARTGRID_MLOPS_APP_ENV=production

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY product/ ./product/
COPY artifacts/research_tables/ ./artifacts/research_tables/
COPY artifacts/experimental_design/ ./artifacts/experimental_design/
COPY config/ ./config/
COPY data/manifests/ ./data/manifests/

EXPOSE 8000
# product.backend_api is a regular package inside the image (product/__init__.py present).
CMD ["python", "-m", "uvicorn", "product.backend_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''')

w(r"docker\docker-compose.yml",
'''services:
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      SMARTGRID_MLOPS_APP_ENV: production
      # SMARTGRID_MLOPS_ALLOWED_ORIGINS: https://your-frontend.example.com
      # SMARTGRID_MLOPS_API_TOKEN: set-to-require-bearer-auth
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

  frontend:
    image: node:22-alpine
    working_dir: /app
    volumes:
      - ../product/frontend:/app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host"
    depends_on:
      - api
''')
print("docker files done")

# ---- 11) CI workflow ----
w(r".github\workflows\ci.yml",
'''name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install package + dev tools
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -e . pytest
      - name: Run test suite
        run: python -m pytest tests -q
      - name: Final-evaluation artifact verification
        run: python run_final_evaluation.py

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: product/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: product/frontend/package-lock.json
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx vitest run
      - run: npm run build
''')

# ---- 12) optional bearer-token auth middleware (off unless token configured) ----
p = ROOT + r"\product\backend_api\app\main.py"
s = io.open(p, encoding="utf-8").read()
old = '''    app.add_middleware(SecurityHeadersMiddleware)'''
new = '''    app.add_middleware(SecurityHeadersMiddleware)

    # Optional bearer-token auth. Disabled unless SMARTGRID_MLOPS_API_TOKEN is
    # set; the local research default is open because the API is read-only with
    # respect to the lifecycle and research writes are confined to
    # artifacts/research_ui/. Set the env var to require
    # "Authorization: Bearer <token>" on every /api route (health stays open).
    api_token = os.environ.get("SMARTGRID_MLOPS_API_TOKEN")
    if api_token:
        from starlette.middleware import Middleware as _MW  # noqa: F401  (documented above)

        class _BearerTokenMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                if request.url.path.startswith("/api"):
                    header = request.headers.get("authorization", "")
                    if header != f"Bearer {api_token}":
                        return JSONResponse(
                            status_code=401,
                            content={"error": {"type": "auth", "status": 401,
                                               "detail": "missing or invalid bearer token",
                                               "path": request.url.path}},
                        )
                return await call_next(request)

        app.add_middleware(_BearerTokenMiddleware)
        logger.info("Bearer-token auth enabled on /api routes")'''
assert old in s
s = s.replace(old, new, 1)
if "\nimport os\n" not in s:
    s = s.replace("import logging\n", "import logging\nimport os\n", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched main.py auth middleware")

# ---- 32/46) LICENSE (proprietary, matching pyproject) ----
w(r"LICENSE",
'''Proprietary Research License

Copyright (c) 2026 the smartgrid-mlops research authors. All rights reserved.

This software and its accompanying artifacts, documentation, and datasets
derivatives are provided for internal research and educational evaluation
only. Redistribution, commercial use, or public deployment in operational
grid infrastructure is not permitted without the copyright holders' written
consent.

Third-party components remain under their own licenses (BSD/MIT/Apache-2.0;
see requirements.txt). The RTS-GMLC dataset is provided by the U.S. National
Renewable Energy Laboratory under its own license (BSD-3-style) and is used
here for research purposes only.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY ARISING FROM ITS USE.
''')

# ---- 45) CHANGELOG ----
w(r"CHANGELOG.md",
'''# Changelog

All notable changes to the smartgrid-mlops research platform are documented
here. The canonical phase-by-phase record is `reports/phase_*_completion.md`;
this file summarizes user-visible and structural changes only.

## [0.20.0] - 2026-09-14
### Added
- Product layer: FastAPI evidence API (17 read-only routes) and React console;
  live research console for user-registered datasets and local chronological
  forecasting runs (manifests recorded before first use).
- Optional bearer-token auth on /api routes (SMARTGRID_MLOPS_API_TOKEN).
- Docker image + compose files; GitHub Actions CI (pytest + frontend).
- requirements.txt (pinned) and .env for local configuration.
- Final-evaluation verification entry point (run_final_evaluation.py).

### Changed
- Environment-variable prefix renamed QSMLOPS_* -> SMARTGRID_MLOPS_*
  (legacy names still honored as fallback in product config and replay script).
- API/package version aligned at 0.20.0; product.backend_api now ships in the wheel.

### Fixed
- Quantum "Trust Layer" contamination in docs/paper removed; the drafts now
  describe the actual classical system (rewritten from repository artifacts).
- Frontend health check called /api/health (404); now calls /health.
- Silent metric-parse failures in the historical importer are now recorded on
  the imported record.

## [0.1.0] - 2026-08/09 (Phases 00-19)
- Data ingestion and checksummed RTS-GMLC manifests; feature pipelines;
  classical + neural experiments with rolling-origin validation; Phase 11
  finalist selection; Phase 13 governance policy and engine; Phase 19 protocol
  freeze and single final evaluation (artifacts under artifacts/research_tables
  and artifacts/final_release); drift monitoring research (Stages 07-14);
  honest 7/7 governance DENY outcome recorded.''')

print("BATCH 2 DONE")
