"""HTTP creation with real credentials and independent persistence checks."""

import pytest
from sqlalchemy import Integer, MetaData, func, select, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from tests.test_auth_api import client, pending, signup
from app.core.security import issue
from app.domains.auth.models import User
from app.domains.practice.models import Practice
from app.domains.practice import router as routes


@pytest.fixture
def api(client):
    c, engine = client
    metadata = MetaData()
    User.__table__.to_metadata(metadata)
    table = Practice.__table__.to_metadata(metadata)
    if engine.dialect.name == 'sqlite':
        table.c.id.type = Integer()
    table.create(engine)
    account = signup(c, pending(c)).json()
    headers = {'Authorization': 'Bearer ' + account['access_token']}
    return c, engine, headers, account['user']['id']


def count(engine):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(Practice))


@pytest.mark.parametrize('script', ['가', '가' * 1500, ' \r\n  발표 시작  \r\n다음 줄\t '])
def test_create_persists_for_authenticated_owner(api, script):
    c, engine, headers, uid = api
    response = c.post('/practices', headers=headers, json={'script': script})
    assert response.status_code == 201, response.text
    body = response.json()
    title = next(line.strip() for line in script.splitlines() if line.strip())[:100]
    assert body['script'] == script
    assert body['title'] == title
    assert body['created_at'] and body['updated_at']
    with Session(engine) as db:
        saved = db.get(Practice, body['id'])
        assert saved.user_id == uid
        assert saved.script == script
        assert saved.title == title
        # Onboarding is deliberately not an authorization gate.
        assert db.get(User, uid).onboarding_completed is False


def test_client_cannot_select_owner(api):
    c, engine, headers, uid = api
    with Session(engine) as db:
        other = User(google_sub='other', email='other@example.test', name='Other')
        db.add(other)
        db.commit()
        other_id = other.id
    response = c.post('/practices', headers=headers,
                      json={'script': '대본', 'user_id': other_id})
    assert response.status_code == 422
    assert response.json()['error']['fields'] == ['user_id']
    assert count(engine) == 0
    assert c.post('/practices', headers=headers, json={'script': '대본'}).status_code == 201
    with Session(engine) as db:
        assert db.scalar(select(Practice)).user_id == uid


@pytest.mark.parametrize('body', [{}, {'script': ''}, {'script': ' \t\r\n'},
                                  {'script': '가' * 1501}, {'script': None},
                                  {'script': 123}, {'script': ['대본']}])
def test_invalid_script_does_not_write(api, body):
    c, engine, headers, _ = api
    response = c.post('/practices', headers=headers, json=body)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert response.json()['error']['fields'] == ['script']
    assert count(engine) == 0


def test_reject_credentials(api):
    c, engine, _, _ = api
    with Session(engine) as db:
        user = User(google_sub='no-consent', email='pending@example.test', name='Pending')
        db.add(user)
        db.commit()
        incomplete_id = user.id
    signup_token = issue('signup', 'new-user', email='new@example.test', name='New')
    for token in [None, 'invalid', signup_token, issue('access', '999'),
                  issue('access', 'not-an-id'), issue('access', incomplete_id)]:
        headers = {} if token is None else {'Authorization': 'Bearer ' + token}
        response = c.post('/practices', headers=headers, json={'script': '대본'})
        assert response.status_code == 401
        assert response.json()['error']['code'] == 'ACCESS_CREDENTIAL_INVALID'
    assert count(engine) == 0


@pytest.mark.parametrize('stage', ['after_flush', 'commit'])
def test_rollback_on_save_failure(api, monkeypatch, stage):
    c, engine, headers, _ = api
    original = routes.create_practice
    sessions = []
    rollback_calls = []

    def create(db, **kwargs):
        sessions.append(db)
        original_rollback = db.rollback

        def rollback():
            rollback_calls.append(db)
            return original_rollback()

        # Session.close() cleans up its transaction without calling this public
        # method, so this spy detects the router's explicit rollback call.
        monkeypatch.setattr(db, 'rollback', rollback)
        result = original(db, **kwargs)
        if stage == 'after_flush':
            raise SQLAlchemyError('injected save failure')
        def fail_commit(session):
            raise SQLAlchemyError('injected save failure')
        event.listen(db, 'before_commit', fail_commit, once=True)
        return result

    monkeypatch.setattr(routes, 'create_practice', create)
    with pytest.raises(SQLAlchemyError, match='injected save failure'):
        c.post('/practices', headers=headers, json={'script': '저장 실패'})
    assert rollback_calls == sessions
    assert count(engine) == 0
    assert not sessions[0].in_transaction()
    monkeypatch.setattr(routes, 'create_practice', original)
    assert c.post('/practices', headers=headers, json={'script': '재시도'}).status_code == 201
    assert count(engine) == 1
