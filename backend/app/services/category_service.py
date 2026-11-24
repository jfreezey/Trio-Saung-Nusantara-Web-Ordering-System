"""Query & aturan bisnis kategori."""
from fastapi import HTTPException, status
from psycopg import errors

COLUMNS = "id, name, sort_order"

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori tidak ditemukan.")
DUPLICATE = HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nama kategori sudah dipakai.")


def list_categories(conn) -> list[dict]:
    return conn.execute(
        f"SELECT {COLUMNS} FROM app.categories WHERE is_active ORDER BY sort_order, name"
    ).fetchall()


def get_category(conn, category_id) -> dict:
    row = conn.execute(
        f"SELECT {COLUMNS} FROM app.categories WHERE id = %s AND is_active", (category_id,)
    ).fetchone()
    if row is None:
        raise NOT_FOUND
    return row


def create_category(conn, name: str, sort_order: int) -> dict:
    name = name.strip()
    # Unique index memakai lower(btrim(name)) dan ikut menghitung kategori yang sudah
    # di-soft-delete. Jadi kalau namanya pernah dihapus, kategori lama diaktifkan lagi.
    existing = conn.execute(
        "SELECT id, is_active FROM app.categories WHERE lower(btrim(name)) = lower(%s) FOR UPDATE",
        (name,),
    ).fetchone()
    if existing and existing["is_active"]:
        raise DUPLICATE
    if existing:
        return conn.execute(
            f"""UPDATE app.categories SET name = %s, sort_order = %s, is_active = true
                WHERE id = %s RETURNING {COLUMNS}""",
            (name, sort_order, existing["id"]),
        ).fetchone()
    try:
        return conn.execute(
            f"INSERT INTO app.categories (name, sort_order) VALUES (%s, %s) RETURNING {COLUMNS}",
            (name, sort_order),
        ).fetchone()
    except errors.UniqueViolation:
        raise DUPLICATE


def update_category(conn, category_id, name: str, sort_order: int) -> dict:
    try:
        row = conn.execute(
            f"""UPDATE app.categories SET name = %s, sort_order = %s
                WHERE id = %s AND is_active RETURNING {COLUMNS}""",
            (name.strip(), sort_order, category_id),
        ).fetchone()
    except errors.UniqueViolation:
        raise DUPLICATE
    if row is None:
        raise NOT_FOUND
    return row


def delete_category(conn, category_id) -> None:
    get_category(conn, category_id)
    in_use = conn.execute(
        "SELECT count(*) AS n FROM app.menus WHERE category_id = %s AND is_active",
        (category_id,),
    ).fetchone()["n"]
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kategori masih dipakai oleh {in_use} menu. Pindahkan atau hapus menunya dulu.",
        )
    conn.execute("UPDATE app.categories SET is_active = false WHERE id = %s", (category_id,))
