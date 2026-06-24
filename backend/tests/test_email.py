import utils.email as email


def test_dev_fallback_prints_link_when_no_api_key(monkeypatch, capsys):
    monkeypatch.setattr(email, "RESEND_API_KEY", None)

    email.send_email("alice@example.com", "Subject", "<p>hello world</p>")

    captured = capsys.readouterr()
    assert "alice@example.com" in captured.out
    assert "hello world" in captured.out


def test_send_email_posts_to_resend_when_api_key_set(monkeypatch):
    monkeypatch.setattr(email, "RESEND_API_KEY", "test-key")
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json})
        return FakeResponse()

    monkeypatch.setattr(email.httpx, "post", fake_post)

    email.send_email("alice@example.com", "Subject", "<p>hello</p>")

    assert len(calls) == 1
    assert calls[0]["json"]["to"] == ["alice@example.com"]
    assert calls[0]["json"]["subject"] == "Subject"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"


def test_send_verification_email_includes_link(monkeypatch, capsys):
    monkeypatch.setattr(email, "RESEND_API_KEY", None)

    email.send_verification_email("alice@example.com", "https://app.example.com/verify-email?token=abc")

    captured = capsys.readouterr()
    assert "https://app.example.com/verify-email?token=abc" in captured.out


def test_send_reset_email_includes_link(monkeypatch, capsys):
    monkeypatch.setattr(email, "RESEND_API_KEY", None)

    email.send_reset_email("alice@example.com", "https://app.example.com/reset-password?token=xyz")

    captured = capsys.readouterr()
    assert "https://app.example.com/reset-password?token=xyz" in captured.out
