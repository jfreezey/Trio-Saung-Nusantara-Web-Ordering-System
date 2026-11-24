"""Alur pelanggan: token akses dari QR, checkout, dan melihat pesanan meja.

Urutan penguncian baris (FOR UPDATE) di seluruh backend SELALU:
    restaurant_tables -> ordering_sessions / customer_accesses -> orders/order_items
Urutan yang konsisten mencegah deadlock antara checkout pelanggan dan pembayaran kasir.
"""
from fastapi import HTTPException, status

from app.core.config import CUSTOMER_ACCESS_HOURS
from app.core.security import new_customer_token
from app.core.utils import fingerprint, generate_code, rupiah

INVALID_ACCESS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesi pemesanan tidak valid atau sudah berakhir. Silakan scan ulang QR di meja.",
)


# ---------- Akses dari QR ----------

def create_customer_access(conn, qr_token: str) -> dict:
    table = conn.execute(
        """SELECT id, table_number, access_epoch FROM app.restaurant_tables
           WHERE qr_token = %s AND is_active""",
        (qr_token,),
    ).fetchone()
    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code tidak valid. Silakan minta bantuan staf.",
        )

    raw_token, token_hash = new_customer_token()
    row = conn.execute(
        """INSERT INTO app.customer_accesses
               (token_hash, access_type, table_id, table_epoch, expires_at)
           VALUES (%s, 'table', %s, %s, now() + make_interval(hours => %s))
           RETURNING expires_at""",
        (token_hash, table["id"], table["access_epoch"], CUSTOMER_ACCESS_HOURS),
    ).fetchone()
    return {
        "access_token": raw_token,  # hanya dikirim sekali; database menyimpan hash-nya
        "table_number": table["table_number"],
        "expires_at": row["expires_at"],
    }


# ---------- Membaca pesanan ----------

def attach_items(conn, orders: list[dict]) -> list[dict]:
    if not orders:
        return []
    order_ids = [o["id"] for o in orders]
    items = conn.execute(
        """SELECT id, order_id, menu_id, menu_name_snapshot AS menu_name,
                  unit_price_snapshot AS unit_price, original_quantity, quantity, notes
           FROM app.order_items WHERE order_id = ANY(%s)
           ORDER BY created_at, id""",
        (order_ids,),
    ).fetchall()
    by_order: dict = {o["id"]: [] for o in orders}
    for item in items:
        price = rupiah(item["unit_price"])
        by_order[item.pop("order_id")].append(
            {**item, "unit_price": price, "subtotal": price * item["quantity"]}
        )
    result = []
    for order in orders:
        order_items = by_order[order["id"]]
        result.append({**order, "items": order_items, "total": sum(i["subtotal"] for i in order_items)})
    return result


def get_order(conn, order_id) -> dict:
    order = conn.execute(
        """SELECT o.id, o.order_code, o.status, o.created_at, o.session_id, t.table_number
           FROM app.orders o
           JOIN app.ordering_sessions s ON s.id = o.session_id
           LEFT JOIN app.restaurant_tables t ON t.id = s.table_id
           WHERE o.id = %s""",
        (order_id,),
    ).fetchone()
    return attach_items(conn, [order])[0]


def get_session_orders(conn, session_id) -> list[dict]:
    orders = conn.execute(
        """SELECT id, order_code, status, created_at FROM app.orders
           WHERE session_id = %s ORDER BY created_at""",
        (session_id,),
    ).fetchall()
    return attach_items(conn, orders)


def get_customer_table_view(conn, access: dict) -> dict:
    session = conn.execute(
        """SELECT id, opened_at FROM app.ordering_sessions
           WHERE table_id = %s AND status = 'open'""",
        (access["table_id"],),
    ).fetchone()
    orders = get_session_orders(conn, session["id"]) if session else []
    return {
        "table_number": access["table_number"],
        "has_open_bill": session is not None,
        "orders": orders,
        "total": sum(o["total"] for o in orders),
    }


# ---------- Checkout ----------

