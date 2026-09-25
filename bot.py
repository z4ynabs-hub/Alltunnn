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
    intents=intents,
    case_insensitive=True
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
    color=0x5865F2,
    thumbnail_url=None
):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )

    if thumbnail_url:
        embed.set_thumbnail(
            url=thumbnail_url
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

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        try:
            channel = await bot.fetch_channel(
                channel_id
            )
        except Exception:
            return

    try:
        await channel.send(
            embed=embed
        )
    except Exception as e:
        print(
            "Log send error:",
            repr(e)
        )


# ============================================================
# GET MEMBER FROM MENTION / REPLY
# ============================================================

async def get_target_member(
    ctx,
    member: discord.Member = None
):
    """
    Target can be:
    1. Mention:
       mute @user
       Bfra @user

    2. Reply:
       Reply to user's message + mute
       Reply to user's message + Bfra

    3. If both exist, mention has priority.
    """

    if member is not None:
        return member

    if ctx.message.reference:

        try:
            ref_message = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )

            if isinstance(
                ref_message.author,
                discord.Member
            ):
                return ref_message.author

        except Exception as e:

            print(
                "Reply target error:",
                repr(e)
            )

    return None


# ============================================================
# MUTED ROLE
# ============================================================

async def apply_muted_permissions(
    channel,
    mute_role
):
    try:

        await channel.set_permissions(
            mute_role,
            send_messages=False,
            add_reactions=False,
            send_messages_in_threads=False,
            create_public_threads=False,
            create_private_threads=False,
            reason="Karezma Muted role protection"
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
        TypeError
    ):
        pass


async def get_or_create_muted_role(
    guild: discord.Guild
):

    mute_role = discord.utils.get(
        guild.roles,
        name="Muted"
    )

    if mute_role:

        return mute_role

    try:

        mute_role = await guild.create_role(
            name="Muted",
            reason="Karezma mute role"
        )

        print(
            f"Created Muted role in {guild.name}"
        )

    except discord.Forbidden:

        print(
            "Muted role error: Bot cannot create roles."
        )

        return None

    except discord.HTTPException as e:

        print(
            "Muted role HTTP error:",
            repr(e)
        )

        return None

    # Apply mute permissions to every existing channel
    for channel in guild.channels:

        await apply_muted_permissions(
            channel,
            mute_role
        )

    return mute_role


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

    draw = ImageDraw.Draw(
        mask
    )

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

    avatar.putalpha(
        mask
    )

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

            # Existing Muted role
            mute_role = discord.utils.get(
                guild.roles,
                name="Muted"
            )

            if mute_role:

                for channel in guild.channels:

                    await apply_muted_permissions(
                        channel,
                        mute_role
                    )

    except Exception as e:

        print(
            "Ready error:",
            repr(e)
        )


# ============================================================
# MEMBER JOIN
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
        0x57F287,
        member.display_avatar.url
    )

    await send_log(
        member.guild,
        "member",
        embed
    )


# ============================================================
# MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(
    member: discord.Member
):

    embed = create_log_embed(
        "Member Left",
        f"**Member:** `{member}`\n"
        f"**ID:** `{member.id}`\n"
        f"**Time:** `{current_time()}`",
        0xED4245,
        member.display_avatar.url
    )

    await send_log(
        member.guild,
        "left",
        embed
    )


# ============================================================
# /STAF
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
            0x5865F2,
            name.display_avatar.url
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
# /TEST
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
# SAFIKA
#
# Because case_insensitive=True:
#
# safika
# Safika
# SAFIKA
# SaFiKa
#
# all work.
# ============================================================

@bot.command(
    name="safika"
)
@commands.has_permissions(
    manage_messages=True
)
async def safika(
    ctx,
    amount: int = None
):

    # Delete command itself
    try:

        await ctx.message.delete()

    except Exception:
        pass

    if amount is None:
        return

    if amount <= 0:
        return

    # Maximum requested amount
    if amount > 10000:
        amount = 10000

    try:

        deleted = await ctx.channel.purge(
            limit=amount,
            bulk=True
        )

        print(
            f"Safika deleted {len(deleted)} messages "
            f"in #{ctx.channel.name}"
        )

    except discord.Forbidden:

        print(
            "Safika error: Bot needs Manage Messages."
        )

    except discord.HTTPException as e:

        print(
            "Safika HTTP error:",
            repr(e)
        )

    except Exception as e:

        print(
            "Safika error:",
            repr(e)
        )


# ============================================================
# MUTE
#
# Examples:
#
# mute @User
# Mute @User
# MUTE @User
#
# OR:
#
# Reply to user's message
# mute
#
# ============================================================

