"""외부 DB에 접속하지 않고 SQLite 메모리 DB로 생성 흐름을 검증한다."""

import pytest
from pydantic import ValidationError
from sqlalchemy import Integer, MetaData, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.auth.models import User
from app.domains.practice.models import Practice
from app.domains.practice.schemas import PracticeCreate
from app.domains.practice.service import create_practice


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    # SQLite의 자동 ID에는 INTEGER가 필요하다. 테스트 전용 복사본의 DDL만
    # 맞추며, 실제 모델·마이그레이션·공용 메타데이터는 변경하지 않는다.
    metadata = MetaData()
    for model in (User, Practice):
        table = model.__table__.to_metadata(metadata)
        table.c.id.type = Integer()
    metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add(User(id=1, google_sub="test-user", email="test@example.com", name="테스트"))
            session.commit()
            yield session
    finally:
        engine.dispose()


@pytest.mark.parametrize("script", ["안녕하세요. 발표를 시작합니다.", "가", "가" * 1500])
def test_create_and_persist_valid_script(db, script):
    practice = create_practice(db, user_id=1, data=PracticeCreate(script=script))
    assert practice.id is not None
    practice_id = practice.id
    db.commit()
    db.expunge_all()

    saved = db.get(Practice, practice_id)
    assert saved.user_id == 1
    assert saved.script == script
    assert saved.title == script[:Practice.__table__.c.title.type.length]


@pytest.mark.parametrize("script", ["", " ", "\t", "\n", " \t\r\n  ", "가" * 1501, "가" * 1500 + " "])
def test_reject_invalid_script(script):
    with pytest.raises(ValidationError):
        PracticeCreate(script=script)


def test_preserve_original_and_use_first_nonblank_line_for_title(db):
    script = " \t\r\n\n  첫 번째 줄, 안녕하세요!  \r\n\t두 번째 줄?  \n"
    practice = create_practice(db, user_id=1, data=PracticeCreate(script=script))
    practice_id = practice.id
    db.commit()
    db.expunge_all()

    saved = db.get(Practice, practice_id)
    assert saved.script == script
    assert saved.title == "첫 번째 줄, 안녕하세요!"


def test_title_does_not_exceed_column_length(db):
    title_limit = Practice.__table__.c.title.type.length
    script = "\n\t" + "긴" * (title_limit + 20) + "\n다음 줄"
    practice = create_practice(db, user_id=1, data=PracticeCreate(script=script))
    practice_id = practice.id
    db.commit()
    db.expunge_all()

    saved = db.get(Practice, practice_id)
    assert saved.title == "긴" * title_limit
    assert len(saved.title) <= title_limit
    assert saved.script == script


def test_caller_can_rollback_creation(db):
    practice = create_practice(db, user_id=1, data=PracticeCreate(script="저장 취소"))
    practice_id = practice.id
    db.rollback()

    assert db.get(Practice, practice_id) is None


def test_caller_rolls_back_after_flush_failure(db):
    with pytest.raises(IntegrityError):
        create_practice(db, user_id=999, data=PracticeCreate(script="없는 사용자"))
    db.rollback()

    # 호출자의 rollback 이후 같은 세션에서 정상 저장할 수 있다.
    practice = create_practice(db, user_id=1, data=PracticeCreate(script="정상 사용자"))
    db.commit()
    assert db.get(Practice, practice.id).user_id == 1
