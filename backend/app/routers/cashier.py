"""Endpoint kasir. Membaca: admin & kasir. Mengubah transaksi: hanya kasir."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.database import DbConn
from app.core.deps import require_cashier, require_staff
from app.schemas.cashier import AdjustItemsRequest, CancelSessionRequest, PaymentRequest
from app.services import cashier_service

router = APIRouter(prefix="/api/cashier", tags=["Cashier"])


@router.get("/sessions", dependencies=[Depends(require_staff)])
def get_open_sessions(conn=DbConn):
    """Daftar meja yang tagihannya masih terbuka (belum dibayar) + total sementara."""
    return {"success": True, "data": cashier_service.list_open_sessions(conn)}


@router.get("/orders/new", dependencies=[Depends(require_staff)])
def get_new_orders(since: datetime | None = None, conn=DbConn):
    """Polling notifikasi pesanan baru. Kirim ?since=<server_time dari respons sebelumnya>."""
    return {"success": True, "data": cashier_service.list_new_orders(conn, since)}


@router.get("/sessions/{session_id}", dependencies=[Depends(require_staff)])
def get_session_detail(session_id: UUID, conn=DbConn):
    return {"success": True, "data": cashier_service.get_session_detail(conn, session_id)}


@router.post("/sessions/{session_id}/adjustments")
def adjust_items(
    session_id: UUID,
    body: AdjustItemsRequest,
    user: dict = Depends(require_cashier),
    conn=DbConn,
):
    """Mengurangi jumlah item (mis. stok habis setelah dipesan). Wajib ada alasan."""
    data = cashier_service.adjust_items(conn, session_id, user, body.reason, body.items)
    return {"success": True, "message": "Pesanan berhasil dikoreksi.", "data": data}


@router.post("/sessions/{session_id}/payment", status_code=201)
def pay_session(
    session_id: UUID,
    body: PaymentRequest,
    response: Response,
    user: dict = Depends(require_cashier),
    conn=DbConn,
):
    receipt, created = cashier_service.pay(
        conn, session_id, user, body.payment_key, body.payment_method, body.cash_received
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return {"success": True, "message": "Pembayaran berhasil.", "data": receipt}


@router.get("/sessions/{session_id}/receipt", dependencies=[Depends(require_staff)])
def get_receipt(session_id: UUID, conn=DbConn):
    """Data struk untuk cetak ulang."""
    return {"success": True, "data": cashier_service.get_receipt(conn, session_id)}


@router.post("/sessions/{session_id}/cancel")
def cancel_session(
    session_id: UUID,
    body: CancelSessionRequest,
    user: dict = Depends(require_cashier),
    conn=DbConn,
):
    data = cashier_service.cancel_session(conn, session_id, user, body.reason)
    return {"success": True, "message": "Sesi meja dibatalkan.", "data": data}
