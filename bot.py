import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os
import asyncio

# =========================================================
# 1. BOT SETTINGS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="",
    intents=intents,
    case_insensitive=True
)

RESTRICTED_COLOR_USERS = set()

# =========================================================
# 2. IDS
# =========================================================

WELCOME_CHANNEL_ID = 863844473851215893

SERVER_LOG_ID = 863857583146926090
CHAT_LOG_ID = 863857498719780874
VOICE_LOG_ID = 863857530941341718
BAN_LOG_ID = 867084771477553183
LEFT_LOG_ID = 863857555948175381
CHANNEL_LOG_ID = 867085144061771806
ROLE_LOG_ID = 867085174662889503
MEMBER_LOG_ID = 867085715787612220
NICKNAME_LOG_ID = 867085807445213215

ROLE_BARXAKAN = 864962613582102560
ROLE_MSHAXOR = 863850042123878421

REGRI_ALLOWED_ROLES = {
    1548633166531530802,
    865587893568274482,
    863846779921629216
}

# =========================================================
# 3. LOG HELPERS
# =========================================================

def get_log_channel(channel_id):
    return bot.get_channel(channel_id)

async def send_log(channel_id, embed):
    try:
        channel = get_log_channel(channel_id)
        if channel is None:
            return
        await channel.send(embed=embed)
    except Exception:
        pass

def make_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_footer(text="Karezma Logs")
    return embed

def add_user_thumbnail(embed, user):
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass

# =========================================================
# 4. AUDIT LOG HELPER
# =========================================================

async def get_audit_executor(guild, action, target_id=None, delay=1.0):
    try:
        await asyncio.sleep(delay)

        async for entry in guild.audit_logs(
            limit=10,
            action=action
        ):
            if target_id is not None:
                if (
                    entry.target is None
                    or getattr(entry.target, "id", None) != target_id
                ):
                    continue

            if entry.created_at:
                now = datetime.datetime.now(
                    datetime.timezone.utc
                )

                if (
                    now - entry.created_at
                ).total_seconds() > 15:
                    continue

            return entry

    except Exception:
        pass

    return None

# =========================================================
# 5. READY
# =========================================================

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception:
        pass

    # =====================================================
    # MUTED PERMISSION SYNC AFTER BOT STARTS
    # =====================================================

    for guild in bot.guilds:
        try:
            mute_role = discord.utils.get(
                guild.roles,
                name="Muted"
            )

            if mute_role:
                await sync_muted_permissions(
                    guild,
                    mute_role
                )

        except Exception:
            pass

    print(
        f"بۆتەکە بە سەرکەوتوویی چالاک بوو وەک: {bot.user}"
    )

