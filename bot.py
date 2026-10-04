import discord
from discord import app_commands
from discord.ext import commands

import datetime
import os
import asyncio
import sqlite3
import json
import traceback
import re


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
# 2. LEGACY / ORIGINAL SERVER IDS
#    DO NOT CHANGE THESE
# =========================================================

RESTRICTED_COLOR_USERS = set()

WELCOME_CHANNEL_ID = 863844473851215893

SERVER_LOG_ID = 863857583146926090
CHAT_LOG_ID = 863857498719780874
VOICE_LOG_ID = 863857530941341718
BAN_LOG_ID = 867084771477553183
LEFT_LOG_ID = 863857555948175381
CHANNEL_LOG_ID = 867085144061771806
ROLE_LOG_ID = 867085174662889503
MEMBER_LOG_ID = 867085715787612220
NICKNAME_LOG_ID = 867085807787612220

ROLE_BARXAKAN = 864962613582102560
ROLE_MSHAXOR = 863850042123878421

REGRI_ALLOWED_ROLES = {
    1548633166531530802,
    865587893568274482,
    863846779921629216
}


# =========================================================
# 3. MULTI-SERVER DATABASE
# =========================================================

CONFIG_DB = "karezma_config.db"

DEVELOPER_IDS = set()

try:
    env_developers = os.getenv("DEVELOPER_IDS", "")

    if env_developers.strip():
        DEVELOPER_IDS.update(
            int(x.strip())
            for x in env_developers.split(",")
            if x.strip().isdigit()
        )

except Exception:
    pass


# You can optionally put:
# ORIGINAL_GUILD_ID=123456789012345678
#
# If you don't put it, the bot automatically detects
# the original server from WELCOME_CHANNEL_ID.

try:
    ORIGINAL_GUILD_ID = int(
        os.getenv("ORIGINAL_GUILD_ID", "0") or 0
    )

    if ORIGINAL_GUILD_ID <= 0:
        ORIGINAL_GUILD_ID = None

except Exception:
    ORIGINAL_GUILD_ID = None


LEGACY_GUILD_ID = ORIGINAL_GUILD_ID


CONFIG_FIELDS = (
    "welcome_channel_id",
    "welcome_image",
    "welcome_message",
    "server_log_id",
    "chat_log_id",
    "voice_log_id",
    "ban_log_id",
    "left_log_id",
    "channel_log_id",
    "role_log_id",
    "member_log_id",
    "nickname_log_id",
    "role_barxakan",
    "role_mshaxor",
    "regri_allowed_roles",
)


# =========================================================
# 4. DATABASE INIT + MIGRATION
# =========================================================

def init_config_db():

    conn = sqlite3.connect(CONFIG_DB)

    try:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                welcome_image TEXT,
                welcome_message TEXT,
                server_log_id INTEGER,
                chat_log_id INTEGER,
                voice_log_id INTEGER,
                ban_log_id INTEGER,
                left_log_id INTEGER,
                channel_log_id INTEGER,
                role_log_id INTEGER,
                member_log_id INTEGER,
                nickname_log_id INTEGER,
                role_barxakan INTEGER,
                role_mshaxor INTEGER,
                regri_allowed_roles TEXT,
                setup_done INTEGER DEFAULT 0
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS restricted_color_users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        # -------------------------------------------------
        # DATABASE MIGRATION
        # -------------------------------------------------

        existing_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(guild_config)"
            ).fetchall()
        }

        required_columns = {
            "welcome_channel_id": "INTEGER",
            "welcome_image": "TEXT",
            "welcome_message": "TEXT",
            "server_log_id": "INTEGER",
            "chat_log_id": "INTEGER",
            "voice_log_id": "INTEGER",
            "ban_log_id": "INTEGER",
            "left_log_id": "INTEGER",
            "channel_log_id": "INTEGER",
            "role_log_id": "INTEGER",
            "member_log_id": "INTEGER",
            "nickname_log_id": "INTEGER",
            "role_barxakan": "INTEGER",
            "role_mshaxor": "INTEGER",
            "regri_allowed_roles": "TEXT",
            "setup_done": "INTEGER DEFAULT 0",
        }

        for column, definition in required_columns.items():

            if column not in existing_columns:

                try:
                    conn.execute(
                        f"""
                        ALTER TABLE guild_config
                        ADD COLUMN {column} {definition}
                        """
                    )
                except Exception:
                    pass

        conn.commit()

    finally:
        conn.close()


# =========================================================
# 5. DATABASE HELPERS
# =========================================================

