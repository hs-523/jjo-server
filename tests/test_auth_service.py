"""Persistence tests; no credentials are accepted or externally verified here.

Set AUTH_TEST_DATABASE_URL to a disposable PostgreSQL database to run the same
tests there. Each test uses a unique schema and rolls back all DDL and data.
SQLite uses INTEGER for the existing BIGINT primary key only in test DDL, since
SQLite requires that exact type for generated IDs. Production metadata is intact.
"""

import os
from uuid import uuid4

import pytest
from sqlalchemy import Integer, MetaData, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema

from app.domains.auth.models import User
from app.domains.auth.service import GoogleIdentity, get_or_create_google_user, get_user_by_id


@pytest.fixture(params=["sqlite", "postgresql"])
def db(request):
    if request.param == "postgresql":
        url = os.environ.get("AUTH_TEST_DATABASE_URL")
        if not url:
            pytest.skip("AUTH_TEST_DATABASE_URL is not configured")
        engine = create_engine(url)
        if engine.dialect.name != "postgresql":
            engine.dispose()
            pytest.fail("AUTH_TEST_DATABASE_URL must point to PostgreSQL")
    else:
        engine = create_engine("sqlite://")

        @event.listens_for(engine, "connect")
        def disable_legacy_transaction_mode(connection, record):
            connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def explicit_begin(connection):
            connection.exec_driver_sql("BEGIN")

    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                if engine.dialect.name == "postgresql":
                    schema = "auth_test_" + uuid4().hex
                    connection.execute(CreateSchema(schema))
                    connection = connection.execution_options(schema_translate_map={None: schema})
                table = User.__table__.to_metadata(MetaData())
                if engine.dialect.name == "sqlite":
                    table.c.id.type = Integer()
                table.create(connection)
                with Session(bind=connection, expire_on_commit=False) as session:
                    yield session
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def identity():
    return GoogleIdentity(
        sub="test-google-subject", email="person@example.test", name="테스트 사용자",
        profile_image_url="https://example.test/avatar.png",
    )


def test_first_login_creates_user_with_existing_model_defaults(db, identity):
    user = get_or_create_google_user(db, identity)

    assert user.id is not None
    assert (user.google_sub, user.email, user.name, user.profile_image_url) == (
        identity.sub, identity.email, identity.name, identity.profile_image_url,
    )
    assert user.terms_agreed_at is None
    assert user.marketing_agreed is False
    assert user.onboarding_completed is False
    assert user.created_at is not None
    assert get_user_by_id(db, user.id) is user


def test_repeated_login_reuses_subject_without_overwriting_profile(db, identity):
    first = get_or_create_google_user(db, identity)
    changed = GoogleIdentity(sub=identity.sub, email="changed@example.test", name="변경")

    assert get_or_create_google_user(db, changed) is first
    assert first.email == identity.email
    assert first.name == identity.name
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_same_email_does_not_merge_different_google_subjects(db, identity):
    first = get_or_create_google_user(db, identity)
    second = get_or_create_google_user(
        db, GoogleIdentity(sub="another-subject", email=identity.email, name="다른 계정")
    )

    assert first.id != second.id
    assert second.profile_image_url is None
    assert db.scalar(select(func.count()).select_from(User)) == 2


def test_unknown_user_returns_none(db):
    assert get_user_by_id(db, 12345) is None


def test_caller_can_rollback_user_creation(db, identity):
    with db.begin_nested() as transaction:
        get_or_create_google_user(db, identity)
        transaction.rollback()

    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_unrelated_integrity_error_is_not_hidden_and_session_stays_usable(db):
    # NULL violates the existing schema, independently of provider validation.
    invalid = GoogleIdentity(sub="invalid", email=None, name="테스트")
    with pytest.raises(IntegrityError):
        get_or_create_google_user(db, invalid)

    valid = get_or_create_google_user(
        db, GoogleIdentity(sub="valid", email="valid@example.test", name="정상")
    )
    assert get_user_by_id(db, valid.id) is valid


def test_duplicate_subject_race_recovers_winner(db, identity, monkeypatch):
    winner = get_or_create_google_user(db, identity)
    original_scalar = db.scalar
    first_lookup = True

    def miss_initial_lookup(*args, **kwargs):
        nonlocal first_lookup
        if first_lookup:
            first_lookup = False
            return None
        return original_scalar(*args, **kwargs)

    # Deterministically simulate a stale initial read. The duplicate INSERT and
    # savepoint recovery use the real database constraint, not a mocked error.
    monkeypatch.setattr(db, "scalar", miss_initial_lookup)
    assert get_or_create_google_user(db, identity) is winner
    assert original_scalar(select(func.count()).select_from(User)) == 1
