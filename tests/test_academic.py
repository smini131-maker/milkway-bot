from decimal import Decimal

import pytest

from discord_bot.utils.academic import calculate_gpa, required_future_gpa, split_teams


def test_calculate_weighted_gpa() -> None:
    result = calculate_gpa("자료구조=3:A+, 교양=2:B0, 영어=2:A0")
    assert result.total_credits == Decimal("7")
    assert result.gpa == Decimal("3.93")
    assert result.entries[0].name == "자료구조"


def test_calculate_gpa_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError):
        calculate_gpa("자료구조 A+")


def test_required_future_gpa() -> None:
    required = required_future_gpa(
        current_credits=30,
        current_gpa=3.5,
        future_credits=18,
        target_gpa=3.8,
    )
    assert required == Decimal("4.30")


def test_split_teams_balances_team_sizes() -> None:
    teams = split_teams("가,나,다,라,마,바,사", 3)
    sizes = sorted(len(team) for team in teams)
    assert sizes == [2, 2, 3]
    assert sorted(member for team in teams for member in team) == sorted("가나다라마바사")
