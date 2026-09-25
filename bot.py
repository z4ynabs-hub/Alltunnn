import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os


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

# STAFF ROLES
STAFF_ROLE_1_ID = 995343531482812488
STAFF_ROLE_2_ID = 863850042123878421


# =========================================================
# 3. READY
# =========================================================

@bot.event
async def on_ready():

    print(f"بۆتەکە بە سەرکەوتوویی چالاک بوو وەک: {bot.user}")
    print(f"Bot ID: {bot.user.id}")

    try:
        synced = await bot.tree.sync()
        print(f"Slash Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Slash sync error: {e}")


# =========================================================
# 4. STAFF SLASH COMMAND
# =========================================================

@bot.tree.command(
    name="staff",
    description="Give both Staff roles to a member."
)
@app_commands.describe(
    member="ئەو کەسەی دەتەوێت ببێتە Staff"
)
async def staff_command(
    interaction: discord.Interaction,
    member: discord.Member
):

    # ADMIN ONLY

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ تەنها ئەدمین دەتوانێت Staff بەکاربهێنێت.",
            ephemeral=True
        )

        return


    # GET ROLES

    role_1 = interaction.guild.get_role(
        STAFF_ROLE_1_ID
    )

    role_2 = interaction.guild.get_role(
        STAFF_ROLE_2_ID
    )


    # CHECK ROLES

    if role_1 is None or role_2 is None:

        await interaction.response.send_message(
            "❌ یەکێک لە ڕۆڵەکانی Staff نەدۆزرایەوە.",
            ephemeral=True
        )

        return


    # BOT HIERARCHY CHECK

    bot_member = interaction.guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ بۆتەکە لە سێرڤەرەکە نەدۆزرایەوە.",
            ephemeral=True
        )

        return


    if role_1 >= bot_member.top_role or role_2 >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ ڕۆڵەکانی Staff دەبێت لە خوار ڕۆڵی بۆتەکە بن.",
            ephemeral=True
        )

        return


    try:

        # ADD BOTH STAFF ROLES

        await member.add_roles(
            role_1,
            role_2,
            reason=f"Karezma Staff by {interaction.user}"
        )


        # REQUIRED MESSAGE

        await interaction.response.send_message(
            f"bw ba staf {member.mention}"
        )


    except discord.Forbidden:

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ بۆتەکە دەسەڵاتی زیادکردنی ڕۆڵی Staff ـی نییە.",
                ephemeral=True
            )

        else:

            await interaction.followup.send(
                "❌ بۆتەکە دەسەڵاتی زیادکردنی ڕۆڵی Staff ـی نییە.",
                ephemeral=True
            )


    except Exception as e:

        print(f"Staff error: {e}")

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ کێشەیەک لە Staff ڕوویدا.",
                ephemeral=True
            )

        else:

            await interaction.followup.send(
                "❌ کێشەیەک لە Staff ڕوویدا.",
                ephemeral=True
            )


# =========================================================
# 5. WELCOME
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

        # وێنەی پرۆفایلی ئەو کەسە لای ڕاست

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


# =========================================================
# 6. GET TARGET FROM TAG OR REPLY
# =========================================================

async def get_target_member(message):

    # -------------------------
    # TAG
    # -------------------------

    if message.mentions:

        member = message.mentions[0]

        if isinstance(member, discord.Member):
            return member


    # -------------------------
    # REPLY
    # -------------------------

    if message.reference:

        try:

            referenced_message = await message.channel.fetch_message(
                message.reference.message_id
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
# 7. MUTED ROLE
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

        print(
            f"Muted permission error in {channel.name}: {e}"
        )


async def get_or_create_muted_role(guild):

    mute_role = discord.utils.get(
        guild.roles,
        name="Muted"
    )

    if mute_role:
        return mute_role


    # -------------------------
    # CREATE ROLE
    # -------------------------

    mute_role = await guild.create_role(
        name="Muted",
        reason="Karezma mute role"
    )


    # -------------------------
    # APPLY TO CHANNELS
    # -------------------------

    for channel in guild.channels:

        await apply_muted_permissions(
            channel,
            mute_role
        )


    return mute_role


# =========================================================
# 8. NEW CHANNEL -> MUTED ROLE PERMISSION
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
# 9. MAIN COMMAND SYSTEM
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

                user = await bot.fetch_user(
                    int(parts[1])
                )

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
# 10. ERROR HANDLER
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

    print(
        f"Command error: {repr(error)}"
    )


# =========================================================
# 11. RUN BOT
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is missing."
    )


bot.run(TOKEN)
