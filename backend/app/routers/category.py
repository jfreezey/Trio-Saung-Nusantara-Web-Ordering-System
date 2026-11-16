from fastapi import APIRouter, Depends, HTTPException
from app.schemas.category import CategoryCreate, CategoryUpdate

router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"]
)

#dummy data sementara
categories = [
    {
    "id": 1,
    "name": "Paket",
    "description": "Paket nasi dan lauk hidangan nusantara"
    },
    {
    "id": 2,
    "name": "Nasi",
    "description": "Pilihan nasi"
    }, 
    {
    "id": 3,
    "name": "Lauk",
    "description": "Berbagai pilihan lauk khas nusantara"
    }
]

@router.get("")
def get_categories():
    return {
        "success": True,
        "data": categories
    }
    
@router.get("/{category_id}")
def get_category_detail(category_id: int):
    for category in categories:
        if category["id"] == category_id:
            return {
                "success": True,
                "data": category
            }
    
    raise HTTPException(
        status_code=404,
        detail="Category not found"
    )
    
@router.post("")
def create_category(category: CategoryCreate):
    new_category = {
        "id": len(categories) + 1,
        "name": category.name,
        "description": category.description
    }
    categories.append(new_category)
    return {
        "success": True,
        "message": "Category created successfully",
        "data": new_category
    }
    
@router.put("/{category_id}")
def update_category(category_id: int, category: CategoryUpdate):
    for existing_category in categories:
        if existing_category["id"] == category_id:
            existing_category["name"] = category.name
            existing_category["description"] = category.description
            return {
                "success": True,
                "message": "Category updated successfully",
                "data": existing_category
            }
    
    raise HTTPException(
        status_code=404,
        detail="Category not found"
    )   
    
@router.delete("/{category_id}")
def delete_category(category_id: int):
    global categories
    categories = [category for category in categories if category["id"] != category_id]
    return {
        "success": True,
        "message": "Category deleted successfully"
    }