def checkout(conn, access: dict, checkout_key, items: list) -> tuple[dict, bool]:
    """Mengembalikan (order, created). created=False berarti permintaan ulang (idempoten)."""
    checkout_fp = fingerprint(
        sorted([str(i.menu_id), i.quantity, i.notes or ""] for i in items)
    )

    # 1) Kunci meja, lalu akses pelanggan (urutan sama dengan pembayaran kasir).
    table = conn.execute(
        "SELECT id, access_epoch, is_active FROM app.restaurant_tables WHERE id = %s FOR UPDATE",
        (access["table_id"],),
    ).fetchone()
    acc = conn.execute(
        """SELECT id, session_id, table_epoch, (revoked_at IS NULL AND expires_at > now()) AS usable
           FROM app.customer_accesses WHERE id = %s FOR UPDATE""",
        (access["id"],),
    ).fetchone()
    # Cek ulang setelah dikunci: bisa saja kasir baru saja menutup meja ini.
    if not table["is_active"] or not acc["usable"] or acc["table_epoch"] != table["access_epoch"]:
        raise INVALID_ACCESS

    # 2) Idempotensi: checkout_key yang sama tidak boleh membuat pesanan baru.
    existing = conn.execute(
        """SELECT id, checkout_fingerprint FROM app.orders
           WHERE customer_access_id = %s AND checkout_key = %s""",
        (acc["id"], checkout_key),
    ).fetchone()
    if existing:
        if existing["checkout_fingerprint"] != checkout_fp:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="checkout_key sudah dipakai untuk isi keranjang yang berbeda.",
            )
        return get_order(conn, existing["id"]), False

    # 3) Ambil harga & status menu dari DATABASE, bukan dari client.
    menu_ids = list({i.menu_id for i in items})
    menus = {
        m["id"]: m
        for m in conn.execute(
            """SELECT m.id, m.name, m.price, m.is_available
               FROM app.menus m JOIN app.categories c ON c.id = m.category_id
               WHERE m.id = ANY(%s) AND m.is_active AND c.is_active""",
            (menu_ids,),
        ).fetchall()
    }
    if len(menus) != len(menu_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ada menu yang sudah tidak tersedia di katalog. Muat ulang halaman menu.",
        )
    sold_out = sorted(m["name"] for m in menus.values() if not m["is_available"])
    if sold_out:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Menu sedang habis: " + ", ".join(sold_out),
        )

    # 4) Sesi meja: pakai yang masih open, atau buka sesi baru.
    session = conn.execute(
        "SELECT id FROM app.ordering_sessions WHERE table_id = %s AND status = 'open'",
        (table["id"],),
    ).fetchone()
    if session is None:
        session = conn.execute(
            """INSERT INTO app.ordering_sessions (session_code, session_type, table_id)
               VALUES (%s, 'table', %s) RETURNING id""",
            (generate_code("SES"), table["id"]),
        ).fetchone()
    if acc["session_id"] is None:
        conn.execute(
            "UPDATE app.customer_accesses SET session_id = %s WHERE id = %s",
            (session["id"], acc["id"]),
        )
    elif acc["session_id"] != session["id"]:
        raise INVALID_ACCESS

    # 5) Simpan pesanan + item dengan snapshot nama & harga saat ini.
    order = conn.execute(
        """INSERT INTO app.orders
               (order_code, session_id, customer_access_id, fulfillment_type,
                checkout_key, checkout_fingerprint)
           VALUES (%s, %s, %s, 'dine_in', %s, %s) RETURNING id""",
        (generate_code("ORD"), session["id"], acc["id"], checkout_key, checkout_fp),
    ).fetchone()
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO app.order_items
                   (order_id, menu_id, menu_name_snapshot, unit_price_snapshot,
                    original_quantity, quantity, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [
                (order["id"], i.menu_id, menus[i.menu_id]["name"], menus[i.menu_id]["price"],
                 i.quantity, i.quantity, i.notes)
                for i in items
            ],
        )
    return get_order(conn, order["id"]), True
