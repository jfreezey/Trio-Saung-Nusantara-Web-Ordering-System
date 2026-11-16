
from fastapi import APIRouter, HTTPException
from app.schemas.menu import (
    MenuCreate,
    MenuUpdate,
    MenuAvailabilityUpdate
)

router = APIRouter(
    prefix="/api/menus",
    tags=["Menus"]
)


# Dummy data sementara
menus = [
    {
        "id": 1,
        "name": "Nasi Liwet",
        "description": "Nasi liwet khas Sunda",
        "price": 15000,
        "category_id": 1,
        "is_available": True
    },
    {
        "id": 2,
        "name": "Nasi Putih",
        "description": "Nasi putih biasa",
        "price": 5000,
        "category_id": 1,
        "is_available": True
    }
]


# get all menu
@router.get("")
def get_menus():
    return {
        "success": True,
        "data": menus
    }


# get menu by id
@router.get("/{menu_id}")
def get_menu_detail(menu_id: int):
    for menu in menus:
        if menu["id"] == menu_id:
            return {
                "success": True,
                "data": menu
            }

    raise HTTPException(
        status_code=404,
        detail="Menu not found"
    )


# post add menu
@router.post("", status_code=201)
def create_menu(menu_data: MenuCreate):
    new_id = max(
        [menu["id"] for menu in menus],
        default=0
    ) + 1

    new_menu = {
        "id": new_id,
        **menu_data.model_dump()
    }

    menus.append(new_menu)

    return {
        "success": True,
        "message": "New menu created",
        "data": new_menu
    }


# put update menu
@router.put("/{menu_id}")
def update_menu(menu_id: int, menu_data: MenuUpdate):
    for index, menu in enumerate(menus):
        if menu["id"] == menu_id:
            updated_menu = {
                "id": menu_id,
                **menu_data.model_dump()
            }

            menus[index] = updated_menu

            return {
                "success": True,
                "message": "Menu update successed",
                "data": updated_menu
            }

    raise HTTPException(
        status_code=404,
        detail="Menu not found, please check the menu ID"
    )


# delete remove menu
@router.delete("/{menu_id}")
def delete_menu(menu_id: int):
    for menu in menus:
        if menu["id"] == menu_id:
            menus.remove(menu)

            return {
                "success": True,
                "message": "Menu delete successed",
            }

    raise HTTPException(
        status_code=404,
        detail="Menu not found, please check the menu ID"
    )


# patch update menu availability
@router.patch("/{menu_id}/availability")
def update_menu_availability(
    menu_id: int,
    availability_data: MenuAvailabilityUpdate
):
    for menu in menus:
        if menu["id"] == menu_id:
            menu["is_available"] = availability_data.is_available

            return {
                "success": True,
                "message": "Menu availability update successed",
                "data": menu
            }

    raise HTTPException(
        status_code=404,
        detail="Menu not found, please check the menu ID"
    )
