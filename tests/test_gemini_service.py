from types import SimpleNamespace

from discord_bot.services.gemini_service import AISource, _extract_sources


def test_extract_sources_deduplicates_urls() -> None:
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(web=SimpleNamespace(title="공식 문서", uri="https://example.com/a")),
                        SimpleNamespace(web=SimpleNamespace(title="중복", uri="https://example.com/a")),
                        SimpleNamespace(web=SimpleNamespace(title="두 번째", uri="https://example.com/b")),
                    ]
                )
            )
        ]
    )

    assert _extract_sources(response) == (
        AISource(title="공식 문서", url="https://example.com/a"),
        AISource(title="두 번째", url="https://example.com/b"),
    )


def test_extract_sources_handles_missing_metadata() -> None:
    assert _extract_sources(SimpleNamespace(candidates=[])) == ()
