from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import groq
from groq import AsyncGroq

from discord_bot.services.gemini_service import (
    AIRequestError,
    AIResponse,
    AISource,
    AIUnavailableError,
)

LOGGER = logging.getLogger(__name__)

_AUTO_MODEL = "auto"
_PREFERRED_MODELS = (
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
)
_SEARCH_FALLBACKS = ("groq/compound-mini", "groq/compound")
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.IGNORECASE | re.DOTALL)


def _normalize_model_name(value: object) -> str:
    return str(value or "").strip()


def _choose_groq_model(
    available_models: list[str] | tuple[str, ...] | set[str],
    *,
    configured: str = _AUTO_MODEL,
    excluded: set[str] | None = None,
) -> str | None:
    available = {_normalize_model_name(item) for item in available_models if _normalize_model_name(item)}
    available.difference_update({_normalize_model_name(item) for item in (excluded or set())})

    configured_name = _normalize_model_name(configured)
    if configured_name and configured_name != _AUTO_MODEL and configured_name in available:
        return configured_name

    for preferred in _PREFERRED_MODELS:
        if preferred in available:
            return preferred
    return None


def _value(item: object, name: str, default: object = None) -> object:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _search_result_items(search_results: object) -> list[object]:
    if not search_results:
        return []
    nested = _value(search_results, "results", None)
    if nested is not None:
        return list(nested or [])
    if isinstance(search_results, (list, tuple)):
        return list(search_results)
    return []


def _extract_groq_sources(message: object, *, maximum: int = 6) -> tuple[AISource, ...]:
    tools = _value(message, "executed_tools", []) or []
    sources: list[AISource] = []
    seen_urls: set[str] = set()

    for tool in tools:
        search_results = _value(tool, "search_results", []) or []
        for result in _search_result_items(search_results):
            url = str(_value(result, "url", "") or _value(result, "uri", "") or "").strip()
            if not url or url in seen_urls:
                continue
            title = str(_value(result, "title", "") or "검색 출처").strip() or "검색 출처"
            sources.append(AISource(title=title, url=url))
            seen_urls.add(url)
            if len(sources) >= maximum:
                return tuple(sources)
    return tuple(sources)


def _clean_model_output(value: object) -> str:
    output = str(value or "").strip()
    output = _THINK_BLOCK_RE.sub("", output).strip()

    # 일부 추론 모델은 여는 태그 없이 Thinking Process를 쓰고 </think>로 끝내기도 합니다.
    lowered = output.lower()
    if "</think>" in lowered:
        tail = output[lowered.rfind("</think>") + len("</think>") :].strip()
        if tail:
            output = tail

    return output.strip()


