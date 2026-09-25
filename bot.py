import os
import discord
from discord import app_commands
from discord.ext import commands
from config import WELCOME_CHANNEL_ID, OWNER_ID, STAFF_ROLE_IDS, LOG_VIEW_ROLE_IDS, LOG_CHANNELS, WELCOME_GIF

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

def embed(title, text, color=0x5865F2):
    e = discord.Embed(title=f"╔══ {title} ══╗", description=text, color=color, timestamp=discord.utils.utcnow())
    e.set_footer(text="Karezma • Server Logs")
    return e

async def log(guild, kind, e):
    ch = guild.get_channel(LOG_CHANNELS.get(kind, 0))
    if ch:
        try: await ch.send(embed=e)
        except discord.HTTPException: pass

async def secure_logs(guild):
    for cid in LOG_CHANNELS.values():
        ch = guild.get_channel(cid)
        if not ch: continue
        try:
            await ch.set_permissions(guild.default_role, view_channel=False, reason="Karezma log privacy")
            for rid in LOG_VIEW_ROLE_IDS:
                role = guild.get_role(rid)
                if role: await ch.set_permissions(role, view_channel=True, reason="Karezma log privacy")
            owner = guild.get_member(OWNER_ID)
            if owner: await ch.set_permissions(owner, view_channel=True, reason="Karezma log privacy")
        except discord.HTTPException: pass

@bot.event
async def on_ready():
    await bot.tree.sync()
    for guild in bot.guilds: await secure_logs(guild)
    print(f"Online as {bot.user}")

@bot.event
async def on_member_join(m):
    ch = m.guild.get_channel(WELCOME_CHANNEL_ID)
    if ch:
        e = discord.Embed(title="╔══ Welcome to Karezma ══╗", description=f"Welcome {m.mention}!\nWe are happy to have you here.", color=0x5865F2)
        e.set_thumbnail(url=m.display_avatar.url)
        if WELCOME_GIF: e.set_image(url=WELCOME_GIF)
        try: await ch.send(embed=e)
        except discord.HTTPException: pass
    await log(m.guild, "member", embed("MEMBER JOIN", f"**Member:** {m.mention}\n**Name:** `{m}`\n**ID:** `{m.id}`", 0x57F287))

@bot.event
async def on_member_remove(m):
    await log(m.guild, "leave", embed("MEMBER LEFT", f"**Member:** `{m}`\n**ID:** `{m.id}`", 0xED4245))

@bot.event
async def on_member_ban(guild, user):
    await log(guild, "ban", embed("MEMBER BANNED", f"**User:** `{user}`\n**ID:** `{user.id}`", 0xED4245))

@bot.event
async def on_member_unban(guild, user):
    await log(guild, "ban", embed("MEMBER UNBANNED", f"**User:** `{user}`\n**ID:** `{user.id}`", 0x57F287))

@bot.event
async def on_message_delete(m):
    if not m.guild or m.author.bot: return
    await log(m.guild, "chat", embed("MESSAGE DELETED", f"**Author:** {m.author.mention}\n**Channel:** {m.channel.mention}\n**Content:**\n```{(m.content or '*No text content*')[:1500]}```", 0xED4245))

