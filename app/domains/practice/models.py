from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Practice(Base):
    __tablename__ = "practices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100))  # 자동 생성
    script: Mapped[str] = mapped_column(Text)  # 현재 대본, 최대 1,500자
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Recording(Base):
    __tablename__ = "recordings"
    __table_args__ = (UniqueConstraint("practice_id", "attempt_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    practice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("practices.id", ondelete="CASCADE"), index=True
    )
    attempt_no: Mapped[int] = mapped_column(Integer)  # 1부터
    script_snapshot: Mapped[str] = mapped_column(Text)  # 녹음 시점의 대본
    audio_path: Mapped[str] = mapped_column(String(500))
    duration_ms: Mapped[int] = mapped_column(Integer)  # 밀리초
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
