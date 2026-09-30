import discord
from discord.ext import commands
import datetime
import os
import asyncio

=========================================================

1. BOT SETTINGS

=========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="",
    intents=intents,
    case_insensitive=True
)

# Global dictionary to manage color change restrictions via /regri
RESTRICTED_COLOR_USERS = set()

=========================================================

2. IDs

=========================================================

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

STAFF_ROLE_1 = 995343531482812488
STAFF_ROLE_2 = 863850042123878421

REGRI_ALLOWED_ROLES = {
    1548633166531530802,
    865587893568274482,
    863846779921629216
}

=========================================================

3. LOG HELPERS

=========================================================

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
    embed.set_footer(text="Karezma Logs")  
    return embed

def add_user_thumbnail(embed, user):
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass

=========================================================

4. AUDIT LOG HELPER

=========================================================

async def get_audit_executor(guild, action, target_id=None, delay=1.0):
    try:  
        await asyncio.sleep(delay)  
        async for entry in guild.audit_logs(limit=10, action=action):  
            if target_id is not None:  
                if entry.target is None:  
                    continue  
                if getattr(entry.target, "id", None) != target_id:  
                    continue  
            if entry.created_at:  
                now = datetime.datetime.now(datetime.timezone.utc)  
                difference = (now - entry.created_at).total_seconds()  
                if difference > 15:  
                    continue  
            return entry  
    except discord.Forbidden:  
        print("❌ Bot cannot read Audit Log.")  
    except Exception as e:  
        print(f"Audit log error: {e}")  
    return None

=========================================================

5. READY

=========================================================

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print("✅ Slash commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    print(f"بۆتەکە بە سەرکەوتوویی چالاک بوو وەک: {bot.user}")  
    print(f"Bot ID: {bot.user.id}")  

    embed = make_embed(  
        "🟢 BOT ONLINE",  
        f"**Bot:** {bot.user.mention}\n"  
        f"**ID:** `{bot.user.id}`",  
        discord.Color.green()  
    )  
    add_user_thumbnail(embed, bot.user)  
    await send_log(SERVER_LOG_ID, embed)

=========================================================

6. WELCOME

=========================================================

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)  
    if channel is None:  
        print("❌ Welcome channel not found.")  
    else:  
        try:  
            embed = discord.Embed(  
                title="WELCOME",  
                description=(f"{member.mention}\naxer beyt bo karezma")  
            )  
            embed.set_thumbnail(url=member.display_avatar.url)  
            await channel.send(embed=embed)  
            print(f"✅ Welcome sent for {member}")  
        except Exception as e:  
            print(f"❌ Welcome error: {repr(e)}")  

    embed = make_embed(  
        "📥 Member Joined",  
        f"**Member:** {member.mention}\n"  
        f"**Username:** `{member}`\n"  
        f"**ID:** `{member.id}`",  
        discord.Color.green()  
    )  
    add_user_thumbnail(embed, member)  
    await send_log(MEMBER_LOG_ID, embed)

=========================================================

7. MEMBER LEFT

=========================================================

@bot.event
async def on_member_remove(member):
    embed = make_embed(  
        "📤 Member Left",  
        f"**Member:** {member.mention}\n"  
        f"**Username:** `{member}`\n"  
        f"**ID:** `{member.id}`",  
        discord.Color.red()  
    )  
    add_user_thumbnail(embed, member)  
    await send_log(LEFT_LOG_ID, embed)

=========================================================

8. MEMBER UPDATE

