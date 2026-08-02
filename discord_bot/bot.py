from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config import Settings
from discord_bot.database import Database
from discord_bot.services.ai_service import AIService

LOGGER = logging.getLogger(__name__)


ROOT_COMMAND_RENAMES = {
    "대학생": "학교",
    "메시지": "전송",
    "서버정보": "서버",
    "사용자정보": "사용자",
}

GROUP_COMMAND_RENAMES = {
    "과제": {"보기": "목록"},
    "시험": {"보기": "목록"},
    "시간표": {"보기": "전체"},
    "학교": {"한눈에": "오늘"},
    "인공지능": {"사용량": "상태"},
    "알림": {"보기": "목록"},
    "예약": {"간격": "반복", "보기": "목록"},
    "설정": {"자동역할": "역할", "보기": "확인"},
    "관리": {
        "삭제": "정리",
        "타임아웃": "제한",
        "타임아웃해제": "제한해제",
        "경고보기": "경고목록",
        "경고삭제": "경고초기화",
    },
}

ROOT_DESCRIPTION_OVERRIDES = {
    "학교": "오늘 일정, 학점 계산, 집중 타이머를 사용합니다.",
    "전송": "봇이 지정한 채널에 메시지를 보냅니다.",
    "서버": "현재 서버 정보를 확인합니다.",
    "사용자": "사용자의 서버 정보를 확인합니다.",
}

