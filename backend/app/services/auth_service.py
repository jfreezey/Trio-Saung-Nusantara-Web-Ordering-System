"""Logika login dan ganti password untuk admin & kasir."""
from fastapi import HTTPException, status

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import create_access_token, hash_password, verify_password

INVALID_LOGIN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    # Pesan sama untuk email salah maupun password salah (cegah user enumeration).
    detail="Email atau kata sandi salah.",
)


def login(conn, email: str, password: str) -> dict:
    user = conn.execute(
        """
        SELECT id, name, email, role, password_hash
        FROM app.users
        WHERE email = %s AND is_active
        """,
        (email.strip().lower(),),
    ).fetchone()

    stored_hash = user["password_hash"] if user else None
    if not verify_password(password, stored_hash) or user is None:
        raise INVALID_LOGIN

    token = create_access_token(user_id=str(user["id"]), role=user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


def change_password(conn, user_id, current_password: str, new_password: str) -> None:
    row = conn.execute(
        "SELECT password_hash FROM app.users WHERE id = %s AND is_active FOR UPDATE",
        (user_id,),
    ).fetchone()
    if row is None or not verify_password(current_password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kata sandi lama salah.")
    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru harus berbeda dari kata sandi lama.",
        )
    conn.execute(
        "UPDATE app.users SET password_hash = %s WHERE id = %s",
        (hash_password(new_password), user_id),
    )
