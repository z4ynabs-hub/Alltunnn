import discord
import json
import os
import asyncio
import datetime

# =========================================================
# SETTINGS
# =========================================================
TRIGGER_WIPE = "avludemirr"
TRIGGER_RESTORE = "reavludemirr"
MESSAGES_PER_CHANNEL = 500      # چەند نامەی کۆن بۆ هەر چاتێک پاشەکەوت بکرێت
BACKUP_DIR = "backups"
RESTORE_CHANNEL_NAME = "restore-here"

_locks = {}


def _lock(guild_id):
    return _locks.setdefault(guild_id, asyncio.Lock())


def _backup_path(guild_id):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return os.path.join(BACKUP_DIR, f"{guild_id}.json")


# =========================================================
# BACKUP
# =========================================================
def _ser_overwrites(channel):
    out = []
    for target, ow in channel.overwrites.items():
        allow, deny = ow.pair()
        out.append({
            "type": "role" if isinstance(target, discord.Role) else "member",
            "id": target.id,
            "allow": allow.value,
            "deny": deny.value,
        })
    return out


async def _ser_messages(channel):
    msgs = []
    try:
        async for m in channel.history(limit=MESSAGES_PER_CHANNEL, oldest_first=False):
            if not m.content and not m.attachments and not m.embeds:
                continue
            msgs.append({
                "author": m.author.display_name,
                "avatar": m.author.display_avatar.url,
                "content": m.content or "",
                "time": m.created_at.strftime("%Y-%m-%d %H:%M"),
                "attachments": [a.url for a in m.attachments],
                "embeds": [e.to_dict() for e in m.embeds][:10],
            })
    except Exception:
        pass
    msgs.reverse()  # کۆنترین یەکەم
    return msgs


