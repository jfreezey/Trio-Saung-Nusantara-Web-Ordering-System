"""Query & aturan bisnis menu, termasuk upload gambar."""
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import MAX_IMAGE_BYTES, MENU_IMAGE_DIR
from app.core.utils import rupiah

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu tidak ditemukan.")

SELECT_MENU = """
    SELECT m.id, m.name, m.description, m.price, m.image_url, m.is_available,
           m.category_id, c.name AS category_name
    FROM app.menus m
    JOIN app.categories c ON c.id = m.category_id
    WHERE m.is_active AND c.is_active
"""


def _out(row: dict) -> dict:
    return {**row, "price": rupiah(row["price"])}


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_menus(conn, category_id=None, search: str | None = None, available_only: bool = False):
    query = SELECT_MENU
    params: list = []
    if category_id:
        query += " AND m.category_id = %s"
        params.append(category_id)
    if search:
        query += " AND m.name ILIKE %s"
        params.append(f"%{_escape_like(search.strip())}%")
    if available_only:
        query += " AND m.is_available"
    query += " ORDER BY c.sort_order, c.name, m.name"
    return [_out(r) for r in conn.execute(query, params).fetchall()]


def get_menu(conn, menu_id) -> dict:
    row = conn.execute(SELECT_MENU + " AND m.id = %s", (menu_id,)).fetchone()
    if row is None:
        raise NOT_FOUND
    return _out(row)


def _ensure_category(conn, category_id) -> None:
    ok = conn.execute(
        "SELECT 1 FROM app.categories WHERE id = %s AND is_active", (category_id,)
    ).fetchone()
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kategori tidak valid.")


def create_menu(conn, data: dict) -> dict:
    _ensure_category(conn, data["category_id"])
    row = conn.execute(
        """INSERT INTO app.menus (category_id, name, description, price, is_available)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (data["category_id"], data["name"].strip(), data["description"], data["price"], data["is_available"]),
    ).fetchone()
    return get_menu(conn, row["id"])


def update_menu(conn, menu_id, data: dict) -> dict:
    _ensure_category(conn, data["category_id"])
    row = conn.execute(
        """UPDATE app.menus
           SET category_id = %s, name = %s, description = %s, price = %s, is_available = %s
           WHERE id = %s AND is_active RETURNING id""",
        (data["category_id"], data["name"].strip(), data["description"], data["price"],
         data["is_available"], menu_id),
    ).fetchone()
    if row is None:
        raise NOT_FOUND
    return get_menu(conn, menu_id)


def set_availability(conn, menu_id, is_available: bool) -> dict:
    row = conn.execute(
        "UPDATE app.menus SET is_available = %s WHERE id = %s AND is_active RETURNING id",
        (is_available, menu_id),
    ).fetchone()
    if row is None:
        raise NOT_FOUND
    return get_menu(conn, menu_id)


def delete_menu(conn, menu_id) -> None:
    # Soft delete: riwayat pesanan tetap menunjuk ke menu ini.
    row = conn.execute(
        "UPDATE app.menus SET is_active = false WHERE id = %s AND is_active RETURNING id",
        (menu_id,),
    ).fetchone()
    if row is None:
        raise NOT_FOUND


# ---------- Upload gambar ----------

def _detect_image_ext(head: bytes) -> str | None:
    """Cek isi file (magic bytes), bukan cuma nama file / Content-Type dari client."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def save_menu_image(conn, menu_id, upload: UploadFile) -> dict:
    current = conn.execute(
        "SELECT image_url FROM app.menus WHERE id = %s AND is_active FOR UPDATE", (menu_id,)
    ).fetchone()
    if current is None:
        raise NOT_FOUND

    content = upload.file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran gambar maksimal 2 MB.")
    ext = _detect_image_ext(content[:16])
    if ext is None:
        raise HTTPException(status_code=400, detail="Format gambar harus PNG, JPG, atau WEBP.")

    MENU_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"  # nama file dibuat server, bukan dari client
    (MENU_IMAGE_DIR / filename).write_bytes(content)
    image_url = f"/static/menu-images/{filename}"

    conn.execute("UPDATE app.menus SET image_url = %s WHERE id = %s", (image_url, menu_id))

    # Hapus file lama (hanya kalau memang file milik folder upload ini).
    old = current["image_url"] or ""
    if old.startswith("/static/menu-images/"):
        old_path = MENU_IMAGE_DIR / Path(old).name
        if old_path.is_file():
            old_path.unlink()

    return get_menu(conn, menu_id)
