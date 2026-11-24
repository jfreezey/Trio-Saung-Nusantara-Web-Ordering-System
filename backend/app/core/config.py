import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"

load_dotenv(ROOT_DIR / ".env", override=False, interpolate=False)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or "ISI_" in value:
        raise RuntimeError(f"{name} belum diisi di file .env (root repo).")
    return value


APP_ENV = os.getenv("APP_ENV", "development")

DB_HOST = _required("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_APP_USER = _required("DB_APP_USER")
DB_APP_PASSWORD = _required("DB_APP_PASSWORD")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")
DB_SSLROOTCERT = os.getenv("DB_SSLROOTCERT", "")

# JWT untuk admin & kasir 
JWT_SECRET_KEY = _required("JWT_SECRET_KEY")
if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY minimal 32 karakter. Buat dengan secrets.token_urlsafe(48).")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "90"))

# Akses pelanggan dari QR 
CUSTOMER_ACCESS_HOURS = int(os.getenv("CUSTOMER_ACCESS_HOURS", "4"))

# Frontend 
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
    if origin.strip()
]
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500").rstrip("/")
CUSTOMER_MENU_PATH = "/frontend/components/customer/menu.html"

# Upload gambar menu 
STATIC_DIR = BACKEND_DIR / "static"
MENU_IMAGE_DIR = STATIC_DIR / "menu-images"
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB
