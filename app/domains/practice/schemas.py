from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PracticeCreate(BaseModel):
    """연습 생성 입력. 사용자 ID는 요청 본문 대신 인증 정보에서 받는다."""

    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")

    script: str = Field(min_length=1, max_length=1500)

    @field_validator("script")
    @classmethod
    def validate_script(cls, script: str) -> str:
        if not script.strip():
            raise ValueError("대본에는 공백이 아닌 글자가 최소 1자 있어야 합니다.")
        # strip()은 검사에만 사용한다. 분석의 글자 위치 기준인 원문을 반환한다.
        return script


class PracticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    script: str
    created_at: datetime
    updated_at: datetime
