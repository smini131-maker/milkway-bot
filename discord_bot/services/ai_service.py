from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from discord_bot.services.gemini_service import (
    AIRequestError,
    AIResponse,
    AISource,
    AIUnavailableError,
    AIService as GeminiService,
)
from discord_bot.services.groq_service import GroqService

ProviderName = Literal["groq", "gemini", "none"]


@dataclass(slots=True)
class AIService:
    provider: str
    groq_api_key: str | None
    groq_model: str
    groq_search_model: str
    gemini_api_key: str | None
    gemini_model: str
    max_output_tokens: int
    _service: GroqService | GeminiService | None = field(init=False, repr=False, default=None)
    _provider_name: ProviderName = field(init=False, default="none")

    def __post_init__(self) -> None:
        requested = self.provider.strip().lower() or "auto"
        if requested not in {"auto", "groq", "gemini"}:
            raise RuntimeError("AI_PROVIDER는 auto, groq, gemini 중 하나여야 합니다.")

        if requested in {"auto", "groq"} and self.groq_api_key:
            self._service = GroqService(
                api_key=self.groq_api_key,
                model=self.groq_model,
                search_model=self.groq_search_model,
                max_output_tokens=self.max_output_tokens,
            )
            self._provider_name = "groq"
            return

        if requested in {"auto", "gemini"} and self.gemini_api_key:
            self._service = GeminiService(
                api_key=self.gemini_api_key,
                model=self.gemini_model,
                max_output_tokens=self.max_output_tokens,
            )
            self._provider_name = "gemini"

    @property
    def available(self) -> bool:
        return self._service is not None and self._service.available

    @property
    def provider_name(self) -> str:
        return {"groq": "Groq", "gemini": "Gemini", "none": "미설정"}[self._provider_name]

    @property
    def active_model(self) -> str:
        if self._service is None:
            return "미설정"
        return self._service.active_model

    @property
    def active_search_model(self) -> str:
        if isinstance(self._service, GroqService):
            return self._service.active_search_model
        if self._service is None:
            return "미설정"
        return self._service.active_model

    async def close(self) -> None:
        if self._service is not None:
            await self._service.close()

    async def generate(
        self,
        *,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None = None,
        use_search: bool = False,
    ) -> AIResponse:
        if self._service is None:
            raise AIUnavailableError(
                "AI 기능이 비활성화되어 있습니다. GROQ_API_KEY 또는 GEMINI_API_KEY를 설정하세요."
            )
        return await self._service.generate(
            prompt=prompt,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            use_search=use_search,
        )


__all__ = [
    "AIRequestError",
    "AIResponse",
    "AISource",
    "AIService",
    "AIUnavailableError",
]
