from __future__ import annotations

import discord
from discord import app_commands


def _send_permission_name(channel: discord.abc.GuildChannel | discord.Thread) -> str:
    return "send_messages_in_threads" if isinstance(channel, discord.Thread) else "send_messages"


def ensure_user_can_send(
    interaction: discord.Interaction,
    channel: discord.abc.GuildChannel | discord.Thread,
) -> None:
    member = interaction.user
    if not isinstance(member, discord.Member):
        raise app_commands.NoPrivateMessage

    permissions = channel.permissions_for(member)
    send_permission = _send_permission_name(channel)
    missing = [
        name
        for name in ("view_channel", send_permission)
        if not getattr(permissions, name, False)
    ]
    if missing:
        raise app_commands.MissingPermissions(missing)


def ensure_bot_channel_permissions(
    interaction: discord.Interaction,
    channel: discord.abc.GuildChannel | discord.Thread,
    *,
    embed_links: bool = False,
    add_reactions: bool = False,
    read_message_history: bool = False,
) -> None:
    bot_member = interaction.guild.me if interaction.guild else None
    if bot_member is None:
        raise app_commands.BotMissingPermissions(["view_channel"])

    permissions = channel.permissions_for(bot_member)
    required = ["view_channel", _send_permission_name(channel)]
    if embed_links:
        required.append("embed_links")
    if add_reactions:
        required.append("add_reactions")
    if read_message_history:
        required.append("read_message_history")

    missing = [name for name in required if not getattr(permissions, name, False)]
    if missing:
        raise app_commands.BotMissingPermissions(missing)