# =========================================================
# 6. WELCOME
# =========================================================

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(
        WELCOME_CHANNEL_ID
    )

    if channel:
        try:
            embed = discord.Embed(
                title="WELCOME",
                description=(
                    f"{member.mention}\n"
                    f"axer beyt bo karezma"
                )
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(
                embed=embed
            )

        except Exception:
            pass

    embed = make_embed(
        "📥 Member Joined",
        f"**Member:** {member.mention}\n"
        f"**Username:** `{member}`\n"
        f"**ID:** `{member.id}`",
        discord.Color.green()
    )

    add_user_thumbnail(
        embed,
        member
    )

    await send_log(
        MEMBER_LOG_ID,
        embed
    )

# =========================================================
# 7. MEMBER LEFT
# =========================================================

@bot.event
async def on_member_remove(member):
    embed = make_embed(
        "📤 Member Left",
        f"**Member:** {member.mention}\n"
        f"**Username:** `{member}`\n"
        f"**ID:** `{member.id}`",
        discord.Color.red()
    )

    add_user_thumbnail(
        embed,
        member
    )

    await send_log(
        LEFT_LOG_ID,
        embed
    )

# =========================================================
# 8. MEMBER UPDATE
# =========================================================

@bot.event
async def on_member_update(before, after):

    if before.nick != after.nick:

        old_nick = (
            before.nick
            if before.nick
            else before.name
        )

        new_nick = (
            after.nick
            if after.nick
            else after.name
        )

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.member_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown / Self"
        )

        embed = make_embed(
            "✏️ Nickname Changed",
            f"**Member:** {after.mention}\n"
            f"**Changed By:** {editor}\n"
            f"**Before:** `{old_nick}`\n"
            f"**After:** `{new_nick}`",
            discord.Color.gold()
        )

        add_user_thumbnail(
            embed,
            after
        )

        await send_log(
            NICKNAME_LOG_ID,
            embed
        )

    before_roles = set(before.roles)
    after_roles = set(after.roles)

    added_roles = after_roles - before_roles
    removed_roles = before_roles - after_roles

    real_added_roles = [
        role
        for role in added_roles
        if role.name not in ["@everyone", "Muted"]
    ]

    if real_added_roles:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.member_role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        roles_text = "\n".join(
            f"➕ {role.mention}"
            for role in real_added_roles
        )

        embed = make_embed(
            "➕ Role Added",
            f"**Member:** {after.mention}\n"
            f"**Given By:** {editor}\n\n"
            f"{roles_text}",
            discord.Color.green()
        )

        add_user_thumbnail(
            embed,
            after
        )

        await send_log(
            MEMBER_LOG_ID,
            embed
        )

    real_removed_roles = [
        role
        for role in removed_roles
        if role.name not in ["@everyone", "Muted"]
    ]

    if real_removed_roles:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.member_role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        roles_text = "\n".join(
            f"➖ {role.mention}"
            for role in real_removed_roles
        )

        embed = make_embed(
            "➖ Role Removed",
            f"**Member:** {after.mention}\n"
            f"**Removed By:** {editor}\n\n"
            f"{roles_text}",
            discord.Color.red()
        )

        add_user_thumbnail(
            embed,
            after
        )

        await send_log(
            MEMBER_LOG_ID,
            embed
        )

# =========================================================
# 9. GET TARGET FROM TAG OR REPLY
# =========================================================

async def get_target_member(message):

    if message.mentions:
        member = message.mentions[0]

        if isinstance(
            member,
            discord.Member
        ):
            return member

    if message.reference:
        try:
            referenced_message = (
                await message.channel.fetch_message(
                    message.reference.message_id
                )
            )

            if isinstance(
                referenced_message.author,
                discord.Member
            ):
                return referenced_message.author

            return message.guild.get_member(
                referenced_message.author.id
            )

        except Exception:
            pass

    return None

# =========================================================
# 10. MUTED ROLE
# =========================================================

async def apply_muted_permissions(
    channel,
    mute_role
):
    try:

        if isinstance(
            channel,
            (
                discord.TextChannel,
                discord.NewsChannel,
                discord.ForumChannel
            )
        ):

            await channel.set_permissions(
                mute_role,

                send_messages=False,
                add_reactions=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,

                reason="Karezma Muted role - block chat"
            )

    except discord.Forbidden:
        pass

    except Exception:
        pass


async def sync_muted_permissions(
    guild,
    mute_role
):
    for channel in guild.channels:
        await apply_muted_permissions(
            channel,
            mute_role
        )


async def get_or_create_muted_role(guild):

    mute_role = discord.utils.get(
        guild.roles,
        name="Muted"
    )

    if not mute_role:
        mute_role = await guild.create_role(
            name="Muted",
            reason="Karezma mute role"
        )

    await sync_muted_permissions(
        guild,
        mute_role
    )

    return mute_role

# =========================================================
# 11 & 12. CHANNEL CREATE LOG
# =========================================================

@bot.event
async def on_guild_channel_create(channel):

    try:

        mute_role = discord.utils.get(
            channel.guild.roles,
            name="Muted"
        )

        if mute_role:
            await apply_muted_permissions(
                channel,
                mute_role
            )

        entry = await get_audit_executor(
            channel.guild,
            discord.AuditLogAction.channel_create,
            channel.id
        )

        creator = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "📁 Channel Created",
            f"**Channel:** {channel.mention}\n"
            f"**Name:** `{channel.name}`\n"
            f"**ID:** `{channel.id}`\n"
            f"**Type:** `{channel.type}`\n"
            f"**Created By:** {creator}",
            discord.Color.green()
        )

        await send_log(
            CHANNEL_LOG_ID,
            embed
        )

    except Exception:
        pass

