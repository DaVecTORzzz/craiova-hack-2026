from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.routers.health import record_edge_seen
from app.schemas import EdgeEventIn, EventOut
from app.services.events import ingest

router = APIRouter(prefix="/edge", tags=["edge"])


def verify_edge_token(x_edge_token: str | None = Header(default=None, alias="X-Edge-Token")) -> None:
    settings = get_settings()
    if not x_edge_token or x_edge_token != settings.edge_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid edge token",
        )
    record_edge_seen()


@router.post("/events", response_model=EventOut)
async def post_edge_event(
    payload: EdgeEventIn,
    response: Response,
    session: Session = Depends(get_session),
    _token: None = Depends(verify_edge_token),
) -> EventOut:
    out, created = ingest(session, payload)
    if created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
    return out
