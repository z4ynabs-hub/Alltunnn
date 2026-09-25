import discord
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


# =========================================================
# 2. IDs
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


# =========================================================
# 3. LOG HELPERS
# =========================================================

def get_log_channel(channel_id):
    return bot.get_channel(channel_id)


async def send_log(channel_id, embed):
    try:
        channel = get_log_channel(channel_id)

        if channel is None:
            print(f"❌ Log channel not found: {channel_id}")
            return

        await channel.send(embed=embed)

    except discord.Forbidden:
        print(f"❌ No permission to send log: {channel_id}")

    except Exception as e:
        print(f"❌ Log error {channel_id}: {e}")


def make_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.set_footer(
        text="Karezma Logs"
    )

    return embed


def add_user_thumbnail(embed, user):
    try:
        embed.set_thumbnail(
            url=user.display_avatar.url
        )
    except Exception:
        pass


# =========================================================
# 4. AUDIT LOG HELPER
# =========================================================

async def get_audit_executor(
    guild,
    action,
    target_id=None,
    delay=1.0
):

    try:

        await asyncio.sleep(delay)

        async for entry in guild.audit_logs(
            limit=10,
            action=action
        ):

            if target_id is not None:

                if entry.target is None:
                    continue

                if getattr(
                    entry.target,
                    "id",
                    None
                ) != target_id:

                    continue

            if entry.created_at:

                now = datetime.datetime.now(
                    datetime.timezone.utc
                )

                difference = (
                    now - entry.created_at
                ).total_seconds()

                if difference > 10:
                    continue

            return entry

    except discord.Forbidden:
        print("❌ Bot cannot read Audit Log.")

    except Exception as e:
        print(f"Audit log error: {e}")

    return None


# =========================================================
# 5. READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"بۆتەکە بە سەرکەوتوویی چالاک بوو وەک: {bot.user}"
    )

    print(
        f"Bot ID: {bot.user.id}"
    )

    embed = make_embed(
        "🟢 BOT ONLINE",
        f"**Bot:** {bot.user.mention}\n"
        f"**ID:** `{bot.user.id}`",
        discord.Color.green()
    )

    add_user_thumbnail(
        embed,
        bot.user
    )

    await send_log(
        SERVER_LOG_ID,
        embed
    )


# =========================================================
# 6. WELCOME
# =========================================================

