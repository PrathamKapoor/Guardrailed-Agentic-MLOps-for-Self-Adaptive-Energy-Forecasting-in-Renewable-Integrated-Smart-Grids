"""API configuration: where to find the project root, how to talk to the
frontend, and which deployment-level environment variables are honored.

All variables are read at import time. None of them are secrets and none of
them are LLM / quantum / cloud credentials. The product is offline evaluation
over frozen artefacts, so the configuration surface is intentionally small.

Environment variables
---------------------
SMARTGRID_MLOPS_PROJECT_ROOT
    Override the resolved project root. Used by deployments that copy or
    symlink the API package outside the repository (e.g. read-only mounts).
    Default: 3 directories up from this file (product/backend_api/app/).

SMARTGRID_MLOPS_API_HOST, SMARTGRID_MLOPS_API_PORT
    Read by the runbook and smoke test; not consumed by the app itself
    (uvicorn accepts --host / --port directly).

SMARTGRID_MLOPS_ALLOWED_ORIGINS
    Comma-separated list of origins allowed by the CORS middleware. The
    default for development is the Vite dev server origin
    (http://127.0.0.1:5173). Production deployments MUST set this to the
    origin that serves the built frontend (or omit and accept the dev
    default at one's own risk; the app refuses to start with an empty
    allow-list in production mode).

SMARTGRID_MLOPS_APP_ENV
    "development" or "production". Controls the CORS default, the error
    envelope verbosity, and a startup check that required artefacts exist.
    Unknown values fall back to "development" with a logged warning.
"""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger("smartgrid_mlops.api.config")

# Default CORS origin for local development. Production deployments must
# override via SMARTGRID_MLOPS_ALLOWED_ORIGINS.
DEFAULT_DEV_ORIGINS: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")


def _find_project_root() -> Path:
    """The repository root: parent of `src/`, `tests/`, `artifacts/`, `product/`.

    Env override `SMARTGRID_MLOPS_PROJECT_ROOT` is honored so deployments can
    point at any working tree (e.g. CI checkout in a different location).
    """
    override = os.environ.get("SMARTGRID_MLOPS_PROJECT_ROOT") or os.environ.get("QSMLOPS_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    return here.parents[3]


def _parse_origins(value: str | None) -> List[str]:
    """Parse a comma-separated origins string. Whitespace is stripped; empty
    entries are dropped. An unset / empty value yields the development
    default so the dev server works out of the box."""
    if not value:
        return list(DEFAULT_DEV_ORIGINS)
    out = [v.strip() for v in value.split(",")]
    return [v for v in out if v]


def _parse_app_env(value: str | None) -> str:
    v = (value or "development").strip().lower()
    if v not in {"development", "production"}:
        logger.warning("Unknown SMARTGRID_MLOPS_APP_ENV=%r; falling back to 'development'", value)
        return "development"
    return v


@dataclass(frozen=True)
class APIConfig:
    project_root: Path
    api_title: str = "Guardrailed Agentic MLOps — Forecast API"
    api_version: str = "0.20.0"
    api_description: str = ("Thin FastAPI service layer over the Stage 1 productization "
                            "contract. Read-only and advisory-only; protected lifecycle "
                            "operations are NOT exposed as endpoints. See "
                            "docs/productization/api_contract.md for the complete contract.")
    app_env: str = "development"
    allowed_origins: List[str] = field(default_factory=lambda: list(DEFAULT_DEV_ORIGINS))

    @classmethod
    def from_env(cls) -> "APIConfig":
        env = _parse_app_env(os.environ.get("SMARTGRID_MLOPS_APP_ENV") or os.environ.get("QSMLOPS_APP_ENV"))
        origins = _parse_origins(os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS") or os.environ.get("QSMLOPS_ALLOWED_ORIGINS"))
        if env == "production" and not (os.environ.get("SMARTGRID_MLOPS_ALLOWED_ORIGINS") or os.environ.get("QSMLOPS_ALLOWED_ORIGINS")):
            logger.warning(
                "SMARTGRID_MLOPS_APP_ENV=production but SMARTGRID_MLOPS_ALLOWED_ORIGINS is unset; "
                "falling back to the development default. Set SMARTGRID_MLOPS_ALLOWED_ORIGINS "
                "to the production frontend origin in real deployments."
            )
        return cls(
            project_root=_find_project_root(),
            app_env=env,
            allowed_origins=origins,
        )


CONFIG = APIConfig.from_env()
