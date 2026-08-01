from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config import Settings
from discord_bot.database import Database
from discord_bot.services.gemini_service import AIService

LOGGER = logging.getLogger(__name__)


class UtilityCommandTree(app_commands.CommandTree):
    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        handler = getattr(self.client, "handle_app_command_error", None)
        if handler is None:
            await super().on_error(interaction, error)
            return
        await handler(interaction, error)


EXTENSIONS = (
    "discord_bot.cogs.schedule",
    "discord_bot.cogs.reminders",
    "discord_bot.cogs.messaging",
    "discord_bot.cogs.moderation",
    "discord_bot.cogs.automation",
    "discord_bot.cogs.utility",
    "discord_bot.cogs.campus",
    "discord_bot.cogs.ai",
)


class UtilityBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = settings.enable_member_intent
        intents.message_content = settings.enable_message_content_intent

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
            tree_cls=UtilityCommandTree,
        )
        self.settings = settings
        self.db = Database(settings.database_path)
        self.ai = AIService(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        self._identity_applied = False

    async def close(self) -> None:
        await self.ai.close()
        await super().close()

    async def setup_hook(self) -> None:
        await self.db.initialize()
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info("개발 서버 %s에 한글 명령어 %s개 동기화", guild.id, len(synced))

            # 과거에 전역 등록된 영문 명령어가 남아 중복 표시되지 않도록 정리합니다.
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            LOGGER.info("기존 전역 명령어 정리 완료")
        else:
            synced = await self.tree.sync()
            LOGGER.info("전역 명령어 %s개 동기화", len(synced))

    async def _apply_display_name(self) -> None:
        if self._identity_applied or self.user is None:
            return
        self._identity_applied = True
        desired = self.settings.bot_display_name

        # 봇 전용 관리 역할의 표시명은 봇 사용자명을 따라가므로 먼저 전역 사용자명을 바꿉니다.
        if self.user.name != desired:
            try:
                await self.user.edit(username=desired)
                LOGGER.info("Discord 봇 사용자명을 '%s'(으)로 변경", desired)
            except discord.HTTPException:
                LOGGER.warning(
                    "봇 사용자명을 '%s'(으)로 변경하지 못했습니다. "
                    "Discord Developer Portal의 Bot > Username에서 직접 변경하세요.",
                    desired,
                    exc_info=True,
                )

        # 서버마다 별명이 따로 설정되어 있어도 동일하게 보이도록 맞춥니다.
        for guild in self.guilds:
            member = guild.me
            if member is None or member.nick == desired:
                continue
            try:
                await member.edit(nick=desired, reason="Milkway Bot 표시 이름 동기화")
            except (discord.Forbidden, discord.HTTPException):
                LOGGER.warning(
                    "서버 %s에서 봇 별명을 '%s'(으)로 변경하지 못했습니다.",
                    guild.id,
                    desired,
                    exc_info=True,
                )

    async def on_ready(self) -> None:
        if self.user:
            await self._apply_display_name()
            LOGGER.info("로그인 완료: %s (%s)", self.user, self.user.id)
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="/도움말 | 한글 명령어",
                )
            )

    async def handle_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
        else:
            original = error

        if isinstance(original, app_commands.MissingPermissions):
            message = "이 명령어를 사용할 권한이 없습니다."
        elif isinstance(original, app_commands.BotMissingPermissions):
            missing = ", ".join(original.missing_permissions)
            message = f"봇 권한이 부족합니다: `{missing}`"
        elif isinstance(original, app_commands.CommandOnCooldown):
            message = f"잠시 후 다시 시도하세요. 약 {original.retry_after:.1f}초 남았습니다."
        elif isinstance(original, app_commands.NoPrivateMessage):
            message = "이 명령어는 서버에서만 사용할 수 있습니다."
        elif isinstance(original, ValueError):
            message = str(original)
        else:
            LOGGER.error(
                "처리되지 않은 앱 명령어 오류",
                exc_info=(type(error), error, error.__traceback__),
            )
            message = "명령어 처리 중 오류가 발생했습니다. 로그를 확인하세요."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
