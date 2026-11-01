from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.routers.health import record_edge_seen


def verify_edge_token(x_edge_token: str | None = Header(default=None, alias="X-Edge-Token")) -> None:
    """The edge proves itself with the shared token; every write route uses it."""
    settings = get_settings()
    if not x_edge_token or x_edge_token != settings.edge_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid edge token",
        )
    record_edge_seen()
