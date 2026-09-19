"""FastAPI app factory + middleware.

This is a thin FastAPI wrapper. The app:
- exposes the 7 route groups
- attaches typed Pydantic error envelopes
- never registers lifecycle mutation routes
- never weakens the existing Stage 1 safety tests
- adds deployment-grade hardening (CORS, security headers, error envelope
  hygiene) on top of the existing app
"""
from __future__ import annotations
import logging
import os
from typing import Iterable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .config import CONFIG
from .routers import health, forecasts, models, monitoring, governance, agents, audit, research

logger = logging.getLogger("smartgrid_mlops.api")


# Deployment-grade security headers. A CSP is intentionally NOT set here:
# FastAPI's /docs and /redoc pages use inline scripts/styles, and a strict
# CSP would break them. The /openapi.json and JSON API responses have no
# executable content, so these headers cover them safely.
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # The API serves JSON only; this signals that the response is meant to
    # be consumed by JavaScript and not navigated to.
    "X-Content-Type-Options": "nosniff",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a fixed set of safe-by-default HTTP headers to every response.

    Headers are additive: they do not strip any header a downstream proxy
    may have set, so this composes with reverse proxies and ingresses."""

    def __init__(self, app: ASGIApp, headers: dict[str, str] | None = None) -> None:
        super().__init__(app)
        self._headers = dict(headers or _SECURITY_HEADERS)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in self._headers.items():
            response.headers.setdefault(name, value)
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=CONFIG.api_title,
        version=CONFIG.api_version,
        description=CONFIG.api_description,
    )

    # CORS. Deliberately env-driven; the dev default matches the Vite dev
    # server origin so the local workflow works without configuration. The
    # configuration layer logs a warning when production runs without an
    # explicit allow-list, so the operator sees the risk.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CONFIG.allowed_origins,
        allow_credentials=False,  # the API issues no cookies; this is honest
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware)

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
        logger.info("Bearer-token auth enabled on /api routes")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        # Honest, typed error envelope; do NOT coerce governance denials into
        # 500 (they are 4xx by definition and must remain visible as such).
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": "http", "status": exc.status_code,
                              "detail": exc.detail, "path": request.url.path}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback server-side so operators can debug, but
        # return a generic message to the client. Never echo the exception
        # message verbatim: it can carry filesystem paths, SQL fragments,
        # or environment variables. Development mode reveals only the
        # exception class name; production mode reveals only the status.
        logger.exception("Unhandled exception on %s", request.url.path)
        if CONFIG.app_env == "production":
            detail = "internal server error"
        else:
            detail = type(exc).__name__
        return JSONResponse(
            status_code=500,
            content={"error": {"type": "internal", "status": 500,
                              "detail": detail, "path": request.url.path}},
        )

    app.include_router(health.router)
    app.include_router(forecasts.router)
    app.include_router(models.router)
    app.include_router(monitoring.router)
    app.include_router(governance.router)
    app.include_router(agents.router)
    app.include_router(audit.router)
    app.include_router(research.router)

    # Starlette returns its own `{"detail": "Not Found"}` envelope for
    # routing 404s (the HTTPException handler is not invoked for those).
    # Register a 404 handler so every error path uses the typed envelope
    # and never leaks implementation strings.
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request,
                                                exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"type": "http", "status": exc.status_code,
                              "detail": str(exc.detail), "path": request.url.path}},
        )

    return app


# Module-level app for `uvicorn product.backend_api.app.main:app`
app = create_app()
