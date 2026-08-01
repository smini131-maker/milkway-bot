from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_DURATION_RE = re.compile(r"(?P<value>\d+)\s*(?P<unit>[smhdw])", re.IGNORECASE)
_WEEKDAYS = {
    "월": 0,
    "월요일": 0,
    "mon": 0,
    "monday": 0,
    "화": 1,
    "화요일": 1,
    "tue": 1,
    "tuesday": 1,
    "수": 2,
    "수요일": 2,
    "wed": 2,
    "wednesday": 2,
    "목": 3,
    "목요일": 3,
    "thu": 3,
    "thursday": 3,
    "금": 4,
    "금요일": 4,
    "fri": 4,
    "friday": 4,
    "토": 5,
    "토요일": 5,
    "sat": 5,
    "saturday": 5,
    "일": 6,
    "일요일": 6,
    "sun": 6,
    "sunday": 6,
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone-aware datetime이 필요합니다.")
    return value.astimezone(UTC).isoformat()


def from_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"알 수 없는 시간대입니다: {name}") from exc


def parse_duration(text: str) -> timedelta:
    normalized = text.strip().lower().replace(" ", "")
    matches = list(_DURATION_RE.finditer(normalized))
    if not matches or "".join(match.group(0) for match in matches).lower() != normalized:
        raise ValueError("시간은 10m, 1h30m, 2d 형식으로 입력하세요.")

    seconds = 0
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    for match in matches:
        seconds += int(match.group("value")) * multipliers[match.group("unit").lower()]

    if seconds <= 0:
        raise ValueError("0보다 큰 시간을 입력하세요.")
    return timedelta(seconds=seconds)


def parse_clock(text: str) -> tuple[int, int]:
    try:
        parsed = datetime.strptime(text.strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError("시간은 HH:MM 형식으로 입력하세요. 예: 09:30") from exc
    return parsed.hour, parsed.minute


def parse_local_datetime(text: str, timezone_name: str) -> datetime:
    zone = get_timezone(timezone_name)
    cleaned = text.strip().replace("T", " ")
    formats = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=zone)
        except ValueError:
            continue
    raise ValueError("날짜는 YYYY-MM-DD HH:MM 형식으로 입력하세요.")


def parse_weekday(text: str) -> int:
    key = text.strip().lower()
    if key not in _WEEKDAYS:
        raise ValueError("요일은 월~일 또는 Monday~Sunday로 입력하세요.")
    return _WEEKDAYS[key]


def next_daily(clock: str, timezone_name: str, after: datetime | None = None) -> datetime:
    zone = get_timezone(timezone_name)
    base = (after or utc_now()).astimezone(zone)
    hour, minute = parse_clock(clock)
    candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= base:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def next_weekly(
    weekday: int,
    clock: str,
    timezone_name: str,
    after: datetime | None = None,
) -> datetime:
    if weekday not in range(7):
        raise ValueError("weekday는 0~6이어야 합니다.")
    zone = get_timezone(timezone_name)
    base = (after or utc_now()).astimezone(zone)
    hour, minute = parse_clock(clock)
    days_ahead = (weekday - base.weekday()) % 7
    candidate = (base + timedelta(days=days_ahead)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if candidate <= base:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)


def human_duration(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    units = ((604800, "주"), (86400, "일"), (3600, "시간"), (60, "분"), (1, "초"))
    parts: list[str] = []
    for size, label in units:
        value, seconds = divmod(seconds, size)
        if value:
            parts.append(f"{value}{label}")
        if len(parts) == 2:
            break
    return " ".join(parts) or "0초"