CHILD_DESCRIPTION_OVERRIDES = {
    ("인공지능", "질문"): "일반 질문을 합니다.",
    ("인공지능", "검색"): "웹에서 최신 정보를 찾아 출처와 함께 답합니다.",
    ("인공지능", "상태"): "연결 상태, 모델, 오늘 사용량을 확인합니다.",
    ("학교", "오늘"): "오늘 강의와 가까운 과제·시험을 한 번에 봅니다.",
    ("예약", "반복"): "정한 간격마다 메시지를 자동 전송합니다.",
    ("관리", "정리"): "현재 채널의 최근 메시지를 여러 개 삭제합니다.",
    ("관리", "제한"): "사용자를 일정 시간 동안 채팅 제한합니다.",
    ("관리", "제한해제"): "사용자의 채팅 제한을 해제합니다.",
    ("관리", "경고목록"): "사용자의 경고 기록을 확인합니다.",
    ("관리", "경고초기화"): "사용자의 경고 기록을 모두 삭제합니다.",
}


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
        self.db = Database(settings.database_path, settings.database_url)
        self.ai = AIService(
            provider=settings.ai_provider,
            groq_api_key=settings.groq_api_key,
            groq_model=settings.groq_model,
            groq_search_model=settings.groq_search_model,
            gemini_api_key=settings.gemini_api_key,
            gemini_model=settings.gemini_model,
            max_output_tokens=settings.ai_max_output_tokens,
        )
        self._identity_applied = False

    @staticmethod
    def _set_command_name(command: app_commands.Command | app_commands.Group, name: str) -> None:
        command.name = name
        command._locale_name = None

    @staticmethod
    def _set_command_description(
        command: app_commands.Command | app_commands.Group,
        description: str,
    ) -> None:
        command.description = description
        command._locale_description = None

    def _simplify_command_names(self) -> None:
        for old_name, new_name in ROOT_COMMAND_RENAMES.items():
            command = self.tree.get_command(old_name)
            if command is None:
                LOGGER.warning("이름을 바꿀 명령어를 찾지 못했습니다: /%s", old_name)
                continue
            self.tree.remove_command(old_name)
            self._set_command_name(command, new_name)
            if new_name in ROOT_DESCRIPTION_OVERRIDES:
                self._set_command_description(command, ROOT_DESCRIPTION_OVERRIDES[new_name])
            self.tree.add_command(command, override=True)

        for group_name, renames in GROUP_COMMAND_RENAMES.items():
            group = self.tree.get_command(group_name)
            if not isinstance(group, app_commands.Group):
                LOGGER.warning("명령어 그룹을 찾지 못했습니다: /%s", group_name)
                continue
            for old_name, new_name in renames.items():
                command = group.get_command(old_name)
                if command is None:
                    LOGGER.warning(
                        "이름을 바꿀 하위 명령어를 찾지 못했습니다: /%s %s",
                        group_name,
                        old_name,
                    )
                    continue
                group.remove_command(old_name)
                self._set_command_name(command, new_name)
                description = CHILD_DESCRIPTION_OVERRIDES.get((group_name, new_name))
                if description:
                    self._set_command_description(command, description)
                group.add_command(command, override=True)

        for group_name, command_name in CHILD_DESCRIPTION_OVERRIDES:
            group = self.tree.get_command(group_name)
            if not isinstance(group, app_commands.Group):
                continue
            command = group.get_command(command_name)
            if command is not None:
                self._set_command_description(
                    command,
                    CHILD_DESCRIPTION_OVERRIDES[(group_name, command_name)],
                )

        LOGGER.info("슬래시 명령어 이름 간소화 완료")

    def _flatten_question_commands(self) -> None:
        group = self.tree.get_command("인공지능")
        if not isinstance(group, app_commands.Group):
            LOGGER.warning("질문 명령어 그룹을 찾지 못했습니다.")
            return

        self.tree.remove_command("인공지능")
        for command in list(group.commands):
            if self.tree.get_command(command.name) is not None:
                raise RuntimeError(f"최상위 명령어 이름이 중복됩니다: /{command.name}")
            group.remove_command(command.name)
            command.parent = None
            self.tree.add_command(command)

        LOGGER.info("질문·검색 명령어를 최상위 명령어로 변경 완료")

    def _install_concise_help(self) -> None:
        self.tree.remove_command("도움말")

        @app_commands.command(name="도움말", description="자주 쓰는 명령어를 한눈에 확인합니다.")
        async def concise_help(interaction: discord.Interaction) -> None:
            embed = discord.Embed(
                title="🌌 Milkway Bot 명령어",
                description="`/`를 입력한 뒤 아래 이름을 선택하세요.",
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="🎓 학교",
                value=(
                    "`/학교 오늘` `/학교 학점` `/학교 집중`\n"
                    "`/과제 추가|목록|완료|삭제`\n"
                    "`/시험 추가|목록|삭제`\n"
                    "`/시간표 추가|오늘|전체|삭제`"
                ),
                inline=False,
            )
            embed.add_field(
                name="💬 질문·검색",
                value="`/질문` `/검색` `/요약` `/퀴즈` `/상태`",
                inline=False,
            )
            embed.add_field(
                name="⏰ 알림·예약",
                value=(
                    "`/알림 후에|날짜|목록|삭제`\n"
                    "`/예약 반복|매일|매주|한번|목록|삭제`"
                ),
                inline=False,
            )
            embed.add_field(
                name="📢 전송·설정",
                value=(
                    "`/전송` `/공지` `/투표`\n"
                    "`/설정 시간대|환영|퇴장|역할|로그|끄기|확인`"
                ),
                inline=False,
            )
            embed.add_field(
                name="🛡️ 관리",
                value=(
                    "`/관리 정리|제한|제한해제|추방|차단|차단해제`\n"
                    "`/관리 슬로우|경고|경고목록|경고초기화`"
                ),
                inline=False,
            )
            embed.add_field(
                name="🧰 기타",
                value="`/핑` `/초대` `/서버` `/사용자` `/아바타` `/선택` `/주사위` `/동전` `/시간`",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        self.tree.add_command(concise_help, override=True)

    async def close(self) -> None:
        await self.ai.close()
        await self.db.close()
        await super().close()

    async def setup_hook(self) -> None:
        await self.db.initialize()
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        self._simplify_command_names()
        self._flatten_question_commands()
        self._install_concise_help()

        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info("개발 서버 %s에 간단 명령어 %s개 동기화", guild.id, len(synced))

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

        if desired is None:
            LOGGER.info("BOT_DISPLAY_NAME 미설정: 현재 Discord 봇 이름 유지")
            return

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
            LOGGER.info(
                "AI 공급자: %s | 일반 모델: %s | 검색 모델: %s",
                self.ai.provider_name,
                self.ai.active_model,
                self.ai.active_search_model,
            )
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="/도움말 | 간단 명령어",
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
