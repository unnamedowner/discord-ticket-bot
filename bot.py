
import os
import discord
from discord.ext import commands, tasks

OUTPUT_CHANNEL_ID = 1361521776760328253
SUPPORT_ROLE_NAME = "support"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
embed_message = None

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    update_embed.start()

@tasks.loop(minutes=2)
async def update_embed():
    global embed_message
    print("🔄 Запуск обновления embed")

    channel = bot.get_channel(OUTPUT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(OUTPUT_CHANNEL_ID)
        except Exception as e:
            print(f"❌ Не удалось получить канал по ID: {e}")
            return

    guild = channel.guild
    if not guild:
        print("❌ Не удалось получить guild (сервер)")
        return

    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
    if not support_role:
        print(f"⚠️ Роль '{SUPPORT_ROLE_NAME}' не найдена на сервере {guild.name}")

    ticket_channels = [ch for ch in guild.text_channels if 'ticket' in ch.name]
    print(f"🔍 Найдено {len(ticket_channels)} тикет-каналов")

    ticket_list_lines = []

    for ch in ticket_channels:
        try:
            last_messages = [m async for m in ch.history(limit=1)]
        except Exception as e:
            print(f"⚠️ Ошибка при получении сообщений из {ch.name}: {e}")
            continue

        if not last_messages:
            print(f"ℹ️ В канале {ch.name} нет сообщений")
            continue

        last_message = last_messages[0]
        author = last_message.author
        author_name = f"{author.name}#{author.discriminator}" if hasattr(author, "name") else str(author)

        is_support = False
        if hasattr(author, "roles"):
            is_support = (support_role in author.roles) if support_role else False
        else:
            try:
                member = guild.get_member(author.id) or await guild.fetch_member(author.id)
                is_support = (support_role in member.roles) if support_role else False
            except Exception:
                is_support = False

        if is_support or author.bot:
            print(f"🚫 Пропущено: последнее сообщение в {ch.name} от {author_name} (бот/поддержка)")
            continue

        message_time = last_message.created_at
        if message_time.tzinfo:
            message_time = message_time.replace(tzinfo=None)

        try:
            now_time = discord.utils.utcnow().replace(tzinfo=None)
        except AttributeError:
            from datetime import datetime
            now_time = datetime.utcnow()

        diff_minutes = int((now_time - message_time).total_seconds() // 60)
        print(f"✅ Добавлено: {ch.name} — от {author_name} ({diff_minutes} мин назад)")

        channel_link = f"[#{ch.name}](https://discord.com/channels/{guild.id}/{ch.id})"
        ticket_list_lines.append(f"{channel_link} — {diff_minutes} мин назад")

    embed = discord.Embed(title="Тикеты, ожидающие ответа", color=discord.Color.orange())
    embed.description = "\n".join(ticket_list_lines) if ticket_list_lines else "Нет тикетов, ожидающих ответа."

    try:
        if embed_message is None:
            embed_message = await channel.send(embed=embed)
        else:
            await embed_message.edit(embed=embed)
        print("📬 Embed отправлен/обновлён")
    except Exception as e:
        print(f"❌ Ошибка при отправке/редактировании embed: {e}")
        embed_message = None

token = os.getenv("DISCORD_TOKEN")
if not token:
    print("❌ Переменная окружения DISCORD_TOKEN не установлена!")
else:
    bot.run(token)
