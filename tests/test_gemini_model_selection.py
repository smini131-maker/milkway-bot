from discord_bot.services.gemini_service import _choose_model


def test_configured_available_model_is_kept() -> None:
    assert (
        _choose_model(
            ["models/gemini-3.6-flash", "models/gemini-3.5-flash-lite"],
            configured="gemini-3.5-flash-lite",
        )
        == "gemini-3.5-flash-lite"
    )


def test_retired_configured_model_falls_back_to_current_stable_flash() -> None:
    assert (
        _choose_model(
            [
                "models/gemini-2.5-flash",
                "models/gemini-3.5-flash-lite",
                "models/gemini-3.6-flash",
            ],
            configured="gemini-2.5-flash",
            excluded={"gemini-2.5-flash"},
        )
        == "gemini-3.6-flash"
    )


def test_auto_mode_ignores_image_live_and_embedding_models() -> None:
    assert (
        _choose_model(
            [
                "models/gemini-4.0-flash-image",
                "models/gemini-3.1-flash-live-preview",
                "models/gemini-embedding-2",
                "models/gemini-4.0-flash",
            ]
        )
        == "gemini-4.0-flash"
    )


def test_future_stable_flash_is_selected_without_code_change() -> None:
    assert (
        _choose_model(
            ["models/gemini-4.1-flash-lite", "models/gemini-4.0-flash-image"]
        )
        == "gemini-4.1-flash-lite"
    )