@bot.event
async def on_message_edit(before, after):
    if not before.guild or before.author.bot or before.content == after.content: return
    await log(before.guild, "chat", embed("MESSAGE EDITED", f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:**\n```{before.content[:1000]}```\n**After:**\n```{after.content[:1000]}```", 0xFEE75C))

@bot.event
async def on_voice_state_update(m, before, after):
    if m.bot or (before.channel == after.channel and before.mute == after.mute and before.deaf == after.deaf): return
    if before.channel is None: action = f"Joined **{after.channel.name}**"
    elif after.channel is None: action = f"Left **{before.channel.name}**"
    elif before.channel != after.channel: action = f"Moved from **{before.channel.name}** to **{after.channel.name}**"
    else: action = "Voice state changed"
    await log(m.guild, "voice", embed("VOICE LOG", f"**Member:** {m.mention}\n**Action:** {action}"))

@bot.event
async def on_guild_channel_create(ch):
    await log(ch.guild, "channel", embed("CHANNEL CREATED", f"**Name:** `{ch.name}`\n**ID:** `{ch.id}`", 0x57F287))

@bot.event
async def on_guild_channel_delete(ch):
    await log(ch.guild, "channel", embed("CHANNEL DELETED", f"**Name:** `{ch.name}`\n**ID:** `{ch.id}`", 0xED4245))

@bot.event
async def on_guild_role_create(r):
    await log(r.guild, "role", embed("ROLE CREATED", f"**Role:** {r.mention}\n**Name:** `{r.name}`\n**ID:** `{r.id}`", 0x57F287))

@bot.event
async def on_guild_role_delete(r):
    await log(r.guild, "role", embed("ROLE DELETED", f"**Name:** `{r.name}`\n**ID:** `{r.id}`", 0xED4245))

@bot.event
async def on_guild_role_update(before, after):
    changes=[]
    if before.name != after.name: changes.append(f"**Name:** `{before.name}` → `{after.name}`")
    if before.color != after.color: changes.append(f"**Color:** `{before.color}` → `{after.color}`")
    if before.permissions != after.permissions: changes.append("**Permissions:** changed")
    if before.position != after.position: changes.append(f"**Position:** `{before.position}` → `{after.position}`")
    if changes: await log(after.guild, "role", embed("ROLE UPDATED", f"**Role:** {after.mention}\n" + "\n".join(changes), 0xFEE75C))

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        await log(after.guild, "nickname", embed("NICKNAME CHANGED", f"**Member:** {after.mention}\n**Before:** `{before.nick or before.name}`\n**After:** `{after.nick or after.name}`", 0xFEE75C))
    added=[r for r in after.roles if r not in before.roles]; removed=[r for r in before.roles if r not in after.roles]
    if added or removed:
        s=f"**Member:** {after.mention}"
        if added: s += "\n**Added:** " + ", ".join(r.mention for r in added)
        if removed: s += "\n**Removed:** " + ", ".join(r.mention for r in removed)
        await log(after.guild, "member", embed("MEMBER ROLES CHANGED", s))

@bot.event
async def on_guild_update(before, after):
    changes=[]
    if before.name != after.name: changes.append(f"**Name:** `{before.name}` → `{after.name}`")
    if before.icon != after.icon: changes.append("**Icon:** changed")
    if before.banner != after.banner: changes.append("**Banner:** changed")
    if changes: await log(after, "server", embed("SERVER UPDATED", "\n".join(changes), 0xFEE75C))

@bot.tree.command(name="staf", description="Give both Staff roles to a member")
@app_commands.describe(name="Choose the member")
async def staf(interaction: discord.Interaction, name: discord.Member):
    # Only members with the Discord Administrator permission can use /staf.
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ تەنها ئەدمینیستڕاتۆرەکان دەتوانن /staf بەکاربهێنن.",
            ephemeral=True,
        )
        return
    added=[]
    for rid in STAFF_ROLE_IDS:
        role=interaction.guild.get_role(rid)
        if not role: continue
        if role not in name.roles:
            try:
                await name.add_roles(role, reason=f"/staf by {interaction.user}")
                added.append(role.mention)
            except discord.Forbidden:
                await interaction.response.send_message("❌ بۆت ناتوانێت Staff role بدات. ڕۆڵی بۆت دەبێت لەسەر Staff role ـەکان بێت.", ephemeral=True)
                return
    await interaction.response.send_message(embed=embed("STAFF ADDED", f"**Member:** {name.mention}\n**Given by:** {interaction.user.mention}\n**Roles:** {', '.join(added) if added else 'Already had both roles'}", 0x57F287))
    await log(interaction.guild, "member", embed("STAFF ROLE GIVEN", f"**Member:** {name.mention}\n**Given by:** {interaction.user.mention}", 0x57F287))

@bot.tree.command(name="test", description="Test the bot")
async def test(interaction):
    await interaction.response.send_message("✅ Karezma bot is online.", ephemeral=True)

token=os.getenv("DISCORD_TOKEN")
if not token: raise RuntimeError("DISCORD_TOKEN is missing")
bot.run(token)
