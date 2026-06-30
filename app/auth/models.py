import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlanTier(str, Enum):
    free = "free"
    pro = "pro"


# Monthly analysis quotas per tier
TIER_QUOTAS = {
    PlanTier.free: 10,
    PlanTier.pro: 500,
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    plan_tier: Mapped[str] = mapped_column(String, default=PlanTier.free, nullable=False)
    monthly_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
