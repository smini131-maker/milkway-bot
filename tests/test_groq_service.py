from types import SimpleNamespace

from discord_bot.services.gemini_service import AISource
from discord_bot.services.groq_service import (
    _choose_groq_model,
    _clean_model_output,
    _extract_groq_sources,
)


def test_choose_groq_model_prefers_current_multilingual_model() -> None:
    assert _choose_groq_model(
        {
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "qwen/qwen3.6-27b",
        }
    ) == "qwen/qwen3.6-27b"


def test_choose_groq_model_honors_configured_and_excluded() -> None:
    available = {"openai/gpt-oss-120b", "llama-3.3-70b-versatile"}
    assert (
        _choose_groq_model(available, configured="llama-3.3-70b-versatile")
        == "llama-3.3-70b-versatile"
    )
    assert (
        _choose_groq_model(
            available,
            configured="llama-3.3-70b-versatile",
            excluded={"llama-3.3-70b-versatile"},
        )
        == "openai/gpt-oss-120b"
    )


def test_extract_groq_sources_handles_nested_results_and_deduplicates() -> None:
    message = SimpleNamespace(
        executed_tools=[
            SimpleNamespace(
                search_results={
                    "results": [
                        {"title": "공식 문서", "url": "https://example.com/a"},
                        {"title": "중복", "url": "https://example.com/a"},
                        {"title": "두 번째", "url": "https://example.com/b"},
                    ]
                }
            )
        ]
    )

    assert _extract_groq_sources(message) == (
        AISource(title="공식 문서", url="https://example.com/a"),
        AISource(title="두 번째", url="https://example.com/b"),
    )


def test_clean_model_output_removes_think_block() -> None:
    assert _clean_model_output("<think>private reasoning</think>\n\nOK") == "OK"


def test_clean_model_output_removes_unmatched_thinking_prefix() -> None:
    value = "Thinking Process:\n1. reason\n</think>\n\nOK"
    assert _clean_model_output(value) == "OK"
