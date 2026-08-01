from __future__ import annotations

import ast
from pathlib import Path

COGS = Path(__file__).parents[1] / "discord_bot" / "cogs"

EXPECTED_GROUPS = {
    "과제": {"추가", "보기", "완료", "삭제"},
    "시험": {"추가", "보기", "삭제"},
    "시간표": {"추가", "오늘", "보기", "삭제"},
    "대학생": {"한눈에", "학점", "집중"},
    "인공지능": {"질문", "검색", "요약", "퀴즈", "사용량"},
    "알림": {"후에", "날짜", "보기", "삭제"},
    "예약": {"간격", "매일", "매주", "한번", "보기", "삭제"},
    "설정": {"시간대", "환영", "퇴장", "자동역할", "로그", "끄기", "보기"},
    "관리": {
        "삭제",
        "타임아웃",
        "타임아웃해제",
        "추방",
        "차단",
        "차단해제",
        "슬로우",
        "경고",
        "경고보기",
        "경고삭제",
    },
}

REMOVED_NAMES = {
    "attendance",
    "study",
    "lock",
    "unlock",
    "pause",
    "resume",
    "edit",
    "time",
    "run",
    "autoresponse",
}


def _surface() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in COGS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            group_name = None
            for keyword in node.keywords:
                if keyword.arg == "group_name" and isinstance(keyword.value, ast.Constant):
                    group_name = str(keyword.value.value)
            if group_name is None:
                continue
            commands: set[str] = set()
            for item in node.body:
                if not isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    continue
                for decorator in item.decorator_list:
                    if not (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr == "command"
                    ):
                        continue
                    for keyword in decorator.keywords:
                        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                            commands.add(str(keyword.value.value))
            result[group_name] = commands
    return result


def test_korean_command_surface() -> None:
    surface = _surface()
    for group, commands in EXPECTED_GROUPS.items():
        assert surface[group] == commands


def test_removed_features_are_not_registered() -> None:
    surface = _surface()
    all_names = set(surface)
    for commands in surface.values():
        all_names.update(commands)
    assert all_names.isdisjoint(REMOVED_NAMES)
    assert not (COGS / "campus_attendance.py").exists()
    assert not (COGS / "campus_study.py").exists()
