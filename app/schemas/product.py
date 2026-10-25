
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    product_name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=100)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=30)
    expected_price: float = Field(gt=0)
    location: str = Field(min_length=2, max_length=150)
    harvest_date: datetime
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)


class ProductUpdate(BaseModel):
    product_name: str | None = Field(
        default=None, min_length=2, max_length=100
    )
    category: str | None = Field(
        default=None, min_length=2, max_length=100
    )
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    expected_price: float | None = Field(default=None, gt=0)
    location: str | None = Field(
        default=None, min_length=2, max_length=150
    )
    harvest_date: datetime | None = None
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)


class ProductResponse(BaseModel):
    id: int
    farmer_id: int
    product_name: str
    category: str
    quantity: float
    unit: str
    expected_price: float
    location: str
    harvest_date: datetime
    description: str | None
    image_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