def get_db_row(guild_id):

    init_config_db()

    conn = sqlite3.connect(CONFIG_DB)
    conn.row_factory = sqlite3.Row

    try:

        row = conn.execute(
            """
            SELECT *
            FROM guild_config
            WHERE guild_id = ?
            """,
            (guild_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()


def ensure_guild_config(guild_id):

    init_config_db()

    row = get_db_row(guild_id)

    if row is not None:
        return row

    conn = sqlite3.connect(CONFIG_DB)

    try:

        conn.execute(
            """
            INSERT OR IGNORE INTO guild_config (
                guild_id,
                welcome_channel_id,
                welcome_image,
                welcome_message,
                server_log_id,
                chat_log_id,
                voice_log_id,
                ban_log_id,
                left_log_id,
                channel_log_id,
                role_log_id,
                member_log_id,
                nickname_log_id,
                role_barxakan,
                role_mshaxor,
                regri_allowed_roles,
                setup_done
            )
            VALUES (
                ?,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                ?,
                0
            )
            """,
            (
                guild_id,
                json.dumps([])
            )
        )

        conn.commit()

    finally:
        conn.close()

    return get_db_row(guild_id)


def update_config(guild_id, **values):

    ensure_guild_config(guild_id)

    allowed = set(CONFIG_FIELDS) | {
        "setup_done"
    }

    values = {
        key: value
        for key, value in values.items()
        if key in allowed
    }

    if not values:
        return

    assignments = ", ".join(
        f"{key} = ?"
        for key in values
    )

    conn = sqlite3.connect(CONFIG_DB)

    try:

        conn.execute(
            f"""
            UPDATE guild_config
            SET {assignments}
            WHERE guild_id = ?
            """,
            tuple(values.values()) + (
                guild_id,
            )
        )

        conn.commit()

    finally:
        conn.close()


def mark_setup_done(guild_id):

    update_config(
        guild_id,
        setup_done=1
    )


# =========================================================
# 6. LEGACY SERVER
# =========================================================

def is_legacy_guild(guild):

    return (
        guild is not None
        and LEGACY_GUILD_ID is not None
        and guild.id == LEGACY_GUILD_ID
    )


def get_guild_config(guild):

    if guild is None:

        return {
            field: None
            for field in CONFIG_FIELDS
        }

    # -----------------------------------------------------
    # ORIGINAL SERVER
    # -----------------------------------------------------

    if is_legacy_guild(guild):

        return {
            "welcome_channel_id":
                WELCOME_CHANNEL_ID,

            "welcome_image":
                None,

            "welcome_message":
                "axer beyt bo karezma",

            "server_log_id":
                SERVER_LOG_ID,

            "chat_log_id":
                CHAT_LOG_ID,

            "voice_log_id":
                VOICE_LOG_ID,

            "ban_log_id":
                BAN_LOG_ID,

            "left_log_id":
                LEFT_LOG_ID,

            "channel_log_id":
                CHANNEL_LOG_ID,

            "role_log_id":
                ROLE_LOG_ID,

            "member_log_id":
                MEMBER_LOG_ID,

            "nickname_log_id":
                NICKNAME_LOG_ID,

            "role_barxakan":
                ROLE_BARXAKAN,

            "role_mshaxor":
                ROLE_MSHAXOR,

            "regri_allowed_roles":
                set(REGRI_ALLOWED_ROLES),
        }

    # -----------------------------------------------------
    # NEW SERVERS
    # -----------------------------------------------------

    row = get_db_row(guild.id)

    if not row:

        return {
            field: None
            for field in CONFIG_FIELDS
        }

    try:

        allowed_roles = set(
            json.loads(
                row.get(
                    "regri_allowed_roles"
                ) or "[]"
            )
        )

    except Exception:

        allowed_roles = set()

    return {
        "welcome_channel_id":
            row.get("welcome_channel_id"),

        "welcome_image":
            row.get("welcome_image"),

        "welcome_message":
            row.get("welcome_message"),

        "server_log_id":
            row.get("server_log_id"),

        "chat_log_id":
            row.get("chat_log_id"),

        "voice_log_id":
            row.get("voice_log_id"),

        "ban_log_id":
            row.get("ban_log_id"),

        "left_log_id":
            row.get("left_log_id"),

        "channel_log_id":
            row.get("channel_log_id"),

        "role_log_id":
            row.get("role_log_id"),

        "member_log_id":
            row.get("member_log_id"),

        "nickname_log_id":
            row.get("nickname_log_id"),

        "role_barxakan":
            row.get("role_barxakan"),

        "role_mshaxor":
            row.get("role_mshaxor"),

        "regri_allowed_roles":
            allowed_roles,
    }


def get_config_value(
    guild,
    key,
    default=None
):

    config = get_guild_config(guild)

    value = config.get(key)

    if value is None:
        return default

    return value


def get_log_id(guild, key):

    return get_config_value(
        guild,
        key
    )


def get_role_id(guild, key):

    return get_config_value(
        guild,
        key
    )


# =========================================================
# 7. RESTRICTED COLOR USERS
# =========================================================

def get_restricted_users(guild_id):

    if guild_id is None:
        return set()

    init_config_db()

    conn = sqlite3.connect(CONFIG_DB)

    try:

        rows = conn.execute(
            """
            SELECT user_id
            FROM restricted_color_users
            WHERE guild_id = ?
            """,
            (guild_id,)
        ).fetchall()

        return {
            row[0]
            for row in rows
        }

    finally:
        conn.close()


def set_restricted_user(
    guild_id,
    user_id,
    restricted=True
):

    if guild_id is None:
        return

    init_config_db()

    conn = sqlite3.connect(CONFIG_DB)

    try:

        if restricted:

            conn.execute(
                """
                INSERT OR IGNORE INTO
                restricted_color_users
                (guild_id, user_id)
                VALUES (?, ?)
                """,
                (
                    guild_id,
                    user_id
                )
            )

        else:

            conn.execute(
                """
                DELETE FROM
                restricted_color_users
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            )

        conn.commit()

    finally:
        conn.close()


# =========================================================
# 8. DEVELOPER / OWNER PERMISSIONS
# =========================================================

async def is_bot_developer(user):

    if user.id in DEVELOPER_IDS:
        return True

    try:

        app_info = await bot.application_info()

        if (
            app_info.owner
            and app_info.owner.id == user.id
        ):
            return True

        team = getattr(
            app_info,
            "team",
            None
        )

        if team:

            for member in team.members:

                if member.id == user.id:
                    return True

    except Exception:
        pass

    return False


async def is_config_manager(interaction):

    if interaction.guild is None:
        return False

    if (
        interaction.user.id
        == interaction.guild.owner_id
    ):
        return True

    return await is_bot_developer(
        interaction.user
    )


async def require_config_manager(
    interaction
):

    allowed = await is_config_manager(
        interaction
    )

    if not allowed:

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ تەنها **Server Owner** یان "
                "**Bot Developer** دەتوانێت "
                "ئەم کۆماندە بەکاربهێنێت.",
                ephemeral=True
            )

        return False

    return True


# =========================================================
# 9. INPUT HELPERS
# =========================================================

def parse_id(value):

    value = str(value).strip()

    if not value.isdigit():

        raise ValueError(
            "ID دەبێت تەنها ژمارە بێت."
        )

    number = int(value)

    if number <= 0:

        raise ValueError(
            "ID ـەکە دروست نییە."
        )

    return number


def parse_roles(value):

    value = str(value).replace(
        ",",
        " "
    )

    ids = []

    for part in value.split():

        part = part.strip()

        # Role mention:
        # <@&123456789>
        mention_match = re.fullmatch(
            r"<@&(\d+)>",
            part
        )

        if mention_match:

            ids.append(
                int(
                    mention_match.group(1)
                )
            )

        elif part.isdigit():

            ids.append(
                int(part)
            )

        else:

            raise ValueError(
                "Role ID ـەکان دەبێت بە "
                "ژمارە یان Role Mention بن."
            )

    return sorted(
        set(ids)
    )


def short_value(
    value,
    limit=70
):

    if value is None:
        return "❌ دانەنراوە"

    value = str(value)

    if len(value) > limit:

        return (
            value[:limit - 3]
            + "..."
        )

    return value


# =========================================================
# 10. LOG HELPERS
# =========================================================

def get_log_channel(channel_id):

    if not channel_id:
        return None

    return bot.get_channel(
        channel_id
    )


async def send_log(
    channel_id,
    embed
):

    try:

        channel = get_log_channel(
            channel_id
        )

        if channel is None:
            return

        await channel.send(
            embed=embed
        )

    except Exception:
        pass


def make_embed(
    title,
    description,
    color=None
):

    if color is None:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now(
            datetime.timezone.utc
        )
    )

    embed.set_footer(
        text="Karezma Logs"
    )

    return embed


def add_user_thumbnail(
    embed,
    user
):

    try:

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

    except Exception:
        pass


# =========================================================
# 11. AUDIT LOG
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

                if (
                    entry.target is None
                    or getattr(
                        entry.target,
                        "id",
                        None
                    ) != target_id
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
# 12. READY
# =========================================================

@bot.event
async def on_ready():

    global LEGACY_GUILD_ID

    init_config_db()

    # -----------------------------------------------------
    # Detect original server
    # -----------------------------------------------------

    if LEGACY_GUILD_ID is None:

        try:

            legacy_channel = bot.get_channel(
                WELCOME_CHANNEL_ID
            )

            if legacy_channel:

                LEGACY_GUILD_ID = (
                    legacy_channel.guild.id
                )

        except Exception:
            pass

    # -----------------------------------------------------
    # Create blank config for every NEW server
    # -----------------------------------------------------

    for guild in bot.guilds:

        try:

            if not is_legacy_guild(guild):

                ensure_guild_config(
                    guild.id
                )

        except Exception:
            pass

    # -----------------------------------------------------
    # Sync slash commands
    # -----------------------------------------------------

    try:

        await bot.tree.sync()

    except Exception as e:

        print(
            "Slash sync error:",
            e
        )

    # -----------------------------------------------------
    # Sync muted role permissions
    # -----------------------------------------------------

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
        f"✅ Bot connected as: {bot.user}"
    )

    if LEGACY_GUILD_ID:

        print(
            f"✅ Original server: "
            f"{LEGACY_GUILD_ID}"
        )

    print(
        f"✅ Servers: {len(bot.guilds)}"
    )


# =========================================================
# 13. WELCOME
# =========================================================

@bot.event
async def on_member_join(member):

    config = get_guild_config(
        member.guild
    )

    welcome_channel_id = config.get(
        "welcome_channel_id"
    )

    if welcome_channel_id:

        channel = member.guild.get_channel(
            welcome_channel_id
        )

        if channel:

            try:

                welcome_message = (
                    config.get(
                        "welcome_message"
                    )
                    or "axer beyt bo karezma"
                )

                embed = discord.Embed(
                    title="WELCOME",
                    description=(
                        f"{member.mention}\n"
                        f"{welcome_message}"
                    ),
                    color=discord.Color.blurple()
                )

                welcome_image = config.get(
                    "welcome_image"
                )

                if welcome_image:

                    try:

                        embed.set_image(
                            url=welcome_image
                        )

                    except Exception:
                        pass

                try:

                    embed.set_thumbnail(
                        url=member.display_avatar.url
                    )

                except Exception:
                    pass

                await channel.send(
                    embed=embed
                )

            except Exception:
                pass

    # Member log

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
        config.get(
            "member_log_id"
        ),
        embed
    )


# =========================================================
# 14. MEMBER LEFT
# =========================================================

@bot.event
async def on_member_remove(member):

    config = get_guild_config(
        member.guild
    )

    embed = make_embed(
        "📤 Member Left",
        f"Member: {member.mention}\n"
        f"Username: {member}\n"
        f"ID: {member.id}",
        discord.Color.red()
    )

    add_user_thumbnail(
        embed,
        member
    )

    await send_log(
        config.get(
            "left_log_id"
        ),
        embed
    )


# =========================================================
# 15. MEMBER UPDATE
# =========================================================

@bot.event
async def on_member_update(
    before,
    after
):

    config = get_guild_config(
        after.guild
    )

    # -----------------------------------------------------
    # Nickname
    # -----------------------------------------------------

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
            if entry
            and entry.user
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
            config.get(
                "nickname_log_id"
            ),
            embed
        )

    # -----------------------------------------------------
    # Roles
    # -----------------------------------------------------

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

    real_added_roles = [
        role
        for role in added_roles
        if role.name not in [
            "@everyone",
            "Muted"
        ]
    ]

    if real_added_roles:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.member_role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry
            and entry.user
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
            config.get(
                "member_log_id"
            ),
            embed
        )

    real_removed_roles = [
        role
        for role in removed_roles
        if role.name not in [
            "@everyone",
            "Muted"
        ]
    ]

    if real_removed_roles:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.member_role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry
            and entry.user
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
            config.get(
                "member_log_id"
            ),
            embed
        )


# =========================================================
# 16. TARGET MEMBER
# =========================================================

async def get_target_member(message):

    if message.mentions:

        for member in message.mentions:

            if (
                bot.user
                and member.id == bot.user.id
            ):
                continue

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

            if (
                bot.user
                and referenced_message.author.id
                == bot.user.id
            ):
                return None

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
# 17. MUTED ROLE
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


async def get_or_create_muted_role(
    guild
):

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
# 18. CHANNEL CREATE
# =========================================================

@bot.event
async def on_guild_channel_create(
    channel
):

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
            if entry
            and entry.user
            else "Unknown"
        )

        mention = getattr(
            channel,
            "mention",
            f"`{channel.name}`"
        )

        embed = make_embed(
            "📁 Channel Created",
            f"**Channel:** {mention}\n"
            f"**Name:** `{channel.name}`\n"
            f"**ID:** `{channel.id}`\n"
            f"**Type:** `{channel.type}`\n"
            f"**Created By:** {creator}",
            discord.Color.green()
        )

        config = get_guild_config(
            channel.guild
        )

        await send_log(
            config.get(
                "channel_log_id"
            ),
            embed
        )

    except Exception:
        pass


# =========================================================
# 19. CHANNEL DELETE
# =========================================================

@bot.event
async def on_guild_channel_delete(
    channel
):

    entry = await get_audit_executor(
        channel.guild,
        discord.AuditLogAction.channel_delete,
        channel.id
    )

    deleter = (
        entry.user.mention
        if entry
        and entry.user
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

    config = get_guild_config(
        channel.guild
    )

    await send_log(
        config.get(
            "channel_log_id"
        ),
        embed
    )


# =========================================================
# 20. CHANNEL UPDATE
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
            f"**Name:** `{before.name}` → "
            f"`{after.name}`"
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

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.channel_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry
            and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "✏️ Channel Updated",
            f"**Channel:** {after.mention}\n"
            f"**ID:** `{after.id}`\n"
            f"**Updated By:** {editor}\n\n"
            + "\n".join(changes),
            discord.Color.gold()
        )

        config = get_guild_config(
            after.guild
        )

        await send_log(
            config.get(
                "channel_log_id"
            ),
            embed
        )


# =========================================================
# 21. ROLE CREATE
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
        if entry
        and entry.user
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

    config = get_guild_config(
        role.guild
    )

    await send_log(
        config.get(
            "role_log_id"
        ),
        embed
    )


# =========================================================
# 22. ROLE DELETE
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
        if entry
        and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "🗑️ Role Deleted",
        f"**Role:** `{role.name}`\n"
        f"**ID:** `{role.id}`\n"
        f"**Deleted By:** {deleter}",
        discord.Color.red()
    )

    config = get_guild_config(
        role.guild
    )

    await send_log(
        config.get(
            "role_log_id"
        ),
        embed
    )


# =========================================================
# 23. ROLE UPDATE
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
            f"**Name:** `{before.name}` → "
            f"`{after.name}`"
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

    if changes:

        entry = await get_audit_executor(
            after.guild,
            discord.AuditLogAction.role_update,
            after.id
        )

        editor = (
            entry.user.mention
            if entry
            and entry.user
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

        config = get_guild_config(
            after.guild
        )

        await send_log(
            config.get(
                "role_log_id"
            ),
            embed
        )


# =========================================================
# 24. VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(
    member,
    before,
    after
):

    config = get_guild_config(
        member.guild
    )

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
            config.get(
                "voice_log_id"
            ),
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
            config.get(
                "voice_log_id"
            ),
            embed
        )

        return

    if (
        before.channel is not None
        and after.channel is not None
        and before.channel.id
        != after.channel.id
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
            config.get(
                "voice_log_id"
            ),
            embed
        )


# =========================================================
# 25. BAN / UNBAN
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
        if entry
        and entry.user
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

    config = get_guild_config(
        guild
    )

    await send_log(
        config.get(
            "ban_log_id"
        ),
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
        if entry
        and entry.user
        else "Unknown"
    )

    embed = make_embed(
        "♻️ Member Unbanned",
        f"**Member:** {user.mention}\n"
        f"**Unbanned By:** {admin_text}",
        discord.Color.green()
    )

    add_user_thumbnail(
        embed,
        user
    )

    config = get_guild_config(
        guild
    )

    await send_log(
        config.get(
            "ban_log_id"
        ),
        embed
    )


# =========================================================
# 26. SERVER UPDATE
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

    if changes:

        entry = await get_audit_executor(
            after,
            discord.AuditLogAction.guild_update
        )

        editor = (
            entry.user.mention
            if entry
            and entry.user
            else "Unknown"
        )

        embed = make_embed(
            "⚙️ Server Updated",
            f"**Updated By:** {editor}\n\n"
            + "\n".join(changes),
            discord.Color.gold()
        )

        if after.icon:

            try:

                embed.set_thumbnail(
                    url=after.icon.url
                )

            except Exception:
                pass

        config = get_guild_config(
            after
        )

        await send_log(
            config.get(
                "server_log_id"
            ),
            embed
        )


# =========================================================
# 27. MESSAGE DELETE
# =========================================================

@bot.event
async def on_message_delete(
    message
):

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

    channel_mention = getattr(
        message.channel,
        "mention",
        f"#{message.channel.name}"
    )

    embed = make_embed(
        "🗑️ Message Deleted",
        f"**Author:** {message.author.mention}\n"
        f"**Channel:** {channel_mention}\n\n"
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

    config = get_guild_config(
        message.guild
    )

    await send_log(
        config.get(
            "chat_log_id"
        ),
        embed
    )


# =========================================================
# 28. MESSAGE EDIT
# =========================================================

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

    config = get_guild_config(
        after.guild
    )

    await send_log(
        config.get(
            "chat_log_id"
        ),
        embed
    )


# =========================================================
# 29. TEXT COMMAND SYSTEM
# =========================================================

@bot.event
async def on_message(message):

    if (
        message.author.bot
        or message.guild is None
    ):
        return

    # -----------------------------------------------------
    # MUTED
    # -----------------------------------------------------

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

    command = ""

    for part in parts:

        clean_part = (
            part.lower().strip()
        )

        if clean_part in [
            "safika",
            "mute",
            "unmute",
            "bfra",
            "unban",
            "lock",
            "unlock"
        ]:

            command = clean_part
            break

    if not command and parts:

        command = parts[0].lower()

    # -----------------------------------------------------
    # SAFIKA
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # MUTE
    # -----------------------------------------------------

    if command == "mute":

        if not message.author.guild_permissions.administrator:
            return

        target = await get_target_member(
            message
        )

        if target:

            try:

                mute_role = (
                    await get_or_create_muted_role(
                        message.guild
                    )
                )

                if mute_role not in target.roles:

                    await target.add_roles(
                        mute_role,
                        reason=(
                            f"Muted by "
                            f"{message.author}"
                        )
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

    # -----------------------------------------------------
    # UNMUTE
    # -----------------------------------------------------

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
                    f"xwa xerm bnwse dllm basha aqllba amjara "
                    f"{target.mention}",
                    delete_after=2
                )

            except Exception:
                pass

        return

    # -----------------------------------------------------
    # BFRA
    # -----------------------------------------------------

    if command == "bfra":

        if not message.author.guild_permissions.administrator:
            return

        target = await get_target_member(
            message
        )

        if target:

            try:

                await target.ban(
                    reason=f"Banned by {message.author}"
                )

                try:
                    await message.delete()
                except Exception:
                    pass

                await message.channel.send(
                    f"Frenraa✈️ {target.mention}",
                    delete_after=2
                )

            except Exception:
                pass

        return

    # -----------------------------------------------------
    # UNBAN
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # LOCK
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # UNLOCK
    # -----------------------------------------------------

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
# 30. /STAFF
# =========================================================

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
            "❌ تەنها ئەدیمین دەتوانێت "
            "ئەم کۆماندە بەکاربهێنێت.",
            ephemeral=True
        )

        return

    try:

        role_key = (
            "role_barxakan"
            if role_choice == "barxakan"
            else "role_mshaxor"
        )

        role_id = get_role_id(
            interaction.guild,
            role_key
        )

        if not role_id:

            await interaction.response.send_message(
                "❌ ئەم ڕۆڵە بۆ ئەم سێرڤەرە "
                "config نەکراوە.",
                ephemeral=True
            )

            return

        role = interaction.guild.get_role(
            role_id
        )

        if not role:

            await interaction.response.send_message(
                "❌ ڕۆڵەکە لە سێرڤەرەکە "
                "نەدۆزرایەوە!",
                ephemeral=True
            )

            return

        if role in member.roles:

            await interaction.response.send_message(
                f"⚠️ {member.mention} پێشتر "
                f"ئەم ڕۆڵەی هەیە (`{role.name}`).",
                ephemeral=True
            )

        else:

            await member.add_roles(
                role,
                reason=(
                    f"Staff given by "
                    f"{interaction.user}"
                )
            )

            await interaction.response.send_message(
                f"✅ ڕۆڵی **{role.name}** بە "
                f"سەرکەوتوویی درا بە "
                f"{member.mention}",
                ephemeral=True
            )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ کێشەیەک ڕوویدا: {e}",
            ephemeral=True
        )


# =========================================================
# 31. /RANGI-ROLE
# =========================================================

@bot.tree.command(
    name="rangi-role",
    description="گۆڕینی ڕەنگی ڕۆڵ"
)
@app_commands.describe(
    role="ناوی ڕۆڵەکە یان ID ـی",
    color="کۆدی ڕەنگ بۆ نموونە #FF0000"
)
async def rangi_role(
    interaction: discord.Interaction,
    role: str,
    color: str
):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ تەنها ئەدیمین دەتوانێت "
            "ئەم کۆماندە بەکاربهێنێت.",
            ephemeral=True
        )

        return

    restricted_users = get_restricted_users(
        interaction.guild.id
    )

    if is_legacy_guild(
        interaction.guild
    ):

        restricted_users |= (
            RESTRICTED_COLOR_USERS
        )

    if interaction.user.id in restricted_users:

        await interaction.response.send_message(
            "❌ تۆ قەدەغەکراوی لە گۆڕینی ڕەنگ!",
            ephemeral=True
        )

        return

    guild = interaction.guild

    target_role = None

    if role.isdigit():

        target_role = guild.get_role(
            int(role)
        )

    else:

        target_role = discord.utils.get(
            guild.roles,
            name=role
        )

    if not target_role:

        await interaction.response.send_message(
            "❌ ڕۆڵەکە نەدۆزرایەوە!",
            ephemeral=True
        )

        return

    user_top_role = (
        interaction.user.top_role
    )

    is_owner = (
        interaction.user.id
        == guild.owner_id
    )

    # FIX:
    # Do not use is_bot_managed().
    # role.managed is the safe discord.py property.

    if (
        target_role.name == "@everyone"
        or target_role.managed
    ):

        await interaction.response.send_message(
            "❌ ناتوانیت ڕەنگی ئەم ڕۆڵە بگۆڕیت!",
            ephemeral=True
        )

        return

    if (
        not is_owner
        and target_role >= user_top_role
    ):

        await interaction.response.send_message(
            "❌ ناتوانیت ڕەنگی ئەم ڕۆڵە بگۆڕیت "
            "چونکە لەسەروو ڕۆڵەکەتدایە!",
            ephemeral=True
        )

        return

    try:

        color_text = (
            color.strip()
            .lstrip("#")
        )

        if len(color_text) not in (
            6,
            8
        ):

            raise ValueError(
                "کۆدی ڕەنگ دەبێت وەک #FF0000 بێت."
            )

        color_obj = discord.Color(
            int(
                color_text[:6],
                16
            )
        )

        await target_role.edit(
            color=color_obj,
            reason=(
                f"Role color changed by "
                f"{interaction.user}"
            )
        )

        await interaction.response.send_message(
            f"✅ ڕەنگی ڕۆڵی **{target_role.name}** "
            f"بە سەرکەوتوویی گۆڕدرا!",
            ephemeral=True
        )

    except ValueError as e:

        await interaction.response.send_message(
            f"❌ {e}",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ بۆتەکە دەسەڵاتی گۆڕینی ئەم ڕۆڵەی نییە.",
            ephemeral=True
        )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ هەڵە ڕوویدا: {e}",
            ephemeral=True
        )


@rangi_role.autocomplete(
    "role"
)
async def rangi_role_autocomplete(
    interaction: discord.Interaction,
    current: str
):

    guild = interaction.guild

    if not guild:
        return []

    user_top_role = (
        interaction.user.top_role
    )

    is_owner = (
        interaction.user.id
        == guild.owner_id
    )

    options = []

    for r in guild.roles:

        if (
            r.name == "@everyone"
            or r.managed
        ):
            continue

        if (
            not is_owner
            and r >= user_top_role
        ):
            continue

        if (
            current.lower()
            in r.name.lower()
        ):

            options.append(
                app_commands.Choice(
                    name=r.name[:100],
                    value=str(r.id)
                )
            )

            if len(options) >= 25:
                break

    return options


# =========================================================
# 32. /REGRI
# =========================================================

@bot.tree.command(
    name="regri",
    description="قەدەغەکردن یان لابردنی قەدەغەی گۆڕینی ڕەنگ"
)
@app_commands.choices(
    action=[
        app_commands.Choice(
            name="Add (قەدەغەکردن)",
            value="add"
        ),
        app_commands.Choice(
            name="Remove (ڕێگەپێدان)",
            value="remove"
        )
    ]
)
async def regri(
    interaction: discord.Interaction,
    member: discord.Member,
    action: str
):

    config = get_guild_config(
        interaction.guild
    )

    allowed_roles = (
        config.get(
            "regri_allowed_roles"
        )
        or set()
    )

    is_owner = (
        interaction.user.id
        == interaction.guild.owner_id
    )

    has_allowed_role = any(
        role.id in allowed_roles
        for role in interaction.user.roles
    )

    if not is_owner and not has_allowed_role:

        await interaction.response.send_message(
            "❌ تەنها خاوەنی سێرڤەر یان "
            "ئەو ڕۆڵە دیاریکراوانە دەتوانن "
            "ئەم کۆماندە بەکاربهێنن.",
            ephemeral=True
        )

        return

    action = action.lower()

    if is_legacy_guild(
        interaction.guild
    ):

        if action == "add":

            RESTRICTED_COLOR_USERS.add(
                member.id
            )

        else:

            RESTRICTED_COLOR_USERS.discard(
                member.id
            )

    set_restricted_user(
        interaction.guild.id,
        member.id,
        action == "add"
    )

    if action == "add":

        await interaction.response.send_message(
            f"🚫 {member.mention} قەدەغەکرا "
            f"لە گۆڕینی ڕەنگ.",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            f"✅ ڕێگەدرا بە {member.mention} "
            f"بۆ گۆڕینی ڕەنگ.",
            ephemeral=True
        )


# =========================================================
# 33. /SETUP
# =========================================================

@bot.tree.command(
    name="setup",
    description="دەستپێکردنی config ـی Karezma بۆ ئەم سێرڤەرە"
)
async def setup(
    interaction: discord.Interaction
):

    if not await require_config_manager(
        interaction
    ):
        return

    if is_legacy_guild(
        interaction.guild
    ):

        await interaction.response.send_message(
            "ℹ️ ئەمە سێرڤەری کۆنە. "
            "Config ـەکانی کۆنەکە هەر وەک خۆی "
            "پارێزراون.",
            ephemeral=True
        )

        return

    ensure_guild_config(
        interaction.guild.id
    )

    mark_setup_done(
        interaction.guild.id
    )

    await interaction.response.send_message(
        "✅ Config ـی ئەم سێرڤەرە دروست کرا.\n\n"
        "ئێستا دەتوانیت ئەمانە بەکاربهێنیت:\n"
        "• `/welcome`\n"
        "• `/log`\n"
        "• `/roles`\n"
        "• `/regri-roles`\n"
        "• `/config`",
        ephemeral=True
    )


# =========================================================
# 34. /WELCOME
# =========================================================

@bot.tree.command(
    name="welcome",
    description="ڕێکخستنی welcome channel و message و image"
)
@app_commands.describe(
    channel="کەناڵی welcome",
    message="دەقی welcome",
    image="URL ـی وێنە/GIF، یان clear بۆ سڕینەوە"
)
async def welcome_config(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str = "axer beyt bo karezma",
    image: str = "clear"
):

    if not await require_config_manager(
        interaction
    ):
        return

    if is_legacy_guild(
        interaction.guild
    ):

        await interaction.response.send_message(
            "⚠️ بۆ ئەوەی config ـی سێرڤەری کۆن "
            "نەشکێت، ئەم command ـە لە "
            "سێرڤەری کۆن ناتوانێت ID ـە کۆنەکان "
            "بگۆڕێت.",
            ephemeral=True
        )

        return

    # -----------------------------------------------------
    # Make sure selected channel belongs to same server
    # -----------------------------------------------------

    if channel.guild.id != interaction.guild.id:

        await interaction.response.send_message(
            "❌ ئەو کەناڵە هی ئەم سێرڤەرە نییە.",
            ephemeral=True
        )

        return

    image_value = None

    image_text = (
        str(image).strip()
    )

    if image_text.lower() not in {
        "clear",
        "none",
        "off",
        "-"
    }:

        if not image_text.startswith(
            (
                "http://",
                "https://"
            )
        ):

            await interaction.response.send_message(
                "❌ Image دەبێت URL بێت، "
                "یان `clear` بنووسە.",
                ephemeral=True
            )

            return

        image_value = image_text

    message = (
        str(message).strip()
    )

    if not message:

        message = (
            "axer beyt bo karezma"
        )

    try:

        update_config(
            interaction.guild.id,
            welcome_channel_id=channel.id,
            welcome_message=message,
            welcome_image=image_value,
            setup_done=1
        )

        await interaction.response.send_message(
            "✅ Welcome بە سەرکەوتوویی config کرا.\n\n"
            f"**Channel:** {channel.mention}\n"
            f"**Message:** `{short_value(message)}`\n"
            f"**Image:** "
            f"`{'دانراوە' if image_value else 'نییە'}`",
            ephemeral=True
        )

    except Exception as e:

        print(
            "WELCOME ERROR:"
        )

        traceback.print_exc()

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ کێشەیەک لە config ـکردنی "
                "Welcome ڕوویدا.",
                ephemeral=True
            )


# =========================================================
# 35. /LOG
# =========================================================

LOG_NAMES = {

    "server":
        "server_log_id",

    "chat":
        "chat_log_id",

    "voice":
        "voice_log_id",

    "ban":
        "ban_log_id",

    "left":
        "left_log_id",

    "channel":
        "channel_log_id",

    "role":
        "role_log_id",

    "member":
        "member_log_id",

    "nickname":
        "nickname_log_id",
}


LOG_LABELS = {

    "server":
        "Server",

    "chat":
        "Chat",

    "voice":
        "Voice",

    "ban":
        "Ban",

    "left":
        "Left",

    "channel":
        "Channel",

    "role":
        "Role",

    "member":
        "Member",

    "nickname":
        "Nickname",
}


@bot.tree.command(
    name="log",
    description="دانانی log channel بۆ جۆرێکی دیاریکراو"
)
@app_commands.describe(
    log_type="جۆری log",
    channel="کەناڵی log"
)
@app_commands.choices(
    log_type=[
        app_commands.Choice(
            name="Server",
            value="server"
        ),
        app_commands.Choice(
            name="Chat",
            value="chat"
        ),
        app_commands.Choice(
            name="Voice",
            value="voice"
        ),
        app_commands.Choice(
            name="Ban",
            value="ban"
        ),
        app_commands.Choice(
            name="Left",
            value="left"
        ),
        app_commands.Choice(
            name="Channel",
            value="channel"
        ),
        app_commands.Choice(
            name="Role",
            value="role"
        ),
        app_commands.Choice(
            name="Member",
            value="member"
        ),
        app_commands.Choice(
            name="Nickname",
            value="nickname"
        )
    ]
)
async def log_config(
    interaction: discord.Interaction,
    log_type: str,
    channel: discord.TextChannel
):

    if not await require_config_manager(
        interaction
    ):
        return

    if is_legacy_guild(
        interaction.guild
    ):

        await interaction.response.send_message(
            "⚠️ Config ـی log ـی سێرڤەری کۆن "
            "ناگۆڕدرێت بۆ پاراستنی کۆدەکەی پێشووت.",
            ephemeral=True
        )

        return

    if channel.guild.id != interaction.guild.id:

        await interaction.response.send_message(
            "❌ ئەو کەناڵە هی ئەم سێرڤەرە نییە.",
            ephemeral=True
        )

        return

    field = LOG_NAMES.get(
        log_type
    )

    if not field:

        await interaction.response.send_message(
            "❌ جۆری log دروست نییە.",
            ephemeral=True
        )

        return

    update_config(
        interaction.guild.id,
        **{
            field: channel.id,
            "setup_done": 1
        }
    )

    await interaction.response.send_message(
        f"✅ Log ـی **{LOG_LABELS[log_type]}** "
        f"خرایە سەر {channel.mention}.",
        ephemeral=True
    )


# =========================================================
# 36. /ROLES
# =========================================================

@bot.tree.command(
    name="roles",
    description="دانانی role ـە سەرەکییەکانی bot"
)
@app_commands.describe(
    role_type="جۆری role",
    role="ڕۆڵەکە"
)
@app_commands.choices(
    role_type=[
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
async def roles_config(
    interaction: discord.Interaction,
    role_type: str,
    role: discord.Role
):

    if not await require_config_manager(
        interaction
    ):
        return

    if is_legacy_guild(
        interaction.guild
    ):

        await interaction.response.send_message(
            "⚠️ Role ID ـەکانی سێرڤەری کۆن "
            "ناگۆڕدرێن بۆ ئەوەی behavior ـی کۆن "
            "نەشکێت.",
            ephemeral=True
        )

        return

    if role.guild.id != interaction.guild.id:

        await interaction.response.send_message(
            "❌ ئەو role ـە هی ئەم سێرڤەرە نییە.",
            ephemeral=True
        )

        return

    field = (
        "role_barxakan"
        if role_type == "barxakan"
        else "role_mshaxor"
    )

    update_config(
        interaction.guild.id,
        **{
            field: role.id,
            "setup_done": 1
        }
    )

    await interaction.response.send_message(
        f"✅ ڕۆڵی **{role_type}** بوو بە "
        f"{role.mention}.",
        ephemeral=True
    )


# =========================================================
# 37. /REGRI-ROLES
# =========================================================

@bot.tree.command(
    name="regri-roles",
    description="دیاریکردنی role ـەکانی بەکارهێنانی regri"
)
@app_commands.describe(
    roles="Role ID ـەکان یان mention ـەکان بە space یان comma"
)
async def regri_roles_config(
    interaction: discord.Interaction,
    roles: str
):

    if not await require_config_manager(
        interaction
    ):
        return

    if is_legacy_guild(
        interaction.guild
    ):

        await interaction.response.send_message(
            "⚠️ Regri role ـەکانی سێرڤەری کۆن "
            "ناگۆڕدرێن بۆ پاراستنی behavior ـی کۆن.",
            ephemeral=True
        )

        return

    try:

        role_ids = parse_roles(
            roles
        )

    except ValueError as e:

        await interaction.response.send_message(
            f"❌ {e}",
            ephemeral=True
        )

        return

    valid_role_ids = []

    invalid_role_ids = []

    for role_id in role_ids:

        if interaction.guild.get_role(
            role_id
        ):

            valid_role_ids.append(
                role_id
            )

        else:

            invalid_role_ids.append(
                role_id
            )

    update_config(
        interaction.guild.id,
        regri_allowed_roles=json.dumps(
            valid_role_ids
        ),
        setup_done=1
    )

    mentions = []

    for role_id in valid_role_ids:

        role = interaction.guild.get_role(
            role_id
        )

        if role:
            mentions.append(
                role.mention
            )

    text = (
        "✅ Regri roles نوێکرانەوە:\n"
        + (
            "\n".join(mentions)
            if mentions
            else "هیچ role ـێکی دروست دانەنراوە."
        )
    )

    if invalid_role_ids:

        text += (
            "\n\n⚠️ ئەم ID ـانە لەم سێرڤەرەدا "
            "نەدۆزرایەوە:\n"
            + "\n".join(
                f"`{x}`"
                for x in invalid_role_ids
            )
        )

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


# =========================================================
# 38. /CONFIG
# =========================================================

@bot.tree.command(
    name="config",
    description="پیشاندانی config ـی ئەم سێرڤەرە"
)
async def config_view(
    interaction: discord.Interaction
):

    if not await require_config_manager(
        interaction
    ):
        return

    try:

        guild = interaction.guild

        config = get_guild_config(
            guild
        )

        embed = discord.Embed(
            title="⚙️ Karezma Server Config",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now(
                datetime.timezone.utc
            )
        )

        embed.add_field(
            name="🏠 Server",
            value=(
                f"**Name:** {guild.name}\n"
                f"**ID:** `{guild.id}`\n"
                f"**Original:** "
                f"`{'Yes' if is_legacy_guild(guild) else 'No'}`"
            ),
            inline=False
        )

        # -------------------------------------------------
        # WELCOME
        # -------------------------------------------------

        welcome_channel_id = config.get(
            "welcome_channel_id"
        )

        welcome_channel = (
            guild.get_channel(
                welcome_channel_id
            )
            if welcome_channel_id
            else None
        )

        embed.add_field(
            name="👋 Welcome",
            value=(
                f"**Channel:** "
                f"{welcome_channel.mention if welcome_channel else '❌'}\n"
                f"**Message:** "
                f"`{short_value(config.get('welcome_message'))}`\n"
                f"**Image:** "
                f"`{'Yes' if config.get('welcome_image') else 'No'}`"
            ),
            inline=False
        )

        # -------------------------------------------------
        # LOGS
        # -------------------------------------------------

        log_lines = []

        for key, field in LOG_NAMES.items():

            value = config.get(
                field
            )

            channel = (
                guild.get_channel(
                    value
                )
                if value
                else None
            )

            log_lines.append(
                f"**{LOG_LABELS[key]}:** "
                f"{channel.mention if channel else '❌'}"
            )

        embed.add_field(
            name="📋 Logs",
            value="\n".join(
                log_lines
            ),
            inline=False
        )

        # -------------------------------------------------
        # ROLES
        # -------------------------------------------------

        barxakan_id = config.get(
            "role_barxakan"
        )

        mshaxor_id = config.get(
            "role_mshaxor"
        )

        barxakan = (
            guild.get_role(
                barxakan_id
            )
            if barxakan_id
            else None
        )

        mshaxor = (
            guild.get_role(
                mshaxor_id
            )
            if mshaxor_id
            else None
        )

        allowed_roles = (
            config.get(
                "regri_allowed_roles"
            )
            or set()
        )

        regri_mentions = []

        for role_id in sorted(
            allowed_roles
        ):

            role = guild.get_role(
                role_id
            )

            if role:

                regri_mentions.append(
                    role.mention
                )

            else:

                regri_mentions.append(
                    f"`{role_id}`"
                )

        embed.add_field(
            name="🎭 Roles",
            value=(
                f"**Barxakan:** "
                f"{barxakan.mention if barxakan else '❌'}\n"
                f"**mshaxor:** "
                f"{mshaxor.mention if mshaxor else '❌'}\n"
                f"**Regri:** "
                f"{', '.join(regri_mentions) if regri_mentions else '❌'}"
            ),
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    except Exception:

        print(
            "CONFIG VIEW ERROR:"
        )

        traceback.print_exc()

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ کێشەیەک لە پیشاندانی config "
                "ڕوویدا.",
                ephemeral=True
            )


# =========================================================
# 39. SLASH COMMAND ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):

    original_error = getattr(
        error,
        "original",
        error
    )

    print(
        "\n========== SLASH COMMAND ERROR =========="
    )

    print(
        f"Command: "
        f"{getattr(interaction.command, 'name', 'Unknown')}"
    )

    print(
        f"Guild: "
        f"{getattr(interaction.guild, 'id', 'DM')}"
    )

    traceback.print_exception(
        type(original_error),
        original_error,
        original_error.__traceback__
    )

    print(
        "==========================================\n"
    )

    try:

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ هەڵەیەک لە جێبەجێکردنی "
                "کۆماندەکە ڕوویدا.",
                ephemeral=True
            )

        elif interaction.followup:

            await interaction.followup.send(
                "❌ هەڵەیەک لە جێبەجێکردنی "
                "کۆماندەکە ڕوویدا.",
                ephemeral=True
            )

    except Exception:
        pass


# =========================================================
# 40. GLOBAL ERROR HANDLER
# =========================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"\n========== BOT EVENT ERROR =========="
    )

    print(
        f"Event: {event}"
    )

    traceback.print_exc()

    print(
        "=====================================\n"
    )


# =========================================================
# 41. RUN BOT
# =========================================================

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if TOKEN:

    try:

        bot.run(TOKEN)

    except Exception:

        print(
            "\n❌ BOT START ERROR:"
        )

        traceback.print_exc()

else:

    print(
        "❌ DISCORD_TOKEN environment variable "
        "نەدۆزرایەوە."
    )
