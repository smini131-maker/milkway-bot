from __future__ import annotations

from dataclasses import dataclass, field

from google import genai
from google.genai import errors, types


class AIUnavailableError(RuntimeError):
    """Raised when the optional Gemini integration is not configured."""


class AIRequestError(RuntimeError):
    """Raised when a Gemini request fails in a user-facing way."""


@dataclass(frozen=True, slots=True)
class AISource:
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class AIResponse:
    text: str
    sources: tuple[AISource, ...] = ()


def _extract_sources(response: object, *, maximum: int = 6) -> tuple[AISource, ...]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ()

    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []
    sources: list[AISource] = []
    seen_urls: set[str] = set()

    for chunk in chunks:
        web = getattr(chunk, "web", None)
        url = str(getattr(web, "uri", "") or "").strip()
        if not url or url in seen_urls:
            continue
        title = str(getattr(web, "title", "") or "출처").strip() or "출처"
        sources.append(AISource(title=title, url=url))
        seen_urls.add(url)
        if len(sources) >= maximum:
            break

    return tuple(sources)


@dataclass(slots=True)
class AIService:
    api_key: str | None
    model: str
    max_output_tokens: int
    _client: genai.Client | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._client = genai.Client(api_key=self.api_key) if self.api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def close(self) -> None:
        if self._client is None:
            return
        await self._client.aio.aclose()
        self._client.close()

    async def generate(
        self,
        *,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None = None,
        use_search: bool = False,
    ) -> AIResponse:
        if self._client is None:
            raise AIUnavailableError(
                "AI 기능이 비활성화되어 있습니다. 운영자가 GEMINI_API_KEY를 설정해야 합니다."
            )

        cleaned = prompt.strip()
        if not cleaned:
            raise ValueError("AI에 전달할 내용을 입력하세요.")
        if len(cleaned) > 24_000:
            raise ValueError("입력 내용이 너무 깁니다. 24,000자 이하로 줄여 주세요.")

        config_kwargs: dict[str, object] = {
            "system_instruction": instructions,
            "max_output_tokens": max_output_tokens or self.max_output_tokens,
            "temperature": 0.35,
        }
        if use_search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=cleaned,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code == 429:
                message = (
                    "Gemini 무료 사용량 또는 요청 속도 한도에 도달했습니다. "
                    "잠시 후 다시 시도하거나 Google AI Studio의 사용량을 확인하세요."
                )
            elif code in {400, 401, 403}:
                message = "Gemini API 키 또는 모델 설정이 올바르지 않습니다."
            else:
                message = "Gemini API 요청에 실패했습니다. API 키와 모델 설정을 확인하세요."
            raise AIRequestError(message) from exc
        except Exception as exc:
            raise AIRequestError(
                "Gemini API에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도하세요."
            ) from exc

        try:
            output = str(response.text or "").strip()
        except Exception as exc:
            raise AIRequestError(
                "Gemini 응답이 안전 필터에 의해 차단되었거나 텍스트를 반환하지 않았습니다."
            ) from exc
        if not output:
            raise AIRequestError("Gemini가 빈 응답을 반환했습니다. 다시 시도해 주세요.")
        return AIResponse(text=output, sources=_extract_sources(response) if use_search else ())
