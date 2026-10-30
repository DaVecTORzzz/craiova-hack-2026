from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine, init_db
from app.routers import edge, events, health, ws
from app.seed import ensure_placeholder_image, seed


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

    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
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
    app.include_router(ws.router)
    return app


app = create_app()