=========================================================

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:  
        old_nick = before.nick if before.nick else before.name  
        new_nick = after.nick if after.nick else after.name  

        entry = await get_audit_executor(after.guild, discord.AuditLogAction.member_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown / Self"

        embed = make_embed(  
            "✏️ Nickname Changed",  
            f"**Member:** {after.mention}\n"  
            f"**Changed By:** {editor}\n"  
            f"**Before:** `{old_nick}`\n"  
            f"**After:** `{new_nick}`",  
            discord.Color.gold()  
        )  
        add_user_thumbnail(embed, after)  
        await send_log(NICKNAME_LOG_ID, embed)  

    before_roles = set(before.roles)  
    after_roles = set(after.roles)  
    added_roles = after_roles - before_roles  
    removed_roles = before_roles - after_roles  

    real_added_roles = [role for role in added_roles if role.name not in ["@everyone", "Muted"]]  
    if real_added_roles:  
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"

        roles_text = "\n".join(f"➕ {role.mention}" for role in real_added_roles)  
        embed = make_embed(  
            "➕ Role Added",  
            f"**Member:** {after.mention}\n**Given By:** {editor}\n\n{roles_text}",  
            discord.Color.green()  
        )  
        add_user_thumbnail(embed, after)  
        await send_log(MEMBER_LOG_ID, embed)  

    real_removed_roles = [role for role in removed_roles if role.name not in ["@everyone", "Muted"]]  
    if real_removed_roles:  
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"

        roles_text = "\n".join(f"➖ {role.mention}" for role in real_removed_roles)  
        embed = make_embed(  
            "➖ Role Removed",  
            f"**Member:** {after.mention}\n**Removed By:** {editor}\n\n{roles_text}",  
            discord.Color.red()  
        )  
        add_user_thumbnail(embed, after)  
        await send_log(MEMBER_LOG_ID, embed)

=========================================================

9. GET TARGET FROM TAG OR REPLY

=========================================================

async def get_target_member(message):
    if message.mentions:  
        member = message.mentions[0]  
        if isinstance(member, discord.Member):  
            return member  

    if message.reference:  
        try:  
            referenced_message = await message.channel.fetch_message(message.reference.message_id)  
            if isinstance(referenced_message.author, discord.Member):  
                return referenced_message.author  
            member = message.guild.get_member(referenced_message.author.id)  
            return member  
        except Exception as e:  
            print(f"Reply target error: {repr(e)}")  
    return None

=========================================================

10. MUTED ROLE

=========================================================

async def apply_muted_permissions(channel, mute_role):
    try:  
        if isinstance(channel, (discord.TextChannel, discord.NewsChannel, discord.ForumChannel)):  
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
    mute_role = discord.utils.get(guild.roles, name="Muted")  
    if mute_role:  
        return mute_role  
    mute_role = await guild.create_role(name="Muted", reason="Karezma mute role")  
    for channel in guild.channels:  
        await apply_muted_permissions(channel, mute_role)  
    return mute_role

=========================================================

11 & 12. CHANNEL CREATE LOG

=========================================================

@bot.event
async def on_guild_channel_create(channel):
    try:  
        mute_role = discord.utils.get(channel.guild.roles, name="Muted")  
        if mute_role:  
            await apply_muted_permissions(channel, mute_role)  

        entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        creator = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(  
            "📁 Channel Created",  
            f"**Channel:** {channel.mention}\n"  
            f"**Name:** `{channel.name}`\n"  
            f"**ID:** `{channel.id}`\n"  
            f"**Type:** `{channel.type}`\n"  
            f"**Created By:** {creator}",  
            discord.Color.green()  
        )  
        await send_log(CHANNEL_LOG_ID, embed)  
    except Exception as e:  
        print(f"New channel error: {e}")

=========================================================

13. CHANNEL DELETE LOG

=========================================================

@bot.event
async def on_guild_channel_delete(channel):
    entry = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
    deleter = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(  
        "🗑️ Channel Deleted",  
        f"**Channel:** `#{channel.name}`\n"  
        f"**ID:** `{channel.id}`\n"  
        f"**Type:** `{channel.type}`\n"  
        f"**Deleted By:** {deleter}",  
        discord.Color.red()  
    )  
    await send_log(CHANNEL_LOG_ID, embed)

=========================================================

14. CHANNEL UPDATE LOG

=========================================================

@bot.event
async def on_guild_channel_update(before, after):
    changes = []  
    if before.name != after.name:  
        changes.append(f"**Name:** `{before.name}` → `{after.name}`")  
    if before.category != after.category:  
        old_category = before.category.name if before.category else "None"  
        new_category = after.category.name if after.category else "None"  
        changes.append(f"**Category:** `{old_category}` → `{new_category}`")  
    if before.position != after.position:  
        changes.append(f"**Position:** `{before.position}` → `{after.position}`")  

    if changes:  
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.channel_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(  
            "✏️ Channel Updated",  
            f"**Channel:** {after.mention}\n"  
            f"**ID:** `{after.id}`\n"  
            f"**Updated By:** {editor}\n\n"  
            + "\n".join(changes),  
            discord.Color.gold()  
        )  
        await send_log(CHANNEL_LOG_ID, embed)

=========================================================

15. ROLE CREATE

=========================================================

@bot.event
async def on_guild_role_create(role):
    if role.name == "Muted":  
        return  

    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_create, role.id)
    creator = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(  
        "➕ Role Created",  
        f"**Role:** {role.mention}\n"  
        f"**Name:** `{role.name}`\n"  
        f"**ID:** `{role.id}`\n"  
        f"**Created By:** {creator}",  
        discord.Color.green()  
    )  
    await send_log(ROLE_LOG_ID, embed)

