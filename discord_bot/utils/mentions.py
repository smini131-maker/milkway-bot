from __future__ import annotations

from dataclasses import dataclass

import discord
from discord import app_commands


@dataclass(frozen=True, slots=True)
class MentionSpec:
    kind: str = "none"
    target_id: int | None = None


def resolve_mention(
    role: discord.Role | None = None,
    user: discord.Member | discord.User | None = None,
    ping_everyone: bool = False,
    ping_here: bool = False,
) -> MentionSpec:
    choices = [role is not None, user is not None, ping_everyone, ping_here]
    if sum(choices) > 1:
        raise ValueError("맨션 대상은 역할, 사용자, @everyone, @here 중 하나만 선택하세요.")
    if role is not None:
        return MentionSpec("role", role.id)
    if user is not None:
        return MentionSpec("user", user.id)
    if ping_everyone:
        return MentionSpec("everyone")
    if ping_here:
        return MentionSpec("here")
    return MentionSpec()


def ensure_mention_permissions(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    *,
    role: discord.Role | None = None,
    ping_everyone: bool = False,
    ping_here: bool = False,
) -> None:
    """Prevent commands from bypassing Discord's mention-everyone permission."""
    requires_elevated_permission = ping_everyone or ping_here or (
        role is not None and not role.mentionable
    )
    if not requires_elevated_permission:
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        raise app_commands.NoPrivateMessage

    if not channel.permissions_for(member).mention_everyone:
        raise app_commands.MissingPermissions(["mention_everyone"])

    bot_member = interaction.guild.me if interaction.guild else None
    if bot_member is None or not channel.permissions_for(bot_member).mention_everyone:
        raise app_commands.BotMissingPermissions(["mention_everyone"])


def render_message(message: str, spec: MentionSpec) -> tuple[str, discord.AllowedMentions]:
    if spec.kind == "role" and spec.target_id:
        return (
            f"<@&{spec.target_id}> {message}",
            discord.AllowedMentions(everyone=False, roles=[discord.Object(spec.target_id)], users=False),
        )
    if spec.kind == "user" and spec.target_id:
        return (
            f"<@{spec.target_id}> {message}",
            discord.AllowedMentions(everyone=False, roles=False, users=[discord.Object(spec.target_id)]),
        )
    if spec.kind == "everyone":
        return f"@everyone {message}", discord.AllowedMentions(everyone=True, roles=False, users=False)
    if spec.kind == "here":
        return f"@here {message}", discord.AllowedMentions(everyone=True, roles=False, users=False)
    return message, discord.AllowedMentions.none()
