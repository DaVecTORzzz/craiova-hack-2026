from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    LOCAL_TZ = ZoneInfo("Europe/Bucharest")
except Exception:
    from datetime import timedelta
    LOCAL_TZ = timezone(timedelta(hours=2))


def utcnow() -> datetime:
    """Naive UTC 'now', the only form stored in the DB."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime | None) -> str | None:
    """Naive UTC -> '2026-10-30T10:42:13.120Z'."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def local_hms(dt: datetime) -> str:
    """Naive UTC -> '10:42:13' in Europe/Bucharest."""
    return dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ).strftime("%H:%M:%S")