# =========================================================
# 13. CHANNEL DELETE LOG
# =========================================================

@bot.event
async def on_guild_channel_delete(channel):

    entry = await get_audit_executor(
        channel.guild,
        discord.AuditLogAction.channel_delete,
        channel.id
    )

    deleter = (
        entry.user.mention
        if entry and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "🗑️ Channel Deleted",
        f"**Channel:** `#{channel.name}`\n"
        f"**ID:** `{channel.id}`\n"
        f"**Type:** `{channel.type}`\n"
        f"**Deleted By:** {deleter}",
        discord.Color.red()
    )

    await send_log(
        CHANNEL_LOG_ID,
        embed
    )

# =========================================================
# 14. CHANNEL UPDATE LOG
# =========================================================

@bot.event
async def on_guild_channel_update(
    before,
    after
):

    if before.category != after.category:

        try:
            mute_role = discord.utils.get(
                after.guild.roles,
                name="Muted"
            )

            if mute_role:
                await apply_muted_permissions(
                    after,
                    mute_role
                )

        except Exception:
            pass

    changes = []

    if before.name != after.name:
        changes.append(
            f"**Name:** `{before.name}` → `{after.name}`"
        )

    if before.category != after.category:

        old_category = (
            before.category.name
            if before.category
            else "None"
        )

        new_category = (
            after.category.name
            if after.category
            else "None"
        )

        changes.append(
            f"**Category:** `{old_category}` → `{new_category}`"
        )

    if before.position != after.position:

        changes.append(
            f"**Position:** `{before.position}` → `{after.position}`"
        )

    if changes:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.channel_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "✏ Channel Updated",
            f"**Channel:** {after.mention}\n"
            f"**ID:** `{after.id}`\n"
            f"**Updated By:** {editor}\n\n"
            + "\n".join(changes),
            discord.Color.gold()
        )

        await send_log(
            CHANNEL_LOG_ID,
            embed
        )

# =========================================================
# 15. ROLE CREATE
# =========================================================

@bot.event
async def on_guild_role_create(role):

    if role.name == "Muted":
        return

    entry = await get_audit_executor(
        role.guild,
        discord.AuditLogAction.role_create,
        role.id
    )

    creator = (
        entry.user.mention
        if entry and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "➕ Role Created",
        f"**Role:** {role.mention}\n"
        f"**Name:** `{role.name}`\n"
        f"**ID:** `{role.id}`\n"
        f"**Created By:** {creator}",
        discord.Color.green()
    )

    await send_log(
        ROLE_LOG_ID,
        embed
    )

# =========================================================
# 16. ROLE DELETE
# =========================================================

@bot.event
async def on_guild_role_delete(role):

    if role.name == "Muted":
        return

    entry = await get_audit_executor(
        role.guild,
        discord.AuditLogAction.role_delete,
        role.id
    )

    deleter = (
        entry.user.mention
        if entry and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "🗑️ Role Deleted",
        f"**Role:** `{role.name}`\n"
        f"**ID:** `{role.id}`\n"
        f"**Deleted By:** {deleter}",
        discord.Color.red()
    )

    await send_log(
        ROLE_LOG_ID,
        embed
    )

# =========================================================
# 17. ROLE UPDATE
# =========================================================

@bot.event
async def on_guild_role_update(
    before,
    after
):

    if after.name == "Muted":
        return

    changes = []

    if before.name != after.name:
        changes.append(
            f"**Name:** `{before.name}` → `{after.name}`"
        )

    if before.color != after.color:
        changes.append(
            f"**Color:** `{before.color}` → `{after.color}`"
        )

    if before.position != after.position:
        changes.append(
            f"**Position:** `{before.position}` → `{after.position}`"
        )

    if changes:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "✏️ Role Updated",
            f"**Role:** {after.mention}\n"
            f"**ID:** `{after.id}`\n"
            f"**Updated By:** {editor}\n\n"
            + "\n".join(changes),
            discord.Color.gold()
        )

        await send_log(
            ROLE_LOG_ID,
            embed
        )

