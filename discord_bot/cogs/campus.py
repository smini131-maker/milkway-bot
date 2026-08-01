from __future__ import annotations

from discord.ext import commands

from discord_bot.cogs.campus_assignments import AssignmentCog
from discord_bot.cogs.campus_exams import ExamCog
from discord_bot.cogs.campus_timetable import TimetableCog
from discord_bot.cogs.campus_tools import CampusCog


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AssignmentCog(bot))
    await bot.add_cog(ExamCog(bot))
    await bot.add_cog(TimetableCog(bot))
    await bot.add_cog(CampusCog(bot))
