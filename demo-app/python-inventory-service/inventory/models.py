"""Data models for the inventory service."""

from pydantic import BaseModel, Field


class Product(BaseModel):
    """A product in the inventory."""

    id: int
    name: str
    quantity: int = Field(ge=0)
    price: float = Field(gt=0)
    category: str


class StockAdjustment(BaseModel):
    """Request body for adjusting stock quantity."""

    product_id: int
    delta: int  # positive = restock, negative = sell