# =========================================================
# 18. VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    if (
        before.channel is None
        and after.channel is not None
    ):

        embed = make_embed(
            "🔊 Voice Join",
            f"**Member:** {member.mention}\n"
            f"**Channel:** {after.channel.mention}",
            discord.Color.green()
        )

        add_user_thumbnail(
            embed,
            member
        )

        await send_log(
            VOICE_LOG_ID,
            embed
        )

        return

    if (
        before.channel is not None
        and after.channel is None
    ):

        embed = make_embed(
            "🔇 Voice Leave",
            f"**Member:** {member.mention}\n"
            f"**Channel:** `{before.channel.name}`",
            discord.Color.red()
        )

        add_user_thumbnail(
            embed,
            member
        )

        await send_log(
            VOICE_LOG_ID,
            embed
        )

        return

    if (
        before.channel is not None
        and after.channel is not None
        and before.channel.id != after.channel.id
    ):

        embed = make_embed(
            "🔀 Voice Move",
            f"**Member:** {member.mention}\n"
            f"**From:** `{before.channel.name}`\n"
            f"**To:** `{after.channel.name}`",
            discord.Color.gold()
        )

        add_user_thumbnail(
            embed,
            member
        )

        await send_log(
            VOICE_LOG_ID,
            embed
        )

# =========================================================
# 19 & 20. BAN / UNBAN LOG
# =========================================================

@bot.event
async def on_member_ban(
    guild,
    user
):

    entry = await get_audit_executor(
        guild,
        discord.AuditLogAction.ban,
        user.id
    )

    admin_text = (
        entry.user.mention
        if entry and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "🔨 Member Banned",
        f"**Member:** {user.mention}\n"
        f"**Banned By:** {admin_text}",
        discord.Color.red()
    )

    add_user_thumbnail(
        embed,
        user
    )

    await send_log(
        BAN_LOG_ID,
        embed
    )


@bot.event
async def on_member_unban(
    guild,
    user
):

    entry = await get_audit_executor(
        guild,
        discord.AuditLogAction.unban,
        user.id
    )

    admin_text = (
        entry.user.mention
        if entry and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "♻ Member Unbanned",
        f"**Member:** {user.mention}\n"
        f"**Unbanned By:** {admin_text}",
        discord.Color.green()
    )

    add_user_thumbnail(
        embed,
        user
    )

    await send_log(
        BAN_LOG_ID,
        embed
    )

# =========================================================
# 21. SERVER UPDATE
# =========================================================

@bot.event
async def on_guild_update(
    before,
    after
):

    changes = []

    if before.name != after.name:
        changes.append(
            f"**Server Name:** `{before.name}` → `{after.name}`"
        )

    if changes:

        entry = await get_audit_executor(
            after,
            discord.AuditLogAction.guild_update
        )

        editor = (
            entry.user.mention
            if entry and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "⚙ Server Updated",
            f"**Updated By:** {editor}\n\n"
            + "\n".join(changes),
            discord.Color.gold()
        )

        if after.icon:
            embed.set_thumbnail(
                url=after.icon.url
            )

        await send_log(
            SERVER_LOG_ID,
            embed
        )

# =========================================================
# 22 & 23. MESSAGE DELETE / EDIT
# =========================================================

@bot.event
async def on_message_delete(message):

    if (
        message.author.bot
        or message.guild is None
    ):
        return

    content = (
        message.content[:1500]
        if message.content
        else "*No text content*"
    )

    embed = make_embed(
        "🗑️ Message Deleted",
        f"**Author:** {message.author.mention}\n"
        f"**Channel:** {message.channel.mention}\n\n"
        f"**Message:**\n```text\n"
        f"{content}\n"
        f"```",
        discord.Color.red()
    )

    add_user_thumbnail(
        embed,
        message.author
    )

    await send_log(
        CHAT_LOG_ID,
        embed
    )


@bot.event
async def on_message_edit(
    before,
    after
):

    if (
        before.author.bot
        or before.guild is None
        or before.content == after.content
    ):
        return

    old_content = (
        before.content[:700]
        if before.content
        else "*Empty*"
    )

    new_content = (
        after.content[:700]
        if after.content
        else "*Empty*"
    )

    embed = make_embed(
        "✏️ Message Edited",
        f"**Author:** {after.author.mention}\n"
        f"**Before:**\n```text\n"
        f"{old_content}\n"
        f"```\n"
        f"**After:**\n```text\n"
        f"{new_content}\n"
        f"```",
        discord.Color.gold()
    )

    add_user_thumbnail(
        embed,
        after.author
    )

    await send_log(
        CHAT_LOG_ID,
        embed
    )

