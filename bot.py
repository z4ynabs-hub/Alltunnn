import os
import io
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps


# ============================================================
# KAREZMA BOT CONFIG
# ============================================================

WELCOME_CHANNEL_ID = 863844473851215893

OWNER_ID = 926473403790151701

STAFF_ROLE_IDS = [
    863850042123878421,
    995343531482812488,
]

LOG_VIEW_ROLE_IDS = [
    1548633166531530802,
    865587893568274482,
    863846779921629216,
]

LOG_CHANNELS = {
    "server": 863857583146926090,
    "chat": 863857498719780874,
    "voice": 863857530941341718,
    "ban": 867084771477553183,
    "left": 863857555948175381,
    "channel": 867085144061771806,
    "role": 867085174662889503,
    "member": 867085715787612220,
    "nickname": 867085807445213215,
}


# ============================================================
# WELCOME IMAGE SETTINGS
# ============================================================

TEMPLATE_FILE = "welcome_template.jpg"

AVATAR_X = 690
AVATAR_Y = 70
AVATAR_W = 430
AVATAR_H = 430

NAME_X = 70
NAME_Y = 150

SUBTEXT_X = 70
SUBTEXT_Y = 235

WELCOME_X = 70
WELCOME_Y = 300


# ============================================================
# DISCORD INTENTS
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True


bot = commands.Bot(
    command_prefix="",
    intents=intents
)


# ============================================================
# HELPERS
# ============================================================

def current_time():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def create_log_embed(
    title,
    description,
    color=0x5865F2
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_footer(
        text="Karezma Logs"
    )

    return embed


async def send_log(
    guild: discord.Guild,
    log_type: str,
    embed: discord.Embed
):
    channel_id = LOG_CHANNELS.get(log_type)

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(
            "Log send error:",
            repr(e)
        )


# ============================================================
# LOG CHANNEL PERMISSIONS
# ============================================================

async def protect_log_channels(
    guild: discord.Guild
):
    for channel_id in LOG_CHANNELS.values():
        channel = guild.get_channel(
            channel_id
        )

        if channel is None:
            continue

        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=False,
                reason="Karezma log protection"
            )

            for role_id in LOG_VIEW_ROLE_IDS:
                role = guild.get_role(
                    role_id
                )

                if role:
                    await channel.set_permissions(
                        role,
                        view_channel=True,
                        read_message_history=True,
                        reason="Karezma log viewer"
                    )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# ============================================================
# FONT & AVATAR
# ============================================================

def get_font(
    size: int,
    bold=False
):
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


def create_avatar(
    avatar_bytes,
    width,
    height
):
    avatar = Image.open(
        io.BytesIO(avatar_bytes)
    ).convert("RGBA")

    avatar = ImageOps.fit(
        avatar,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )

    mask = Image.new(
        "L",
        (width, height),
        0
    )

    draw = ImageDraw.Draw(mask)

    radius = max(
        12,
        min(width, height) // 10
    )

    draw.rounded_rectangle(
        (
            0,
            0,
            width - 1,
            height - 1
        ),
        radius=radius,
        fill=255
    )

    avatar.putalpha(mask)

    return avatar


