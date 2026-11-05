from sqlalchemy.orm import Session

from app.domains.practice.models import Practice
from app.domains.practice.schemas import PracticeCreate


def create_practice(db: Session, *, user_id: int, data: PracticeCreate) -> Practice:
    """검증된 대본으로 연습을 생성하고, ID가 채워진 객체를 반환한다.

    user_id는 이후 HTTP 연결 시 반드시 인증된 사용자 ID를 전달해야 한다.
    이 함수 자체는 로그인이나 사용자 인증을 수행하지 않는다.

    서비스는 flush만 수행한다. 호출자가 트랜잭션의 commit을 책임지며,
    flush/commit 실패를 포함한 예외 발생 시 rollback도 수행해야 한다.
    반환 시점에는 아직 저장이 확정되지 않았다.
    """
    # 초기 제목 생성 방식: AI 호출 없이 첫 번째 유효한 줄을 사용한다.
    # 제목에서만 앞뒤 공백을 제거하고, 대본 원문은 변형하지 않는다.
    first_line = next(line.strip() for line in data.script.splitlines() if line.strip())
    title_limit = Practice.__table__.c.title.type.length
    practice = Practice(
        user_id=user_id,
        title=first_line[:title_limit],
        script=data.script,
    )
    db.add(practice)
    db.flush()
    return practice