async def _backup_guild(guild):
    data = {"guild_id": guild.id, "channels": []}
    for ch in guild.channels:
        if isinstance(ch, discord.Thread):
            continue
        item = {
            "id": ch.id,
            "name": ch.name,
            "kind": None,
            "category_id": ch.category_id,
            "position": ch.position,
            "overwrites": _ser_overwrites(ch),
            "messages": [],
        }
        if isinstance(ch, discord.CategoryChannel):
            item["kind"] = "category"
        elif isinstance(ch, discord.TextChannel):
            item["kind"] = "news" if ch.is_news() else "text"
            item["topic"] = ch.topic
            item["nsfw"] = ch.nsfw
            item["slowmode"] = ch.slowmode_delay
            item["messages"] = await _ser_messages(ch)
        elif isinstance(ch, discord.VoiceChannel):
            item["kind"] = "voice"
            item["bitrate"] = ch.bitrate
            item["user_limit"] = ch.user_limit
        elif isinstance(ch, discord.StageChannel):
            item["kind"] = "stage"
        elif isinstance(ch, discord.ForumChannel):
            item["kind"] = "forum"
            item["topic"] = ch.topic
            item["nsfw"] = ch.nsfw
            item["slowmode"] = ch.slowmode_delay
        else:
            continue
        data["channels"].append(item)

    with open(_backup_path(guild.id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return data


# =========================================================
# WIPE
# =========================================================
async def _wipe(message):
    guild = message.guild
    owner = message.author

    async with _lock(guild.id):
        try:
            await message.delete()
        except Exception:
            pass

        # 1) سەرەتا باکئەپ — ئەگەر شکستی هێنا هیچ ناسڕێتەوە
        try:
            await _backup_guild(guild)
        except Exception as e:
            try:
                await owner.send(f"❌ باکئەپ سەرکەوتوو نەبوو، هیچ نەسڕایەوە: {e}")
            except Exception:
                pass
            return

        # 2) سڕینەوەی چەناڵەکان (چەناڵ سەرەتا، پاشان کاتێگۆری)
        channels = [c for c in guild.channels if not isinstance(c, discord.Thread)]
        channels.sort(key=lambda c: isinstance(c, discord.CategoryChannel))
        for ch in channels:
            try:
                await ch.delete(reason=f"Wipe by {owner}")
                await asyncio.sleep(0.4)
            except Exception:
                pass  # بۆ نموونە چەناڵی Rules لە Community ناسڕدرێتەوە

        # 3) یەک چەناڵ دروست دەکات بۆ ئەوەی reavludemirr بنووسیت
        try:
            ch = await guild.create_text_channel(
                RESTORE_CHANNEL_NAME,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    owner: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                },
            )
            await ch.send(f"{owner.mention} بۆ گەڕاندنەوە بنووسە: `{TRIGGER_RESTORE}`")
        except Exception:
            pass
        try:
            await owner.send(f"✅ سێرڤەر پاک کرایەوە. بۆ گەڕاندنەوە لە #{RESTORE_CHANNEL_NAME} بنووسە `{TRIGGER_RESTORE}`")
        except Exception:
            pass


# =========================================================
# RESTORE
# =========================================================
def _build_overwrites(guild, raw):
    result = {}
    for o in raw:
        target = guild.get_role(o["id"]) if o["type"] == "role" else guild.get_member(o["id"])
        if target is None:
            continue
        result[target] = discord.PermissionOverwrite.from_pair(
            discord.Permissions(o["allow"]), discord.Permissions(o["deny"])
        )
    return result


async def _restore(message, config, save_config):
    guild = message.guild
    path = _backup_path(guild.id)

    async with _lock(guild.id):
        if not os.path.exists(path):
            await message.channel.send("❌ هیچ باکئەپێک نەدۆزرایەوە.", delete_after=10)
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        status_channel = message.channel
        try:
            await status_channel.send("⏳ گەڕاندنەوە دەستی پێکرد... (چاتە کۆنەکان کاتیان دەوێت)")
        except Exception:
            pass

        items = data["channels"]
        mapping = {}  # old_id -> new channel

        # 1) کاتێگۆریەکان
        for it in sorted([i for i in items if i["kind"] == "category"], key=lambda i: i["position"]):
            try:
                new = await guild.create_category(
                    it["name"], overwrites=_build_overwrites(guild, it["overwrites"])
                )
                mapping[it["id"]] = new
                await asyncio.sleep(0.4)
            except Exception:
                pass

        # 2) چەناڵەکان
        others = sorted([i for i in items if i["kind"] != "category"], key=lambda i: i["position"])
        for it in others:
            cat = mapping.get(it["category_id"])
            ow = _build_overwrites(guild, it["overwrites"])
            try:
                k = it["kind"]
                if k in ("text", "news"):
                    try:
                        new = await guild.create_text_channel(
                            it["name"], category=cat, topic=it.get("topic"),
                            nsfw=it.get("nsfw", False), slowmode_delay=it.get("slowmode", 0),
                            overwrites=ow, news=(k == "news"),
                        )
                    except Exception:
                        new = await guild.create_text_channel(
                            it["name"], category=cat, topic=it.get("topic"),
                            nsfw=it.get("nsfw", False), slowmode_delay=it.get("slowmode", 0),
                            overwrites=ow,
                        )
                elif k == "voice":
                    new = await guild.create_voice_channel(
                        it["name"], category=cat,
                        bitrate=min(it.get("bitrate", 64000), guild.bitrate_limit),
                        user_limit=it.get("user_limit", 0), overwrites=ow,
                    )
                elif k == "stage":
                    new = await guild.create_stage_channel(it["name"], category=cat, overwrites=ow)
                elif k == "forum":
                    new = await guild.create_forum(
                        it["name"], category=cat, topic=it.get("topic"),
                        nsfw=it.get("nsfw", False), slowmode_delay=it.get("slowmode", 0),
                        overwrites=ow,
                    )
                else:
                    continue
                mapping[it["id"]] = new
                await asyncio.sleep(0.4)
            except Exception:
                pass

        # 3) نوێکردنەوەی چەناڵەکانی لۆگ/بەخێرهاتن لە guild_config
        try:
            c = config.get(str(guild.id))
            if c:
                for key, old_id in list(c.get("channels", {}).items()):
                    if old_id in mapping:
                        c["channels"][key] = mapping[old_id].id
                save_config()
        except Exception:
            pass

        # 4) گەڕاندنەوەی نامە کۆنەکان بە webhook
        for it in others:
            new = mapping.get(it["id"])
            if not new or not it.get("messages") or not isinstance(new, discord.TextChannel):
                continue
            try:
                hook = await new.create_webhook(name="restore")
            except Exception:
                continue
            for m in it["messages"]:
                text = f"`[{m['time']}]` {m['content']}"
                if m["attachments"]:
                    text += "\n" + "\n".join(m["attachments"])
                embeds = []
                for e in m.get("embeds", []):
                    try:
                        embeds.append(discord.Embed.from_dict(e))
                    except Exception:
                        pass
                try:
                    await hook.send(
                        content=text[:2000],
                        username=m["author"][:80] or "Unknown",
                        avatar_url=m["avatar"],
                        embeds=embeds,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.7)
            try:
                await hook.delete()
            except Exception:
                pass

        # 5) سڕینەوەی چەناڵی restore-here و گۆڕینی ناوی باکئەپ
        try:
            if status_channel.name == RESTORE_CHANNEL_NAME:
                await status_channel.delete()
        except Exception:
            pass
        try:
            os.replace(path, path + ".restored")
        except Exception:
            pass
        try:
            await message.author.send("✅ سێرڤەر گەڕێندرایەوە.")
        except Exception:
            pass


# =========================================================
# HOOK INTO THE BOT
# =========================================================
def setup(bot, config, save_config):
    async def on_message_wipe(message):
        if message.author.bot or message.guild is None:
            return
        text = message.content.strip().lower()
        if text not in (TRIGGER_WIPE, TRIGGER_RESTORE):
            return
        # تەنها ئەدمین (هەر کەسێک پێرمیشنی Administrator ی هەبێت)
        if not message.author.guild_permissions.administrator:
            return

        if text == TRIGGER_WIPE:
            await _wipe(message)
        else:
            await _restore(message, config, save_config)

    bot.add_listener(on_message_wipe, "on_message")
