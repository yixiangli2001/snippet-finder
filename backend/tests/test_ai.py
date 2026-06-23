from openai import OpenAIError
from fastapi.testclient import TestClient

import routers.snippets as snippets_router
from main import app
from models.ai import SnippetMetadata
from tests.test_snippets import auth_header, use_fake_data


def fake_analyze(result):
    """Return an async stand-in for analyze_snippet that yields `result`.

    `result` may be a SnippetMetadata to return, or an exception to raise —
    this lets each test drive the endpoint's success and failure branches
    without ever touching the real OpenAI API.
    """
    async def _analyze(code: str):
        if isinstance(result, Exception):
            raise result
        return result
    return _analyze


def test_analyze_requires_auth(monkeypatch):
    use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.post("/snippets/analyze", json={"code": "print('hi')"})

    assert response.status_code == 401


def test_analyze_returns_metadata(monkeypatch):
    alice, _, _, _ = use_fake_data(monkeypatch)
    metadata = SnippetMetadata(
        title="Print greeting",
        language="PYTHON",
        description="Prints a greeting to standard output.",
        tags=["print", "io"],
    )
    monkeypatch.setattr(snippets_router, "analyze_snippet", fake_analyze(metadata))
    client = TestClient(app)

    response = client.post(
        "/snippets/analyze",
        json={"code": "print('hi')"},
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Print greeting"
    assert body["language"] == "PYTHON"
    assert body["tags"] == ["print", "io"]


def test_analyze_rejects_empty_code(monkeypatch):
    alice, _, _, _ = use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/snippets/analyze",
        json={"code": ""},
        headers=auth_header(alice),
    )

    assert response.status_code == 422


def test_analyze_missing_key_returns_503(monkeypatch):
    alice, _, _, _ = use_fake_data(monkeypatch)
    error = RuntimeError("OPENAI_API_KEY is not configured")
    monkeypatch.setattr(snippets_router, "analyze_snippet", fake_analyze(error))
    client = TestClient(app)

    response = client.post(
        "/snippets/analyze",
        json={"code": "print('hi')"},
        headers=auth_header(alice),
    )

    assert response.status_code == 503


def test_analyze_provider_error_returns_502(monkeypatch):
    alice, _, _, _ = use_fake_data(monkeypatch)
    monkeypatch.setattr(snippets_router, "analyze_snippet", fake_analyze(OpenAIError("boom")))
    client = TestClient(app)

    response = client.post(
        "/snippets/analyze",
        json={"code": "print('hi')"},
        headers=auth_header(alice),
    )

    assert response.status_code == 502
