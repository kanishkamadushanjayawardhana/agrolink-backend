from datetime import datetime
import enum

from sqlalchemy import DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuctionStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    starting_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    current_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    status: Mapped[AuctionStatus] = mapped_column(
        Enum(AuctionStatus),
        default=AuctionStatus.UPCOMING,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def update_status(self):

        now = datetime.utcnow()

        if self.status == AuctionStatus.CANCELLED:
            return self.status

        if now < self.start_time:
            self.status = AuctionStatus.UPCOMING

        elif self.start_time <= now <= self.end_time:
            self.status = AuctionStatus.LIVE

        else:
            self.status = AuctionStatus.ENDED

        return self.status