=========================================================

16. ROLE DELETE

=========================================================

@bot.event
async def on_guild_role_delete(role):
    if role.name == "Muted":  
        return  

    entry = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
    deleter = entry.user.mention if entry and entry.user else "Unknown"

    embed = make_embed(  
        "🗑️ Role Deleted",  
        f"**Role:** `{role.name}`\n"  
        f"**ID:** `{role.id}`\n"  
        f"**Deleted By:** {deleter}",  
        discord.Color.red()  
    )  
    await send_log(ROLE_LOG_ID, embed)

=========================================================

17. ROLE UPDATE

=========================================================

@bot.event
async def on_guild_role_update(before, after):
    if after.name == "Muted":  
        return  

    changes = []  
    if before.name != after.name:  
        changes.append(f"**Name:** `{before.name}` → `{after.name}`")  
    if before.color != after.color:  
        changes.append(f"**Color:** `{before.color}` → `{after.color}`")  
    if before.position != after.position:  
        changes.append(f"**Position:** `{before.position}` → `{after.position}`")  
    if before.hoist != after.hoist:  
        changes.append(f"**Hoisted:** `{before.hoist}` → `{after.hoist}`")  
    if before.mentionable != after.mentionable:  
        changes.append(f"**Mentionable:** `{before.mentionable}` → `{after.mentionable}`")  

    if changes:  
        entry = await get_audit_executor(after.guild, discord.AuditLogAction.role_update, after.id)
        editor = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(  
            "✏️ Role Updated",  
            f"**Role:** {after.mention}\n"  
            f"**ID:** `{after.id}`\n"  
            f"**Updated By:** {editor}\n\n"  
            + "\n".join(changes),  
            discord.Color.gold()  
        )  
        await send_log(ROLE_LOG_ID, embed)

=========================================================

18. VOICE LOG

=========================================================

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:  
        embed = make_embed("🔊 Voice Join", f"**Member:** {member.mention}\n**Channel:** {after.channel.mention}\n**ID:** `{after.channel.id}`", discord.Color.green())  
        add_user_thumbnail(embed, member)  
        await send_log(VOICE_LOG_ID, embed)  
        return  

    if before.channel is not None and after.channel is None:  
        embed = make_embed("🔇 Voice Leave", f"**Member:** {member.mention}\n**Channel:** `{before.channel.name}`\n**ID:** `{before.channel.id}`", discord.Color.red())  
        add_user_thumbnail(embed, member)  
        await send_log(VOICE_LOG_ID, embed)  
        return  

    if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:  
        embed = make_embed("🔀 Voice Move", f"**Member:** {member.mention}\n**From:** `{before.channel.name}`\n**To:** `{after.channel.name}`", discord.Color.gold())  
        add_user_thumbnail(embed, member)  
        await send_log(VOICE_LOG_ID, embed)  

    if before.mute != after.mute:  
        entry = await get_audit_executor(member.guild, discord.AuditLogAction.member_update, member.id)
        admin = entry.user.mention if entry and entry.user else "System/Unknown"
        status = "🔇 Server Muted" if after.mute else "🔊 Server Unmuted"  
        embed = make_embed(status, f"**Member:** {member.mention}\n**Done By:** {admin}\n**Status:** `{after.mute}`", discord.Color.red() if after.mute else discord.Color.green())  
        add_user_thumbnail(embed, member)  
        await send_log(VOICE_LOG_ID, embed)  

    if before.deaf != after.deaf:  
        entry = await get_audit_executor(member.guild, discord.AuditLogAction.member_update, member.id)
        admin = entry.user.mention if entry and entry.user else "System/Unknown"
        status = "🔇 Server Deafened" if after.deaf else "🔊 Server Undeafened"  
        embed = make_embed(status, f"**Member:** {member.mention}\n**Done By:** {admin}\n**Status:** `{after.deaf}`", discord.Color.red() if after.deaf else discord.Color.green())  
        add_user_thumbnail(embed, member)  
        await send_log(VOICE_LOG_ID, embed)

