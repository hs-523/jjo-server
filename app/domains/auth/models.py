from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)  # Google 계정 고유 식별자
    email: Mapped[str] = mapped_column(String(255))  # Google 계정 이메일
    name: Mapped[str] = mapped_column(String(50))
    profile_image_url: Mapped[str | None] = mapped_column(String(500))
    terms_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 필수 약관 동의 시각
    marketing_agreed: Mapped[bool] = mapped_column(Boolean, server_default=false())
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
