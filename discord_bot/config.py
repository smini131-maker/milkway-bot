from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"정수 환경변수 값이 올바르지 않습니다: {value}") from exc
    if not minimum <= parsed <= maximum:
        raise RuntimeError(f"환경변수 값은 {minimum}~{maximum} 범위여야 합니다: {parsed}")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_path: Path
    dev_guild_id: int | None
    log_level: str
    enable_member_intent: bool
    enable_message_content_intent: bool
    openai_api_key: str | None
    openai_model: str
    openai_max_output_tokens: int
    openai_moderation_enabled: bool
    ai_daily_user_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN이 없습니다. .env 파일을 확인하세요.")

        raw_guild_id = os.getenv("DEV_GUILD_ID", "").strip()
        dev_guild_id = int(raw_guild_id) if raw_guild_id else None
        database_path = Path(os.getenv("DATABASE_PATH", "data/bot.db")).expanduser()
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
        openai_model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"

        return cls(
            token=token,
            database_path=database_path,
            dev_guild_id=dev_guild_id,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            enable_member_intent=_as_bool(os.getenv("ENABLE_MEMBER_INTENT"), True),
            enable_message_content_intent=_as_bool(
                os.getenv("ENABLE_MESSAGE_CONTENT_INTENT"), True
            ),
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            openai_max_output_tokens=_as_int(
                os.getenv("OPENAI_MAX_OUTPUT_TOKENS"),
                1200,
                minimum=200,
                maximum=8000,
            ),
            openai_moderation_enabled=_as_bool(
                os.getenv("OPENAI_MODERATION_ENABLED"), True
            ),
            ai_daily_user_limit=_as_int(
                os.getenv("AI_DAILY_USER_LIMIT"),
                20,
                minimum=1,
                maximum=500,
            ),
        )
