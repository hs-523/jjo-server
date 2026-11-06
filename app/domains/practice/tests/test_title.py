from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai import errors
from pydantic import ValidationError

from app.domains.practice import title
from app.domains.practice.models import Practice
from app.domains.practice.schemas import PracticeCreate
from app.domains.practice.service import create_practice
from app.domains.practice.tests.test_create import db


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(title.settings, "gemini_api_key", "test-key")
    client = MagicMock()
    client.__enter__.return_value = client
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(title.genai, "Client", factory)
    client.models.generate_content.return_value = SimpleNamespace(text='  “발표의 미래”\n ')
    return factory, client.models.generate_content


def test_generated_title_is_persisted(db, gemini):
    practice = create_practice(db, user_id=1, data=PracticeCreate(script="발표를 시작합니다."))
    pk = practice.id
    db.commit()
    db.expunge_all()
    assert db.get(Practice, pk).title == "발표의 미래"
    factory, call = gemini
    options = factory.call_args.kwargs['http_options']
    assert options.timeout == 15000
    assert options.retry_options.attempts == 1
    assert call.call_args.kwargs['model'] == title.settings.gemini_model
    assert '"script"' in call.call_args.kwargs['contents']
    assert "지시문" in call.call_args.kwargs['config'].system_instruction


@pytest.mark.parametrize('script', ['', ' \n\t', '가' * 1501])
def test_invalid_script_never_calls_gemini(db, gemini, script):
    with pytest.raises(ValidationError):
        create_practice(db, user_id=1, data=PracticeCreate(script=script))
    gemini[0].assert_not_called()


@pytest.mark.parametrize(('raw', 'expected'), [
    (' \n"제목\n 두 줄"\n', '제목 두 줄'),
    ('“' + '가' * 120 + '”', '가' * 100),
    ("`'제목'`", '제목'),
])
def test_cleanup(gemini, raw, expected):
    gemini[1].return_value = SimpleNamespace(text=raw)
    assert title.generate_title('대본') == expected


@pytest.mark.parametrize('response', [None, '', ' \n ', '""'])
def test_empty_fallback(gemini, response):
    gemini[1].return_value = SimpleNamespace(text=response)
    assert title.generate_title('\n  첫 줄  \n다음 줄') == '첫 줄'


@pytest.mark.parametrize('error', [
    errors.APIError(429, {'error': {'message': 'quota'}}),
    httpx.ConnectError('offline'), httpx.ReadTimeout('timeout'), TimeoutError(),
])
def test_external_error_fallback(gemini, error):
    gemini[1].side_effect = error
    assert title.generate_title('\n' + '가' * 120) == '가' * 100


def test_programming_error_is_not_hidden(gemini):
    gemini[1].side_effect = TypeError('bug')
    with pytest.raises(TypeError, match='bug'):
        title.generate_title('대본')
