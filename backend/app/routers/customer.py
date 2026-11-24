"""Endpoint pelanggan. Tanpa login: identitas = token dari scan QR (header X-Customer-Token)."""
from fastapi import APIRouter, Depends, Response, status

from app.core.database import DbConn
from app.core.deps import get_customer_access
from app.core.rate_limit import checkout_limiter, customer_access_limiter
from app.schemas.order import CheckoutRequest, CustomerAccessRequest
from app.services import order_service

router = APIRouter(prefix="/api/customer", tags=["Customer"])


@router.post("/access", status_code=201, dependencies=[Depends(customer_access_limiter)])
def create_access(body: CustomerAccessRequest, conn=DbConn):
    """Dipanggil otomatis oleh halaman menu saat dibuka dari QR (?t=<qr_token>)."""
    data = order_service.create_customer_access(conn, body.qr_token)
    return {"success": True, "data": data}


@router.get("/table")
def get_my_table(access: dict = Depends(get_customer_access), conn=DbConn):
    """Nomor meja + semua pesanan di tagihan meja yang masih terbuka."""
    return {"success": True, "data": order_service.get_customer_table_view(conn, access)}


@router.post("/orders", status_code=201, dependencies=[Depends(checkout_limiter)])
def checkout(
    body: CheckoutRequest,
    response: Response,
    access: dict = Depends(get_customer_access),
    conn=DbConn,
):
    order, created = order_service.checkout(conn, access, body.checkout_key, body.items)
    if not created:
        response.status_code = status.HTTP_200_OK  # permintaan ulang, pesanan yang sama
    return {
        "success": True,
        "message": "Pesanan berhasil dikirim ke kasir." if created else "Pesanan ini sudah terkirim sebelumnya.",
        "data": order,
    }
