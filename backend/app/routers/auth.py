"""Endpoint autentikasi admin & kasir. Tidak ada registrasi."""
from fastapi import APIRouter, Depends

from app.core.database import DbConn
from app.core.deps import require_staff
from app.core.rate_limit import login_limiter
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", dependencies=[Depends(login_limiter)])
def login(body: LoginRequest, conn=DbConn):
    data = auth_service.login(conn, body.email, body.password)
    return {"success": True, "message": "Login berhasil.", "data": data}


@router.get("/me")
def me(user: dict = Depends(require_staff)):
    return {"success": True, "data": user}


@router.put("/password")
def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(require_staff),
    conn=DbConn,
):
    auth_service.change_password(conn, user["id"], body.current_password, body.new_password)
    return {"success": True, "message": "Kata sandi berhasil diubah. Silakan login ulang."}
