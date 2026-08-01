from __future__ import annotations

import logging

from discord_bot.bot import UtilityBot
from discord_bot.config import Settings


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = UtilityBot(settings)
    bot.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
