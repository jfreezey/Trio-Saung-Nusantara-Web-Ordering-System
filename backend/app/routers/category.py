"""Endpoint kategori. GET publik, sisanya hanya admin."""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.database import DbConn
from app.core.deps import require_admin
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("")
def get_categories(conn=DbConn):
    return {"success": True, "data": category_service.list_categories(conn)}


@router.get("/{category_id}")
def get_category_detail(category_id: UUID, conn=DbConn):
    return {"success": True, "data": category_service.get_category(conn, category_id)}


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def create_category(body: CategoryCreate, conn=DbConn):
    data = category_service.create_category(conn, body.name, body.sort_order)
    return {"success": True, "message": "Kategori berhasil ditambahkan.", "data": data}


@router.put("/{category_id}", dependencies=[Depends(require_admin)])
def update_category(category_id: UUID, body: CategoryUpdate, conn=DbConn):
    data = category_service.update_category(conn, category_id, body.name, body.sort_order)
    return {"success": True, "message": "Kategori berhasil diperbarui.", "data": data}


@router.delete("/{category_id}", dependencies=[Depends(require_admin)])
def delete_category(category_id: UUID, conn=DbConn):
    category_service.delete_category(conn, category_id)
    return {"success": True, "message": "Kategori berhasil dihapus."}
