from __future__ import annotations

import random
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_GRADE_POINTS_45 = {
    "A+": Decimal("4.5"),
    "A0": Decimal("4.0"),
    "A": Decimal("4.0"),
    "B+": Decimal("3.5"),
    "B0": Decimal("3.0"),
    "B": Decimal("3.0"),
    "C+": Decimal("2.5"),
    "C0": Decimal("2.0"),
    "C": Decimal("2.0"),
    "D+": Decimal("1.5"),
    "D0": Decimal("1.0"),
    "D": Decimal("1.0"),
    "F": Decimal("0.0"),
}
_ENTRY_RE = re.compile(
    r"^(?:(?P<name>[^:=,]+?)\s*[:=]\s*)?(?P<credits>\d+(?:\.\d+)?)\s*[:/]\s*(?P<grade>A\+|A0|A|B\+|B0|B|C\+|C0|C|D\+|D0|D|F)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class GradeEntry:
    name: str
    credits: Decimal
    grade: str
    points: Decimal


@dataclass(frozen=True, slots=True)
class GpaResult:
    entries: tuple[GradeEntry, ...]
    total_credits: Decimal
    total_points: Decimal
    gpa: Decimal


def _decimal(value: str | int | float | Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("숫자 형식이 올바르지 않습니다.") from exc


def parse_grade_entries(text: str) -> tuple[GradeEntry, ...]:
    raw_items = [item.strip() for item in text.split(",") if item.strip()]
    if not raw_items:
        raise ValueError("과목 성적을 하나 이상 입력하세요.")
    if len(raw_items) > 30:
        raise ValueError("한 번에 계산할 수 있는 과목은 최대 30개입니다.")

    entries: list[GradeEntry] = []
    for index, raw in enumerate(raw_items, start=1):
        match = _ENTRY_RE.fullmatch(raw)
        if not match:
            raise ValueError(
                f"`{raw}` 형식이 올바르지 않습니다. 예: `자료구조=3:A+, 교양=2:B0`"
            )
        credits = _decimal(match.group("credits"))
        if credits <= 0 or credits > 12:
            raise ValueError("과목별 학점은 0보다 크고 12 이하여야 합니다.")
        grade = match.group("grade").upper()
        name = (match.group("name") or f"과목 {index}").strip()
        entries.append(
            GradeEntry(
                name=name[:40],
                credits=credits,
                grade=grade,
                points=_GRADE_POINTS_45[grade],
            )
        )
    return tuple(entries)


def calculate_gpa(text: str) -> GpaResult:
    entries = parse_grade_entries(text)
    total_credits = sum((entry.credits for entry in entries), Decimal("0"))
    total_points = sum(
        (entry.credits * entry.points for entry in entries), Decimal("0")
    )
    gpa = (total_points / total_credits).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return GpaResult(entries, total_credits, total_points, gpa)


def required_future_gpa(
    *,
    current_credits: float,
    current_gpa: float,
    future_credits: float,
    target_gpa: float,
) -> Decimal:
    current_credits_d = _decimal(current_credits)
    current_gpa_d = _decimal(current_gpa)
    future_credits_d = _decimal(future_credits)
    target_gpa_d = _decimal(target_gpa)

    if current_credits_d < 0:
        raise ValueError("현재 이수학점은 0 이상이어야 합니다.")
    if future_credits_d <= 0:
        raise ValueError("앞으로 이수할 학점은 0보다 커야 합니다.")
    if not Decimal("0") <= current_gpa_d <= Decimal("4.5"):
        raise ValueError("현재 평점은 0~4.5 범위여야 합니다.")
    if not Decimal("0") <= target_gpa_d <= Decimal("4.5"):
        raise ValueError("목표 평점은 0~4.5 범위여야 합니다.")

    required = (
        target_gpa_d * (current_credits_d + future_credits_d)
        - current_gpa_d * current_credits_d
    ) / future_credits_d
    return required.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def split_teams(members_text: str, team_size: int) -> list[list[str]]:
    members = [item.strip() for item in re.split(r"[,\n|]", members_text) if item.strip()]
    if len(members) < 2:
        raise ValueError("팀을 나눌 구성원을 2명 이상 입력하세요.")
    if len(members) > 100:
        raise ValueError("구성원은 최대 100명까지 입력할 수 있습니다.")
    if len(set(members)) != len(members):
        raise ValueError("중복된 이름이 있습니다.")
    if not 1 <= team_size <= 20:
        raise ValueError("팀당 인원은 1~20명이어야 합니다.")

    random.shuffle(members)
    team_count = max(1, (len(members) + team_size - 1) // team_size)
    teams: list[list[str]] = [[] for _ in range(team_count)]
    for index, member in enumerate(members):
        teams[index % team_count].append(member)
    return teams