@bot.command(
    name="mute"
)
@commands.has_permissions(
    manage_roles=True
)
async def mute(
    ctx,
    member: discord.Member = None
):

    # Delete command
    try:

        await ctx.message.delete()

    except Exception:
        pass

    # Get member from mention OR reply
    member = await get_target_member(
        ctx,
        member
    )

    if member is None:
        return

    # Get/create Muted role
    mute_role = await get_or_create_muted_role(
        ctx.guild
    )

    if mute_role is None:
        return

    # Bot must be above Muted role
    if mute_role >= ctx.guild.me.top_role:

        print(
            "Mute error: Muted role must be below bot role."
        )

        return

    # Bot cannot mute someone above/equal to itself
    if member.top_role >= ctx.guild.me.top_role:

        print(
            "Mute error: Target role is too high."
        )

        return

    # Already muted
    if mute_role in member.roles:
        return

    try:

        await member.add_roles(
            mute_role,
            reason=f"Karezma mute by {ctx.author}"
        )

        print(
            f"Muted {member} by {ctx.author}"
        )

    except discord.Forbidden:

        print(
            "Mute error: Bot cannot manage this member."
        )

    except discord.HTTPException as e:

        print(
            "Mute HTTP error:",
            repr(e)
        )

    except Exception as e:

        print(
            "Mute error:",
            repr(e)
        )


# ============================================================
# UNMUTE
#
# Examples:
#
# unmute @User
# Unmute @User
# UNMUTE @User
#
# OR reply to user's message:
#
# unmute
#
# ============================================================

@bot.command(
    name="unmute"
)
@commands.has_permissions(
    manage_roles=True
)
async def unmute(
    ctx,
    member: discord.Member = None
):

    # Delete command
    try:

        await ctx.message.delete()

    except Exception:
        pass

    # Get member from mention OR reply
    member = await get_target_member(
        ctx,
        member
    )

    if member is None:
        return

    mute_role = discord.utils.get(
        ctx.guild.roles,
        name="Muted"
    )

    if mute_role is None:
        return

    if mute_role not in member.roles:
        return

    try:

        await member.remove_roles(
            mute_role,
            reason=f"Karezma unmute by {ctx.author}"
        )

        print(
            f"Unmuted {member} by {ctx.author}"
        )

    except discord.Forbidden:

        print(
            "Unmute error: Bot cannot manage this member."
        )

    except discord.HTTPException as e:

        print(
            "Unmute HTTP error:",
            repr(e)
        )

    except Exception as e:

        print(
            "Unmute error:",
            repr(e)
        )


# ============================================================
# BFRA = BAN
#
# IMPORTANT:
# You wanted Bfra, not "ban".
#
# Because case_insensitive=True:
#
# bfra
# Bfra
# BFRA
#
# all work.
#
# It also works by Reply:
#
# Reply to user message + bfra
#
# ============================================================

@bot.command(
    name="bfra"
)
@commands.has_permissions(
    ban_members=True
)
async def bfra(
    ctx,
    member: discord.Member = None
):

    # Delete command
    try:

        await ctx.message.delete()

    except Exception:
        pass

    # Get member from mention OR reply
    member = await get_target_member(
        ctx,
        member
    )

    if member is None:
        return

    # Bot cannot ban itself
    if member.id == bot.user.id:
        return

    # Bot cannot ban someone above/equal to itself
    if member.top_role >= ctx.guild.me.top_role:

        print(
            "Bfra error: Target role is too high."
        )

        return

    try:

        await member.ban(
            reason=f"Karezma Bfra by {ctx.author}"
        )

        msg = await ctx.send(
            f"frenraa✈️ {member.mention}"
        )

        await msg.delete(
            delay=2
        )

        print(
            f"Bfra banned {member} by {ctx.author}"
        )

    except discord.Forbidden:

        print(
            "Bfra error: Bot needs Ban Members permission."
        )

    except discord.HTTPException as e:

        print(
            "Bfra HTTP error:",
            repr(e)
        )

    except Exception as e:

        print(
            "Bfra error:",
            repr(e)
        )


# ============================================================
# UNBAN
#
# Works with:
#
# unban USER_ID
#
# OR reply to a message from the banned user
# ============================================================

@bot.command(
    name="unban"
)
@commands.has_permissions(
    ban_members=True
)
async def unban(
    ctx,
    user_id: int = None
):

    # Delete command
    try:

        await ctx.message.delete()

    except Exception:
        pass

    user = None

    # If ID was provided
    if user_id is not None:

        try:

            user = await bot.fetch_user(
                user_id
            )

        except Exception:
            return

    # If replying to a user's message
    elif ctx.message.reference:

        try:

            ref_message = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )

            user = ref_message.author

        except Exception:
            return

    if user is None:
        return

    try:

        await ctx.guild.unban(
            user,
            reason=f"Karezma unban by {ctx.author}"
        )

        msg = await ctx.send(
            f"🔓 `{user}` ئەنباندی کرا."
        )

        await msg.delete(
            delay=2
        )

        print(
            f"Unbanned {user} by {ctx.author}"
        )

    except discord.NotFound:

        print(
            "Unban error: User is not banned."
        )

    except discord.Forbidden:

        print(
            "Unban error: Bot needs Ban Members permission."
        )

    except discord.HTTPException as e:

        print(
            "Unban HTTP error:",
            repr(e)
        )

    except Exception as e:

        print(
            "Unban error:",
            repr(e)
        )


# ============================================================
# LOCK
# ============================================================

