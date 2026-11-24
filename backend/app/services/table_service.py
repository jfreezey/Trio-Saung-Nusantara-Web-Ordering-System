"""Query & aturan bisnis meja dan QR code."""
import secrets
from urllib.parse import quote

from fastapi import HTTPException, status
from psycopg import errors

from app.core.config import CUSTOMER_MENU_PATH, FRONTEND_BASE_URL

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meja tidak ditemukan.")
DUPLICATE = HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nomor meja sudah dipakai.")

SELECT_TABLE = """
    SELECT t.id, t.table_number, t.qr_token,
           EXISTS (SELECT 1 FROM app.ordering_sessions s
                   WHERE s.table_id = t.id AND s.status = 'open') AS has_open_session
    FROM app.restaurant_tables t
    WHERE t.is_active
"""


def _out(row: dict) -> dict:
    data = dict(row)
    data["qr_url"] = f"{FRONTEND_BASE_URL}{CUSTOMER_MENU_PATH}?t={quote(row['qr_token'])}"
    return data


def list_tables(conn) -> list[dict]:
    # Urutkan "2" sebelum "10": angka dulu, lalu teks.
    rows = conn.execute(
        SELECT_TABLE
        + " ORDER BY (t.table_number ~ '^[0-9]+$') DESC,"
        "   CASE WHEN t.table_number ~ '^[0-9]+$' THEN t.table_number::numeric END,"
        "   t.table_number"
    ).fetchall()
    return [_out(r) for r in rows]


def get_table(conn, table_id) -> dict:
    row = conn.execute(SELECT_TABLE + " AND t.id = %s", (table_id,)).fetchone()
    if row is None:
        raise NOT_FOUND
    return _out(row)


def create_table(conn, table_number: str) -> dict:
    table_number = table_number.strip()
    existing = conn.execute(
        "SELECT id, is_active FROM app.restaurant_tables WHERE table_number = %s FOR UPDATE",
        (table_number,),
    ).fetchone()
    if existing and existing["is_active"]:
        raise DUPLICATE
    if existing:
        # Meja yang pernah dihapus diaktifkan lagi dengan QR baru (QR lama tidak berlaku).
        conn.execute(
            "UPDATE app.restaurant_tables SET is_active = true, qr_token = %s WHERE id = %s",
            (secrets.token_urlsafe(24), existing["id"]),
        )
        return get_table(conn, existing["id"])
    row = conn.execute(
        "INSERT INTO app.restaurant_tables (table_number, qr_token) VALUES (%s, %s) RETURNING id",
        (table_number, secrets.token_urlsafe(24)),
    ).fetchone()
    return get_table(conn, row["id"])


def update_table(conn, table_id, table_number: str) -> dict:
    try:
        row = conn.execute(
            "UPDATE app.restaurant_tables SET table_number = %s WHERE id = %s AND is_active RETURNING id",
            (table_number.strip(), table_id),
        ).fetchone()
    except errors.UniqueViolation:
        raise DUPLICATE
    if row is None:
        raise NOT_FOUND
    return get_table(conn, table_id)


def regenerate_qr(conn, table_id) -> dict:
    """Pakai kalau QR bocor/rusak. QR lama langsung tidak bisa dipakai untuk scan baru."""
    row = conn.execute(
        "UPDATE app.restaurant_tables SET qr_token = %s WHERE id = %s AND is_active RETURNING id",
        (secrets.token_urlsafe(24), table_id),
    ).fetchone()
    if row is None:
        raise NOT_FOUND
    return get_table(conn, table_id)


def delete_table(conn, table_id) -> None:
    table = get_table(conn, table_id)
    if table["has_open_session"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meja masih punya pesanan yang belum dibayar.",
        )
    conn.execute("UPDATE app.restaurant_tables SET is_active = false WHERE id = %s", (table_id,))
