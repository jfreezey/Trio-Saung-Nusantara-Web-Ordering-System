from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import DbConn
from app.core.security import decode_access_token, hash_customer_token

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesi login tidak valid atau sudah berakhir. Silakan login ulang.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    conn=DbConn,
) -> dict:
    if credentials is None:
        raise _UNAUTHORIZED
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise _UNAUTHORIZED

    # Database adalah sumber kebenaran: akun nonaktif atau role berubah langsung berlaku.
    user = conn.execute(
        "SELECT id, name, email, role FROM app.users WHERE id = %s AND is_active",
        (user_id,),
    ).fetchone()
    if user is None:
        raise _UNAUTHORIZED
    return user


def require_role(*allowed_roles: str):
    """Pemakaian: Depends(require_role("admin")) atau require_role("admin", "cashier")."""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses ke fitur ini.",
            )
        return user

    return checker


require_admin = require_role("admin")
require_cashier = require_role("cashier")
require_staff = require_role("admin", "cashier")


_INVALID_CUSTOMER = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesi pemesanan tidak valid atau sudah berakhir. Silakan scan ulang QR di meja.",
)


def get_customer_access(
    x_customer_token: str | None = Header(default=None, alias="X-Customer-Token"),
    conn=DbConn,
) -> dict:
    """Validasi token pelanggan yang didapat dari POST /api/customer/access."""
    if not x_customer_token or len(x_customer_token) > 128:
        raise _INVALID_CUSTOMER

    access = conn.execute(
        """
        SELECT ca.id, ca.table_id, ca.table_epoch, ca.session_id, ca.expires_at,
               t.table_number, t.access_epoch
        FROM app.customer_accesses ca
        JOIN app.restaurant_tables t ON t.id = ca.table_id
        WHERE ca.token_hash = %s
          AND ca.access_type = 'table'
          AND ca.revoked_at IS NULL
          AND ca.expires_at > now()
          AND t.is_active
        """,
        (hash_customer_token(x_customer_token),),
    ).fetchone()

    if access is None or access["table_epoch"] != access["access_epoch"]:
        raise _INVALID_CUSTOMER
    return access