@bot.command(
    name="lock"
)
@commands.has_permissions(
    manage_channels=True
)
async def lock(ctx):

    try:

        await ctx.message.delete()

    except Exception:
        pass

    try:

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            send_messages=False
        )

        msg = await ctx.send(
            "🔒 ئەم کەناڵە داخرا."
        )

        await msg.delete(
            delay=2
        )

    except Exception as e:

        print(
            "Lock error:",
            repr(e)
        )


# ============================================================
# UNLOCK
# ============================================================

@bot.command(
    name="unlock"
)
@commands.has_permissions(
    manage_channels=True
)
async def unlock(ctx):

    try:

        await ctx.message.delete()

    except Exception:
        pass

    try:

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            send_messages=True
        )

        msg = await ctx.send(
            "🔓 ئەم کەناڵە کرایەوە."
        )

        await msg.delete(
            delay=2
        )

    except Exception as e:

        print(
            "Unlock error:",
            repr(e)
        )


# ============================================================
# MESSAGE DELETE LOG
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
        0xED4245,
        message.author.display_avatar.url
    )

    await send_log(
        message.guild,
        "chat",
        embed
    )


# ============================================================
# MESSAGE EDIT LOG
# ============================================================

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
        0xFEE75C,
        before.author.display_avatar.url
    )

    await send_log(
        before.guild,
        "chat",
        embed
    )


# ============================================================
# ROLE CREATE
# ============================================================

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


# ============================================================
# ROLE DELETE
# ============================================================

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


# ============================================================
# ROLE UPDATE
# ============================================================

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


# ============================================================
# CHANNEL CREATE
# ============================================================

@bot.event
async def on_guild_channel_create(
    channel: discord.abc.GuildChannel
):

    # Protect newly-created channel from Muted role
    mute_role = discord.utils.get(
        channel.guild.roles,
        name="Muted"
    )

    if mute_role:

        await apply_muted_permissions(
            channel,
            mute_role
        )

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


# ============================================================
# CHANNEL DELETE
# ============================================================

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


# ============================================================
# CHANNEL UPDATE
# ============================================================

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


# ============================================================
# MEMBER UPDATE
# ============================================================

@bot.event
async def on_member_update(
    before: discord.Member,
    after: discord.Member
):

    # Nickname
    if before.nick != after.nick:

        old = (
            before.nick
            or before.name
        )

        new = (
            after.nick
            or after.name
        )

        updater = None

        try:

            async for entry in after.guild.audit_logs(
                limit=3,
                action=discord.AuditLogAction.member_update
            ):

                if entry.target.id == after.id:

                    updater = entry.user
                    break

        except Exception:
            pass

        lines = [
            f"**Member:** {after.mention}"
        ]

        if updater:

            lines.append(
                f"**By:** {updater.mention}"
            )

        else:

            lines.append(
                f"**By:** {after.mention} *(Self/Reset)*"
            )

        lines.append(
            f"**Before:** `{old}`"
        )

        lines.append(
            f"**After:** `{new}`"
        )

        embed = create_log_embed(
            "Nickname Changed",
            "\n".join(lines),
            0xFEE75C,
            after.display_avatar.url
        )

        await send_log(
            after.guild,
            "nickname",
            embed
        )

    # Roles
    before_roles = {
        r.id: r
        for r in before.roles
    }

    after_roles = {
        r.id: r
        for r in after.roles
    }

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

        updater = None

        try:

            async for entry in after.guild.audit_logs(
                limit=3,
                action=discord.AuditLogAction.member_role_update
            ):

                if entry.target.id == after.id:

                    updater = entry.user
                    break

        except Exception:
            pass

        lines = [
            f"**Member:** {after.mention}"
        ]

        if updater:

            lines.append(
                f"**By:** {updater.mention}"
            )

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
            0x5865F2,
            after.display_avatar.url
        )

        await send_log(
            after.guild,
            "member",
            embed
        )


# ============================================================
# VOICE LOG
# ============================================================

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
                0xFEE75C,
                member.display_avatar.url
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
        0x5865F2,
        member.display_avatar.url
    )

    await send_log(
        member.guild,
        "voice",
        embed
    )


# ============================================================
# SERVER UPDATE
# ============================================================

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


# ============================================================
# BAN LOG
# ============================================================

@bot.event
async def on_member_ban(
    guild: discord.Guild,
    user: discord.User
):

    embed = create_log_embed(
        "Member Banned",
        f"**User:** `{user}`\n"
        f"**ID:** `{user.id}`",
        0xED4245,
        user.display_avatar.url
    )

    await send_log(
        guild,
        "ban",
        embed
    )


# ============================================================
# UNBAN LOG
# ============================================================

@bot.event
async def on_member_unban(
    guild: discord.Guild,
    user: discord.User
):

    embed = create_log_embed(
        "Member Unbanned",
        f"**User:** `{user}`\n"
        f"**ID:** `{user.id}`",
        0x57F287,
        user.display_avatar.url
    )

    await send_log(
        guild,
        "ban",
        embed
    )


# ============================================================
# COMMAND ERROR HANDLER
# ============================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):
        return

    print(
        "Command error:",
        repr(error)
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

bot.run(
    TOKEN
)