async def create_welcome_image(
    member: discord.Member
):
    if not os.path.exists(
        TEMPLATE_FILE
    ):
        raise FileNotFoundError(
            "welcome_template.jpg نەدۆزرایەوە."
        )

    background = Image.open(
        TEMPLATE_FILE
    ).convert("RGBA")

    avatar_asset = member.display_avatar.replace(
        format="png",
        size=512
    )

    avatar_bytes = await avatar_asset.read()

    avatar = create_avatar(
        avatar_bytes,
        AVATAR_W,
        AVATAR_H
    )

    background.alpha_composite(
        avatar,
        (
            AVATAR_X,
            AVATAR_Y
        )
    )

    draw = ImageDraw.Draw(
        background
    )

    name_font = get_font(
        48,
        bold=True
    )
    sub_font = get_font(
        28,
        bold=False
    )
    welcome_font = get_font(
        42,
        bold=True
    )

    name = (
        "@"
        + member.display_name
    )

    max_width = max(
        200,
        AVATAR_X - NAME_X - 50
    )

    while (
        name_font.getbbox(name)[2]
        > max_width
        and name_font.size > 20
    ):
        name_font = get_font(
            name_font.size - 2,
            bold=True
        )

    draw.text(
        (
            NAME_X,
            NAME_Y
        ),
        name,
        font=name_font,
        fill=(
            255,
            255,
            255,
            255
        )
    )

    draw.text(
        (
            SUBTEXT_X,
            SUBTEXT_Y
        ),
        "baxerbeyt bo karezma",
        font=sub_font,
        fill=(
            255,
            255,
            255,
            255
        )
    )

    draw.text(
        (
            WELCOME_X,
            WELCOME_Y
        ),
        "WELCOME",
        font=welcome_font,
        fill=(
            255,
            255,
            255,
            255
        )
    )

    output = io.BytesIO()

    background.convert(
        "RGB"
    ).save(
        output,
        format="JPEG",
        quality=95,
        optimize=True
    )

    output.seek(0)

    return output


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user}"
    )

    try:
        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} slash commands."
        )

        for guild in bot.guilds:
            await protect_log_channels(
                guild
            )

    except Exception as e:
        print(
            "Ready error:",
            repr(e)
        )


# ============================================================
# WELCOME & LEAVE EVENTS
# ============================================================