# =========================================================
# 24. MAIN COMMAND SYSTEM
# =========================================================

@bot.event
async def on_message(message):

    if (
        message.author.bot
        or message.guild is None
    ):
        return

    mute_role = discord.utils.get(
        message.guild.roles,
        name="Muted"
    )

    if (
        mute_role
        and mute_role in message.author.roles
        and not message.author.guild_permissions.administrator
    ):

        try:
            await message.delete()
        except Exception:
            pass

        return

    content = message.content.strip()

    if not content:
        return

    parts = content.split()
    command = parts[0].lower()

    if command == "safika":

        if not message.author.guild_permissions.administrator:
            return

        if (
            len(parts) >= 2
            and parts[1].isdigit()
        ):

            amount = min(
                int(parts[1]),
                1000
            )

            try:
                deleted = await message.channel.purge(
                    limit=amount + 1
                )

                await message.channel.send(
                    f"✅ `{len(deleted)}` نامە سڕایەوە.",
                    delete_after=3
                )
            except Exception:
                pass

        return

    if command == "mute":

        if not message.author.guild_permissions.administrator:
            return

        target = await get_target_member(
            message
        )

        if target:

            try:
                mute_role = await get_or_create_muted_role(
                    message.guild
                )

                if mute_role not in target.roles:
                    await target.add_roles(
                        mute_role,
                        reason=f"Muted by {message.author}"
                    )

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    f"damt daxaa {target.mention}",
                    delete_after=2
                )
            except Exception:
                pass

        return

    if command == "unmute":

        if not message.author.guild_permissions.administrator:
            return

        target = await get_target_member(
            message
        )

        if target:

            try:
                mute_role = discord.utils.get(
                    message.guild.roles,
                    name="Muted"
                )

                if (
                    mute_role
                    and mute_role in target.roles
                ):
                    await target.remove_roles(
                        mute_role
                    )

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    f"xwa xerm bnwse dllm basha aqllba amjara {target.mention}",
                    delete_after=2
                )
            except Exception:
                pass

        return

    if command == "bfra":

        if not message.author.guild_permissions.administrator:
            return

        target = await get_target_member(
            message
        )

        if target:

            try:
                await target.ban()

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    f"✈️ Frenra {target.mention}",
                    delete_after=2
                )
            except Exception:
                pass

        return

    if command == "unban":

        if not message.author.guild_permissions.administrator:
            return

        if (
            len(parts) >= 2
            and parts[1].isdigit()
        ):

            try:
                user = await bot.fetch_user(
                    int(parts[1])
                )

                await message.guild.unban(
                    user
                )

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    "✅ Unban کرا.",
                    delete_after=3
                )
            except Exception:
                pass

        return

    if command == "lock":

        if not message.author.guild_permissions.manage_channels:
            return

        try:
            await message.channel.set_permissions(
                message.guild.default_role,
                send_messages=False
            )

            try:
                await message.delete()
            except Exception:
                pass

            await message.channel.send(
                "🔒 کەناڵەکە Lock کرا.",
                delete_after=3
            )
        except Exception:
            pass

        return

    if command == "unlock":

        if not message.author.guild_permissions.manage_channels:
            return

        try:
            await message.channel.set_permissions(
                message.guild.default_role,
                send_messages=None
            )

            try:
                await message.delete()
            except Exception:
                pass

            await message.channel.send(
                "🔓 کەناڵەکە Unlock کرا.",
                delete_after=3
            )
        except Exception:
            pass

        return

# =========================================================
# 25. SLASH COMMANDS
# =========================================================