@dataclass(slots=True)
class GroqService:
    api_key: str | None
    model: str
    search_model: str
    max_output_tokens: int
    _client: AsyncGroq | None = field(init=False, repr=False, default=None)
    _active_model: str | None = field(init=False, default=None)
    _active_search_model: str | None = field(init=False, default=None)
    _model_lock: asyncio.Lock = field(init=False, repr=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self.model = _normalize_model_name(self.model) or _AUTO_MODEL
        self.search_model = _normalize_model_name(self.search_model) or "groq/compound-mini"
        self._client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def active_model(self) -> str:
        return self._active_model or ("자동 선택 대기" if self.model == _AUTO_MODEL else self.model)

    @property
    def active_search_model(self) -> str:
        return self._active_search_model or self.search_model

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def _available_models(self) -> list[str]:
        if self._client is None:
            return []
        page = await self._client.models.list()
        return [
            _normalize_model_name(_value(item, "id", ""))
            for item in (_value(page, "data", []) or [])
            if _normalize_model_name(_value(item, "id", ""))
        ]

    async def _resolve_model(self, *, excluded: set[str] | None = None) -> str:
        if self._client is None:
            raise AIUnavailableError("AI 기능이 비활성화되어 있습니다. GROQ_API_KEY를 설정하세요.")

        async with self._model_lock:
            excluded_names = {_normalize_model_name(item) for item in (excluded or set())}
            if self._active_model and self._active_model not in excluded_names:
                return self._active_model

            try:
                available = await self._available_models()
            except groq.APIConnectionError as exc:
                raise AIRequestError("Groq API에 연결하지 못했습니다. 인터넷 연결을 확인하세요.") from exc
            except groq.APIStatusError as exc:
                raise self._user_facing_error(exc, use_search=False) from exc

            selected = _choose_groq_model(
                available,
                configured=self.model,
                excluded=excluded_names,
            )
            if selected is None:
                raise AIRequestError(
                    "이 Groq API 키로 사용할 수 있는 일반 대화 모델을 찾지 못했습니다. "
                    "Groq Console의 모델 목록과 키 상태를 확인하세요."
                )
            self._active_model = selected
            LOGGER.info("Groq 일반 모델 자동 선택: %s", selected)
            return selected

    async def _resolve_search_model(self, *, excluded: set[str] | None = None) -> str:
        excluded_names = {_normalize_model_name(item) for item in (excluded or set())}
        candidates = (self.search_model, *_SEARCH_FALLBACKS)
        for candidate in candidates:
            normalized = _normalize_model_name(candidate)
            if normalized and normalized not in excluded_names:
                self._active_search_model = normalized
                return normalized
        raise AIRequestError("사용 가능한 Groq 검색 모델을 찾지 못했습니다.")

    def _user_facing_error(self, exc: groq.APIStatusError, *, use_search: bool) -> AIRequestError:
        code = int(getattr(exc, "status_code", 0) or 0)
        detail = str(exc)
        LOGGER.warning("Groq API 오류 code=%s detail=%s", code, detail)

        if code == 401:
            return AIRequestError("Groq API 키 인증에 실패했습니다. GROQ_API_KEY를 확인하세요.")
        if code == 403:
            return AIRequestError("Groq API 키에 현재 모델 또는 기능을 사용할 권한이 없습니다.")
        if code == 404:
            return AIRequestError("설정한 Groq 모델을 찾을 수 없습니다. 모델을 자동으로 다시 선택하세요.")
        if code == 429:
            return AIRequestError(
                "Groq 무료 사용량 또는 요청 속도 한도에 도달했습니다. 잠시 후 다시 시도하세요."
            )
        if code in {498, 500, 502, 503, 504}:
            return AIRequestError("Groq 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도하세요.")
        if use_search and code in {400, 422, 424}:
            return AIRequestError(
                "Groq 웹 검색 요청을 처리하지 못했습니다. 검색어를 줄이거나 잠시 후 다시 시도하세요."
            )
        if code in {400, 413, 422}:
            return AIRequestError("Groq 요청 내용이 너무 길거나 형식이 올바르지 않습니다.")
        return AIRequestError("Groq API 요청에 실패했습니다. 터미널의 상세 오류를 확인하세요.")

    async def _generate_once(
        self,
        *,
        model: str,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None,
    ) -> Any:
        if self._client is None:
            raise AIUnavailableError("AI 기능이 비활성화되어 있습니다. GROQ_API_KEY를 설정하세요.")

        request: dict[str, object] = {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_output_tokens or self.max_output_tokens,
        }
        if model.startswith("qwen/"):
            request["reasoning_format"] = "hidden"

        return await self._client.chat.completions.create(**request)

    async def generate(
        self,
        *,
        prompt: str,
        instructions: str,
        max_output_tokens: int | None = None,
        use_search: bool = False,
    ) -> AIResponse:
        if self._client is None:
            raise AIUnavailableError("AI 기능이 비활성화되어 있습니다. GROQ_API_KEY를 설정하세요.")

        cleaned = prompt.strip()
        if not cleaned:
            raise ValueError("AI에 전달할 내용을 입력하세요.")
        if len(cleaned) > 24_000:
            raise ValueError("입력 내용이 너무 깁니다. 24,000자 이하로 줄여 주세요.")

        model = await self._resolve_search_model() if use_search else await self._resolve_model()

        try:
            response = await self._generate_once(
                model=model,
                prompt=cleaned,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
            )
        except groq.APIConnectionError as exc:
            raise AIRequestError("Groq API에 연결하지 못했습니다. 인터넷 연결을 확인하세요.") from exc
        except groq.APIStatusError as exc:
            if int(getattr(exc, "status_code", 0) or 0) == 404:
                if use_search:
                    self._active_search_model = None
                    replacement = await self._resolve_search_model(excluded={model})
                else:
                    self._active_model = None
                    replacement = await self._resolve_model(excluded={model})
                LOGGER.warning("Groq 모델 %s 사용 불가; %s로 자동 교체 후 재시도", model, replacement)
                try:
                    response = await self._generate_once(
                        model=replacement,
                        prompt=cleaned,
                        instructions=instructions,
                        max_output_tokens=max_output_tokens,
                    )
                    model = replacement
                except groq.APIStatusError as retry_exc:
                    raise self._user_facing_error(retry_exc, use_search=use_search) from retry_exc
            else:
                raise self._user_facing_error(exc, use_search=use_search) from exc

        message = response.choices[0].message if response.choices else None
        output = _clean_model_output(_value(message, "content", ""))
        if not output:
            raise AIRequestError("Groq가 빈 응답을 반환했습니다. 다시 시도해 주세요.")

        if use_search:
            self._active_search_model = model
        else:
            self._active_model = model
        return AIResponse(
            text=output,
            sources=_extract_groq_sources(message) if use_search else (),
        )
