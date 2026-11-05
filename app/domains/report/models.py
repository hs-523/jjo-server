import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recordings.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(
            ReportStatus,
            native_enum=False,  # DB 타입은 VARCHAR(20) 유지
            length=20,
            name="ck_reports_status",
            create_constraint=True,  # 허용값 밖은 CHECK 제약으로 DB가 차단
            values_callable=lambda e: [m.value for m in e],
        )
    )
    analysis_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 음성 분석 결과
    feedback: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 총평 및 AI 피드백
    schema_version: Mapped[str | None] = mapped_column(String(10))  # 분석 결과 JSON 버전
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
