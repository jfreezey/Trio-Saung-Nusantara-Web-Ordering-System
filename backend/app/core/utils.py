import hashlib
import json
import secrets
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")


def rupiah(value) -> int:
    """numeric(14,2) dari database (Decimal) -> int rupiah untuk JSON."""
    if value is None:
        return 0
    return int(Decimal(value))


def generate_code(prefix: str) -> str:
    """Kode yang mudah dibaca manusia, mis. ORD-20261123-7F3A9C2B."""
    today = datetime.now(WIB).strftime("%Y%m%d")
    return f"{prefix}-{today}-{secrets.token_hex(4).upper()}"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(payload) -> str:
    """SHA-256 dari JSON yang dinormalisasi (urutan key tetap, tanpa spasi)."""
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_hex(normalized)
