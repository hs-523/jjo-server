from sqlalchemy.orm import Session

from app.domains.practice.models import Practice
from app.domains.practice.schemas import PracticeCreate
from app.domains.practice.title import generate_title


def create_practice(db: Session, *, user_id: int, data: PracticeCreate) -> Practice:
    """검증된 대본으로 연습을 생성하고, ID가 채워진 객체를 반환한다.

    user_id는 이후 HTTP 연결 시 반드시 인증된 사용자 ID를 전달해야 한다.
    이 함수 자체는 로그인이나 사용자 인증을 수행하지 않는다.

    서비스는 flush만 수행한다. 호출자가 트랜잭션의 commit을 책임지며,
    flush/commit 실패를 포함한 예외 발생 시 rollback도 수행해야 한다.
    반환 시점에는 아직 저장이 확정되지 않았다.
    """
    practice = Practice(
        user_id=user_id,
        title=generate_title(data.script),
        script=data.script,
    )
    db.add(practice)
    db.flush()
    return practice
