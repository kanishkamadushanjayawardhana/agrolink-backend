from datetime import datetime
import enum

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Enum,
    String,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# =========================================================
# ESCROW STATUS
# =========================================================

class EscrowStatus(str, enum.Enum):
    PENDING = "pending"
    FUNDED = "funded"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


# =========================================================
# MILESTONE STATUS
# =========================================================

class MilestoneStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    RELEASED = "released"


# =========================================================
# ESCROW MODEL
# =========================================================

class Escrow(Base):
    __tablename__ = "escrows"

    # -----------------------------------------------------
    # ESCROW ID
    # -----------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    # -----------------------------------------------------
    # AUCTION ID
    # -----------------------------------------------------

    auction_id: Mapped[int] = mapped_column(
        ForeignKey("auctions.id"),
        nullable=False,
        unique=True,
        index=True
    )

    # -----------------------------------------------------
    # FARMER ID
    # -----------------------------------------------------

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # -----------------------------------------------------
    # BUYER ID
    # -----------------------------------------------------

    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # -----------------------------------------------------
    # TOTAL ESCROW AMOUNT
    # -----------------------------------------------------

    total_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # -----------------------------------------------------
    # RELEASED AMOUNT
    # -----------------------------------------------------

    released_amount: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    # -----------------------------------------------------
    # REMAINING AMOUNT
    # -----------------------------------------------------

    remaining_amount: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    # -----------------------------------------------------
    # ESCROW STATUS
    # -----------------------------------------------------

    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus),
        default=EscrowStatus.PENDING,
        nullable=False
    )

    # -----------------------------------------------------
    # CREATED AT
    # -----------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------
    # UPDATED AT
    # -----------------------------------------------------

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------
    # ESCROW MILESTONES RELATIONSHIP
    # -----------------------------------------------------

    milestones: Mapped[list["EscrowMilestone"]] = relationship(
        "EscrowMilestone",
        back_populates="escrow",
        cascade="all, delete-orphan"
    )


# =========================================================
# ESCROW MILESTONE MODEL
# =========================================================

class EscrowMilestone(Base):
    __tablename__ = "escrow_milestones"

    # -----------------------------------------------------
    # MILESTONE ID
    # -----------------------------------------------------

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    # -----------------------------------------------------
    # ESCROW ID
    # -----------------------------------------------------

    escrow_id: Mapped[int] = mapped_column(
        ForeignKey("escrows.id"),
        nullable=False,
        index=True
    )

    # -----------------------------------------------------
    # MILESTONE NAME
    # -----------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # -----------------------------------------------------
    # MILESTONE AMOUNT
    # -----------------------------------------------------

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # -----------------------------------------------------
    # MILESTONE STATUS
    # -----------------------------------------------------

    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus),
        default=MilestoneStatus.PENDING,
        nullable=False
    )

    # -----------------------------------------------------
    # COMPLETED
    # -----------------------------------------------------

    completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # -----------------------------------------------------
    # CREATED AT
    # -----------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------
    # UPDATED AT
    # -----------------------------------------------------

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # -----------------------------------------------------
    # ESCROW RELATIONSHIP
    # -----------------------------------------------------

    escrow: Mapped["Escrow"] = relationship(
        "Escrow",
        back_populates="milestones"
    )