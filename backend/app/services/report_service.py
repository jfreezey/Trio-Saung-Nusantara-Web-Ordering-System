"""Laporan penjualan untuk admin. Tanggal dihitung dalam zona waktu WIB."""
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException

from app.core.utils import WIB, rupiah


def _range(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to tidak boleh sebelum date_from.")
    if (date_to - date_from).days > 366:
        raise HTTPException(status_code=400, detail="Rentang laporan maksimal 1 tahun.")
    start = datetime.combine(date_from, time.min, tzinfo=WIB)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=WIB)
    return start, end


def summary(conn, date_from: date, date_to: date) -> dict:
    start, end = _range(date_from, date_to)
    params = {"start": start, "end": end}

    totals = conn.execute(
        """SELECT count(*) AS transactions, COALESCE(sum(total_amount), 0) AS revenue
           FROM app.payments WHERE paid_at >= %(start)s AND paid_at < %(end)s""",
        params,
    ).fetchone()

    by_method = conn.execute(
        """SELECT payment_method, count(*) AS transactions, sum(total_amount) AS revenue
           FROM app.payments WHERE paid_at >= %(start)s AND paid_at < %(end)s
           GROUP BY payment_method ORDER BY revenue DESC""",
        params,
    ).fetchall()

    daily = conn.execute(
        """SELECT (paid_at AT TIME ZONE 'Asia/Jakarta')::date AS day,
                  count(*) AS transactions, sum(total_amount) AS revenue
           FROM app.payments WHERE paid_at >= %(start)s AND paid_at < %(end)s
           GROUP BY day ORDER BY day""",
        params,
    ).fetchall()

    top_menus = conn.execute(
        """SELECT i.menu_id, i.menu_name_snapshot AS menu_name,
                  sum(i.quantity) AS quantity_sold,
                  sum(i.quantity * i.unit_price_snapshot) AS revenue
           FROM app.payments p
           JOIN app.orders o ON o.session_id = p.session_id
           JOIN app.order_items i ON i.order_id = o.id
           WHERE p.paid_at >= %(start)s AND p.paid_at < %(end)s AND i.quantity > 0
           GROUP BY i.menu_id, i.menu_name_snapshot
           ORDER BY quantity_sold DESC, revenue DESC
           LIMIT 10""",
        params,
    ).fetchall()

    transactions = totals["transactions"]
    revenue = rupiah(totals["revenue"])
    return {
        "date_from": date_from,
        "date_to": date_to,
        "transactions": transactions,
        "revenue": revenue,
        "average_per_transaction": revenue // transactions if transactions else 0,
        "by_payment_method": [{**r, "revenue": rupiah(r["revenue"])} for r in by_method],
        "daily": [{**r, "revenue": rupiah(r["revenue"])} for r in daily],
        "top_menus": [
            {**r, "quantity_sold": int(r["quantity_sold"]), "revenue": rupiah(r["revenue"])}
            for r in top_menus
        ],
    }


def transactions(conn, date_from: date, date_to: date, limit: int, offset: int) -> dict:
    start, end = _range(date_from, date_to)
    rows = conn.execute(
        """SELECT p.session_id, p.receipt_number, p.paid_at, p.payment_method, p.total_amount,
                  t.table_number, u.name AS cashier_name,
                  count(*) OVER () AS total_count
           FROM app.payments p
           JOIN app.ordering_sessions s ON s.id = p.session_id
           LEFT JOIN app.restaurant_tables t ON t.id = s.table_id
           JOIN app.users u ON u.id = p.paid_by
           WHERE p.paid_at >= %s AND p.paid_at < %s
           ORDER BY p.paid_at DESC
           LIMIT %s OFFSET %s""",
        (start, end, limit, offset),
    ).fetchall()
    total_count = rows[0]["total_count"] if rows else 0
    items = []
    for r in rows:
        r.pop("total_count")
        items.append({**r, "total_amount": rupiah(r["total_amount"])})
    return {"total_count": total_count, "limit": limit, "offset": offset, "items": items}
