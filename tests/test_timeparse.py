from datetime import datetime, timedelta, timezone

import pytest

from discord_bot.utils.timeparse import (
    next_daily,
    next_weekly,
    parse_clock,
    parse_duration,
    parse_local_datetime,
    parse_weekday,
)


def test_parse_duration_compound() -> None:
    assert parse_duration("1h30m") == timedelta(hours=1, minutes=30)
    assert parse_duration("2d 3h") == timedelta(days=2, hours=3)


def test_parse_duration_rejects_invalid_text() -> None:
    with pytest.raises(ValueError):
        parse_duration("tomorrow")


def test_parse_clock() -> None:
    assert parse_clock("09:05") == (9, 5)
    with pytest.raises(ValueError):
        parse_clock("25:00")


def test_parse_weekday_korean_and_english() -> None:
    assert parse_weekday("월요일") == 0
    assert parse_weekday("Sunday") == 6


def test_parse_local_datetime_uses_timezone() -> None:
    parsed = parse_local_datetime("2026-08-01 15:30", "Asia/Seoul")
    assert parsed.utcoffset() == timedelta(hours=9)


def test_next_daily_rolls_to_next_day() -> None:
    after = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)  # 10:00 KST
    result = next_daily("09:00", "Asia/Seoul", after)
    assert result == datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)


def test_next_weekly() -> None:
    after = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)  # Saturday 10:00 KST
    result = next_weekly(0, "09:00", "Asia/Seoul", after)
    assert result == datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
