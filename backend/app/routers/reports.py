from datetime import date as Date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.schemas import Kpi, ShiftReport
from app.services.kpi import Shift, build_shift_report, compute_kpi, current_shift, events_in_window

router = APIRouter(tags=["reports"])


@router.get("/kpi", response_model=Kpi)
async def get_kpi(
    date: Date | None = None,
    shift: Shift | None = None,
    session: Session = Depends(get_session),
) -> Kpi:
    if date is None and shift is None:
        shift, date = current_shift()
    elif date is None or shift is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date and shift must be given together",
        )
    return compute_kpi(events_in_window(session, shift, date))


@router.get("/reports", response_model=ShiftReport)
async def get_shift_report(
    shift: Shift,
    date: Date,
    refresh: bool = False,
    session: Session = Depends(get_session),
) -> ShiftReport:
    return await build_shift_report(session, shift, date, refresh=refresh)
