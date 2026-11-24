"""Schema kategori menu. Mengikuti tabel app.categories."""
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    sort_order: int = Field(default=0, ge=0, le=10_000)


class CategoryUpdate(CategoryCreate):
    pass
