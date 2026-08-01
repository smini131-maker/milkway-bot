from __future__ import annotations

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.services.ai_service import AIRequestError, AIUnavailableError
from discord_bot.utils.timeparse import get_timezone, utc_now

_BASE_INSTRUCTIONS = """
당신은 대한민국 대학생이 Discord에서 사용하는 학습·검색 보조 AI입니다.
항상 사용자가 입력한 언어로 답하고, 한국어 요청에는 자연스러운 한국어를 사용하세요.
핵심부터 말하고 Discord에서 읽기 좋은 짧은 문단과 목록을 사용하세요.
사실을 모르면 추측하거나 출처를 꾸며내지 말고 불확실하다고 밝히세요.
개인정보, 비밀번호, 토큰, 학번 등 민감정보를 요구하지 마세요.
""".strip()


def _split_message(text: str, limit: int = 1900) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return ["AI가 빈 응답을 반환했습니다."]
    chunks: list[str] = []
    while len(cleaned) > limit:
        split_at = cleaned.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = cleaned.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(cleaned[:split_at].rstrip())
        cleaned = cleaned[split_at:].lstrip()
    if cleaned:
        chunks.append(cleaned)
    return chunks


class AICog(
    commands.GroupCog,
    group_name="인공지능",
    group_description="무료 AI 질문·검색·요약·퀴즈 기능입니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    async def _usage_date(self, interaction: discord.Interaction) -> str:
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        return utc_now().astimezone(get_timezone(timezone_name)).date().isoformat()

    async def _generate(
        self,
        interaction: discord.Interaction,
        *,
        prompt: str,
        instructions: str,
        public: bool,
        max_output_tokens: int | None = None,
        use_search: bool = False,
    ) -> None:
        usage_date = await self._usage_date(interaction)
        limit = self.bot.settings.ai_daily_user_limit
        allowed, used = await self.bot.db.consume_ai_quota(
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            usage_date=usage_date,
            limit=limit,
        )
        if not allowed:
            message = f"오늘 AI 사용 한도 `{used}/{limit}`를 모두 사용했습니다."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
            return

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True, ephemeral=not public)
        try:
            result = await self.bot.ai.generate(
                prompt=prompt,
                instructions=f"{_BASE_INSTRUCTIONS}\n\n{instructions.strip()}",
                max_output_tokens=max_output_tokens,
                use_search=use_search,
            )
        except (AIUnavailableError, AIRequestError, ValueError) as exc:
            await self.bot.db.refund_ai_quota(
                user_id=interaction.user.id,
                guild_id=interaction.guild_id,
                usage_date=usage_date,
            )
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        except Exception:
            await self.bot.db.refund_ai_quota(
                user_id=interaction.user.id,
                guild_id=interaction.guild_id,
                usage_date=usage_date,
            )
            raise

        for index, chunk in enumerate(_split_message(result.text)):
            await interaction.followup.send(
                ("🤖 " if index == 0 else "") + chunk,
                ephemeral=not public,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if result.sources:
            source_lines = []
            for index, source in enumerate(result.sources, start=1):
                title = source.title.replace("[", "").replace("]", "")[:120]
                source_lines.append(f"{index}. [{title}]({source.url})")
            await interaction.followup.send(
                "🔎 **검색 출처**\n" + "\n".join(source_lines),
                ephemeral=not public,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @app_commands.command(name="질문", description="AI에게 일반 질문을 합니다.")
    @app_commands.rename(question="내용", public="공개")
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str,
        public: bool = False,
    ) -> None:
        await self._generate(
            interaction,
            prompt=question,
            instructions=(
                "질문에 직접 답한 뒤 필요한 경우 예시를 덧붙이세요. "
                "수학·과학 문제는 핵심 풀이 과정도 설명하세요."
            ),
            public=public,
        )

    @app_commands.command(name="검색", description="웹 검색으로 최신 정보를 찾아 출처와 함께 답합니다.")
    @app_commands.rename(query="검색어", public="공개")
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        public: bool = False,
    ) -> None:
        today = await self._usage_date(interaction)
        await self._generate(
            interaction,
            prompt=query,
            instructions=(
                f"현재 날짜는 {today}입니다. 웹 검색 결과를 바탕으로 최신 정보를 정확하게 정리하세요. "
                "날짜·수치·고유명사를 확인하고 검색에서 확인되지 않는 내용은 추측하지 마세요."
            ),
            public=public,
            use_search=True,
        )

    @app_commands.command(name="요약", description="긴 글이나 강의 노트를 간단히 요약합니다.")
    @app_commands.rename(text="내용", style="방식", public="공개")
    async def summarize(
        self,
        interaction: discord.Interaction,
        text: str,
        style: Literal["핵심", "시험대비", "발표", "회의록"] = "핵심",
        public: bool = False,
    ) -> None:
        instructions = {
            "핵심": "핵심 주장, 근거, 결론을 짧게 정리하세요.",
            "시험대비": "중요 개념, 정의, 비교점, 암기 포인트를 정리하세요.",
            "발표": "도입-핵심-결론 순서와 발표용 문장으로 정리하세요.",
            "회의록": "결정사항, 할 일, 담당자, 기한, 미해결 질문을 구분하세요.",
        }[style]
        await self._generate(
            interaction,
            prompt=text,
            instructions=instructions,
            public=public,
        )

    @app_commands.command(name="퀴즈", description="강의 자료로 복습 문제와 해설을 만듭니다.")
    @app_commands.rename(material="자료", count="문제수", difficulty="난이도", public="공개")
    async def quiz(
        self,
        interaction: discord.Interaction,
        material: str,
        count: app_commands.Range[int, 3, 10] = 5,
        difficulty: Literal["쉬움", "보통", "어려움"] = "보통",
        public: bool = False,
    ) -> None:
        await self._generate(
            interaction,
            prompt=material,
            instructions=(
                f"제공된 자료 안에서 {difficulty} 난이도 문제 {count}개를 만드세요. "
                "문제를 먼저 제시하고 그 아래에 정답과 짧은 해설을 제시하세요."
            ),
            public=public,
            max_output_tokens=min(2600, 500 + count * 180),
        )

    @app_commands.command(name="사용량", description="AI 연결 상태와 오늘 사용량을 확인합니다.")
    async def usage(self, interaction: discord.Interaction) -> None:
        usage_date = await self._usage_date(interaction)
        used = await self.bot.db.ai_usage_count(
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            usage_date=usage_date,
        )
        limit = self.bot.settings.ai_daily_user_limit
        status = "활성화" if self.bot.ai.available else "비활성화"
        quota = "봇 내부 제한 없음" if limit == 0 else f"{used}/{limit}회 사용"
        await interaction.response.send_message(
            f"AI 상태: **{status}**\n"
            f"공급자: **{self.bot.ai.provider_name}**\n"
            f"일반 모델: `{self.bot.ai.active_model}`\n"
            f"검색 모델: `{self.bot.ai.active_search_model}`\n"
            f"오늘: `{quota}`\n"
            "각 공급자의 무료 분당·일일 한도는 별도로 적용됩니다.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AICog(bot))
