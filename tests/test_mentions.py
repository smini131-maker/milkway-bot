from types import SimpleNamespace

import pytest

from discord_bot.utils.mentions import MentionSpec, render_message, resolve_mention


def test_resolve_none() -> None:
    assert resolve_mention() == MentionSpec()


def test_resolve_role() -> None:
    role = SimpleNamespace(id=123)
    assert resolve_mention(role=role) == MentionSpec("role", 123)


def test_rejects_multiple_mention_targets() -> None:
    role = SimpleNamespace(id=123)
    with pytest.raises(ValueError):
        resolve_mention(role=role, ping_everyone=True)


def test_render_user_mention() -> None:
    content, allowed = render_message("hello", MentionSpec("user", 456))
    assert content == "<@456> hello"
    assert allowed.everyone is False


def test_render_no_mentions() -> None:
    content, allowed = render_message("hello", MentionSpec())
    assert content == "hello"
    assert allowed.everyone is False
