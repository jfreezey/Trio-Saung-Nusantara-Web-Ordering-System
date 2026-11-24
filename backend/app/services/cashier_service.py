"""Fitur kasir: sesi meja, koreksi item, pembayaran, struk, dan pembatalan."""
import uuid

from fastapi import HTTPException, status

from app.core.utils import fingerprint, generate_code, rupiah
from app.services.order_service import attach_items, get_session_orders

SESSION_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi meja tidak ditemukan.")


# ---------- Membaca ----------

def list_open_sessions(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT s.id, s.session_code, s.opened_at, t.id AS table_id, t.table_number,
               count(DISTINCT o.id) FILTER (WHERE o.status = 'active') AS active_orders,
               COALESCE(sum(i.unit_price_snapshot * i.quantity), 0) AS total,
               max(o.created_at) AS last_order_at
        FROM app.ordering_sessions s
        JOIN app.restaurant_tables t ON t.id = s.table_id
        LEFT JOIN app.orders o ON o.session_id = s.id
        LEFT JOIN app.order_items i ON i.order_id = o.id
        WHERE s.status = 'open'
        GROUP BY s.id, t.id
        ORDER BY last_order_at DESC NULLS LAST
        """
    ).fetchall()
    return [{**r, "total": rupiah(r["total"])} for r in rows]


def list_new_orders(conn, since) -> dict:
    """Untuk notifikasi pesanan baru (polling). Frontend menyimpan server_time
    dari respons ini dan mengirimnya lagi sebagai ?since= pada polling berikutnya."""
    server_time = conn.execute("SELECT now() AS t").fetchone()["t"]
    orders = conn.execute(
        """SELECT o.id, o.order_code, o.status, o.created_at, o.session_id, t.table_number
           FROM app.orders o
           JOIN app.ordering_sessions s ON s.id = o.session_id
           LEFT JOIN app.restaurant_tables t ON t.id = s.table_id
           WHERE o.created_at > COALESCE(%s, now() - interval '12 hours')
             AND s.status = 'open'
           ORDER BY o.created_at
           LIMIT 100""",
        (since,),
    ).fetchall()
    return {"server_time": server_time, "orders": attach_items(conn, orders)}


def _get_payment(conn, session_id) -> dict | None:
    row = conn.execute(
        """SELECT p.receipt_number, p.payment_method, p.total_amount, p.cash_received,
                  p.paid_at, u.name AS cashier_name
           FROM app.payments p JOIN app.users u ON u.id = p.paid_by
           WHERE p.session_id = %s""",
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    total = rupiah(row["total_amount"])
    cash = rupiah(row["cash_received"]) if row["cash_received"] is not None else None
    return {
        "receipt_number": row["receipt_number"],
        "payment_method": row["payment_method"],
        "total": total,
        "cash_received": cash,
        "change": (cash - total) if cash is not None else 0,
        "paid_at": row["paid_at"],
        "cashier_name": row["cashier_name"],
    }


def get_session_detail(conn, session_id) -> dict:
    session = conn.execute(
        """SELECT s.id, s.session_code, s.status, s.opened_at, s.closed_at, t.table_number
           FROM app.ordering_sessions s
           LEFT JOIN app.restaurant_tables t ON t.id = s.table_id
           WHERE s.id = %s""",
        (session_id,),
    ).fetchone()
    if session is None:
        raise SESSION_NOT_FOUND
    orders = get_session_orders(conn, session_id)
    return {
        **session,
        "orders": orders,
        "total": sum(o["total"] for o in orders),
        "payment": _get_payment(conn, session_id),
    }


def get_receipt(conn, session_id) -> dict:
    detail = get_session_detail(conn, session_id)
    if detail["payment"] is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi ini belum dibayar.")
    # Gabungkan item yang sama (menu, harga, catatan) dari semua pesanan untuk struk.
    lines: dict = {}
    for order in detail["orders"]:
        for item in order["items"]:
            if item["quantity"] == 0:
                continue
            key = (item["menu_name"], item["unit_price"], item["notes"])
            if key not in lines:
                lines[key] = {"menu_name": item["menu_name"], "unit_price": item["unit_price"],
                              "notes": item["notes"], "quantity": 0, "subtotal": 0}
            lines[key]["quantity"] += item["quantity"]
            lines[key]["subtotal"] += item["subtotal"]
    return {
        "restaurant": "Trio Saung Nusantara",
        "table_number": detail["table_number"],
        "session_code": detail["session_code"],
        "items": list(lines.values()),
        **detail["payment"],
    }


# ---------- Menulis (selalu kunci meja dulu, lalu sesi) ----------

def _lock_session(conn, session_id) -> dict:
    found = conn.execute(
        "SELECT table_id FROM app.ordering_sessions WHERE id = %s", (session_id,)
    ).fetchone()
    if found is None:
        raise SESSION_NOT_FOUND
    if found["table_id"]:
        conn.execute(
            "SELECT 1 FROM app.restaurant_tables WHERE id = %s FOR UPDATE", (found["table_id"],)
        )
    return conn.execute(
        "SELECT id, status, table_id FROM app.ordering_sessions WHERE id = %s FOR UPDATE",
        (session_id,),
    ).fetchone()


def _require_open(session: dict) -> None:
    if session["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sesi meja ini sudah ditutup (sudah dibayar atau dibatalkan).",
        )


def _close_table_access(conn, table_id) -> None:
    """Naikkan access_epoch -> semua token pelanggan lama di meja ini tidak berlaku lagi."""
    if table_id is None:
        return
    conn.execute(
        "UPDATE app.restaurant_tables SET access_epoch = access_epoch + 1 WHERE id = %s",
        (table_id,),
    )
    conn.execute(
        """UPDATE app.customer_accesses SET revoked_at = GREATEST(now(), created_at)
           WHERE table_id = %s AND revoked_at IS NULL""",
        (table_id,),
    )


def _cancel_empty_orders(conn, session_id) -> None:
    conn.execute(
        """UPDATE app.orders o SET status = 'cancelled'
           WHERE o.session_id = %s AND o.status = 'active'
             AND NOT EXISTS (SELECT 1 FROM app.order_items i
                             WHERE i.order_id = o.id AND i.quantity > 0)""",
        (session_id,),
    )


def adjust_items(conn, session_id, user: dict, reason: str, adjustments: list) -> dict:
    session = _lock_session(conn, session_id)
    _require_open(session)

    item_ids = [a.order_item_id for a in adjustments]
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(status_code=400, detail="Item yang sama dikirim lebih dari satu kali.")

    current = {
        row["id"]: row
        for row in conn.execute(
            """SELECT i.id, i.quantity, i.menu_name_snapshot
               FROM app.order_items i JOIN app.orders o ON o.id = i.order_id
               WHERE i.id = ANY(%s) AND o.session_id = %s
               FOR UPDATE OF i""",
            (item_ids, session_id),
        ).fetchall()
    }
    if len(current) != len(item_ids):
        raise HTTPException(status_code=404, detail="Ada item yang tidak ditemukan di sesi meja ini.")

    group_id = uuid.uuid4()
    for adj in adjustments:
        row = current[adj.order_item_id]
        if adj.new_quantity >= row["quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Jumlah baru untuk '{row['menu_name_snapshot']}' harus lebih kecil dari {row['quantity']}.",
            )
        conn.execute(
            """INSERT INTO app.order_adjustments
                   (order_item_id, previous_quantity, new_quantity, reason, changed_by, change_group_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (adj.order_item_id, row["quantity"], adj.new_quantity, reason.strip(), user["id"], group_id),
        )
        conn.execute(
            "UPDATE app.order_items SET quantity = %s WHERE id = %s",
            (adj.new_quantity, adj.order_item_id),
        )
    _cancel_empty_orders(conn, session_id)
    return get_session_detail(conn, session_id)


def pay(conn, session_id, user: dict, payment_key, payment_method: str, cash_received) -> tuple[dict, bool]:
    payment_fp = fingerprint(
        {"session_id": str(session_id), "method": payment_method, "cash_received": cash_received}
    )
    session = _lock_session(conn, session_id)

    # Idempotensi: payment_key yang sama = permintaan ulang, kembalikan struk yang sama.
    existing = conn.execute(
        "SELECT session_id, payment_fingerprint FROM app.payments WHERE payment_key = %s",
        (payment_key,),
    ).fetchone()
    if existing:
        if existing["payment_fingerprint"] != payment_fp:
            raise HTTPException(status_code=409, detail="payment_key sudah dipakai untuk pembayaran lain.")
        return get_receipt(conn, existing["session_id"]), False

    _require_open(session)

    total = rupiah(
        conn.execute(
            """SELECT COALESCE(sum(i.unit_price_snapshot * i.quantity), 0) AS total
               FROM app.order_items i JOIN app.orders o ON o.id = i.order_id
               WHERE o.session_id = %s""",
            (session_id,),
        ).fetchone()["total"]
    )
    if total <= 0:
        raise HTTPException(
            status_code=409,
            detail="Tidak ada item yang perlu dibayar. Gunakan fitur batalkan sesi.",
        )
    if payment_method == "cash" and cash_received < total:
        raise HTTPException(status_code=400, detail=f"Uang diterima kurang dari total (Rp{total:,}).".replace(",", "."))

    conn.execute(
        """INSERT INTO app.payments
               (receipt_number, session_id, subtotal_amount, total_amount, payment_method,
                cash_received, paid_by, payment_key, payment_fingerprint)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (generate_code("RCP"), session_id, total, total, payment_method,
         cash_received, user["id"], payment_key, payment_fp),
    )
    conn.execute(
        """UPDATE app.ordering_sessions
           SET status = 'paid', closed_at = clock_timestamp(), closed_by = %s
           WHERE id = %s""",
        (user["id"], session_id),
    )
    _close_table_access(conn, session["table_id"])
    return get_receipt(conn, session_id), True


def cancel_session(conn, session_id, user: dict, reason: str) -> dict:
    """Batalkan seluruh tagihan meja (mis. pelanggan pergi). Semua item dijadikan 0
    dengan catatan alasan, supaya jejak auditnya tetap ada."""
    session = _lock_session(conn, session_id)
    _require_open(session)

    items = conn.execute(
        """SELECT i.id, i.quantity FROM app.order_items i
           JOIN app.orders o ON o.id = i.order_id
           WHERE o.session_id = %s AND i.quantity > 0
           FOR UPDATE OF i""",
        (session_id,),
    ).fetchall()
    group_id = uuid.uuid4()
    for item in items:
        conn.execute(
            """INSERT INTO app.order_adjustments
                   (order_item_id, previous_quantity, new_quantity, reason, changed_by, change_group_id)
               VALUES (%s, %s, 0, %s, %s, %s)""",
            (item["id"], item["quantity"], reason.strip(), user["id"], group_id),
        )
        conn.execute("UPDATE app.order_items SET quantity = 0 WHERE id = %s", (item["id"],))

    _cancel_empty_orders(conn, session_id)
    conn.execute(
        """UPDATE app.ordering_sessions
           SET status = 'cancelled', closed_at = clock_timestamp(), closed_by = %s
           WHERE id = %s""",
        (user["id"], session_id),
    )
    _close_table_access(conn, session["table_id"])
    return get_session_detail(conn, session_id)
