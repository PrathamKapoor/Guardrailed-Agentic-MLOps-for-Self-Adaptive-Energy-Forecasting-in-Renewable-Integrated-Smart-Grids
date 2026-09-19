# Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository a reproducible, offline, read-only research-evidence application with a safe deployment boundary.

**Architecture:** The default FastAPI app exposes evidence/advisory routes only. The existing research write endpoints become opt-in and authenticated. Pure release verification, Docker smoke checks, CI gates, and docs all share the same runtime contract.

**Tech Stack:** Python, FastAPI, pytest, Docker, GitHub Actions, Vite, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-18-release-hardening-design.md`

## Global Constraints

- Never modify final-test tables, frozen protocols, registries, or Phase 19 reports.
- Never introduce lifecycle-mutation endpoints.
- Production requires explicit origins and bearer-token configuration.
- Research writes are opt-in, authenticated, and isolated under `artifacts/research_ui/`.
- Verification must not rewrite repository artifacts or dashboard outputs.
- Missing Git provenance is a release-gate failure, never fabricated.

---

## File Structure

- `product/backend_api/app/config.py`: validated security and mode settings.
- `product/backend_api/app/main.py`: default versus research-console routing.
- `scripts/verify_release.py`: pure provenance and integrity checker.
- `scripts/smoke_test_container.py`: Docker build/run/probe verifier.
- `tests/test_release_hardening.py`: all new regression tests.
- `tests/test_hackathon_readiness.py`: direct integrity checks only.
- `docker/Dockerfile`, `.github/workflows/ci.yml`: runtime and CI gates.
- README/runbooks/release guide: a single accurate contract.

### Task 1: Harden configuration and API routing

**Files:** Modify `product/backend_api/app/config.py`, `product/backend_api/app/main.py`, and `tests/test_api_service.py`; create `tests/test_release_hardening.py`.

**Interfaces:** Add `APIConfig.research_console_enabled`, `APIConfig.api_token`, and `create_app(config: APIConfig | None = None)`. `SMARTGRID_MLOPS_ENABLE_RESEARCH_CONSOLE=1` enables the research router only with a token.

- [ ] **Step 1: Write the failing tests**

```python
def test_production_requires_origins_and_token(monkeypatch):
    monkeypatch.setenv("SMARTGRID_MLOPS_APP_ENV", "production")
    monkeypatch.delenv("SMARTGRID_MLOPS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("SMARTGRID_MLOPS_API_TOKEN", raising=False)
    with pytest.raises(ValueError, match="production requires"):
        APIConfig.from_env()

def test_default_openapi_excludes_research_write_paths(client):
    assert "/api/research/datasets" not in client.get("/openapi.json").json()["paths"]
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py -q`

Expected: production only warns and default OpenAPI still exposes research paths.

- [ ] **Step 3: Implement the minimum change**

```python
if env == "production" and (not origins_value or not token):
    raise ValueError("production requires SMARTGRID_MLOPS_ALLOWED_ORIGINS and SMARTGRID_MLOPS_API_TOKEN")
if research_console_enabled and not token:
    raise ValueError("research console requires SMARTGRID_MLOPS_API_TOKEN")
if config.research_console_enabled:
    app.include_router(research.router)
```

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_api_service.py tests/test_release_hardening.py -q`

Expected: default OpenAPI excludes write paths and unsafe production config fails before startup.

- [ ] **Step 5: Commit**

Run: `git add product/backend_api/app/config.py product/backend_api/app/main.py tests/test_api_service.py tests/test_release_hardening.py && git commit -m "feat: harden production API boundary"`

### Task 2: Add non-mutating release verification

**Files:** Create `scripts/verify_release.py`; modify `tests/test_hackathon_readiness.py` and `tests/test_release_hardening.py`.

**Interfaces:** Add `resolve_checksum_target(sidecar: Path, root: Path) -> Path` and `verify_release(root: Path, allow_no_commit: bool = False) -> VerificationResult`. The CLI fails for changed artifacts or a missing commit unless given `--allow-no-commit`.

- [ ] **Step 1: Write the failing tests**

```python
def test_resolves_bare_digest_to_yaml(tmp_path):
    payload = tmp_path / "protocol.yaml"
    payload.write_text("frozen: true\n", encoding="utf-8")
    sidecar = tmp_path / "protocol.sha256"
    sidecar.write_text(hashlib.sha256(payload.read_bytes()).hexdigest(), encoding="utf-8")
    assert resolve_checksum_target(sidecar, tmp_path) == payload

def test_verifier_reports_missing_git_commit(tmp_path):
    assert "git_commit" in verify_release(tmp_path).failures
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py -q`

Expected: import failure because verifier functions do not exist.

- [ ] **Step 3: Implement pure verification**

```python
def verify_release(root: Path, *, allow_no_commit: bool = False) -> VerificationResult:
    # Read checksum sidecars, Phase 19 baseline, and Git state only.
    # Return structured failures; never write under root.
    ...
```

Replace the recursive child-pytest logic in `test_pre_freeze_boundary_intact` with direct hash/baseline assertions.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_hackathon_readiness.py tests/test_release_hardening.py -q`

Run: `.venv\Scripts\python.exe scripts/verify_release.py --allow-no-commit`

Expected: no child pytest or dashboard regeneration; no-commit is explicitly reported.

- [ ] **Step 5: Commit**

Run: `git add scripts/verify_release.py tests/test_hackathon_readiness.py tests/test_release_hardening.py && git commit -m "feat: add non-mutating release verification"`

### Task 3: Package the complete Docker runtime

**Files:** Modify `docker/Dockerfile`, `.github/workflows/ci.yml`, and `tests/test_release_hardening.py`; create `scripts/smoke_test_container.py`.

**Interfaces:** Docker must copy `artifacts/model_registry/`, `config/ablation/`, and `data/processed/`, along with current inputs. The smoke runner builds, runs with a production token/origin, probes health/read-only routes, and removes its container in `finally`.

- [ ] **Step 1: Write the failing test**

```python
def test_dockerfile_copies_runtime_inputs():
    text = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    for directory in ("artifacts/model_registry/", "config/ablation/", "data/processed/"):
        assert f"COPY {directory}" in text
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py::test_dockerfile_copies_runtime_inputs -q`

Expected: omitted runtime directories fail.

- [ ] **Step 3: Implement image copies and smoke runner**

```dockerfile
COPY artifacts/model_registry/ ./artifacts/model_registry/
COPY config/ablation/ ./config/ablation/
COPY data/processed/ ./data/processed/
```

```python
def main() -> int:
    # docker build; docker run; HTTP probes; docker rm in finally
    ...
```

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py -q`

Run: `.venv\Scripts\python.exe scripts/smoke_test_container.py`

Expected: tests pass; Docker probes pass where Docker is installed.

- [ ] **Step 5: Commit**

Run: `git add docker/Dockerfile scripts/smoke_test_container.py tests/test_release_hardening.py .github/workflows/ci.yml && git commit -m "fix: package complete API runtime in Docker"`

### Task 4: Align CI and operational documentation

**Files:** Modify `.github/workflows/ci.yml`, `README.md`, `docs/hackathon_installation.md`, `product/backend_api/README.md`, `.env.example`, `scripts/smoke_test_deployment.py`, and `tests/test_release_hardening.py`; create `docs/release.md`.

**Interfaces:** CI invokes release verification, backend tests, frontend typecheck/tests/build, and Docker smoke. All docs use `SMARTGRID_MLOPS_*` and distinguish the default API from the opt-in research console.

- [ ] **Step 1: Write failing tests**

```python
def test_docs_do_not_claim_231_tests():
    for path in (ROOT / "README.md", ROOT / "docs/hackathon_installation.md"):
        assert "231 passed" not in path.read_text(encoding="utf-8")

def test_smoke_script_uses_current_prefix():
    text = (ROOT / "scripts/smoke_test_deployment.py").read_text(encoding="utf-8")
    assert "SMARTGRID_MLOPS_API_HOST" in text
    assert "QSMLOPS_API_HOST" not in text
```

- [ ] **Step 2: Verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py -q`

Expected: stale test-count and legacy environment references fail.

- [ ] **Step 3: Implement CI/docs alignment**

```yaml
- run: python scripts/verify_release.py
- run: python -m pytest tests -q
- run: npm ci && npx tsc --noEmit && npx vitest run && npm run build
- run: python scripts/smoke_test_container.py
```

`docs/release.md` specifies a committed clean checkout, passing gates, explicit production token/origin, and external steps for tagging, image publication, hosting, and independent review.

- [ ] **Step 4: Verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_release_hardening.py tests/test_hackathon_readiness.py -q`

Expected: selected checks pass without recursion.

- [ ] **Step 5: Commit**

Run: `git add .github/workflows/ci.yml README.md docs/hackathon_installation.md product/backend_api/README.md .env.example scripts/smoke_test_deployment.py docs/release.md tests/test_release_hardening.py && git commit -m "docs: align release and deployment contracts"`

### Task 5: Complete verification and handoff

**Files:** Create `reports/release_hardening_completion.md`.

**Interfaces:** The report contains only exact commands, exits, artifact status, and external requirements.

- [ ] **Step 1: Run backend tests**

Run: `.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider`

Expected: complete zero-failure summary; stop and diagnose failures before reporting success.

- [ ] **Step 2: Run frontend tests/build**

Run from `product/frontend`: `npm test`, `npm run typecheck`, `npm run build`.

Expected: each exits zero.

- [ ] **Step 3: Run release/container verification**

Run: `.venv\Scripts\python.exe scripts/verify_release.py`

Run: `.venv\Scripts\python.exe scripts/smoke_test_container.py`

Expected: release verification requires a committed baseline; Docker smoke runs where Docker is installed.

- [ ] **Step 4: Write factual report**

```markdown
| Command | Exit code | Result |
| --- | ---: | --- |
| `python -m pytest -p no:cacheprovider` | 0 | exact passed count |
```

- [ ] **Step 5: Commit**

Run: `git add reports/release_hardening_completion.md && git commit -m "docs: record release hardening verification"`

## Plan Self-Review

- Tasks 1–4 cover every design requirement; Task 5 records evidence.
- No implementation requirement is unspecified; introduced interfaces appear before dependent tasks.
