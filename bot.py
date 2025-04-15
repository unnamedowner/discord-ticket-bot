
import os
import discord
from discord.ext import commands, tasks

# Настройки
OUTPUT_CHANNEL_ID = 1361521776760328253  # ID канала, куда отправляется embed
SUPPORT_ROLE_NAME = "support"           # Имя роли поддержки (учтите регистр букв)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
embed_message = None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    update_embed.start()

@tasks.loop(minutes=2)
async def update_embed():
    global embed_message
    channel = bot.get_channel(OUTPUT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(OUTPUT_CHANNEL_ID)
        except Exception as e:
            print(f"Не удалось получить канал с ID {OUTPUT_CHANNEL_ID}: {e}")
            return

    guild = channel.guild
    if guild is None:
        print("Не удалось определить сервер (guild).")
        return

    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
    if support_role is None:
        print(f"Роль '{SUPPORT_ROLE_NAME}' не найдена на сервере {guild.name}.")

    ticket_channels = [ch for ch in guild.text_channels if 'ticket' in ch.name]
    ticket_list_lines = []
    for ch in ticket_channels:
        try:
            last_messages = [m async for m in ch.history(limit=1)]
        except Exception as e:
            print(f"Не удалось получить последнее сообщение из {ch.name}: {e}")
            continue
        if not last_messages:
            continue
        last_message = last_messages[0]
        author = last_message.author

        is_support = False
        if hasattr(author, "roles"):
            is_support = (support_role in author.roles) if support_role else False
        else:
            try:
                member = guild.get_member(author.id) or await guild.fetch_member(author.id)
            except Exception:
                member = None
            if member:
                is_support = (support_role in member.roles) if support_role else False

        if is_support or author.bot:
            continue

        message_time = last_message.created_at
        if message_time.tzinfo is not None:
            message_time = message_time.replace(tzinfo=None)
        try:
            now_time = discord.utils.utcnow().replace(tzinfo=None)
        except AttributeError:
            from datetime import datetime
            now_time = datetime.utcnow()
        diff_minutes = int((now_time - message_time).total_seconds() // 60)

        channel_link = f"[#{ch.name}](https://discord.com/channels/{guild.id}/{ch.id})"
        ticket_list_lines.append(f"{channel_link} — {diff_minutes} мин назад")

    embed = discord.Embed(title="Тикеты, ожидающие ответа", color=discord.Color.blue())
    embed.description = "\n".join(ticket_list_lines) if ticket_list_lines else "Нет тикетов, ожидающих ответа."

    try:
        if embed_message is None:
            embed_message = await channel.send(embed=embed)
        else:
            await embed_message.edit(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке/редактировании embed: {e}")
        embed_message = None

token = os.getenv("DISCORD_TOKEN")
if not token:
    print("Переменная окружения DISCORD_TOKEN не установлена!")
else:
    bot.run(token)
