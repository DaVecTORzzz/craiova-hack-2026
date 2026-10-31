from collections.abc import Generator
from datetime import timezone
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.sql.sqltypes import UTCDateTime

from app.config import get_settings

# Compatibility shim for SQLModel 0.0.48+ UTCDateTime to support naive UTC datetimes
# as required by Section 1 ("Store datetimes as naive UTC in the DB") and Section 4.
_orig_bind = UTCDateTime.process_bind_param
_orig_result = UTCDateTime.process_result_value


def _patched_bind(self, value, dialect):
    if value is not None and value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return _orig_bind(self, value, dialect)


def _patched_result(self, value, dialect):
    res = _orig_result(self, value, dialect)
    if res is not None:
        return res.replace(tzinfo=None)
    return res


UTCDateTime.process_bind_param = _patched_bind
UTCDateTime.process_result_value = _patched_result

_engine: Engine | None = None


def get_engine(database_url: str | None = None) -> Engine:
    global _engine
    settings = get_settings()
    target_url = database_url or settings.database_url
    if _engine is None or database_url is not None or str(_engine.url) != target_url:
        _engine = create_engine(target_url, connect_args={"check_same_thread": False})
    return _engine


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_db(engine: Engine | None = None) -> None:
    if engine is None:
        engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    engine = get_engine()
    with Session(engine) as session:
        yield session
