"""Schema menu. Mengikuti tabel app.menus."""
from uuid import UUID

from pydantic import BaseModel, Field


class MenuCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: int = Field(ge=0, le=100_000_000)  # rupiah
    category_id: UUID
    is_available: bool = True


class MenuUpdate(MenuCreate):
    pass


class MenuAvailabilityUpdate(BaseModel):
    is_available: bool
