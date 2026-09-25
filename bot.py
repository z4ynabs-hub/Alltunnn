import discord
from discord.ext import commands
import datetime
import os


# =========================================================
# 1. BOT SETTINGS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.bans = True

bot = commands.Bot(
    command_prefix="",
    intents=intents,
    case_insensitive=True
)


# =========================================================
# 2. IDS (CHANNELS)
# =========================================================

WELCOME_CHANNEL_ID = 863844473851215893

SERVER_LOG_ID       = 863857583146926090
CHAT_LOG_ID         = 863857498719780874
VOICE_LOG_ID        = 863857530941341718
BAN_UNBAN_LOG_ID    = 867084771477553183
LEFT_LOG_ID         = 863857555948175381
CHANNEL_LOG_ID      = 867085144061771806
ROLE_LOG_ID         = 867085174662889503
MEMBER_LOG_ID       = 867085715787612220
NICKNAME_LOG_ID     = 867085807445213215


# =========================================================
# 3. READY
# =========================================================

@bot.event
async def on_ready():
    print(f"بۆتەکە بە سەرکەوتوویی چالاک بوو وەک: {bot.user}")
    print(f"Bot ID: {bot.user.id}")


# =========================================================
# 4. WELCOME
# =========================================================

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        print("❌ Welcome channel not found.")
        return

    try:
        embed = discord.Embed(
            title="WELCOME",
            description=(
                f"{member.mention}\n"
                f"baxer beyt bo karezma"
            )
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)
        print(f"✅ Welcome sent for {member}")
    except Exception as e:
        print(f"❌ Welcome error: {repr(e)}")


# =========================================================
# 5. LOGGING EVENTS SYSTEM
# =========================================================

# --- CHAT LOG: DELETE ---
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    
    channel = bot.get_channel(CHAT_LOG_ID)
    if channel:
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="Author", value=f"{message.author} ({message.author.mention})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        if message.content:
            embed.add_field(name="Content", value=message.content[:1024], inline=False)
        await channel.send(embed=embed)

# --- CHAT LOG: EDIT ---
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    
    channel = bot.get_channel(CHAT_LOG_ID)
    if channel:
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange(), timestamp=datetime.datetime.now())
        embed.add_field(name="Author", value=f"{before.author} ({before.author.mention})", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)
        embed.add_field(name="Before", value=before.content[:1024] if before.content else "None", inline=False)
        embed.add_field(name="After", value=after.content[:1024] if after.content else "None", inline=False)
        await channel.send(embed=embed)

# --- VOICE LOG ---
@bot.event
async def on_voice_state_update(member, before, after):
    channel = bot.get_channel(VOICE_LOG_ID)
    if not channel:
        return

    embed = discord.Embed(timestamp=datetime.datetime.now())
    if before.channel is None and after.channel is not None:
        embed.color = discord.Color.green()
        embed.title = "🔊 Voice Channel Joined"
        embed.description = f"{member.mention} joined **{after.channel.name}**"
        await channel.send(embed=embed)
    elif before.channel is not None and after.channel is None:
        embed.color = discord.Color.red()
        embed.title = "🔇 Voice Channel Left"
        embed.description = f"{member.mention} left **{before.channel.name}**"
        await channel.send(embed=embed)
    elif before.channel != after.channel and before.channel is not None and after.channel is not None:
        embed.color = discord.Color.blue()
        embed.title = "🔀 Voice Channel Switched"
        embed.description = f"{member.mention} moved from **{before.channel.name}** to **{after.channel.name}**"
        await channel.send(embed=embed)

