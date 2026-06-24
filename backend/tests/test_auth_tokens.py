from datetime import timedelta

import utils.auth_tokens as auth_tokens
from tests.fakes import FakeCollection
from utils.auth_tokens import consume_auth_token, create_auth_token


def use_fake_tokens(monkeypatch):
    tokens = FakeCollection()
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", tokens)
    return tokens


async def test_created_token_can_be_consumed_once(monkeypatch):
    use_fake_tokens(monkeypatch)

    token = await create_auth_token("user-1", "verify_email", timedelta(hours=1))
    user_id = await consume_auth_token(token, "verify_email")

    assert user_id == "user-1"


async def test_consuming_a_token_twice_fails_the_second_time(monkeypatch):
    use_fake_tokens(monkeypatch)
    token = await create_auth_token("user-1", "verify_email", timedelta(hours=1))

    await consume_auth_token(token, "verify_email")
    second_attempt = await consume_auth_token(token, "verify_email")

    assert second_attempt is None


async def test_token_is_rejected_for_the_wrong_purpose(monkeypatch):
    use_fake_tokens(monkeypatch)
    token = await create_auth_token("user-1", "verify_email", timedelta(hours=1))

    result = await consume_auth_token(token, "reset_password")

    assert result is None


async def test_expired_token_is_rejected(monkeypatch):
    use_fake_tokens(monkeypatch)
    token = await create_auth_token("user-1", "reset_password", timedelta(hours=-1))

    result = await consume_auth_token(token, "reset_password")

    assert result is None
