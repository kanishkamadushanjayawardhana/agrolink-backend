from datetime import datetime

from pydantic import BaseModel, Field


class BidCreate(BaseModel):
    amount: float = Field(gt=0)


class BidResponse(BaseModel):
    id: int
    auction_id: int
    buyer_id: int
    amount: float
    created_at: datetime

    model_config = {
        "from_attributes": True
    }