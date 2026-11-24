"""Schema untuk alur pelanggan: akses dari QR dan checkout."""
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CustomerAccessRequest(BaseModel):
    qr_token: str = Field(min_length=10, max_length=100)


class OrderItemIn(BaseModel):
    menu_id: UUID
    quantity: int = Field(ge=1, le=50)
    notes: str | None = Field(default=None, max_length=200)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CheckoutRequest(BaseModel):
    # Dibuat frontend SATU KALI per keranjang (crypto.randomUUID()).
    # Klik dobel / kirim ulang dengan key yang sama tidak membuat pesanan ganda.
    checkout_key: UUID
    items: list[OrderItemIn] = Field(min_length=1, max_length=30)