=========================================================

19. BAN LOG

=========================================================

@bot.event
async def on_member_ban(guild, user):
    entry = await get_audit_executor(guild, discord.AuditLogAction.ban, user.id)  
    admin = entry.user if entry else None  
    admin_text = admin.mention if admin else "Unknown"  

    embed = make_embed(  
        "🔨 Member Banned",  
        f"**Member:** {user.mention}\n"  
        f"**Username:** `{user}`\n"  
        f"**ID:** `{user.id}`\n\n"  
        f"**Banned By:** {admin_text}",  
        discord.Color.red()  
    )  
    add_user_thumbnail(embed, user)  
    await send_log(BAN_LOG_ID, embed)

=========================================================

20. UNBAN LOG

=========================================================

@bot.event
async def on_member_unban(guild, user):
    entry = await get_audit_executor(guild, discord.AuditLogAction.unban, user.id)  
    admin = entry.user if entry else None  
    admin_text = admin.mention if admin else "Unknown"  

    embed = make_embed(  
        "♻️ Member Unbanned",  
        f"**Member:** {user.mention}\n"  
        f"**Username:** `{user}`\n"  
        f"**ID:** `{user.id}`\n\n"  
        f"**Unbanned By:** {admin_text}",  
        discord.Color.green()  
    )  
    add_user_thumbnail(embed, user)  
    await send_log(BAN_LOG_ID, embed)

=========================================================

21. SERVER UPDATE

=========================================================

@bot.event
async def on_guild_update(before, after):
    changes = []  
    if before.name != after.name:  
        changes.append(f"**Server Name:** `{before.name}` → `{after.name}`")  
    if before.description != after.description:  
        changes.append("**Description changed**")  
    if before.icon != after.icon:  
        changes.append("**Server Icon changed**")  
    if before.banner != after.banner:  
        changes.append("**Server Banner changed**")  
    if before.verification_level != after.verification_level:  
        changes.append(f"**Verification:** `{before.verification_level}` → `{after.verification_level}`")  

    if changes:  
        entry = await get_audit_executor(after, discord.AuditLogAction.guild_update)
        editor = entry.user.mention if entry and entry.user else "Unknown"

        embed = make_embed(  
            "⚙️ Server Updated",  
            f"**Updated By:** {editor}\n\n" + "\n".join(changes),  
            discord.Color.gold()  
        )  
        if after.icon:  
            embed.set_thumbnail(url=after.icon.url)  
        await send_log(SERVER_LOG_ID, embed)

=========================================================

22. MESSAGE DELETE LOG

=========================================================

@bot.event
async def on_message_delete(message):
    if message.author.bot or message.guild is None:  
        return  

    content = message.content if message.content else "*No text content*"  
    if len(content) > 1500:  
        content = content[:1500] + "..."  

    entry = await get_audit_executor(message.guild, discord.AuditLogAction.message_delete, message.author.id)  
    deleter = entry.user if entry else None  
    deleter_text = deleter.mention if deleter else "Unknown / Self"  

    embed = make_embed(  
        "🗑️ Message Deleted",  
        f"**Author:** {message.author.mention}\n"  
        f"**Channel:** {message.channel.mention}\n"  
        f"**Deleted By:** {deleter_text}\n\n"  
        f"**Message:**\n```text\n{content}\n```",  
        discord.Color.red()  
    )  
    add_user_thumbnail(embed, message.author)  
    await send_log(CHAT_LOG_ID, embed)

=========================================================

23. MESSAGE EDIT

=========================================================

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.guild is None or before.content == after.content:  
        return  

    old_content = before.content if before.content else "*Empty*"  
    new_content = after.content if after.content else "*Empty*"  

    if len(old_content) > 700: old_content = old_content[:700] + "..."  
    if len(new_content) > 700: new_content = new_content[:700] + "..."  

    embed = make_embed(  
        "✏️ Message Edited",  
        f"**Author:** {after.author.mention}\n"  
        f"**Channel:** {after.channel.mention}\n\n"  
        f"**Before:**\n```text\n{old_content}\n```\n"  
        f"**After:**\n```text\n{new_content}\n```",  
        discord.Color.gold()  
    )  
    add_user_thumbnail(embed, after.author)  
    await send_log(CHAT_LOG_ID, embed)

