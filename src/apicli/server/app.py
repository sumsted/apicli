"""FastAPI application factory for the apicli web interface."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routes import router


def _web_dist() -> Path:
    """Locate the built SPA in dev and inside a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "web" / "dist"
    return Path(__file__).resolve().parents[3] / "web" / "dist"


WEB_DIST = _web_dist()


def create_app(token: str | None = None) -> FastAPI:
    """Build the FastAPI app.

    When ``token`` is provided, every ``/api`` request must carry a matching
    ``Authorization: Bearer <token>`` header (used by the desktop shell, which
    binds an otherwise-unauthenticated loopback server).
    """
    app = FastAPI(title="apicli", version="0.1.0")

    if token is not None:

        @app.middleware("http")
        async def _require_token(request: Request, call_next):
            if request.url.path.startswith("/api"):
                if request.headers.get("authorization") != f"Bearer {token}":
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app.include_router(router)

    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

    return app
