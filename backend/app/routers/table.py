"""Endpoint meja & QR code. Semua hanya admin (qr_token bersifat rahasia)."""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.database import DbConn
from app.core.deps import require_admin
from app.schemas.table import TableCreate, TableUpdate
from app.services import table_service

router = APIRouter(prefix="/api/tables", tags=["Tables & QR"], dependencies=[Depends(require_admin)])


@router.get("")
def get_tables(conn=DbConn):
    return {"success": True, "data": table_service.list_tables(conn)}


@router.get("/{table_id}")
def get_table_detail(table_id: UUID, conn=DbConn):
    return {"success": True, "data": table_service.get_table(conn, table_id)}


@router.post("", status_code=201)
def create_table(body: TableCreate, conn=DbConn):
    data = table_service.create_table(conn, body.table_number)
    return {"success": True, "message": "Meja berhasil ditambahkan.", "data": data}


@router.put("/{table_id}")
def update_table(table_id: UUID, body: TableUpdate, conn=DbConn):
    data = table_service.update_table(conn, table_id, body.table_number)
    return {"success": True, "message": "Meja berhasil diperbarui.", "data": data}


@router.post("/{table_id}/regenerate-qr")
def regenerate_qr(table_id: UUID, conn=DbConn):
    data = table_service.regenerate_qr(conn, table_id)
    return {"success": True, "message": "QR code baru berhasil dibuat.", "data": data}


@router.delete("/{table_id}")
def delete_table(table_id: UUID, conn=DbConn):
    table_service.delete_table(conn, table_id)
    return {"success": True, "message": "Meja berhasil dihapus."}
