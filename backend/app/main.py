import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine, init_db
from app.routers import cameras, edge, events, health, reports, stream, ws, zones
from app.seed import ensure_placeholder_image, seed
from app.services.escalation import cancel_all, recover_timers


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Create snapshot folders
    snapshot_path = Path(settings.snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    (snapshot_path / "reference").mkdir(parents=True, exist_ok=True)
    (snapshot_path / "live").mkdir(parents=True, exist_ok=True)
    ensure_placeholder_image(settings.snapshot_dir)

    # Initialize DB and seed data
    init_db()
    with Session(get_engine()) as session:
        seed(session)
    await recover_timers()

    mock_task: asyncio.Task | None = None
    if settings.use_mock:
        from app.mock import run_mock_generator
        mock_task = asyncio.create_task(run_mock_generator())

    yield

    cancel_all()

    if mock_task is not None:
        mock_task.cancel()
        try:
            await mock_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # httpx logs every request URL at INFO, which would leak the Slack webhook URL.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()
    app = FastAPI(title="SafeSight API", lifespan=lifespan)

    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(edge.router)
    app.include_router(events.router)
    app.include_router(cameras.router)
    app.include_router(zones.router)
    app.include_router(reports.router)
    app.include_router(stream.router)
    app.include_router(ws.router)

    snapshot_path = Path(settings.snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    app.mount("/snapshots", StaticFiles(directory=str(snapshot_path)), name="snapshots")

    return app


app = create_app()
