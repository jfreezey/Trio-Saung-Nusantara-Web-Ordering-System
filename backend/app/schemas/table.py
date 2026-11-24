"""Schema meja restoran."""
from pydantic import BaseModel, Field


class TableCreate(BaseModel):
    table_number: str = Field(min_length=1, max_length=20)


class TableUpdate(TableCreate):
    pass
