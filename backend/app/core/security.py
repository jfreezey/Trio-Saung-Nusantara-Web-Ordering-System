import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from app.core.utils import sha256_hex

password_hash = PasswordHash.recommended()  
_DUMMY_HASH = password_hash.hash("dummy-password-untuk-timing")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        password_hash.verify(password, _DUMMY_HASH)
        return False
    try:
        return password_hash.verify(password, hashed_password)
    except Exception:
        # Hash rusak/format tidak dikenal diperlakukan sebagai password salah.
        return False


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    # mencegah serangan "alg: none" / algorithm confusion.
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )


def new_customer_token() -> tuple[str, str]:
    """Token acak untuk pelanggan. Yang disimpan di database hanya hash-nya."""
    raw = secrets.token_urlsafe(32)
    return raw, sha256_hex(raw)


def hash_customer_token(raw: str) -> str:
    return sha256_hex(raw)