=========================================================

24. MAIN COMMAND SYSTEM (PREFIX COMMANDS)

=========================================================

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:  
        return  

    content = message.content.strip()  
    if not content:  
        return  

    parts = content.split()  
    command = parts[0].lower()  

    # STAFF COMMAND
    if command == "staff":
        if not message.author.guild_permissions.administrator:
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.", delete_after=5)
            return

        target = await get_target_member(message)
        if target is None:
            await message.channel.send("❌ کەسێک Tag بکە یان Reply ـی نامەکەی بکە و بنووسە `staff`.", delete_after=5)
            return

        try:
            r1 = message.guild.get_role(STAFF_ROLE_1)
            r2 = message.guild.get_role(STAFF_ROLE_2)
            
            roles_to_add = []
            if r1 and r1 not in target.roles: roles_to_add.append(r1)
            if r2 and r2 not in target.roles: roles_to_add.append(r2)

            if roles_to_add:
                await target.add_roles(*roles_to_add, reason=f"Staff given by {message.author}")

            try:
                await message.delete()
            except:
                pass

            await message.channel.send(f"✅ دوو ڕۆڵی ستاف بە سەرکەوتوویی درا بە {target.mention}", delete_after=3)
        except Exception as e:
            print(f"Staff command error: {e}")
            await message.channel.send("❌ کێشەیەک ڕوویدا لە پێدانی ڕۆڵەکان.", delete_after=5)
        return

    # SAFIKA
    if command == "safika":  
        if not message.author.guild_permissions.administrator:  
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت ئەم کۆماندە بەکاربهێنێت.", delete_after=5)  
            return  

        if len(parts) < 2 or not parts[1].isdigit():  
            await message.channel.send("❌ نموونە: `Safika 1000`", delete_after=5)  
            return  

        amount = min(int(parts[1]), 1000)  
        if amount <= 0:  
            await message.channel.send("❌ ژمارەکە دەبێت زیاتر لە 0 بێت.", delete_after=5)  
            return  

        try:  
            deleted = await message.channel.purge(limit=amount + 1, bulk=True)  
            await message.channel.send(f"✅ `{len(deleted)}` نامە سڕایەوە.", delete_after=3)  
        except Exception as e:  
            print(f"Safika error: {e}")  
        return  

    # MUTE
    if command == "mute":  
        if not message.author.guild_permissions.administrator:  
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Mute بەکاربهێنێت.", delete_after=5)  
            return  

        target = await get_target_member(message)  
        if target is None:  
            await message.channel.send("❌ کەسێک Tag بکە یان Reply بکە.", delete_after=5)  
            return  

        try:  
            mute_role = await get_or_create_muted_role(message.guild)  
            if mute_role not in target.roles:  
                await target.add_roles(mute_role, reason=f"Karezma Mute by {message.author}")  

            embed = make_embed("🔇 Member Muted", f"**Member:** {target.mention}\n**Muted By:** {message.author.mention}", discord.Color.red())  
            add_user_thumbnail(embed, target)  
            await send_log(BAN_LOG_ID, embed)  

            try: await message.delete() except: pass  
            await message.channel.send(f"damt daxaa {target.mention}", delete_after=2)  
        except Exception as e:  
            print(f"Mute error: {e}")  
        return  

    # UNMUTE
    if command == "unmute":  
        if not message.author.guild_permissions.administrator:  
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Unmute بەکاربهێنێت.", delete_after=5)  
            return  

        target = await get_target_member(message)  
        if target is None:  
            await message.channel.send("❌ کەسێک Tag بکە یان Reply بکە.", delete_after=5)  
            return  

        try:  
            mute_role = discord.utils.get(message.guild.roles, name="Muted")  
            if mute_role and mute_role in target.roles:  
                await target.remove_roles(mute_role, reason=f"Karezma Unmute by {message.author}")  

            embed = make_embed("🔊 Member Unmuted", f"**Member:** {target.mention}\n**Unmuted By:** {message.author.mention}", discord.Color.green())  
            add_user_thumbnail(embed, target)  
            await send_log(BAN_LOG_ID, embed)  

            try: await message.delete() except: pass  
            await message.channel.send(f"xwa xerm bnwse dllm basha aqllba amjara {target.mention}", delete_after=2)  
        except Exception as e:  
            print(f"Unmute error: {e}")  
        return  

    # BFRA
    if command == "bfra":  
        if not message.author.guild_permissions.administrator:  
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Bfra بەکاربهێنێت.", delete_after=5)  
            return  

        target = await get_target_member(message)  
        if target is None:  
            await message.channel.send("❌ کەسێک Tag بکە یان Reply بکە.", delete_after=5)  
            return  

        try:  
            await target.ban(reason=f"Karezma Bfra by {message.author}")  
            embed = make_embed("🔨 Member Banned", f"**Member:** {target.mention}\n**Banned By:** {message.author.mention}", discord.Color.red())  
            add_user_thumbnail(embed, target)  
            await send_log(BAN_LOG_ID, embed)  

            try: await message.delete() except: pass  
            await message.channel.send(f"✈️ Frenra {target.mention}", delete_after=2)  
        except Exception as e:  
            print(f"Bfra error: {e}")  
        return  

    # UNBAN
    if command == "unban":  
        if not message.author.guild_permissions.administrator:  
            await message.channel.send(f"❌ {message.author.mention} تەنها ئەدمین دەتوانێت Unban بەکاربهێنێت.", delete_after=5)  
            return  

        user = None  
        if len(parts) >= 2 and parts[1].isdigit():  
            try: user = await bot.fetch_user(int(parts[1]))  
            except: user = None  

        if user is None:  
            await message.channel.send("❌ ID ـی بەکارهێنەر بنووسە.", delete_after=5)  
            return  

        try:  
            await message.guild.unban(user, reason=f"Karezma Unban by {message.author}")  
            embed = make_embed("♻️ Member Unbanned", f"**Member:** {user.mention}\n**Unbanned By:** {message.author.mention}", discord.Color.green())  
            add_user_thumbnail(embed, user)  
            await send_log(BAN_LOG_ID, embed)  

            try: await message.delete() except: pass  
            await message.channel.send(f"✅ {user.mention} Unban کرا.", delete_after=3)  
        except Exception as e:  
            print(f"Unban error: {e}")  
        return  

    # LOCK
    if command == "lock":  
        if not message.author.guild_permissions.manage_channels:  
            return  
        try:  
            await message.channel.set_permissions(message.guild.default_role, send_messages=False, reason=f"Locked by {message.author}")  
            try: await message.delete() except: pass  
            await message.channel.send("🔒 کەناڵەکە Lock کرا.", delete_after=3)  
        except Exception as e:  
            print(f"Lock error: {e}")  
        return  

    # UNLOCK
    if command == "unlock":  
        if not message.author.guild_permissions.manage_channels:  
            return  
        try:  
            await message.channel.set_permissions(message.guild.default_role, send_messages=None, reason=f"Unlocked by {message.author}")  
            try: await message.delete() except: pass  
            await message.channel.send("🔓 کەناڵەکە Unlock کرا.", delete_after=3)  
        except Exception as e:  
            print(f"Unlock error: {e}")  
        return

