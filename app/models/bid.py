from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    auction_id: Mapped[int] = mapped_column(
        ForeignKey("auctions.id"),
        nullable=False,
        index=True
    )

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )