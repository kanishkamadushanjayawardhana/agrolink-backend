
from datetime import datetime

from sqlalchemy import String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    product_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    expected_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    location: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    harvest_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
