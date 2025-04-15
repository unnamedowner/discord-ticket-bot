
import os
import discord
from discord.ext import commands, tasks
import time
from discord.ui import View, Button

OUTPUT_CHANNEL_ID = 1361521776760328253
SUPPORT_ROLE_NAME = "support"
MAX_DESCRIPTION_LENGTH = 4000
last_refresh_time = 0

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
embed_messages = []

class RefreshView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RefreshButton())

class RefreshButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="🔄 Обновить вручную")

    async def callback(self, interaction: discord.Interaction):
        global last_refresh_time
        now = time.time()
        if now - last_refresh_time < 10:
            await interaction.response.send_message("⏱ Подожди немного перед повторной попыткой (10 секунд)", ephemeral=True)
        else:
            last_refresh_time = now
            await interaction.response.send_message("🔄 Обновляю тикеты...", ephemeral=True)
            await update_embed()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    update_embed.start()

@tasks.loop(minutes=2)
async def update_embed():
    global embed_messages
    print("🔄 Запуск обновления embed")

    channel = bot.get_channel(OUTPUT_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(OUTPUT_CHANNEL_ID)
        except Exception as e:
            print(f"❌ Не удалось получить канал по ID: {e}")
            return

    guild = channel.guild
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)

    ticket_channels = [ch for ch in guild.text_channels if 'ticket' in ch.name]
    print(f"🔍 Найдено {len(ticket_channels)} тикет-каналов")

    tickets = []
    for ch in ticket_channels:
        try:
            last_messages = [m async for m in ch.history(limit=1)]
        except Exception as e:
            continue
        if not last_messages:
            continue

        last_message = last_messages[0]
        author = last_message.author
        if support_role in getattr(author, 'roles', []) or author.bot:
            continue

        message_time = last_message.created_at.replace(tzinfo=None)
        now_time = discord.utils.utcnow().replace(tzinfo=None)
        diff_minutes = int((now_time - message_time).total_seconds() // 60)
        tickets.append((ch.name, ch.id, diff_minutes))

    tickets.sort(key=lambda x: x[2], reverse=True)

    groups = {
        "🔥 **Старше 1 дня** (1440+ мин)": [],
        "🟡 **От 1 до 3 часов** (60–180 мин)": [],
        "🟢 **Менее часа**": []
    }

    for name, ch_id, minutes in tickets:
        link = f"https://discord.com/channels/{guild.id}/{ch_id}"
        line = f"[#{name}]({link}) — {minutes} мин назад"
        if minutes >= 1440:
            groups["🔥 **Старше 1 дня** (1440+ мин)"].append(line)
        elif 60 <= minutes < 180:
            groups["🟡 **От 1 до 3 часов** (60–180 мин)"].append(line)
        else:
            groups["🟢 **Менее часа**"].append(line)

    for msg in embed_messages:
        try:
            await msg.delete()
        except:
            pass
    embed_messages = []

    pages = []
    current = ""
    for title, lines in groups.items():
        if lines:
            block = f"{title}\n" + "\n".join(lines) + "\n\n"
            if len(current + block) > MAX_DESCRIPTION_LENGTH:
                pages.append(current)
                current = block
            else:
                current += block
    if current:
        pages.append(current)
    if not pages:
        pages = ["Нет тикетов, ожидающих ответа."]

    for i, desc in enumerate(pages):
        embed = discord.Embed(title=f"Тикеты, ожидающие ответа ({i+1}/{len(pages)})", description=desc, color=discord.Color.orange())
        view = RefreshView()
        try:
            msg = await channel.send(embed=embed, view=view)
            embed_messages.append(msg)
        except Exception as e:
            print(f"❌ Ошибка при отправке embed {i+1}: {e}")

bot.run(os.environ["DISCORD_TOKEN"])