@bot.event
async def on_member_join(
    member: discord.Member
):
    welcome_channel = member.guild.get_channel(
        WELCOME_CHANNEL_ID
    )

    if welcome_channel:
        try:
            image = await create_welcome_image(
                member
            )

            await welcome_channel.send(
                content=member.mention,
                file=discord.File(
                    image,
                    filename="welcome.jpg"
                )
            )

        except Exception as e:
            print(
                "Welcome image error:",
                repr(e)
            )

            try:
                embed = discord.Embed(
                    title="WELCOME",
                    description=(
                        f"**@{member.display_name}**\n"
                        "baxerbeyt bo karezma"
                    ),
                    color=0x5865F2
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                await welcome_channel.send(
                    content=member.mention,
                    embed=embed
                )

            except Exception:
                pass

    embed = create_log_embed(
        "Member Joined",
        f"**Member:** {member.mention}\n"
        f"**Username:** `{member}`\n"
        f"**ID:** `{member.id}`\n"
        f"**Time:** `{current_time()}`",
        0x57F287
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await send_log(
        member.guild,
        "member",
        embed
    )


@bot.event
async def on_member_remove(
    member: discord.Member
):
    embed = create_log_embed(
        "Member Left",
        f"**Member:** `{member}`\n"
        f"**ID:** `{member.id}`\n"
        f"**Time:** `{current_time()}`",
        0xED4245
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await send_log(
        member.guild,
        "left",
        embed
    )


# ============================================================
# /STAF COMMAND (SLASH)
# ============================================================

@bot.tree.command(
    name="staf",
    description="Give both Staff roles to a member"
)
@app_commands.describe(
    name="Choose the member"
)
@app_commands.default_permissions(
    administrator=True
)
async def staf(
    interaction: discord.Interaction,
    name: discord.Member
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ تەنها Administrator دەتوانێت ئەم فرمانە بەکاربهێنێت.",
            ephemeral=True
        )
        return

    role1 = interaction.guild.get_role(
        STAFF_ROLE_IDS[0]
    )
    role2 = interaction.guild.get_role(
        STAFF_ROLE_IDS[1]
    )

    if role1 is None or role2 is None:
        await interaction.response.send_message(
            "❌ Staff Role ـەکان نەدۆزرایەوە.",
            ephemeral=True
        )
        return

    bot_member = interaction.guild.me

    if (
        role1 >= bot_member.top_role
        or role2 >= bot_member.top_role
    ):
        await interaction.response.send_message(
            "❌ Staff Role ـەکان دەبێت لە ژێر Highest Role ـی بۆتەکە بن.",
            ephemeral=True
        )
        return

    try:
        await name.add_roles(
            role1,
            role2,
            reason=f"Karezma /staf by {interaction.user}"
        )

        await interaction.response.send_message(
            f"✅ {name.mention} هەردوو Staff Role ـی پێدرا.",
            ephemeral=True
        )

        embed = create_log_embed(
            "Staff Granted",
            f"**Admin:** {interaction.user.mention}\n"
            f"**Member:** {name.mention}\n"
            f"**Roles:** {role1.mention}, {role2.mention}",
            0x5865F2
        )

        await send_log(
            interaction.guild,
            "member",
            embed
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ بۆتەکە دەسەڵاتی Manage Roles نییە.",
            ephemeral=True
        )


# ============================================================
# /TEST COMMAND
# ============================================================

@bot.tree.command(
    name="test",
    description="Test Karezma bot"
)
async def test(
    interaction: discord.Interaction
):
    await interaction.response.send_message(
        "✅ Karezma is online!",
        ephemeral=True
    )


# ============================================================
# PREFIX-LESS MODERATION COMMANDS
# ============================================================

@bot.command(name="safika")
@commands.has_permissions(manage_messages=True)
async def safika(ctx, amount: int):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    deleted = await ctx.channel.purge(limit=amount)
    msg = await ctx.send(f"✅ `{len(deleted)}` نامە سڕایەوە.")
    await msg.delete(delay=2)


@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    if member is None and ctx.message.reference:
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = ref_msg.author
        except Exception:
            pass

    if not member or not isinstance(member, discord.Member):
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        try:
            mute_role = await ctx.guild.create_role(name="Muted")
        except Exception:
            pass

    if mute_role:
        try:
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(mute_role, send_messages=False, add_reactions=False)
                except Exception:
                    pass

            await member.add_roles(mute_role)
            msg = await ctx.send(f"damt daxaa {member.mention}")
            await msg.delete(delay=4)
        except Exception:
            pass


@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    if member is None and ctx.message.reference:
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = ref_msg.author
        except Exception:
            pass

    if not member or not isinstance(member, discord.Member):
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        try:
            await member.remove_roles(mute_role)
            msg = await ctx.send(f"xwa xerm bnwse aqllba amjara {member.mention}")
            await msg.delete(delay=4)
        except Exception:
            pass


@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        msg = await ctx.send("🔒 ئەم کەناڵە داخرا.")
        await msg.delete(delay=4)
    except Exception:
        pass


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        msg = await ctx.send("🔓 ئەم کەناڵە کرایەوە.")
        await msg.delete(delay=4)
    except Exception:
        pass


@bot.command(name="bfra")
@commands.has_permissions(ban_members=True)
async def bfra(ctx, member: discord.Member = None):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    if member is None and ctx.message.reference:
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = ref_msg.author
        except Exception:
            pass

    if not member or not isinstance(member, discord.Member):
        return

    try:
        await member.ban()
        msg = await ctx.send(f"frenraa✈️ {member.mention}")
        await msg.delete(delay=4)
    except Exception:
        pass


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        msg = await ctx.send(f"🔓 `{user}` ئەنباندی کرا.")
        await msg.delete(delay=4)
    except Exception:
        pass


# ============================================================
# LOG EVENTS
# ============================================================

@bot.event
async def on_message_delete(
    message: discord.Message
):
    if (
        not message.guild
        or message.author.bot
    ):
        return

    content = (
        message.content[:1000]
        if message.content
        else "[No text]"
    )

    embed = create_log_embed(
        "Message Deleted",
        f"**Author:** {message.author.mention}\n"
        f"**Channel:** {message.channel.mention}\n"
        f"**Content:** `{content}`",
        0xED4245
    )

    await send_log(
        message.guild,
        "chat",
        embed
    )


@bot.event
async def on_message_edit(
    before: discord.Message,
    after: discord.Message
):
    if (
        not before.guild
        or before.author.bot
    ):
        return

    if before.content == after.content:
        return

    old = (
        before.content[:800]
        if before.content
        else "[No text]"
    )

    new = (
        after.content[:800]
        if after.content
        else "[No text]"
    )

    embed = create_log_embed(
        "Message Edited",
        f"**Author:** {before.author.mention}\n"
        f"**Channel:** {before.channel.mention}\n\n"
        f"**Before:** `{old}`\n"
        f"**After:** `{new}`",
        0xFEE75C
    )

    await send_log(
        before.guild,
        "chat",
        embed
    )


@bot.event
async def on_guild_role_create(
    role: discord.Role
):
    embed = create_log_embed(
        "Role Created",
        f"**Role:** {role.mention}\n"
        f"**Name:** `{role.name}`\n"
        f"**ID:** `{role.id}`",
        0x57F287
    )

    await send_log(
        role.guild,
        "role",
        embed
    )


@bot.event
async def on_guild_role_delete(
    role: discord.Role
):
    embed = create_log_embed(
        "Role Deleted",
        f"**Name:** `{role.name}`\n"
        f"**ID:** `{role.id}`",
        0xED4245
    )

    await send_log(
        role.guild,
        "role",
        embed
    )


@bot.event
async def on_guild_role_update(
    before: discord.Role,
    after: discord.Role
):
    changes = []

    if before.name != after.name:
        changes.append(
            f"**Name:** `{before.name}` → `{after.name}`"
        )

    if before.permissions != after.permissions:
        changes.append(
            "**Permissions:** changed"
        )

    if before.position != after.position:
        changes.append(
            f"**Position:** `{before.position}` → `{after.position}`"
        )

    if not changes:
        return

    embed = create_log_embed(
        "Role Updated",
        f"**Role:** {after.mention}\n"
        + "\n".join(changes),
        0xFEE75C
    )

    await send_log(
        after.guild,
        "role",
        embed
    )


@bot.event
async def on_guild_channel_create(
    channel: discord.abc.GuildChannel
):
    mention = (
        channel.mention
        if hasattr(channel, "mention")
        else channel.name
    )

    embed = create_log_embed(
        "Channel Created",
        f"**Channel:** {mention}\n"
        f"**Name:** `{channel.name}`\n"
        f"**Type:** `{channel.type}`",
        0x57F287
    )

    await send_log(
        channel.guild,
        "channel",
        embed
    )


@bot.event
async def on_guild_channel_delete(
    channel: discord.abc.GuildChannel
):
    embed = create_log_embed(
        "Channel Deleted",
        f"**Name:** `{channel.name}`\n"
        f"**Type:** `{channel.type}`\n"
        f"**ID:** `{channel.id}`",
        0xED4245
    )

    await send_log(
        channel.guild,
        "channel",
        embed
    )


@bot.event
async def on_guild_channel_update(
    before: discord.abc.GuildChannel,
    after: discord.abc.GuildChannel
):
    changes = []

    if before.name != after.name:
        changes.append(
            f"**Name:** `{before.name}` → `{after.name}`"
        )

    if (
        hasattr(before, "topic")
        and hasattr(after, "topic")
        and before.topic != after.topic
    ):
        changes.append(
            f"**Topic:** `{before.topic}` → `{after.topic}`"
        )

    if before.position != after.position:
        changes.append(
            f"**Position:** `{before.position}` → `{after.position}`"
        )

    if not changes:
        return

    mention = (
        after.mention
        if hasattr(after, "mention")
        else after.name
    )

    embed = create_log_embed(
        "Channel Updated",
        f"**Channel:** {mention}\n"
        + "\n".join(changes),
        0xFEE75C
    )

    await send_log(
        after.guild,
        "channel",
        embed
    )


@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member
):
    if before.nick != after.nick:
        old = before.nick or before.name
        new = after.nick or after.name

        embed = create_log_embed(
            "Nickname Changed",
            f"**Member:** {after.mention}\n"
            f"**Before:** `{old}`\n"
            f"**After:** `{new}`",
            0xFEE75C
        )

        await send_log(
            after.guild,
            "nickname",
            embed
        )

    before_roles = {r.id: r for r in before.roles}
    after_roles = {r.id: r for r in after.roles}

    added = [
        after_roles[rid]
        for rid in after_roles
        if rid not in before_roles
    ]

    removed = [
        before_roles[rid]
        for rid in before_roles
        if rid not in after_roles
    ]

    if added or removed:
        lines = [
            f"**Member:** {after.mention}"
        ]

        if added:
            lines.append(
                "**Added:** "
                + ", ".join(
                    f"`{r.name}` ({r.mention})"
                    for r in added
                )
            )

        if removed:
            lines.append(
                "**Removed:** "
                + ", ".join(
                    f"`{r.name}`"
                    for r in removed
                )
            )

        embed = create_log_embed(
            "Member Roles Updated",
            "\n".join(lines),
            0x5865F2
        )

        await send_log(
            after.guild,
            "member",
            embed
        )


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):
    if before.channel == after.channel:
        if (
            before.mute != after.mute
            or before.deaf != after.deaf
        ):
            changes = []

            if before.mute != after.mute:
                changes.append(
                    f"**Server Mute:** `{before.mute}` → `{after.mute}`"
                )

            if before.deaf != after.deaf:
                changes.append(
                    f"**Server Deaf:** `{before.deaf}` → `{after.deaf}`"
                )

            embed = create_log_embed(
                "Voice State Changed",
                f"**Member:** {member.mention}\n"
                + "\n".join(changes),
                0xFEE75C
            )

            await send_log(
                member.guild,
                "voice",
                embed
            )
        return

    if (
        before.channel is None
        and after.channel is not None
    ):
        title = "Voice Joined"
        description = (
            f"**Member:** {member.mention}\n"
            f"**Channel:** {after.channel.mention}"
        )
    elif (
        before.channel is not None
        and after.channel is None
    ):
        title = "Voice Left"
        description = (
            f"**Member:** {member.mention}\n"
            f"**Channel:** `{before.channel.name}`"
        )
    else:
        title = "Voice Moved"
        description = (
            f"**Member:** {member.mention}\n"
            f"**From:** `{before.channel.name}`\n"
            f"**To:** {after.channel.mention}"
        )

    embed = create_log_embed(
        title,
        description,
        0x5865F2
    )

    await send_log(
        member.guild,
        "voice",
        embed
    )


@bot.event
async def on_guild_update(
    before: discord.Guild,
    after: discord.Guild
):
    changes = []

    if before.name != after.name:
        changes.append(
            f"**Server Name:** `{before.name}` → `{after.name}`"
        )

    if before.icon != after.icon:
        changes.append(
            "**Server Icon:** changed"
        )

    if before.banner != after.banner:
        changes.append(
            "**Server Banner:** changed"
        )

    if not changes:
        return

    embed = create_log_embed(
        "Server Updated",
        "\n".join(changes),
        0xFEE75C
    )

    await send_log(
        after,
        "server",
        embed
    )


@bot.event
async def on_member_ban(
    guild: discord.Guild,
    user: discord.User
):
    embed = create_log_embed(
        "Member Banned",
        f"**User:** `{user}`\n"
        f"**ID:** `{user.id}`",
        0xED4245
    )

    await send_log(
        guild,
        "ban",
        embed
    )


@bot.event
async def on_member_unban(
    guild: discord.Guild,
    user: discord.User
):
    embed = create_log_embed(
        "Member Unbanned",
        f"**User:** `{user}`\n"
        f"**ID:** `{user.id}`",
        0x57F287
    )

    await send_log(
        guild,
        "ban",
        embed
    )


# ============================================================
# RUN
# ============================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing."
    )

bot.run(TOKEN)
