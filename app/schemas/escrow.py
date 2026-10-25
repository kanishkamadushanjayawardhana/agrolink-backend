from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EscrowMilestoneCreate(BaseModel):
    name: str
    description: str | None = None
    amount: float


class EscrowMilestoneResponse(BaseModel):
    id: int
    escrow_id: int
    name: str
    description: str | None
    amount: float
    status: str
    completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EscrowCreate(BaseModel):
    auction_id: int
    farmer_id: int
    buyer_id: int
    total_amount: float
    milestones: list[EscrowMilestoneCreate]


class EscrowResponse(BaseModel):
    id: int
    auction_id: int
    farmer_id: int
    buyer_id: int
    total_amount: float
    released_amount: float
    remaining_amount: float
    status: str
    created_at: datetime
    updated_at: datetime
    milestones: list[EscrowMilestoneResponse] = []

    model_config = ConfigDict(from_attributes=True)