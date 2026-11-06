import pytest

from app.domains.practice import title


@pytest.fixture(autouse=True)
def disable_live_gemini(monkeypatch):
    monkeypatch.setattr(title.settings, "gemini_api_key", "")
