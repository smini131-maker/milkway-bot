from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

from google import genai
from google.genai import errors, types

LOGGER = logging.getLogger(__name__)

_AUTO_MODEL = "auto"
_PREFERRED_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
)
_EXCLUDED_MODEL_PARTS = (
    "image",
    "live",
    "tts",
    "audio",
    "embedding",
    "robotics",
    "veo",
    "imagen",
    "lyria",
)
_VERSION_RE = re.compile(r"^gemini-(?P<major>\d+)(?:\.(?P<minor>\d+))?-")


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


def _normalize_model_name(name: object) -> str:
    value = str(name or "").strip()
    return value.removeprefix("models/")


def _is_general_flash_model(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered.startswith("gemini-")
        and "flash" in lowered
        and not any(part in lowered for part in _EXCLUDED_MODEL_PARTS)
    )


def _automatic_model_sort_key(name: str) -> tuple[int, int, int, int, str]:
    """Sort general text Flash models from safest/newest to older fallbacks."""
    lowered = name.lower()
    match = _VERSION_RE.match(lowered)
    major = int(match.group("major")) if match else 0
    minor = int(match.group("minor") or 0) if match else 0
    stable = int(not any(tag in lowered for tag in ("preview", "experimental", "exp", "latest")))
    full_flash = int("flash-lite" not in lowered)
    return stable, major, minor, full_flash, lowered


def _choose_model(
    available_models: list[str] | tuple[str, ...] | set[str],
    *,
    configured: str = _AUTO_MODEL,
    excluded: set[str] | None = None,
) -> str | None:
    """Choose an available generateContent model without hard-coding one endpoint forever."""
    excluded_names = {_normalize_model_name(item) for item in (excluded or set())}
    available = {
        _normalize_model_name(item)
        for item in available_models
        if _normalize_model_name(item)
    }
    available.difference_update(excluded_names)

    configured_name = _normalize_model_name(configured)
    if configured_name and configured_name != _AUTO_MODEL and configured_name in available:
        return configured_name

    for preferred in _PREFERRED_MODELS:
        if preferred in available:
            return preferred

    candidates = [name for name in available if _is_general_flash_model(name)]
    if not candidates:
        return None
    return max(candidates, key=_automatic_model_sort_key)


def _looks_like_search_tier_error(detail: str) -> bool:
    lowered = detail.lower()
    return (
        "google search" in lowered
        or "grounding" in lowered
        or "search tool" in lowered
    ) and any(
        phrase in lowered
        for phrase in (
            "not available",
            "not enabled",
            "permission",
            "billing",
            "paid tier",
            "unsupported",
        )
    )


