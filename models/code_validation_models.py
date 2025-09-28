from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Index
from datetime import datetime
from typing import Optional

from models.users_models import Base


class PhoneEmailVerificationCode(Base):
    __tablename__ = "phone_email_verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_verification_lookup", "email", "phone_number", "code"),
    )