# STAFF
@bot.tree.command(
    name="staff",
    description="پێدانی ڕۆڵی ستاف بە ئەندام"
)
@app_commands.choices(
    role_choice=[
        app_commands.Choice(
            name="Barxakan🐑",
            value="barxakan"
        ),
        app_commands.Choice(
            name="mshaxor",
            value="mshaxor"
        )
    ]
)
async def staff(
    interaction: discord.Interaction,
    member: discord.Member,
    role_choice: str
):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ تەنها ئەدیمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.",
            ephemeral=True
        )
        return

    try:
        role_id = (
            ROLE_BARXAKAN
            if role_choice == "barxakan"
            else ROLE_MSHAXOR
        )

        role = interaction.guild.get_role(
            role_id
        )

        if not role:
            await interaction.response.send_message(
                "❌ ڕۆڵەکە لە سەرۆکایەتی نەدۆزرایەوە!",
                ephemeral=True
            )
            return

        if role in member.roles:
            await interaction.response.send_message(
                f"⚠️️ {member.mention} پێشتر ئەم ڕۆڵەی هەیە (`{role.name}`).",
                ephemeral=True
            )
        else:
            await member.add_roles(
                role,
                reason=f"Staff given by {interaction.user}"
            )
            await interaction.response.send_message(
                f"✅ ڕۆڵی **{role.name}** بە سەرکەوتوویی درا بە {member.mention}",
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ کێشەیەک ڕوویدا: {e}",
            ephemeral=True
        )

# COLOR ROLE
class ColorRoleSelect(discord.ui.Select):
    def __init__(self, roles_data):
        options = [
            discord.SelectOption(
                label=f"{role.name} [{status}]",
                value=str(role.id)
            )
            for role, status in roles_data[:25]
        ]
        super().__init__(
            placeholder="ڕۆڵێک هەڵبژێرە بۆ گۆڕینی ڕەنگ...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id in RESTRICTED_COLOR_USERS:
            await interaction.response.send_message(
                "❌ قەدەغە کراوەی!",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            int(self.values[0])
        )

        if role:
            await interaction.response.send_modal(
                ColorModal(role)
            )


class ColorModal(discord.ui.Modal, title="گۆڕینی ڕەنگی ڕۆڵ"):
    color_input = discord.ui.TextInput(
        label="کۆدی ڕەنگ (#FF0000)",
        placeholder="#HEX",
        required=True,
        max_length=7
    )

    def __init__(self, role):
        super().__init__()
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_obj = discord.Color(
                int(
                    self.color_input.value
                    .strip()
                    .lstrip('#'),
                    16
                )
            )

            await self.role.edit(
                color=color_obj
            )

            await interaction.response.send_message(
                "✅ ڕەنگەکە گۆڕدرا!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ هەڵە: {e}",
                ephemeral=True
            )


@bot.tree.command(
    name="rangirole",
    description="گۆڕینی ڕەنگی ڕۆڵەکان"
)
async def rangirole(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ تەنها ئەدیمین.",
            ephemeral=True
        )
        return

    roles_data = [
        (r, "Normal")
        for r in interaction.guild.roles
        if r.name != "@everyone"
    ]

    view = discord.ui.View()
    view.add_item(ColorRoleSelect(roles_data))

    await interaction.response.send_message(
        "🎨 **ڕۆڵێک هەڵبژێرە:**",
        view=view,
        ephemeral=True
    )


@bot.tree.command(
    name="regri",
    description="قەدەغەکردنی گۆڕینی ڕەنگ"
)
async def regri(
    interaction: discord.Interaction,
    member: discord.Member,
    action: str
):
    if not (
        interaction.guild.owner_id == interaction.user.id
        or any(
            r.id in REGRI_ALLOWED_ROLES
            for r in interaction.user.roles
        )
    ):
        await interaction.response.send_message(
            "❌ دەسەڵاتت نییە.",
            ephemeral=True
        )
        return

    if action.lower() in ["add", "ban"]:
        RESTRICTED_COLOR_USERS.add(member.id)
        await interaction.response.send_message(
            f"🚫 قەدەغەکرا {member.mention}",
            ephemeral=True
        )
    else:
        RESTRICTED_COLOR_USERS.discard(member.id)
        await interaction.response.send_message(
            f"✅ ڕێگەدرا بە {member.mention}",
            ephemeral=True
        )

# =========================================================
# 26. RUN BOT
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
