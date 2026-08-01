from __future__ import annotations

from dataclasses import dataclass, field

from openai import AsyncOpenAI, OpenAIError


class AIUnavailableError(RuntimeError):
    """Raised when the optional OpenAI integration is not configured."""


class AIRequestError(RuntimeError):
    """Raised when an OpenAI request fails in a user-facing way."""


@dataclass(slots=True)
class AIService:
    api_key: str | None
    model: str
    max_output_tokens: int
    moderation_enabled: bool = True
    _client: AsyncOpenAI | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def generate(
        self,
        *,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None = None,
    ) -> str:
        if self._client is None:
            raise AIUnavailableError(
                "AI 기능이 비활성화되어 있습니다. 운영자가 OPENAI_API_KEY를 설정해야 합니다."
            )

        cleaned = prompt.strip()
        if not cleaned:
            raise ValueError("AI에 전달할 내용을 입력하세요.")
        if len(cleaned) > 24_000:
            raise ValueError("입력 내용이 너무 깁니다. 24,000자 이하로 줄여 주세요.")

        try:
            if self.moderation_enabled:
                moderation = await self._client.moderations.create(
                    model="omni-moderation-latest",
                    input=cleaned,
                )
                if moderation.results and moderation.results[0].flagged:
                    raise AIRequestError("안전상 처리할 수 없는 내용이 포함되어 있습니다.")

            response = await self._client.responses.create(
                model=self.model,
                instructions=instructions,
                input=cleaned,
                max_output_tokens=max_output_tokens or self.max_output_tokens,
                store=False,
            )
        except AIRequestError:
            raise
        except OpenAIError as exc:
            raise AIRequestError(
                "OpenAI API 요청에 실패했습니다. API 키, 결제 한도, 모델 설정을 확인하세요."
            ) from exc

        output = response.output_text.strip()
        if not output:
            raise AIRequestError("AI가 빈 응답을 반환했습니다. 다시 시도해 주세요.")
        return output