=========================================================

25. SLASH COMMANDS (/rangirole & /regri)

=========================================================

class ColorRoleSelect(discord.ui.Select):
    def __init__(self, roles_data):
        options = []
        for role, status_text in roles_data[:25]: # Discord select limit
            options.append(
                discord.SelectOption(
                    label=f"{role.name} [{status_text}]",
                    value=str(role.id)
                )
            )
        super().__init__(placeholder="ڕۆڵێک هەڵبژێرە بۆ گۆڕینی ڕەنگ...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.ui.View):
        if interaction.user.id in RESTRICTED_COLOR_USERS:
            await interaction.response.send_message("❌ تۆ لەلایەن بەڕێوەبەرەوە قەدەغە کراوەی لە دەستکاریکردنی ڕەنگەکان!", ephemeral=True)
            return
        
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ ڕۆڵەکە نەدۆزرایەوە.", ephemeral=True)
            return

        # Check hierarchy
        user_top = interaction.user.top_role.position
        if role >= interaction.guild.me.top_role or (role.position >= user_top and interaction.guild.owner != interaction.user):
            await interaction.response.send_message("❌ ناتوانیت دەستکاری ئەم ڕۆڵە بکەیت چونکە لە سەرووی ئاستی تۆوەیە!", ephemeral=True)
            return

        # Prompt user to provide a hex code or color
        modal = ColorModal(role)
        await interaction.response.send_modal(modal)

class ColorModal(discord.ui.Modal, title="گۆڕینی ڕەنگی ڕۆڵ"):
    color_input = discord.ui.TextInput(label="کۆدی ڕەنگ (بۆ نموونە: #FF0000)", placeholder="#HEX code", required=True, max_length=7)

    def __init__(self, role):
        super().__init__()
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        hex_str = self.color_input.value.strip().lstrip('#')
        try:
            color_int = int(hex_str, 16)
            color_obj = discord.Color(color_int)
            await self.role.edit(color=color_obj, reason=f"Color changed by {interaction.user}")
            await interaction.response.send_message(f"✅ ڕەنگی ڕۆڵی {self.role.mention} بە سەرکەوتوویی گۆڕدرا!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ کۆدی ڕەنگەکە هەڵەیە! تکایە کۆدی دروست بنووسە (نموونە: #FF0000).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ کێشەیەک ڕوویدا: {e}", ephemeral=True)

class ColorRoleView(discord.ui.View):
    def __init__(self, roles_data):
        super().__init__(timeout=180)
        self.add_item(ColorRoleSelect(roles_data))

@bot.tree.command(name="rangirole", description="پیشاندانی لیست و گۆڕینی ڕەنگی ڕۆڵەکان")
async def rangirole(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ تەنها ئەدیمینەکان دەتوانن ئەم سڵاشە بەکاربهێنن.", ephemeral=True)
        return

    user_top = interaction.user.top_role.position
    roles_data = []

    for role in reversed(interaction.guild.roles):
        if role.name == "@everyone":
            continue
        
        # Determine status
        is_above = role.position > user_top and interaction.guild.owner != interaction.user
        has_role = role in interaction.user.roles
        
        if is_above:
            status = "ناتوانیت دەستکاری بکەیت (بەرزترە)"
        elif has_role:
            status = "ڕۆڵی خۆتە (دەتوانیت دەستکاری بکەیت)"
        else:
            status = "لە خوار ئاستی تۆیە (دەتوانیت دەستکاری بکەیت)"

        roles_data.append((role, status))

    if not roles_data:
        await interaction.response.send_message("❌ هیچ ڕۆڵێک لە سێرڤەرەکەدا نییە.", ephemeral=True)
        return

    view = ColorRoleView(roles_data)
    await interaction.response.send_message("🎨 **لیستی ڕۆڵەکانی سێرڤەر بۆ گۆڕینی ڕەنگ:**\nڕۆڵێک لە خوارەوە هەڵبژێرە:", view=view, ephemeral=True)


@bot.tree.command(name="regri", description="قەدەغەکردن یان کردنەوەی دەستکاریکردنی ڕەنگ بۆ بەکارهێنەرێک")
async def regri(interaction: discord.Interaction, member: discord.Member, action: str):
    # Check permissions (Owner or specific roles)
    is_owner = interaction.guild.owner_id == interaction.user.id
    has_allowed_role = any(r.id in REGRI_ALLOWED_ROLES for r in interaction.user.roles)

    if not (is_owner or has_allowed_role):
        await interaction.response.send_message("❌ تۆ دەسەڵاتی بەکارهێنانی ئەم سڵاشەت نییە.", ephemeral=True)
        return

    action_lower = action.lower()
    if action_lower == "add" or action_lower == "ban":
        RESTRICTED_COLOR_USERS.add(member.id)
        await interaction.response.send_message(f"🚫 لەمەودوا {member.mention} ناتوانێت ڕەنگی ڕۆڵەکان دەستکاری بکات.", ephemeral=True)
    elif action_lower == "remove" or action_lower == "unban":
        RESTRICTED_COLOR_USERS.discard(member.id)
        await interaction.response.send_message(f"✅ ڕێگەدرا بە {member.mention} کە دووبارە ڕەنگی ڕۆڵەکان دەستکاری بکاتەوە.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ تکایە کردارێکی دروست بنووسە (نموونە: `add` یان `remove`).", ephemeral=True)

=========================================================

26. ERROR HANDLER

=========================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CommandNotFound, commands.MissingPermissions)):  
        return  
    print(f"Command error: {repr(error)}")

=========================================================

27. RUN BOT

=========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

bot.run(TOKEN)
