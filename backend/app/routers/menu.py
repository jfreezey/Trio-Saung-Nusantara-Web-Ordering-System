"""Endpoint menu. GET publik, ubah ketersediaan untuk admin & kasir, sisanya admin."""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.database import DbConn
from app.core.deps import require_admin, require_staff
from app.schemas.menu import MenuAvailabilityUpdate, MenuCreate, MenuUpdate
from app.services import menu_service

router = APIRouter(prefix="/api/menus", tags=["Menus"])


@router.get("")
def get_menus(
    category_id: UUID | None = None,
    search: str | None = Query(default=None, max_length=60),
    available_only: bool = False,
    conn=DbConn,
):
    data = menu_service.list_menus(conn, category_id, search, available_only)
    return {"success": True, "data": data}


@router.get("/{menu_id}")
def get_menu_detail(menu_id: UUID, conn=DbConn):
    return {"success": True, "data": menu_service.get_menu(conn, menu_id)}


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def create_menu(body: MenuCreate, conn=DbConn):
    data = menu_service.create_menu(conn, body.model_dump())
    return {"success": True, "message": "Menu berhasil ditambahkan.", "data": data}


@router.put("/{menu_id}", dependencies=[Depends(require_admin)])
def update_menu(menu_id: UUID, body: MenuUpdate, conn=DbConn):
    data = menu_service.update_menu(conn, menu_id, body.model_dump())
    return {"success": True, "message": "Menu berhasil diperbarui.", "data": data}


@router.delete("/{menu_id}", dependencies=[Depends(require_admin)])
def delete_menu(menu_id: UUID, conn=DbConn):
    menu_service.delete_menu(conn, menu_id)
    return {"success": True, "message": "Menu berhasil dihapus."}


@router.patch("/{menu_id}/availability", dependencies=[Depends(require_staff)])
def update_menu_availability(menu_id: UUID, body: MenuAvailabilityUpdate, conn=DbConn):
    data = menu_service.set_availability(conn, menu_id, body.is_available)
    return {"success": True, "message": "Ketersediaan menu diperbarui.", "data": data}


@router.post("/{menu_id}/image", dependencies=[Depends(require_admin)])
def upload_menu_image(menu_id: UUID, image: UploadFile = File(...), conn=DbConn):
    data = menu_service.save_menu_image(conn, menu_id, image)
    return {"success": True, "message": "Gambar menu berhasil diunggah.", "data": data}
