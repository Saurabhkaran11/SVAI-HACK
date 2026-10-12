"""FastAPI app factory: middleware, error mapping, routers, fallback UI."""
from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .. import __version__
from ..config import settings
from ..hydra import UpstreamError
from ..services import knowledge, personas
from ..state import state
from .guard import public_guard
from .routes import ROUTERS

log = logging.getLogger("whybot")
STATIC = Path(__file__).resolve().parents[2] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("WhyBot %s starting in %s mode (database=%s)", __version__, settings.mode, settings.database)
    try:
        personas.sync_all()
    except Exception as e:
        log.warning("persona sync skipped: %s", e)
    if settings.auto_sample and not state.docs:  # fresh container (no disk): reload the starter brain
        def _load():
            try:
                knowledge.load_sample()
                log.info("starter data loaded")
            except Exception as e:
                log.warning("starter data skipped: %s", e)
        threading.Thread(target=_load, name="whybot-autosample", daemon=True).start()
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = FastAPI(
        title="WhyBot API", version=__version__, lifespan=lifespan,
        description="Company brain on HydraDB: graph-aware answers, persona memory and blast-radius analysis.",
    )
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.middleware("http")(public_guard)

    @app.middleware("http")
    async def timing(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, exc: RequestValidationError):
        """Flatten pydantic errors into one readable sentence (the UI shows `detail` verbatim)."""
        parts = []
        for err in exc.errors()[:3]:
            field = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body", "query"))
            parts.append(f"{field or 'request'}: {err.get('msg', 'invalid value')}")
        safe = [{"loc": [str(x) for x in e.get("loc", ())], "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))}
                for e in exc.errors()[:10]]  # raw errors can hold bytes/exceptions that aren't JSON-safe
        return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request.", "errors": safe})

    @app.exception_handler(UpstreamError)
    async def upstream(_: Request, exc: UpstreamError):
        return JSONResponse(status_code=503, content={
            "detail": f"{exc} — HydraDB is unreachable right now. Your content was saved locally and answers "
                      "will use the local copy; try again shortly."})

    @app.exception_handler(ValueError)
    async def bad_input(_: Request, exc: ValueError):  # includes IngestError
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": f"Internal error: {type(exc).__name__}"})

    for router in ROUTERS:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    def home():  # lightweight fallback UI when the Next.js app isn't running
        return FileResponse(STATIC / "index.html")

    return app