@dataclass(slots=True)
class AIService:
    api_key: str | None
    model: str
    max_output_tokens: int
    _client: genai.Client | None = field(init=False, repr=False, default=None)
    _active_model: str | None = field(init=False, default=None)
    _model_lock: asyncio.Lock = field(init=False, repr=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self.model = _normalize_model_name(self.model) or _AUTO_MODEL
        self._client = genai.Client(api_key=self.api_key) if self.api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def active_model(self) -> str:
        return self._active_model or ("자동 선택 대기" if self.model == _AUTO_MODEL else self.model)

    async def close(self) -> None:
        if self._client is None:
            return
        await self._client.aio.aclose()
        self._client.close()

    async def _available_generate_models(self) -> list[str]:
        if self._client is None:
            return []

        def collect() -> list[str]:
            models: list[str] = []
            for item in self._client.models.list():
                actions = set(getattr(item, "supported_actions", None) or [])
                if "generateContent" not in actions:
                    continue
                name = _normalize_model_name(getattr(item, "name", ""))
                if name:
                    models.append(name)
            return models

        return await asyncio.to_thread(collect)

    async def _resolve_model(self, *, excluded: set[str] | None = None) -> str:
        if self._client is None:
            raise AIUnavailableError(
                "AI 기능이 비활성화되어 있습니다. 운영자가 GEMINI_API_KEY를 설정해야 합니다."
            )

        async with self._model_lock:
            excluded_names = {_normalize_model_name(item) for item in (excluded or set())}
            if self._active_model and self._active_model not in excluded_names:
                return self._active_model

            try:
                available = await self._available_generate_models()
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                detail = str(getattr(exc, "message", "") or exc)
                LOGGER.warning("Gemini 모델 목록 조회 실패 code=%s detail=%s", code, detail)
                raise self._user_facing_api_error(exc, use_search=False) from exc
            except Exception as exc:
                LOGGER.exception("Gemini 모델 목록 조회 중 연결 오류")
                raise AIRequestError(
                    "Gemini에서 사용 가능한 모델 목록을 확인하지 못했습니다. 인터넷 연결을 확인하세요."
                ) from exc

            selected = _choose_model(
                available,
                configured=self.model,
                excluded=excluded_names,
            )
            if selected is None:
                raise AIRequestError(
                    "이 API 키로 사용할 수 있는 일반 Gemini Flash 모델을 찾지 못했습니다. "
                    "Google AI Studio의 프로젝트와 API 키 상태를 확인하세요."
                )

            self._active_model = selected
            LOGGER.info("Gemini 사용 모델 자동 선택: %s", selected)
            return selected

    def _user_facing_api_error(
        self,
        exc: errors.APIError,
        *,
        use_search: bool,
    ) -> AIRequestError:
        code = getattr(exc, "code", None)
        detail = str(getattr(exc, "message", "") or exc)
        LOGGER.warning("Gemini API 오류 code=%s detail=%s", code, detail)

        if use_search and code in {400, 403} and _looks_like_search_tier_error(detail):
            return AIRequestError(
                "현재 Gemini 무료 등급에서는 새 Gemini 3.x 모델의 Google 검색 연결을 "
                "사용할 수 없습니다. 일반 질문은 `/인공지능 질문`으로 사용할 수 있고, "
                "실시간 검색은 Google AI Studio 프로젝트에서 유료 결제를 활성화해야 합니다."
            )
        if code == 401:
            return AIRequestError("Gemini API 키 인증에 실패했습니다. API 키를 다시 확인하세요.")
        if code == 403:
            return AIRequestError(
                "Gemini API 키에 현재 프로젝트·모델·기능을 사용할 권한이 없습니다."
            )
        if code == 400:
            return AIRequestError("Gemini 요청 형식 또는 모델 기능 설정이 올바르지 않습니다.")
        if code == 404:
            return AIRequestError(
                "사용 가능한 Gemini 모델을 자동으로 찾지 못했습니다. 잠시 후 다시 시도하세요."
            )
        if code == 429:
            return AIRequestError(
                "Gemini 무료 사용량 또는 요청 속도 한도에 도달했습니다. "
                "잠시 후 다시 시도하거나 Google AI Studio의 사용량을 확인하세요."
            )
        if code in {500, 502, 503, 504}:
            return AIRequestError("Gemini 서버가 일시적으로 불안정합니다. 잠시 후 다시 시도하세요.")
        return AIRequestError("Gemini API 요청에 실패했습니다. 터미널의 상세 오류를 확인하세요.")

    async def _generate_once(
        self,
        *,
        model: str,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None,
        use_search: bool,
    ) -> object:
        if self._client is None:
            raise AIUnavailableError(
                "AI 기능이 비활성화되어 있습니다. 운영자가 GEMINI_API_KEY를 설정해야 합니다."
            )

        config_kwargs: dict[str, object] = {
            "system_instruction": instructions,
            "max_output_tokens": max_output_tokens or self.max_output_tokens,
        }
        if use_search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        return await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

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

        model = await self._resolve_model() if self.model == _AUTO_MODEL else (self._active_model or self.model)

        try:
            response = await self._generate_once(
                model=model,
                prompt=cleaned,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
                use_search=use_search,
            )
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code == 404:
                failed_model = model
                self._active_model = None
                replacement = await self._resolve_model(excluded={failed_model})
                LOGGER.warning(
                    "Gemini 모델 %s 사용 불가; %s로 자동 교체 후 재시도",
                    failed_model,
                    replacement,
                )
                try:
                    response = await self._generate_once(
                        model=replacement,
                        prompt=cleaned,
                        instructions=instructions,
                        max_output_tokens=max_output_tokens,
                        use_search=use_search,
                    )
                except errors.APIError as retry_exc:
                    raise self._user_facing_api_error(
                        retry_exc,
                        use_search=use_search,
                    ) from retry_exc
            else:
                raise self._user_facing_api_error(exc, use_search=use_search) from exc
        except AIRequestError:
            raise
        except Exception as exc:
            LOGGER.exception("Gemini API 연결 오류")
            raise AIRequestError(
                "Gemini API에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도하세요."
            ) from exc

        self._active_model = self._active_model or model

        try:
            output = str(response.text or "").strip()
        except Exception as exc:
            raise AIRequestError(
                "Gemini 응답이 안전 필터에 의해 차단되었거나 텍스트를 반환하지 않았습니다."
            ) from exc
        if not output:
            raise AIRequestError("Gemini가 빈 응답을 반환했습니다. 다시 시도해 주세요.")
        return AIResponse(text=output, sources=_extract_sources(response) if use_search else ())
