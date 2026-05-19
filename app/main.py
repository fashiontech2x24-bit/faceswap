"""FastAPI application factory and lifespan handler."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.swap import router as swap_router
from app.services.face_swap import face_swap_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify GHOST 2.0 assets exist — fails fast if setup.sh hasn't been run
    face_swap_service.load()
    log.info("Server ready.")
    yield
    log.info("Shutting down.")


app = FastAPI(
    title="GHOST 2.0 Face Swap API",
    version="2.0.0",
    lifespan=lifespan,
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(swap_router)


# ── Static web UI ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(WEB_DIR / "index.html")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}