@bot.event
async def on_member_join(member):

    channel = bot.get_channel(
        WELCOME_CHANNEL_ID
    )

    if channel is None:

        print(
            "❌ Welcome channel not found."
        )

    else:

        try:

            embed = discord.Embed(
                title="WELCOME",
                description=(
                    f"{member.mention}\n"
                    f"baxer beyt bo karezma"
                )
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(
                embed=embed
            )

            print(
                f"✅ Welcome sent for {member}"
            )

        except Exception as e:

            print(
                f"❌ Welcome error: {repr(e)}"
            )


    # MEMBER LOG

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

    # =====================================================
    # NICKNAME
    # =====================================================

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

        embed = make_embed(
            "✏️ Nickname Changed",
            f"**Member:** {after.mention}\n"
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


    # =====================================================
    # ROLE CHANGES
    # =====================================================

    before_roles = set(
        before.roles
    )

    after_roles = set(
        after.roles
    )

    added_roles = (
        after_roles - before_roles
    )

    removed_roles = (
        before_roles - after_roles
    )


    # -------------------------
    # ADDED ROLES
    # -------------------------

    real_added_roles = [
        role
        for role in added_roles
        if role.name != "@everyone"
        and role.name != "Muted"
    ]

    if real_added_roles:

        roles_text = "\n".join(
            f"➕ {role.mention}"
            for role in real_added_roles
        )

        embed = make_embed(
            "➕ Role Added",
            f"**Member:** {after.mention}\n\n"
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


    # -------------------------
    # REMOVED ROLES
    # -------------------------

    real_removed_roles = [
        role
        for role in removed_roles
        if role.name != "@everyone"
        and role.name != "Muted"
    ]

    if real_removed_roles:

        roles_text = "\n".join(
            f"➖ {role.mention}"
            for role in real_removed_roles
        )

        embed = make_embed(
            "➖ Role Removed",
            f"**Member:** {after.mention}\n\n"
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

    # TAG

    if message.mentions:

        member = message.mentions[0]

        if isinstance(
            member,
            discord.Member
        ):
            return member


    # REPLY

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

            member = message.guild.get_member(
                referenced_message.author.id
            )

            return member

        except Exception as e:

            print(
                f"Reply target error: {repr(e)}"
            )


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
                reason="Karezma Muted role"
            )


        elif isinstance(
            channel,
            discord.VoiceChannel
        ):

            await channel.set_permissions(
                mute_role,
                speak=False,
                stream=False,
                reason="Karezma Muted role"
            )

    except Exception as e:

        print(
            f"Muted permission error in "
            f"{channel.name}: {e}"
        )


async def get_or_create_muted_role(guild):

    mute_role = discord.utils.get(
        guild.roles,
        name="Muted"
    )

    if mute_role:
        return mute_role


    mute_role = await guild.create_role(
        name="Muted",
        reason="Karezma mute role"
    )


    for channel in guild.channels:

        await apply_muted_permissions(
            channel,
            mute_role
        )


    return mute_role


# =========================================================
# 11. NEW CHANNEL -> MUTED ROLE
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

    except Exception as e:

        print(
            f"New channel mute permission error: {e}"
        )


# =========================================================
# 12. CHANNEL CREATE LOG
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

        # CHANNEL LOG

        embed = make_embed(
            "📁 Channel Created",
            f"**Channel:** {channel.mention}\n"
            f"**Name:** `{channel.name}`\n"
            f"**ID:** `{channel.id}`\n"
            f"**Type:** `{channel.type}`",
            discord.Color.green()
        )

        await send_log(
            CHANNEL_LOG_ID,
            embed
        )

    except Exception as e:

        print(
            f"New channel error: {e}"
        )


# =========================================================
# 13. CHANNEL DELETE LOG
# =========================================================

@bot.event
async def on_guild_channel_delete(channel):

    embed = make_embed(
        "🗑️ Channel Deleted",
        f"**Channel:** `#{channel.name}`\n"
        f"**ID:** `{channel.id}`\n"
        f"**Type:** `{channel.type}`",
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
            f"**Category:** `{old_category}` → "
            f"`{new_category}`"
        )


    if before.position != after.position:

        changes.append(
            f"**Position:** `{before.position}` → "
            f"`{after.position}`"
        )


    if changes:

        embed = make_embed(
            "✏️ Channel Updated",
            f"**Channel:** {after.mention}\n"
            f"**ID:** `{after.id}`\n\n"
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

    embed = make_embed(
        "➕ Role Created",
        f"**Role:** {role.mention}\n"
        f"**Name:** `{role.name}`\n"
        f"**ID:** `{role.id}`",
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

    embed = make_embed(
        "🗑️ Role Deleted",
        f"**Role:** `{role.name}`\n"
        f"**ID:** `{role.id}`",
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
            f"**Color:** `{before.color}` → "
            f"`{after.color}`"
        )


    if before.position != after.position:

        changes.append(
            f"**Position:** `{before.position}` → "
            f"`{after.position}`"
        )


    if before.hoist != after.hoist:

        changes.append(
            f"**Hoisted:** `{before.hoist}` → "
            f"`{after.hoist}`"
        )


    if before.mentionable != after.mentionable:

        changes.append(
            f"**Mentionable:** `{before.mentionable}` → "
            f"`{after.mentionable}`"
        )


    if changes:

        embed = make_embed(
            "✏️ Role Updated",
            f"**Role:** {after.mention}\n"
            f"**ID:** `{after.id}`\n\n"
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

    # JOIN

    if (
        before.channel is None
        and after.channel is not None
    ):

        embed = make_embed(
            "🔊 Voice Join",
            f"**Member:** {member.mention}\n"
            f"**Channel:** {after.channel.mention}\n"
            f"**ID:** `{after.channel.id}`",
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


    # LEAVE

    if (
        before.channel is not None
        and after.channel is None
    ):

        embed = make_embed(
            "🔇 Voice Leave",
            f"**Member:** {member.mention}\n"
            f"**Channel:** `{before.channel.name}`\n"
            f"**ID:** `{before.channel.id}`",
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


    # MOVE

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


    # SERVER MUTE

    if before.mute != after.mute:

        status = (
            "🔇 Server Muted"
            if after.mute
            else
            "🔊 Server Unmuted"
        )

        embed = make_embed(
            status,
            f"**Member:** {member.mention}\n"
            f"**Status:** `{after.mute}`",
            discord.Color.red()
            if after.mute
            else discord.Color.green()
        )

        add_user_thumbnail(
            embed,
            member
        )

        await send_log(
            VOICE_LOG_ID,
            embed
        )


    # SERVER DEAF

    if before.deaf != after.deaf:

        status = (
            "🔇 Server Deafened"
            if after.deaf
            else
            "🔊 Server Undeafened"
        )

        embed = make_embed(
            status,
            f"**Member:** {member.mention}\n"
            f"**Status:** `{after.deaf}`",
            discord.Color.red()
            if after.deaf
            else discord.Color.green()
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
# 19. BAN LOG
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

    if entry:

        admin = entry.user

    else:

        admin = None


    admin_text = (
        admin.mention
        if admin
        else
        "Unknown"
    )


    embed = make_embed(
        "🔨 Member Banned",
        f"**Member:** {user.mention}\n"
        f"**Username:** `{user}`\n"
        f"**ID:** `{user.id}`\n\n"
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


# =========================================================
# 20. UNBAN LOG
# =========================================================

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

    if entry:

        admin = entry.user

    else:

        admin = None


    admin_text = (
        admin.mention
        if admin
        else
        "Unknown"
    )


    embed = make_embed(
        "♻️ Member Unbanned",
        f"**Member:** {user.mention}\n"
        f"**Username:** `{user}`\n"
        f"**ID:** `{user.id}`\n\n"
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
            f"**Server Name:** `{before.name}` → "
            f"`{after.name}`"
        )


    if before.description != after.description:

        changes.append(
            "**Description changed**"
        )


    if before.icon != after.icon:

        changes.append(
            "**Server Icon changed**"
        )


    if before.banner != after.banner:

        changes.append(
            "**Server Banner changed**"
        )


    if (
        before.verification_level
        != after.verification_level
    ):

        changes.append(
            f"**Verification:** "
            f"`{before.verification_level}` → "
            f"`{after.verification_level}`"
        )


    if changes:

        embed = make_embed(
            "⚙️ Server Updated",
            "\n".join(changes),
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
# 22. MESSAGE DELETE LOG
# =========================================================

@bot.event
async def on_message_delete(message):

    if message.author.bot:
        return

    if message.guild is None:
        return


    content = (
        message.content
        if message.content
        else
        "*No text content*"
    )


    if len(content) > 1500:

        content = (
            content[:1500]
            + "..."
        )


    # FIND ADMIN WHO DELETED IT

    entry = await get_audit_executor(
        message.guild,
        discord.AuditLogAction.message_delete,
        message.author.id
    )


    if entry:

        deleter = entry.user

    else:

        deleter = None


    deleter_text = (
        deleter.mention
        if deleter
        else
        "Unknown / Self"
    )


    embed = make_embed(
        "🗑️ Message Deleted",
        f"**Author:** {message.author.mention}\n"
        f"**Channel:** {message.channel.mention}\n"
        f"**Deleted By:** {deleter_text}\n\n"
        f"**Message:**\n"
        f"```text\n"
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


# =========================================================
# 23. MESSAGE EDIT
# =========================================================

@bot.event
async def on_message_edit(
    before,
    after
):

    if before.author.bot:
        return

    if before.guild is None:
        return

    if before.content == after.content:
        return

    old_content = (
        before.content
        if before.content
        else
        "*Empty*"
    )

    new_content = (
        after.content
        if after.content
        else
        "*Empty*"
    )

    if len(old_content) > 700:

        old_content = (
            old_content[:700]
            + "..."
        )

    if len(new_content) > 700:

        new_content = (
            new_content[:700]
            + "..."
        )


    embed = make_embed(
        "✏️ Message Edited",
        f"**Author:** {after.author.mention}\n"
        f"**Channel:** {after.channel.mention}\n\n"
        f"**Before:**\n"
        f"```text\n"
        f"{old_content}\n"
        f"```\n"
        f"**After:**\n"
        f"```text\n"
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

    if message.author.bot:
        return

    if message.guild is None:
        return


    content = message.content.strip()

    if not content:
        return


    parts = content.split()

    command = parts[0].lower()


    # =====================================================
    # SAFIKA
    # =====================================================

    if command == "safika":

        if not message.author.guild_permissions.administrator:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تەنها ئەدمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.",
                delete_after=5
            )

            return


        if (
            len(parts) < 2
            or not parts[1].isdigit()
        ):

            await message.channel.send(
                "❌ نموونە: `Safika 1000`",
                delete_after=5
            )

            return


        amount = int(
            parts[1]
        )


        if amount <= 0:

            await message.channel.send(
                "❌ ژمارەکە دەبێت زیاتر لە 0 بێت.",
                delete_after=5
            )

            return


        amount = min(
            amount,
            1000
        )


        try:

            deleted = await message.channel.purge(
                limit=amount + 1,
                bulk=True
            )

            await message.channel.send(
                f"✅ `{len(deleted)}` نامە سڕایەوە.",
                delete_after=3
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی سڕینەوەی نامەی نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Safika error: {e}"
            )

            await message.channel.send(
                "❌ کێشەیەک لە سڕینەوەی نامەکان ڕوویدا.",
                delete_after=5
            )


        return


    # =====================================================
    # MUTE
    # =====================================================

    if command == "mute":

        if not message.author.guild_permissions.administrator:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تەنها ئەدمین دەتوانێت Mute بەکاربهێنێت.",
                delete_after=5
            )

            return


        target = await get_target_member(
            message
        )


        if target is None:

            await message.channel.send(
                "❌ کەسێک Tag بکە یان Reply ـی نامەکەی بکە و بنووسە `Mute`.",
                delete_after=5
            )

            return


        if target.id == bot.user.id:

            await message.channel.send(
                "❌ ناتوانم خۆم Mute بکەم.",
                delete_after=5
            )

            return


        if target.top_role >= message.guild.me.top_role:

            await message.channel.send(
                "❌ ڕۆڵی ئەو کەسە لە ڕۆڵی بۆتەکە بەرزترە یان یەکسانە.",
                delete_after=5
            )

            return


        try:

            mute_role = await get_or_create_muted_role(
                message.guild
            )


            if mute_role >= message.guild.me.top_role:

                await message.channel.send(
                    "❌ ڕۆڵی `Muted` دەبێت لە خوار ڕۆڵی بۆتەکە بێت.",
                    delete_after=6
                )

                return


            if mute_role not in target.roles:

                await target.add_roles(
                    mute_role,
                    reason=f"Karezma Mute by {message.author}"
                )


            # MUTE LOG

            embed = make_embed(
                "🔇 Member Muted",
                f"**Member:** {target.mention}\n"
                f"**Username:** `{target}`\n"
                f"**ID:** `{target.id}`\n\n"
                f"**Muted By:** {message.author.mention}",
                discord.Color.red()
            )

            add_user_thumbnail(
                embed,
                target
            )

            await send_log(
                BAN_LOG_ID,
                embed
            )


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                f"damt daxaa {target.mention}",
                delete_after=2
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی زیادکردنی ڕۆڵی نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Mute error: {e}"
            )

            await message.channel.send(
                "❌ کێشەیەک لە Mute ڕوویدا.",
                delete_after=5
            )


        return


    # =====================================================
    # UNMUTE
    # =====================================================

    if command == "unmute":

        if not message.author.guild_permissions.administrator:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تەنها ئەدمین دەتوانێت Unmute بەکاربهێنێت.",
                delete_after=5
            )

            return


        target = await get_target_member(
            message
        )


        if target is None:

            await message.channel.send(
                "❌ کەسێک Tag بکە یان Reply ـی بکە و بنووسە `Unmute`.",
                delete_after=5
            )

            return


        try:

            mute_role = discord.utils.get(
                message.guild.roles,
                name="Muted"
            )


            if mute_role is None:

                await message.channel.send(
                    "❌ ڕۆڵی `Muted` بوونی نییە.",
                    delete_after=5
                )

                return


            if mute_role in target.roles:

                await target.remove_roles(
                    mute_role,
                    reason=f"Karezma Unmute by {message.author}"
                )


            # UNMUTE LOG

            embed = make_embed(
                "🔊 Member Unmuted",
                f"**Member:** {target.mention}\n"
                f"**Username:** `{target}`\n"
                f"**ID:** `{target.id}`\n\n"
                f"**Unmuted By:** {message.author.mention}",
                discord.Color.green()
            )

            add_user_thumbnail(
                embed,
                target
            )

            await send_log(
                BAN_LOG_ID,
                embed
            )


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                f"xwa xerm bnwse dllm basha aqllba amjara {target.mention}",
                delete_after=2
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە ناتوانێت ڕۆڵی Muted لەسەر ئەو کەسە لاببات.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Unmute error: {e}"
            )

            await message.channel.send(
                "❌ کێشەیەک لە Unmute ڕوویدا.",
                delete_after=5
            )


        return


    # =====================================================
    # BFRA
    # =====================================================

    if command == "bfra":

        if not message.author.guild_permissions.administrator:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تەنها ئەدمین دەتوانێت Bfra بەکاربهێنێت.",
                delete_after=5
            )

            return


        target = await get_target_member(
            message
        )


        if target is None:

            await message.channel.send(
                "❌ کەسێک Tag بکە یان Reply ـی بکە و بنووسە `Bfra`.",
                delete_after=5
            )

            return


        if target.id == bot.user.id:

            await message.channel.send(
                "❌ ناتوانم خۆم Ban بکەم.",
                delete_after=5
            )

            return


        if target.top_role >= message.guild.me.top_role:

            await message.channel.send(
                "❌ ڕۆڵی ئەو کەسە لە ڕۆڵی بۆتەکە بەرزترە یان یەکسانە.",
                delete_after=5
            )

            return


        try:

            await target.ban(
                reason=f"Karezma Bfra by {message.author}"
            )


            # BAN LOG

            embed = make_embed(
                "🔨 Member Banned",
                f"**Member:** {target.mention}\n"
                f"**Username:** `{target}`\n"
                f"**ID:** `{target.id}`\n\n"
                f"**Banned By:** {message.author.mention}",
                discord.Color.red()
            )

            add_user_thumbnail(
                embed,
                target
            )

            await send_log(
                BAN_LOG_ID,
                embed
            )


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                f"✈️ Frenra {target.mention}",
                delete_after=2
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی Ban کردنی ئەو کەسە نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Bfra error: {e}"
            )

            await message.channel.send(
                "❌ کێشەیەک لە Bfra ڕوویدا.",
                delete_after=5
            )


        return


    # =====================================================
    # UNBAN
    # =====================================================

    if command == "unban":

        if not message.author.guild_permissions.administrator:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تەنها ئەدمین دەتوانێت Unban بەکاربهێنێت.",
                delete_after=5
            )

            return


        user = None


        # ID

        if (
            len(parts) >= 2
            and parts[1].isdigit()
        ):

            try:

                user = await bot.fetch_user(
                    int(parts[1])
                )

            except:

                user = None


        # REPLY

        elif message.reference:

            try:

                referenced_message = (
                    await message.channel.fetch_message(
                        message.reference.message_id
                    )
                )

                user = referenced_message.author

            except:

                user = None


        if user is None:

            await message.channel.send(
                "❌ ID ـی بەکارهێنەر بنووسە یان Reply بکە و `Unban` بنووسە.",
                delete_after=5
            )

            return


        try:

            await message.guild.unban(
                user,
                reason=f"Karezma Unban by {message.author}"
            )


            # UNBAN LOG

            embed = make_embed(
                "♻️ Member Unbanned",
                f"**Member:** {user.mention}\n"
                f"**Username:** `{user}`\n"
                f"**ID:** `{user.id}`\n\n"
                f"**Unbanned By:** {message.author.mention}",
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


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                f"✅ {user.mention} Unban کرا.",
                delete_after=3
            )


        except discord.NotFound:

            await message.channel.send(
                "❌ ئەم بەکارهێنەرە Ban نەکراوە.",
                delete_after=5
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی Unban کردنی نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Unban error: {e}"
            )

            await message.channel.send(
                "❌ کێشەیەک لە Unban ڕوویدا.",
                delete_after=5
            )


        return


    # =====================================================
    # LOCK
    # =====================================================

    if command == "lock":

        if not message.author.guild_permissions.manage_channels:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تۆ دەسەڵاتی Lock کردنی کەناڵت نییە.",
                delete_after=5
            )

            return


        try:

            await message.channel.set_permissions(
                message.guild.default_role,
                send_messages=False,
                reason=f"Locked by {message.author}"
            )


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                "🔒 کەناڵەکە Lock کرا.",
                delete_after=3
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی Lock کردنی کەناڵی نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Lock error: {e}"
            )


        return


    # =====================================================
    # UNLOCK
    # =====================================================

    if command == "unlock":

        if not message.author.guild_permissions.manage_channels:

            await message.channel.send(
                f"❌ {message.author.mention} "
                f"تۆ دەسەڵاتی Unlock کردنی کەناڵت نییە.",
                delete_after=5
            )

            return


        try:

            await message.channel.set_permissions(
                message.guild.default_role,
                send_messages=None,
                reason=f"Unlocked by {message.author}"
            )


            try:
                await message.delete()
            except:
                pass


            await message.channel.send(
                "🔓 کەناڵەکە Unlock کرا.",
                delete_after=3
            )


        except discord.Forbidden:

            await message.channel.send(
                "❌ بۆتەکە دەسەڵاتی Unlock کردنی کەناڵی نییە.",
                delete_after=5
            )


        except Exception as e:

            print(
                f"Unlock error: {e}"
            )


        return


# =========================================================
# 25. ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        (
            commands.CommandNotFound,
            commands.MissingPermissions
        )
    ):

        return


    print(
        f"Command error: {repr(error)}"
    )


# =========================================================
# 26. RUN BOT
# =========================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)


if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing."
    )


bot.run(TOKEN)
