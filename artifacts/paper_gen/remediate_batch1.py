# -*- coding: utf-8 -*-
"""Audit remediation batch: QSMLOPS rename (with legacy fallback), pyproject
overhaul, requirements.txt, .env, package-init files for product.backend_api."""
import io, re

ROOT = r"C:\Projects\guardrailed-agentic-mlops-smart-grid_trial"

def rw(path, old, new, count=0):
    p = ROOT + "\\" + path
    s = io.open(p, encoding="utf-8").read()
    assert old in s, f"anchor missing in {path}: {old[:60]!r}"
    s = s.replace(old, new) if count == 0 else s.replace(old, new, count)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", path)

# ---- 1) config.py: env prefix rename + legacy fallback + loggers + version ----
p = ROOT + r"\product\backend_api\app\config.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace("QSMLOPS_PROJECT_ROOT", "SMARTGRID_MLOPS_PROJECT_ROOT")
s = s.replace("QSMLOPS_API_HOST, QSMLOPS_API_PORT", "SMARTGRID_MLOPS_API_HOST, SMARTGRID_MLOPS_API_PORT")
s = s.replace("QSMLOPS_ALLOWED_ORIGINS", "SMARTGRID_MLOPS_ALLOWED_ORIGINS")
s = s.replace("QSMLOPS_APP_ENV", "SMARTGRID_MLOPS_APP_ENV")
s = s.replace('override = os.environ.get("SMARTGRID_MLOPS_PROJECT_ROOT")',
              'override = os.environ.get("SMARTGRID_MLOPS_PROJECT_ROOT") or os.environ.get("QSMLOPS_PROJECT_ROOT")')
s = s.replace('logger = logging.getLogger("qsmlops.api.config")',
              'logger = logging.getLogger("smartgrid_mlops.api.config")')
s = s.replace('env = _parse_app_env(os.environ.get("SMARTGRID_MLOPS_APP_ENV"))',
              'env = _parse_app_env(os.environ.get("SMARTGRID_MLOPS_APP_ENV") or os.environ.get("QSMLOPS_APP_ENV"))')
s = s.replace('origins = _parse_origins(os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS"))',
              'origins = _parse_origins(os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS") or os.environ.get("QSMLOPS_ALLOWED_ORIGINS"))')
s = s.replace('if env == "production" and not os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS"):',
              'if env == "production" and not (os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS") or os.environ.get("QSMLOPS_ALLOWED_ORIGINS")):')
s = s.replace('api_version: str = "2.0.0"', 'api_version: str = "0.20.0"')
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched product/backend_api/app/config.py")

# ---- 2) dependencies.py + main.py loggers ----
rw(r"product\backend_api\app\dependencies.py",
   'logging.getLogger("qsmlops.api.deps")', 'logging.getLogger("smartgrid_mlops.api.deps")')
rw(r"product\backend_api\app\dependencies.py",
   '"Re-run the project bootstrap or set QSMLOPS_PROJECT_ROOT to a ',
   '"Re-run the project bootstrap or set SMARTGRID_MLOPS_PROJECT_ROOT to a ')
rw(r"product\backend_api\app\main.py",
   'logging.getLogger("qsmlops.api")', 'logging.getLogger("smartgrid_mlops.api")')

# ---- 3) README + .env.example ----
p = ROOT + r"\product\backend_api\README.md"
s = io.open(p, encoding="utf-8").read()
s = s.replace("QSMLOPS_PROJECT_ROOT", "SMARTGRID_MLOPS_PROJECT_ROOT")
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched product/backend_api/README.md")

p = ROOT + r"\.env.example"
s = io.open(p, encoding="utf-8").read()
s = s.replace("QSMLOPS_", "SMARTGRID_MLOPS_")
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched .env.example")

# ---- 4) package __init__ files so product.backend_api is importable/shippable ----
io.open(ROOT + r"\product\__init__.py", "w", encoding="utf-8").write(
    '"""Product layer: backend API and frontend for the frozen evidence."""\n')
io.open(ROOT + r"\product\backend_api\__init__.py", "w", encoding="utf-8").write(
    '"""FastAPI service exposing the frozen evaluation evidence (read-only)."""\n')
print("created product/__init__.py and product/backend_api/__init__.py")

# ---- 5) pyproject overhaul ----
pyproject = '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "smartgrid-mlops"
version = "0.20.0"
description = "Guardrailed agentic MLOps research platform for smart-grid forecasting (offline evaluation on RTS-GMLC)"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Proprietary" }
authors = [{ name = "Research Team" }]
dependencies = [
  "numpy>=1.26",
  "pyarrow>=25",
  "scikit-learn>=1.5",
  "torch>=2.7",
  "optuna>=4.0",
  "mlflow>=3.0",
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "starlette>=0.38",
  "pydantic>=2.7",
  "python-multipart>=0.0.9",
  "pyyaml>=6.0",
  "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.6", "mypy>=1.10"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.hatch.build.targets.wheel]
packages = ["src/smartgrid_mlops", "product"]

[tool.ruff]
line-length = 120
target-version = "py311"
exclude = [".venv", "node_modules", "data", "artifacts", "product/frontend/dist"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "W"]
ignore = ["E731"]  # lambdas are used sparingly and deliberately in phase scripts

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
check_untyped_defs = false
exclude = ["scripts/", "product/frontend/", "data/", "artifacts/"]
# Notes: the research phase scripts are intentionally untyped; the library
# under src/smartgrid_mlops is the typing target as it stabilizes.
'''
io.open(ROOT + r"\pyproject.toml", "w", encoding="utf-8", newline="\n").write(pyproject)
print("rewrote pyproject.toml")

# ---- 6) requirements.txt from the actual venv (pinned) ----
import subprocess
freeze = subprocess.run(
    [ROOT + r"\.venv\Scripts\python.exe", "-m", "pip", "freeze"],
    capture_output=True, text=True, check=True).stdout
core_prefixes = ("numpy", "pyarrow", "scikit-learn", "torch", "optuna", "mlflow",
                 "fastapi", "uvicorn", "starlette", "pydantic", "pydantic_core",
                 "python-multipart", "pyyaml", "httpx", "anyio", "click", "h11",
                 "typing-extensions", "annotated-types", "idna", "sniffio", "certifi",
                 "tzdata", "PyYAML")
lines = [ln.strip() for ln in freeze.splitlines() if ln.strip()]
pinned = [ln for ln in lines if ln.split("==")[0].lower() in {p.lower() for p in core_prefixes}]
header = ("# Pinned runtime requirements for the API + research pipeline.\n"
          "# Generated from the working virtual environment; pyproject.toml carries the\n"
          "# abstract lower bounds. Regenerate with: pip freeze | grep -iE \"^(numpy|pyarrow|...)\"\n")
io.open(ROOT + r"\requirements.txt", "w", encoding="utf-8", newline="\n").write(
    header + "\n".join(sorted(pinned, key=str.lower)) + "\n")
print("wrote requirements.txt with", len(pinned), "pins")

# ---- 7) .env from example (local defaults, harmless) ----
ex = io.open(ROOT + r"\.env.example", encoding="utf-8").read()
env = ex.replace("# SMARTGRID_MLOPS_", "SMARTGRID_MLOPS_")
header = "# Local environment for the offline research platform. Values mirror .env.example.\n"
io.open(ROOT + r"\.env", "w", encoding="utf-8", newline="\n").write(header + env)
print("wrote .env from example")
print("BATCH DONE")
