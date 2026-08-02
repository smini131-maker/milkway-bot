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


def _display_name(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    name = value.strip()
    if not 2 <= len(name) <= 32:
        raise RuntimeError("BOT_DISPLAY_NAME은 2~32자여야 합니다.")
    return name


def _ai_provider(value: str | None) -> str:
    provider = (value or "auto").strip().lower() or "auto"
    if provider not in {"auto", "groq", "gemini"}:
        raise RuntimeError("AI_PROVIDER는 auto, groq, gemini 중 하나여야 합니다.")
    return provider


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    database_path: Path
    database_url: str | None
    dev_guild_id: int | None
    bot_display_name: str | None
    log_level: str
    enable_member_intent: bool
    enable_message_content_intent: bool
    ai_provider: str
    groq_api_key: str | None
    groq_model: str
    groq_search_model: str
    gemini_api_key: str | None
    gemini_model: str
    ai_max_output_tokens: int
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
        database_url = (
            os.getenv("DATABASE_URL", "").strip()
            or os.getenv("POSTGRES_URI", "").strip()
            or None
        )
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip() or None
        gemini_api_key = (
            os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
            or None
        )
        max_output_value = os.getenv("AI_MAX_OUTPUT_TOKENS")
        if max_output_value is None:
            max_output_value = os.getenv("GEMINI_MAX_OUTPUT_TOKENS")

        return cls(
            token=token,
            database_path=database_path,
            database_url=database_url,
            dev_guild_id=dev_guild_id,
            bot_display_name=_display_name(os.getenv("BOT_DISPLAY_NAME")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            enable_member_intent=_as_bool(os.getenv("ENABLE_MEMBER_INTENT"), True),
            enable_message_content_intent=_as_bool(
                os.getenv("ENABLE_MESSAGE_CONTENT_INTENT"), True
            ),
            ai_provider=_ai_provider(os.getenv("AI_PROVIDER")),
            groq_api_key=groq_api_key,
            groq_model=os.getenv("GROQ_MODEL", "auto").strip() or "auto",
            groq_search_model=(
                os.getenv("GROQ_SEARCH_MODEL", "groq/compound-mini").strip()
                or "groq/compound-mini"
            ),
            gemini_api_key=gemini_api_key,
            gemini_model=os.getenv("GEMINI_MODEL", "auto").strip() or "auto",
            ai_max_output_tokens=_as_int(
                max_output_value,
                1200,
                minimum=200,
                maximum=8000,
            ),
            ai_daily_user_limit=_as_int(
                os.getenv("AI_DAILY_USER_LIMIT"),
                20,
                minimum=0,
                maximum=500,
            ),
        )
