"""Schema untuk fitur kasir."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ItemAdjustment(BaseModel):
    order_item_id: UUID
    new_quantity: int = Field(ge=0, le=50)


class AdjustItemsRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=200)
    items: list[ItemAdjustment] = Field(min_length=1, max_length=50)


class PaymentRequest(BaseModel):
    # Dibuat frontend SATU KALI per klik "Bayar" (crypto.randomUUID()) -> anti bayar dobel.
    payment_key: UUID
    payment_method: Literal["cash", "qris", "debit_card", "credit_card"]
    cash_received: int | None = Field(default=None, ge=0, le=1_000_000_000)

    @model_validator(mode="after")
    def check_cash(self):
        if self.payment_method == "cash" and self.cash_received is None:
            raise ValueError("cash_received wajib diisi untuk pembayaran tunai.")
        if self.payment_method != "cash" and self.cash_received is not None:
            raise ValueError("cash_received hanya diisi untuk pembayaran tunai.")
        return self


class CancelSessionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=200)
