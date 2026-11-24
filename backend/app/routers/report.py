"""Endpoint laporan. Hanya admin."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from app.core.database import DbConn
from app.core.deps import require_admin
from app.core.utils import WIB
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["Reports"], dependencies=[Depends(require_admin)])


def _today() -> date:
    return datetime.now(WIB).date()


@router.get("/summary")
def get_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    conn=DbConn,
):
    """Tanpa parameter = laporan hari ini (WIB)."""
    date_from = date_from or _today()
    date_to = date_to or date_from
    return {"success": True, "data": report_service.summary(conn, date_from, date_to)}


@router.get("/transactions")
def get_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn=DbConn,
):
    date_from = date_from or _today()
    date_to = date_to or date_from
    data = report_service.transactions(conn, date_from, date_to, limit, offset)
    return {"success": True, "data": data}
