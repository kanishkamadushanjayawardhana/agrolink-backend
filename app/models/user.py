
from datetime import datetime

from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

import enum


class UserRole(str, enum.Enum):
    FARMER = "farmer"
    BUYER = "buyer"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.FARMER,
        nullable=False
    )

    # Profile fields
    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    farm_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    company_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    profile_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
