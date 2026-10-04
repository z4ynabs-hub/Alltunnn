import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os
import asyncio
import sqlite3
import json
import traceback

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
# 2. ORIGINAL SERVER SETTINGS (سێرڤەری یەکەم - دەستکاری نەکراوە)
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
NICKNAME_LOG_ID = 867085807445213215

ROLE_BARXAKAN = 864962613582102560
ROLE_MSHAXOR = 863850042123878421

REGRI_ALLOWED_ROLES = {
    1548633166531530802,
    865587893568274482,
    863846779921629216
}

# =========================================================
# 3. MULTI SERVER CONFIG
# =========================================================

CONFIG_DB = "karezma_config.db"
DEVELOPER_IDS = set()

try:
    developers = os.getenv("DEVELOPER_IDS", "")
    if developers.strip():
        DEVELOPER_IDS.update(
            int(x.strip())
            for x in developers.split(",")
            if x.strip().isdigit()
        )
except Exception:
    pass

LEGACY_GUILD_ID = None

# =========================================================
# 3.1 DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    try:
        conn.execute("""
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
            regri_allowed_roles TEXT DEFAULT '[]',
            setup_done INTEGER DEFAULT 0
        )
        """)

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
            "setup_done": "INTEGER"
        }

        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(guild_config)").fetchall()
        }

        for column, column_type in required_columns.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE guild_config ADD COLUMN {column} {column_type}")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS restricted_color_users (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
        """)

        conn.execute("UPDATE guild_config SET regri_allowed_roles = '[]' WHERE regri_allowed_roles IS NULL")
        conn.execute("UPDATE guild_config SET setup_done = 0 WHERE setup_done IS NULL")
        conn.commit()
    finally:
        conn.close()

def get_config(guild_id):
    init_db()
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def ensure_config(guild_id):
    if get_config(guild_id):
        return
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    try:
        conn.execute("""
        INSERT OR IGNORE INTO guild_config (guild_id, regri_allowed_roles, setup_done)
        VALUES (?, ?, ?)
        """, (guild_id, json.dumps([]), 0))
        conn.commit()
    finally:
        conn.close()

def update_config(guild_id, **values):
    ensure_config(guild_id)
    allowed = {
        "welcome_channel_id", "welcome_image", "welcome_message",
        "server_log_id", "chat_log_id", "voice_log_id", "ban_log_id",
        "left_log_id", "channel_log_id", "role_log_id", "member_log_id",
        "nickname_log_id", "role_barxakan", "role_mshaxor",
        "regri_allowed_roles", "setup_done"
    }
    values = {key: value for key, value in values.items() if key in allowed}
    if not values:
        return

    query = ", ".join(f"{key}=?" for key in values)
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    try:
        conn.execute(f"UPDATE guild_config SET {query} WHERE guild_id=?", tuple(values.values()) + (guild_id,))
        conn.commit()
    finally:
        conn.close()

# =========================================================
# 4. LEGACY SERVER
# =========================================================

def is_legacy(guild):
    return guild is not None and LEGACY_GUILD_ID is not None and guild.id == LEGACY_GUILD_ID

def server_config(guild):
    if guild is None:
        return {}

    if is_legacy(guild):
        return {
            "welcome_channel_id": WELCOME_CHANNEL_ID,
            "welcome_image": None,
            "welcome_message": "axer beyt bo karezma",
            "server_log_id": SERVER_LOG_ID,
            "chat_log_id": CHAT_LOG_ID,
            "voice_log_id": VOICE_LOG_ID,
            "ban_log_id": BAN_LOG_ID,
            "left_log_id": LEFT_LOG_ID,
            "channel_log_id": CHANNEL_LOG_ID,
            "role_log_id": ROLE_LOG_ID,
            "member_log_id": MEMBER_LOG_ID,
            "nickname_log_id": NICKNAME_LOG_ID,
            "role_barxakan": ROLE_BARXAKAN,
            "role_mshaxor": ROLE_MSHAXOR,
            "regri_allowed_roles": set(REGRI_ALLOWED_ROLES)
        }

    row = get_config(guild.id)
    if not row:
        return {}

    try:
        allowed = set(json.loads(row.get("regri_allowed_roles") or "[]"))
    except Exception:
        allowed = set()

    row["regri_allowed_roles"] = allowed
    return row

# =========================================================
# 5. OWNER / DEVELOPER
# =========================================================

async def is_developer(user):
    if user.id in DEVELOPER_IDS:
        return True
    try:
        info = await bot.application_info()
        if info.owner and info.owner.id == user.id:
            return True
        team = getattr(info, "team", None)
        if team:
            for member in team.members:
                if member.id == user.id:
                    return True
    except Exception:
        pass
    return False

async def is_config_manager(interaction):
    if not interaction.guild:
        return False
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return await is_developer(interaction.user)

async def require_config_manager(interaction):
    if await is_config_manager(interaction):
        return True
    try:
        await interaction.response.send_message(
            "❌ تەنها **Server Owner** یان **Bot Developer** دەتوانێت ئەم کۆماندە بەکاربهێنێت.",
            ephemeral=True
        )
    except Exception:
        pass
    return False

# =========================================================
# 6. HELPERS
# =========================================================

def get_log_channel(guild, key):
    config = server_config(guild)
    channel_id = config.get(key)
    if not channel_id:
        return None
    return guild.get_channel(channel_id)

async def send_log(guild, key, embed):
    try:
        channel = get_log_channel(guild, key)
        if channel:
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

def add_thumbnail(embed, user):
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass

async def audit_executor(guild, action, target_id=None, delay=1):
    try:
        await asyncio.sleep(delay)
        async for entry in guild.audit_logs(limit=10, action=action):
            if target_id is not None:
                if entry.target is None or getattr(entry.target, "id", None) != target_id:
                    continue
            if entry.created_at:
                now = datetime.datetime.now(datetime.timezone.utc)
                if (now - entry.created_at).total_seconds() > 15:
                    continue
            return entry
    except Exception:
        pass
    return None

def short_value(value, limit=70):
    if value is None:
        return "❌ دانەنراوە"
    value = str(value)
    if len(value) > limit:
        return value[:limit - 3] + "..."
    return value

def parse_roles(value):
    value = value.replace(",", " ")
    result = []
    for item in value.split():
        if not item.isdigit():
            raise ValueError("Role ID ـەکان دەبێت تەنها ژمارە بن.")
        result.append(int(item))
    return sorted(set(result))

# =========================================================
# 7. RESTRICTED USERS
# =========================================================

def restricted_users(guild_id):
    init_db()
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    try:
        rows = conn.execute("SELECT user_id FROM restricted_color_users WHERE guild_id=?", (guild_id,)).fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()

def set_restricted(guild_id, user_id, value):
    init_db()
    conn = sqlite3.connect(CONFIG_DB, timeout=10)
    try:
        if value:
            conn.execute(
                "INSERT OR IGNORE INTO restricted_color_users (guild_id, user_id) VALUES (?, ?)",
                (guild_id, user_id)
            )
        else:
            conn.execute(
                "DELETE FROM restricted_color_users WHERE guild_id=? AND user_id=?",
                (guild_id, user_id)
            )
        conn.commit()
    finally:
        conn.close()

# =========================================================
# 8. READY
# =========================================================

@bot.event
async def on_ready():
    global LEGACY_GUILD_ID
    init_db()

    try:
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            LEGACY_GUILD_ID = channel.guild.id
    except Exception as e:
        print(f"Legacy server detection error: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"Slash sync error: {e}")

    for guild in bot.guilds:
        try:
            role = discord.utils.get(guild.roles, name="Muted")
            if role:
                await sync_muted_permissions(guild, role)
        except Exception as e:
            print(f"Muted sync error in {guild.id}: {e}")

    print("========================================")
    print(f"Bot online: {bot.user}")
    print(f"Servers: {len(bot.guilds)}")
    print(f"Legacy Guild ID: {LEGACY_GUILD_ID}")
    print("========================================")

# =========================================================
# 9. WELCOME EVENT
# =========================================================

@bot.event
async def on_member_join(member):
    config = server_config(member.guild)
    channel_id = config.get("welcome_channel_id")

    if channel_id:
        channel = member.guild.get_channel(channel_id)
        if channel:
            try:
                text = config.get("welcome_message") or "axer beyt bo karezma"
                embed = discord.Embed(
                    title="WELCOME",
                    description=f"{member.mention}\n{text}",
                    color=discord.Color.blurple()
                )
                image = config.get("welcome_image")
                if image:
                    embed.set_image(url=image)
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Welcome send error: {repr(e)}")

    embed = make_embed(
        "📥 Member Joined",
        f"**Member:** {member.mention}\n**Username:** `{member}`\n**ID:** `{member.id}`",
        discord.Color.green()
    )
    add_thumbnail(embed, member)
    await send_log(member.guild, "member_log_id", embed)

# =========================================================
# 10. MEMBER LEFT
# =========================================================

@bot.event
async def on_member_remove(member):
    embed = make_embed(
        "📤 Member Left",
        f"**Member:** {member.mention}\n**Username:** `{member}`\n**ID:** `{member.id}`",
        discord.Color.red()
    )
    add_thumbnail(embed, member)
    await send_log(member.guild, "left_log_id", embed)

# =========================================================
# 11. MEMBER UPDATE
# =========================================================

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        old = before.nick or before.name
        new = after.nick or after.name
        entry = await audit_executor(after.guild, discord.AuditLogAction.member_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown / Self"

        embed = make_embed(
            "✏️ Nickname Changed",
            f"**Member:** {after.mention}\n**Changed By:** {editor}\n**Before:** `{old}`\n**After:** `{new}`",
            discord.Color.gold()
        )
        add_thumbnail(embed, after)
        await send_log(after.guild, "nickname_log_id", embed)

    before_roles = set(before.roles)
    after_roles = set(after.roles)

    added = [r for r in after_roles - before_roles if r.name not in {"@everyone", "Muted"}]
    removed = [r for r in before_roles - after_roles if r.name not in {"@everyone", "Muted"}]

    if added:
        entry = await audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"
        text = "\n".join(f"➕ {r.mention}" for r in added)

        embed = make_embed(
            "➕ Role Added",
            f"**Member:** {after.mention}\n**Given By:** {editor}\n\n{text}",
            discord.Color.green()
        )
        add_thumbnail(embed, after)
        await send_log(after.guild, "member_log_id", embed)

    if removed:
        entry = await audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"
        text = "\n".join(f"➖ {r.mention}" for r in removed)

        embed = make_embed(
            "➖ Role Removed",
            f"**Member:** {after.mention}\n**Removed By:** {editor}\n\n{text}",
            discord.Color.red()
        )
        add_thumbnail(embed, after)
        await send_log(after.guild, "member_log_id", embed)

# =========================================================
# 12. TARGET MEMBER
# =========================================================

async def get_target_member(message):
    if message.mentions:
        for member in message.mentions:
            if bot.user and member.id == bot.user.id:
                continue
            if isinstance(member, discord.Member):
                return member

    if message.reference:
        try:
            msg = await message.channel.fetch_message(message.reference.message_id)
            if bot.user and msg.author.id == bot.user.id:
                return None
            if isinstance(msg.author, discord.Member):
                return msg.author
            return message.guild.get_member(msg.author.id)
        except Exception:
            pass
    return None

# =========================================================
# 13. MUTED
# =========================================================

async def apply_muted_permissions(channel, role):
    try:
        if isinstance(channel, (discord.TextChannel, discord.NewsChannel, discord.ForumChannel)):
            await channel.set_permissions(
                role,
                send_messages=False,
                add_reactions=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
                reason="Karezma Muted"
            )
    except Exception:
        pass

async def sync_muted_permissions(guild, role):
    for channel in guild.channels:
        await apply_muted_permissions(channel, role)

async def get_or_create_muted_role(guild):
    role = discord.utils.get(guild.roles, name="Muted")
    if not role:
        role = await guild.create_role(name="Muted", reason="Karezma mute role")
    await sync_muted_permissions(guild, role)
    return role

# =========================================================
# 14. CHANNEL LOGS
# =========================================================

@bot.event
async def on_guild_channel_create(channel):
    try:
        role = discord.utils.get(channel.guild.roles, name="Muted")
        if role:
            await apply_muted_permissions(channel, role)

        entry = await audit_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "📁 Channel Created",
            f"**Channel:** {channel.mention}\n**Name:** `{channel.name}`\n**ID:** `{channel.id}`\n**Type:** `{channel.type}`\n**Created By:** {user}",
            discord.Color.green()
        )
        await send_log(channel.guild, "channel_log_id", embed)
    except Exception as e:
        print(f"Channel create log error: {repr(e)}")

@bot.event
async def on_guild_channel_delete(channel):
    try:
        entry = await audit_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "🗑️ Channel Deleted",
            f"**Channel:** `#{channel.name}`\n**ID:** `{channel.id}`\n**Type:** `{channel.type}`\n**Deleted By:** {user}",
            discord.Color.red()
        )
        await send_log(channel.guild, "channel_log_id", embed)
    except Exception as e:
        print(f"Channel delete log error: {repr(e)}")

@bot.event
async def on_guild_channel_update(before, after):
    try:
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.category != after.category:
            old = before.category.name if before.category else "None"
            new = after.category.name if after.category else "None"
            changes.append(f"**Category:** `{old}` → `{new}`")
        if before.position != after.position:
            changes.append(f"**Position:** `{before.position}` → `{after.position}`")

        if not changes:
            return

        entry = await audit_executor(after.guild, discord.AuditLogAction.channel_update, after.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "✏️ Channel Updated",
            f"**Channel:** {after.mention}\n**ID:** `{after.id}`\n**Updated By:** {user}\n\n" + "\n".join(changes),
            discord.Color.gold()
        )
        await send_log(after.guild, "channel_log_id", embed)
    except Exception as e:
        print(f"Channel update log error: {repr(e)}")

# =========================================================
# 15. ROLE LOGS
# =========================================================

@bot.event
async def on_guild_role_create(role):
    if role.name == "Muted":
        return
    try:
        entry = await audit_executor(role.guild, discord.AuditLogAction.role_create, role.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "➕ Role Created",
            f"**Role:** {role.mention}\n**Name:** `{role.name}`\n**ID:** `{role.id}`\n**Created By:** {user}",
            discord.Color.green()
        )
        await send_log(role.guild, "role_log_id", embed)
    except Exception as e:
        print(f"Role create log error: {repr(e)}")

@bot.event
async def on_guild_role_delete(role):
    if role.name == "Muted":
        return
    try:
        entry = await audit_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "🗑️ Role Deleted",
            f"**Role:** `{role.name}`\n**ID:** `{role.id}`\n**Deleted By:** {user}",
            discord.Color.red()
        )
        await send_log(role.guild, "role_log_id", embed)
    except Exception as e:
        print(f"Role delete log error: {repr(e)}")

@bot.event
async def on_guild_role_update(before, after):
    if after.name == "Muted":
        return
    try:
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")
        if before.position != after.position:
            changes.append(f"**Position:** `{before.position}` → `{after.position}`")

        if not changes:
            return

        entry = await audit_executor(after.guild, discord.AuditLogAction.role_update, after.id)
        user = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(
            "✏️ Role Updated",
            f"**Role:** {after.mention}\n**ID:** `{after.id}`\n**Updated By:** {user}\n\n" + "\n".join(changes),
            discord.Color.gold()
        )
        await send_log(after.guild, "role_log_id", embed)
    except Exception as e:
        print(f"Role update log error: {repr(e)}")

# =========================================================
# 16. VOICE LOG
# =========================================================

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        embed = make_embed(
            "🔊 Voice Join",
            f"**Member:** {member.mention}\n**Channel:** {after.channel.mention}",
            discord.Color.green()
        )
        add_thumbnail(embed, member)
        await send_log(member.guild, "voice_log_id", embed)
        return

    if before.channel is not None and after.channel is None:
        embed = make_embed(
            "🔇 Voice Leave",
            f"**Member:** {member.mention}\n**Channel:** `{before.channel.name}`",
            discord.Color.red()
        )
        add_thumbnail(embed, member)
        await send_log(member.guild, "voice_log_id", embed)
        return

    if before.channel and after.channel and before.channel.id != after.channel.id:
        embed = make_embed(
            "🔀 Voice Move",
            f"**Member:** {member.mention}\n**From:** `{before.channel.name}`\n**To:** `{after.channel.name}`",
            discord.Color.gold()
        )
        add_thumbnail(embed, member)
        await send_log(member.guild, "voice_log_id", embed)

# =========================================================
# 17. BAN / UNBAN
# =========================================================

@bot.event
async def on_member_ban(guild, user):
    entry = await audit_executor(guild, discord.AuditLogAction.ban, user.id)
    admin = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(
        "🔨 Member Banned",
        f"**Member:** {user.mention}\n**Banned By:** {admin}",
        discord.Color.red()
    )
    add_thumbnail(embed, user)
    await send_log(guild, "ban_log_id", embed)

@bot.event
async def on_member_unban(guild, user):
    entry = await audit_executor(guild, discord.AuditLogAction.unban, user.id)
    admin = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(
        "♻️️ Member Unbanned",
        f"**Member:** {user.mention}\n**Unbanned By:** {admin}",
        discord.Color.green()
    )
    add_thumbnail(embed, user)
    await send_log(guild, "ban_log_id", embed)

# =========================================================
# 18. SERVER UPDATE
# =========================================================

@bot.event
async def on_guild_update(before, after):
    changes = []
    if before.name != after.name:
        changes.append(f"**Server Name:** `{before.name}` → `{after.name}`")

    if not changes:
        return

    entry = await audit_executor(after, discord.AuditLogAction.guild_update)
    user = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(
        "⚙️ Server Updated",
        f"**Updated By:** {user}\n\n" + "\n".join(changes),
        discord.Color.gold()
    )
    if after.icon:
        embed.set_thumbnail(url=after.icon.url)
    await send_log(after, "server_log_id", embed)

# =========================================================
# 19. MESSAGE DELETE
# =========================================================

@bot.event
async def on_message_delete(message):
    if message.author.bot or message.guild is None:
        return

    content = message.content[:1500] if message.content else "*No text content*"

    embed = make_embed(
        "🗑️ Message Deleted",
        f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n\n**Message:**\n```text\n{content}\n```",
        discord.Color.red()
    )
    add_thumbnail(embed, message.author)
    await send_log(message.guild, "chat_log_id", embed)

# =========================================================
# 20. MESSAGE EDIT
# =========================================================

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.guild is None or before.content == after.content:
        return

    old = before.content[:700] if before.content else "*Empty*"
    new = after.content[:700] if after.content else "*Empty*"

    embed = make_embed(
        "✏️ Message Edited",
        f"**Author:** {after.author.mention}\n**Before:**\n```text\n{old}\n```\n**After:**\n```text\n{new}\n```",
        discord.Color.gold()
    )
    add_thumbnail(embed, after.author)
    await send_log(after.guild, "chat_log_id", embed)

# =========================================================
# 21. TEXT COMMANDS
# =========================================================

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    muted = discord.utils.get(message.guild.roles, name="Muted")
    if muted and muted in message.author.roles and not message.author.guild_permissions.administrator:
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
        if len(parts) >= 2 and parts[1].isdigit():
            amount = min(int(parts[1]), 1000)
            try:
                deleted = await message.channel.purge(limit=amount + 1)
                await message.channel.send(f"✅ `{len(deleted)}` نامە سڕایەوە.", delete_after=3)
            except Exception:
                pass
        return

    if command == "mute":
        if not message.author.guild_permissions.administrator:
            return
        target = await get_target_member(message)
        if target:
            try:
                role = await get_or_create_muted_role(message.guild)
                if role not in target.roles:
                    await target.add_roles(role, reason=f"Muted by {message.author}")
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(f"damt daxaa {target.mention}", delete_after=2)
            except Exception:
                pass
        return

    if command == "unmute":
        if not message.author.guild_permissions.administrator:
            return
        target = await get_target_member(message)
        if target:
            try:
                role = discord.utils.get(message.guild.roles, name="Muted")
                if role and role in target.roles:
                    await target.remove_roles(role)
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(f"xwa xerm bnwse dllm basha aqllba amjara {target.mention}", delete_after=2)
            except Exception:
                pass
        return

    if command == "bfra":
        if not message.author.guild_permissions.administrator:
            return
        target = await get_target_member(message)
        if target:
            try:
                await target.ban()
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send(f"Frenraa✈️ {target.mention}", delete_after=2)
            except Exception:
                pass
        return

    if command == "unban":
        if not message.author.guild_permissions.administrator:
            return
        if len(parts) >= 2 and parts[1].isdigit():
            try:
                user = await bot.fetch_user(int(parts[1]))
                await message.guild.unban(user)
                try:
                    await message.delete()
                except Exception:
                    pass
                await message.channel.send("✅ Unban کرا.", delete_after=3)
            except Exception:
                pass
        return

    if command == "lock":
        if not message.author.guild_permissions.manage_channels:
            return
        try:
            await message.channel.set_permissions(message.guild.default_role, send_messages=False)
            await message.delete()
            await message.channel.send("🔒 کەناڵەکە Lock کرا.", delete_after=3)
        except Exception:
            pass
        return

    if command == "unlock":
        if not message.author.guild_permissions.manage_channels:
            return
        try:
            await message.channel.set_permissions(message.guild.default_role, send_messages=None)
            await message.delete()
            await message.channel.send("🔓 کەناڵەکە Unlock کرا.", delete_after=3)
        except Exception:
            pass
        return

# =========================================================
# 22. /STAFF
# =========================================================

@bot.tree.command(name="staff", description="پێدانی ڕۆڵی ستاف بە ئەندام")
@app_commands.choices(
    role_choice=[
        app_commands.Choice(name="Barxakan🐑", value="barxakan"),
        app_commands.Choice(name="mshaxor", value="mshaxor")
    ]
)
async def staff(interaction: discord.Interaction, member: discord.Member, role_choice: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ تەنها ئەدیمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.", ephemeral=True)
        return

    config = server_config(interaction.guild)
    role_id = config.get("role_barxakan") if role_choice == "barxakan" else config.get("role_mshaxor")

    if not role_id:
        await interaction.response.send_message("❌ Role ـەکە هێشتا config نەکراوە.", ephemeral=True)
        return

    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message("❌ ڕۆڵەکە نەدۆزرایەوە.", ephemeral=True)
        return

    try:
        if role in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} پێشتر ئەم ڕۆڵەی هەیە.", ephemeral=True)
        else:
            await member.add_roles(role, reason=f"Staff by {interaction.user}")
            await interaction.response.send_message(f"✅ ڕۆڵی **{role.name}** درا بە {member.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ هەڵە: `{e}`", ephemeral=True)

# =========================================================
# 23. /RANGI-ROLE
# =========================================================

@bot.tree.command(name="rangi-role", description="گۆڕینی ڕەنگی ڕۆڵ")
@app_commands.describe(role="ناوی role یان ID", color="کۆدی ڕەنگ، نموونە #FF0000")
async def rangi_role(interaction: discord.Interaction, role: str, color: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ تەنها ئەدیمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.", ephemeral=True)
        return

    restricted = restricted_users(interaction.guild.id)
    if interaction.user.id in restricted or (is_legacy(interaction.guild) and interaction.user.id in RESTRICTED_COLOR_USERS):
        await interaction.response.send_message("❌ تۆ قەدەغەکراوی لە گۆڕینی ڕەنگ!", ephemeral=True)
        return

    guild = interaction.guild
    target = guild.get_role(int(role)) if role.isdigit() else discord.utils.get(guild.roles, name=role)

    if not target:
        await interaction.response.send_message("❌ ڕۆڵەکە نەدۆزرایەوە.", ephemeral=True)
        return

    owner = interaction.user.id == guild.owner_id
    if target.name == "@everyone" or target.managed or target.is_bot_managed():
        await interaction.response.send_message("❌ ناتوانیت ڕەنگی ئەم ڕۆڵە بگۆڕیت.", ephemeral=True)
        return

    if not owner and target > interaction.user.top_role:
        await interaction.response.send_message("❌ ئەم role ـە لەسەرووی role ـی تۆیە.", ephemeral=True)
        return

    try:
        value = color.strip().lstrip("#")
        if len(value) not in (6, 8):
            raise ValueError("کۆدی ڕەنگ دەبێت 6 یان 8 ژمارەی hex بێت.")

        color_obj = discord.Color(int(value[:6], 16))
        await target.edit(color=color_obj)
        await interaction.response.send_message(f"✅ ڕەنگی **{target.name}** گۆڕدرا.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ هەڵە لە کۆدی ڕەنگ: `{e}`", ephemeral=True)

@rangi_role.autocomplete("role")
async def rangi_role_autocomplete(interaction: discord.Interaction, current: str):
    guild = interaction.guild
    if not guild:
        return []

    owner = interaction.user.id == guild.owner_id
    options = []

    for role in guild.roles:
        if role.name == "@everyone" or role.managed or role.is_bot_managed():
            continue
        if not owner and role > interaction.user.top_role:
            continue
        if current.lower() in role.name.lower():
            options.append(app_commands.Choice(name=role.name, value=str(role.id)))
        if len(options) >= 25:
            break
    return options

# =========================================================
# 24. /REGRI
# =========================================================

@bot.tree.command(name="regri", description="قەدەغەکردن یان لابردنی قەدەغەی ڕەنگ")
@app_commands.choices(
    action=[
        app_commands.Choice(name="Add (قەدەغەکردن)", value="add"),
        app_commands.Choice(name="Remove (ڕێگەپێدان)", value="remove")
    ]
)
async def regri(interaction: discord.Interaction, member: discord.Member, action: str):
    config = server_config(interaction.guild)
    allowed = config.get("regri_allowed_roles") or set()
    owner = interaction.user.id == interaction.guild.owner_id
    has_role = any(role.id in allowed for role in interaction.user.roles)

    if not owner and not has_role:
        await interaction.response.send_message("❌ تۆ دەسەڵاتی ئەم کۆماندە نییت.", ephemeral=True)
        return

    add = action.lower() == "add"
    if is_legacy(interaction.guild):
        if add:
            RESTRICTED_COLOR_USERS.add(member.id)
        else:
            RESTRICTED_COLOR_USERS.discard(member.id)

    set_restricted(interaction.guild.id, member.id, add)
    text = f"🚫 {member.mention} قەدەغەکرا لە گۆڕینی ڕەنگ." if add else f"✅ ڕێگەدرا بە {member.mention} بۆ گۆڕینی ڕەنگ."
    await interaction.response.send_message(text, ephemeral=True)

# =========================================================
# 25. /SETUP
# =========================================================

@bot.tree.command(name="setup", description="دەستپێکردنی config بۆ ئەم سێرڤەرە")
async def setup(interaction: discord.Interaction):
    if not await require_config_manager(interaction):
        return

    if is_legacy(interaction.guild):
        await interaction.response.send_message(
            "ℹ️ ئەمە سێرڤەری کۆنە. Config ـەکانی کۆن هەر وەک خۆی پارێزراون.",
            ephemeral=True
        )
        return

    ensure_config(interaction.guild.id)
    update_config(interaction.guild.id, setup_done=1)

    await interaction.response.send_message(
        "✅ Config ـی سێرڤەرەکە دروست کرا.\n\nئێستا بەکاربهێنە:\n• `/welcome`\n• `/log`\n• `/roles`\n• `/regri-roles`\n• `/config`",
        ephemeral=True
    )

# =========================================================
# 26. /WELCOME (چاککراو - ئۆپشنەکان دڵخواز کراون)
# =========================================================

@bot.tree.command(name="welcome", description="ڕێکخستنی welcome")
@app_commands.describe(
    channel="کەناڵی welcome",
    message="دەقی welcome (ئارەزوومەندانە)",
    image="URL ـی وێنە/GIF یان clear (ئارەزوومەندانە)"
)
async def welcome_config(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str = "axer beyt bo karezma",
    image: str = None
):
    try:
        if not await require_config_manager(interaction):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ ئەم command ـە تەنها لە سێرڤەر کار دەکات.", ephemeral=True)
            return

        if is_legacy(interaction.guild):
            await interaction.response.send_message(
                "⚠️ ئەمە سێرڤەری کۆنە و config ـی کۆنەکە بۆ پاراستنی سێرڤەری یەکەم ناگۆڕدرێت.",
                ephemeral=True
            )
            return

        ensure_config(interaction.guild.id)

        text = message.strip() if message and message.strip() else "axer beyt bo karezma"
        image_value = image.strip() if image and image.strip() else None

        if image_value and image_value.lower() in {"clear", "none", "off", "-", "0"}:
            image_value = None

        update_config(
            interaction.guild.id,
            welcome_channel_id=channel.id,
            welcome_message=text,
            welcome_image=image_value,
            setup_done=1
        )

        await interaction.response.send_message(
            f"✅ **Welcome بە سەرکەوتوویی ڕێکخرا!**\n\n"
            f"📢 **Channel:** {channel.mention}\n"
            f"📝 **Message:** `{short_value(text)}`\n"
            f"🖼️ **Image/GIF:** `{'دانراوە' if image_value else 'نییە'}`",
            ephemeral=True
        )

    except Exception as e:
        traceback.print_exc()
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ هەڵەیەک لە `/welcome` ڕوویدا.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ هەڵەیەک لە `/welcome` ڕوویدا.", ephemeral=True)
        except Exception:
            pass

# =========================================================
# 27. /LOG
# =========================================================

LOG_FIELDS = {
    "server": "server_log_id",
    "chat": "chat_log_id",
    "voice": "voice_log_id",
    "ban": "ban_log_id",
    "left": "left_log_id",
    "channel": "channel_log_id",
    "role": "role_log_id",
    "member": "member_log_id",
    "nickname": "nickname_log_id"
}

@bot.tree.command(name="log", description="دانانی log channel")
@app_commands.choices(
    log_type=[
        app_commands.Choice(name="Server", value="server"),
        app_commands.Choice(name="Chat", value="chat"),
        app_commands.Choice(name="Voice", value="voice"),
        app_commands.Choice(name="Ban", value="ban"),
        app_commands.Choice(name="Left", value="left"),
        app_commands.Choice(name="Channel", value="channel"),
        app_commands.Choice(name="Role", value="role"),
        app_commands.Choice(name="Member", value="member"),
        app_commands.Choice(name="Nickname", value="nickname")
    ]
)
async def log_config(interaction: discord.Interaction, log_type: str, channel: discord.TextChannel):
    try:
        if not await require_config_manager(interaction):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ ئەم command ـە تەنها لە سێرڤەر کار دەکات.", ephemeral=True)
            return

        if is_legacy(interaction.guild):
            await interaction.response.send_message("⚠️ Config ـی سێرڤەری کۆن ناگۆڕدرێت.", ephemeral=True)
            return

        field = LOG_FIELDS.get(log_type)
        if not field:
            await interaction.response.send_message("❌ جۆری Log ـەکە هەڵەیە.", ephemeral=True)
            return

        ensure_config(interaction.guild.id)
        update_config(interaction.guild.id, **{field: channel.id, "setup_done": 1})

        await interaction.response.send_message(f"✅ Log ـی **{log_type}** خرایە سەر {channel.mention}.", ephemeral=True)

    except Exception as e:
        traceback.print_exc()
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ هەڵەیەک لە `/log` ڕوویدا.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ هەڵەیەک لە `/log` ڕوویدا.", ephemeral=True)
        except Exception:
            pass

# =========================================================
# 28. /ROLES
# =========================================================

@bot.tree.command(name="roles", description="دانانی role ـەکانی bot")
@app_commands.choices(
    role_type=[
        app_commands.Choice(name="Barxakan🐑", value="barxakan"),
        app_commands.Choice(name="mshaxor", value="mshaxor")
    ]
)
async def roles_config(interaction: discord.Interaction, role_type: str, role: discord.Role):
    try:
        if not await require_config_manager(interaction):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ ئەم command ـە تەنها لە سێرڤەر کار دەکات.", ephemeral=True)
            return

        if is_legacy(interaction.guild):
            await interaction.response.send_message("⚠️ Role ـەکانی سێرڤەری کۆن ناگۆڕدرێن.", ephemeral=True)
            return

        field = "role_barxakan" if role_type == "barxakan" else "role_mshaxor"
        ensure_config(interaction.guild.id)
        update_config(interaction.guild.id, **{field: role.id, "setup_done": 1})

        await interaction.response.send_message(f"✅ **{role_type}** بوو بە {role.mention}.", ephemeral=True)

    except Exception as e:
        traceback.print_exc()
        try:
            await interaction.response.send_message("❌ هەڵەیەک لە `/roles` ڕوویدا.", ephemeral=True)
        except Exception:
            pass

# =========================================================
# 29. /REGRI-ROLES
# =========================================================

@bot.tree.command(name="regri-roles", description="دیاریکردنی role ـەکانی regri")
@app_commands.describe(roles="Role ID ـەکان بە space یان comma")
async def regri_roles_config(interaction: discord.Interaction, roles: str):
    try:
        if not await require_config_manager(interaction):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ ئەم command ـە تەنها لە سێرڤەر کار دەکات.", ephemeral=True)
            return

        if is_legacy(interaction.guild):
            await interaction.response.send_message("⚠️ Regri role ـەکانی سێرڤەری کۆن ناگۆڕدرێن.", ephemeral=True)
            return

        try:
            role_ids = parse_roles(roles)
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        ensure_config(interaction.guild.id)
        update_config(interaction.guild.id, regri_allowed_roles=json.dumps(role_ids), setup_done=1)

        mentions = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            mentions.append(role.mention if role else f"`{role_id}`")

        await interaction.response.send_message(
            "✅ Regri roles نوێکرانەوە:\n" + ("\n".join(mentions) if mentions else "هیچ role ـێک نییە."),
            ephemeral=True
        )

    except Exception as e:
        traceback.print_exc()
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ هەڵەیەک لە `/regri-roles` ڕوویدا.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ هەڵەیەک لە `/regri-roles` ڕوویدا.", ephemeral=True)
        except Exception:
            pass

# =========================================================
# 30. /CONFIG
# =========================================================

@bot.tree.command(name="config", description="پیشاندانی config ـی سێرڤەر")
async def config_view(interaction: discord.Interaction):
    try:
        if not await require_config_manager(interaction):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ ئەم command ـە تەنها لە سێرڤەر کار دەکات.", ephemeral=True)
            return

        guild = interaction.guild
        config = server_config(guild)

        embed = discord.Embed(title="⚙️ Karezma Server Config", color=discord.Color.blurple())

        embed.add_field(
            name="🏠 Server",
            value=f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Original:** `{'Yes' if is_legacy(guild) else 'No'}`",
            inline=False
        )

        welcome_id = config.get("welcome_channel_id")
        welcome_channel = guild.get_channel(welcome_id) if welcome_id else None

        embed.add_field(
            name="👋 Welcome",
            value=(
                f"**Channel:** {welcome_channel.mention if welcome_channel else '❌'}\n"
                f"**Message:** `{short_value(config.get('welcome_message'))}`\n"
                f"**Image:** `{'Yes' if config.get('welcome_image') else 'No'}`"
            ),
            inline=False
        )

        logs = []
        for name, field in LOG_FIELDS.items():
            channel_id = config.get(field)
            channel = guild.get_channel(channel_id) if channel_id else None
            logs.append(f"**{name}:** {channel.mention if channel else '❌'}")

        embed.add_field(name="📋 Logs", value="\n".join(logs), inline=False)

        barxakan_id = config.get("role_barxakan")
        mshaxor_id = config.get("role_mshaxor")
        barxakan = guild.get_role(barxakan_id) if barxakan_id else None
        mshaxor = guild.get_role(mshaxor_id) if mshaxor_id else None

        allowed = config.get("regri_allowed_roles") or set()
        regri = []
        for role_id in allowed:
            role = guild.get_role(role_id)
            regri.append(role.mention if role else f"`{role_id}`")

        embed.add_field(
            name="🎭 Roles",
            value=(
                f"**Barxakan:** {barxakan.mention if barxakan else '❌'}\n"
                f"**mshaxor:** {mshaxor.mention if mshaxor else '❌'}\n"
                f"**Regri:** {', '.join(regri) if regri else '❌'}"
            ),
            inline=False
        )

        embed.add_field(
            name="🔧 Setup",
            value="✅ Completed" if config.get("setup_done") else "❌ Not completed",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        traceback.print_exc()
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ هەڵەیەک لە `/config` ڕوویدا.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ هەڵەیەک لە `/config` ڕوویدا.", ephemeral=True)
        except Exception:
            pass

# =========================================================
# 31. SLASH COMMAND ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original_error = getattr(error, "original", error)

    print("\n" + "=" * 70)
    print("SLASH COMMAND ERROR")
    print(f"Command: {getattr(interaction.command, 'name', 'Unknown')}")
    print(f"Guild: {getattr(interaction.guild, 'id', None)}")
    print(f"User: {getattr(interaction.user, 'id', None)}")
    print(f"Error Type: {type(original_error).__name__}")
    print(f"Error: {original_error}")
    print("\nFULL TRACEBACK:")
    traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
    print("=" * 70 + "\n")

    try:
        text = "❌ تۆ دەسەڵاتی بەکارهێنانی ئەم کۆماندە نییت." if isinstance(error, app_commands.CheckFailure) else "❌ هەڵەیەک لە جێبەجێکردنی کۆماندەکە ڕوویدا."
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)
    except Exception:
        pass

# =========================================================
# 32. RUN BOT
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN environment variable نەدۆزرایەوە.")
