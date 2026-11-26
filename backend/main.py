import logging
import secrets
import time
from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

from scripts.db import connect


app = FastAPI(title="Trio Saung API")
logger = logging.getLogger(__name__)

password_hasher = PasswordHash.recommended()
dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))

# Konfigurasi sesi untuk pengembangan lokal.
COOKIE_NAME = "trio_session"
SESSION_SECONDS = 60 * 60 * 8  # 8 jam

# Sesi hilang ketika backend restart/reload.
sessions = {}
sessions_lock = Lock()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


def public_user(user):
    """Data pengguna yang boleh dikirim ke browser."""
    return {
        "id": str(user[0]),
        "name": user[1],
        "email": user[2],
        "role": user[4],
    }


def current_user(request: Request):
    """Memeriksa sesi dan mengambil data akun terbaru."""
    token = request.cookies.get(COOKIE_NAME)

    with sessions_lock:
        session = sessions.get(token)

        if not session or session["expires_at"] <= time.time():
            sessions.pop(token, None)
            raise HTTPException(
                status_code=401,
                detail="Silakan login terlebih dahulu.",
            )

    try:
        with connect(as_app=True) as conn:
            user = conn.execute(
                """
                SELECT id, name, email, password_hash, role, is_active
                FROM app.users
                WHERE id = %s
                """,
                (session["user_id"],),
            ).fetchone()
    except Exception:
        logger.error("Gagal memeriksa akun untuk sesi.")
        raise HTTPException(
            status_code=503,
            detail="Database belum dapat diakses.",
        ) from None

    # Password berubah atau akun nonaktif membuat sesi tidak berlaku.
    if (
        not user
        or not user[5]
        or user[3] != session["password_hash"]
    ):
        with sessions_lock:
            sessions.pop(token, None)

        raise HTTPException(
            status_code=401,
            detail="Sesi tidak berlaku. Silakan login kembali.",
        )

    return public_user(user)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
):
    email = data.email.strip().lower()

    try:
        # Menggunakan akun database aplikasi dari .env.
        with connect(as_app=True) as conn:
            user = conn.execute(
                """
                SELECT id, name, email, password_hash, role, is_active
                FROM app.users
                WHERE email = %s
                """,
                (email,),
            ).fetchone()
    except Exception:
        logger.error("Gagal membaca akun dari database.")
        raise HTTPException(
            status_code=503,
            detail="Database belum dapat diakses.",
        ) from None

    # Tetap lakukan verifikasi hash jika email tidak ditemukan.
    stored_hash = user[3] if user else dummy_hash

    try:
        valid_password = password_hasher.verify(
            data.password,
            stored_hash,
        )
    except Exception:
        logger.error("Hash password tidak dapat diverifikasi.")
        raise HTTPException(
            status_code=500,
            detail="Data password akun perlu diperiksa.",
        ) from None

    if not user or not valid_password or not user[5]:
        raise HTTPException(
            status_code=401,
            detail="Email atau kata sandi salah, atau akun tidak aktif.",
        )

    token = secrets.token_urlsafe(32)
    now = time.time()

    with sessions_lock:
        # Hapus sesi yang kedaluwarsa.
        for old_token, session in list(sessions.items()):
            if session["expires_at"] <= now:
                sessions.pop(old_token, None)

        # Ganti sesi lama browser ini.
        old_token = request.cookies.get(COOKIE_NAME)
        sessions.pop(old_token, None)

        sessions[token] = {
            "user_id": str(user[0]),
            "password_hash": user[3],
            "expires_at": now + SESSION_SECONDS,
        }

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=False,  # Lokal HTTP. Gunakan True untuk hosting HTTPS.
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"

    return {
        "message": "Login berhasil.",
        "user": public_user(user),
    }


@app.get("/api/me")
def me(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"

    return {
        "user": current_user(request),
    }


@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)

    with sessions_lock:
        sessions.pop(token, None)

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"

    return {
        "message": "Logout berhasil.",
    }

from pathlib import Path
from fastapi.responses import FileResponse, RedirectResponse


FRONTEND_DIR = (
    Path(__file__).resolve().parents[1] / "frontend"
).resolve()


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(
        url="/frontend/index.html",
        status_code=303,
    )


@app.get("/frontend/{file_path:path}", include_in_schema=False)
def frontend_file(file_path: str, request: Request):
    target = (FRONTEND_DIR / file_path).resolve()

    # Hanya izinkan file di dalam folder frontend.
    if not target.is_relative_to(FRONTEND_DIR):
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    relative_path = target.relative_to(FRONTEND_DIR)
    parts = tuple(part.lower() for part in relative_path.parts)

    if any(part.startswith(".") for part in parts):
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    # Periksa sesi sebelum mengirim halaman admin atau kasir.
    required_role = None

    if parts[:2] == ("components", "admin"):
        required_role = "admin"
    elif parts[:2] == ("components", "kasir"):
        required_role = "cashier"

    if required_role:
        try:
            user = current_user(request)
        except HTTPException as exc:
            if exc.status_code == 401:
                return RedirectResponse(
                    url="/frontend/index.html",
                    status_code=303,
                    headers={"Cache-Control": "no-store"},
                )
            raise

        if user["role"] != required_role:
            raise HTTPException(
                status_code=403,
                detail="Akun ini tidak memiliki akses ke halaman tersebut.",
            )

    if not target.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    return FileResponse(
        path=target,
        headers={"Cache-Control": "no-store"},
    )