# --- LEFT LOG ---
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEFT_LOG_ID)
    if channel:
        embed = discord.Embed(title="📤 Member Left", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member", value=f"{member} ({member.mention})", inline=False)
        await channel.send(embed=embed)

# --- BAN / UNBAN LOG ---
@bot.event
async def on_member_ban(guild, user):
    channel = bot.get_channel(BAN_UNBAN_LOG_ID)
    if channel:
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.dark_red(), timestamp=datetime.datetime.now())
        embed.add_field(name="User", value=f"{user} ({user.mention})", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_member_unban(guild, user):
    channel = bot.get_channel(BAN_UNBAN_LOG_ID)
    if channel:
        embed = discord.Embed(title="🔓 Member Unbanned", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="User", value=f"{user} ({user.mention})", inline=False)
        await channel.send(embed=embed)

# --- CHANNEL LOG ---
@bot.event
async def on_guild_channel_create(channel):
    try:
        mute_role = discord.utils.get(channel.guild.roles, name="Muted")
        if mute_role:
            await apply_muted_permissions(channel, mute_role)
    except Exception as e:
        print(f"New channel mute permission error: {e}")

    log_channel = bot.get_channel(CHANNEL_LOG_ID)
    if log_channel:
        embed = discord.Embed(title="📁 Channel Created", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="Name", value=channel.name, inline=False)
        embed.add_field(name="Type", value=str(channel.type), inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    log_channel = bot.get_channel(CHANNEL_LOG_ID)
    if log_channel:
        embed = discord.Embed(title="🗑️ Channel Deleted", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="Name", value=channel.name, inline=False)
        await log_channel.send(embed=embed)

# --- ROLE LOG ---
@bot.event
async def on_guild_role_create(role):
    channel = bot.get_channel(ROLE_LOG_ID)
    if channel:
        embed = discord.Embed(title="✨ Role Created", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed.add_field(name="Role", value=role.name, inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_guild_role_delete(role):
    channel = bot.get_channel(ROLE_LOG_ID)
    if channel:
        embed = discord.Embed(title="❌ Role Deleted", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="Role", value=role.name, inline=False)
        await channel.send(embed=embed)

# --- NICKNAME & MEMBER LOG ---
@bot.event
async def on_member_update(before, after):
    # Nickname Change Log
    if before.nick != after.nick:
        channel = bot.get_channel(NICKNAME_LOG_ID)
        if channel:
            embed = discord.Embed(title="✏️ Nickname Changed", color=discord.Color.gold(), timestamp=datetime.datetime.now())
            embed.add_field(name="Member", value=f"{after.mention}", inline=False)
            embed.add_field(name="Old Nick", value=before.nick if before.nick else "None", inline=True)
            embed.add_field(name="New Nick", value=after.nick if after.nick else "None", inline=True)
            await channel.send(embed=embed)
            
    # Member Role Update Log
    if before.roles != after.roles:
        channel = bot.get_channel(MEMBER_LOG_ID)
        if channel:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(title="🛡️ Member Roles Updated", color=discord.Color.blue(), timestamp=datetime.datetime.now())
                embed.add_field(name="Member", value=f"{after.mention}", inline=False)
                if added_roles:
                    embed.add_field(name="Added Roles", value=", ".join([r.mention for r in added_roles]), inline=False)
                if removed_roles:
                    embed.add_field(name="Removed Roles", value=", ".join([r.mention for r in removed_roles]), inline=False)
                await channel.send(embed=embed)


# =========================================================
# 6. GET TARGET FROM TAG OR REPLY
# =========================================================

async def get_target_member(message):
    if message.mentions:
        member = message.mentions[0]
        if isinstance(member, discord.Member):
            return member

    if message.reference:
        try:
            referenced_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            if isinstance(referenced_message.author, discord.Member):
                return referenced_message.author

            member = message.guild.get_member(
                referenced_message.author.id
            )
            return member
        except Exception as e:
            print(f"Reply target error: {repr(e)}")

    return None


# =========================================================
# 7. MUTED ROLE FUNCTIONS
# =========================================================

async def apply_muted_permissions(channel, mute_role):
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
        elif isinstance(channel, discord.VoiceChannel):
            await channel.set_permissions(
                mute_role,
                speak=False,
                stream=False,
                reason="Karezma Muted role"
            )
    except Exception as e:
        print(f"Muted permission error in {channel.name}: {e}")


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
# 8. MAIN COMMAND SYSTEM
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
                f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.",
                delete_after=5
            )
            return

        if len(parts) < 2 or not parts[1].isdigit():
            await message.channel.send(
                "❌ نموونە: `Safika 1000`",
                delete_after=5
            )
            return

        amount = int(parts[1])
        if amount <= 0:
            await message.channel.send(
                "❌ ژمارەکە دەبێت زیاتر لە 0 بێت.",
                delete_after=5
            )
            return

        amount = min(amount, 1000)

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
            print(f"Safika error: {e}")
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
                f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Mute بەکاربهێنێت.",
                delete_after=5
            )
            return

        target = await get_target_member(message)
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
            mute_role = await get_or_create_muted_role(message.guild)
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
            print(f"Mute error: {e}")
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
                f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Unmute بەکاربهێنێت.",
                delete_after=5
            )
            return

        target = await get_target_member(message)
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
            print(f"Unmute error: {e}")
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
                f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Bfra بەکاربهێنێت.",
                delete_after=5
            )
            return

        target = await get_target_member(message)
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
            print(f"Bfra error: {e}")
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
                f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Unban بەکاربهێنێت.",
                delete_after=5
            )
            return

        user = None
        if len(parts) >= 2 and parts[1].isdigit():
            try:
                user = await bot.fetch_user(int(parts[1]))
            except:
                user = None
        elif message.reference:
            try:
                referenced_message = await message.channel.fetch_message(
                    message.reference.message_id
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
            print(f"Unban error: {e}")
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
                f"❌ {message.author.mention} تۆ دەسەڵاتی Lock کردنی کەناڵت نییە.",
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
            print(f"Lock error: {e}")
        return


    # =====================================================
    # UNLOCK
    # =====================================================
    if command == "unlock":
        if not message.author.guild_permissions.manage_channels:
            await message.channel.send(
                f"❌ {message.author.mention} تۆ دەسەڵاتی Unlock کردنی کەناڵت نییە.",
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
            print(f"Unlock error: {e}")
        return


# =========================================================
# 9. ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(
        error,
        (
            commands.CommandNotFound,
            commands.MissingPermissions
        )
    ):
        return

    print(f"Command error: {repr(error)}")


# =========================================================
# 10. RUN BOT
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing."
    )

bot.run(TOKEN)
