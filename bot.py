
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime
import asyncio

TOKEN = "MTM2MzY5MDAwMjQyODQ2MTE1OA.GooaWU.ZbYa-VqW9Cinz1F35-cK6NBjpuEx5DjsPPAT6c"
OUTPUT_CHANNEL_ID = 1363689879690547380
SUPPORT_ROLE_NAME = "support"
MAX_DESCRIPTION_LENGTH = 4000
EMBED_REFRESH_INTERVAL = 2

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
last_manual_update = None
embed_messages = []

class UpdateView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UpdateButton())

class UpdateButton(Button):
    def __init__(self):
        super().__init__(label="🔄 Обновить вручную", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        global last_manual_update
        now = datetime.utcnow()
        if last_manual_update and (now - last_manual_update).total_seconds() < 10:
            await interaction.response.send_message("⏱ Подожди немного перед повторным обновлением.", ephemeral=True)
            return
        last_manual_update = now
        await interaction.response.defer(ephemeral=True)
        await update_tickets(interaction.channel)
        await interaction.followup.send("✅ Обновление выполнено!", ephemeral=True)

@bot.event
async def on_ready():
    print("Бот запущен и готов к работе.")
    update_loop.start()

@tasks.loop(minutes=EMBED_REFRESH_INTERVAL)
async def update_loop():
    channel = bot.get_channel(OUTPUT_CHANNEL_ID)
    if channel:
        await update_tickets(channel)

async def update_tickets(channel):
    global embed_messages
    guild = channel.guild
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)

    ticket_channels = [ch for ch in guild.text_channels if "ticket" in ch.name]
    print(f"🔍 Найдено {len(ticket_channels)} тикет-каналов")

    tickets = []
    for ch in ticket_channels:
        messages = [m async for m in ch.history(limit=1)]
        if not messages:
            continue
        last_message = messages[0]
        author = last_message.author

        try:
            member = guild.get_member(author.id)
            if member is None:
                member = await guild.fetch_member(author.id)
        except Exception as e:
            print(f"❌ Ошибка при получении member: {e}")
            continue

        if support_role in member.roles or member.bot:
            continue

        now = datetime.utcnow().replace(tzinfo=None)
        diff = int((now - last_message.created_at.replace(tzinfo=None)).total_seconds() // 60)
        tickets.append((ch, diff))

    tickets.sort(key=lambda x: x[1])

    grouped = {
        "🔥 Старше 3 часов (180+ мин)": [],
        "🟡 От 1 до 3 часов (60–180 мин)": [],
        "🟢 Менее часа": [],
    }

    for ch, mins in tickets:
        line = f"[#{ch.name}](https://discord.com/channels/{guild.id}/{ch.id}) — {mins} мин назад"
        if mins >= 180:
            grouped["🔥 Старше 3 часов (180+ мин)"].append(line)
        elif mins >= 60:
            grouped["🟡 От 1 до 3 часов (60–180 мин)"].append(line)
        else:
            grouped["🟢 Менее часа"].append(line)

    for msg in embed_messages:
        try:
            await msg.delete()
        except:
            pass
    embed_messages = []

    description = ""
    for section, lines in grouped.items():
        if not lines:
            continue
        block = f"**{section}**
" + "\n".join(lines) + "\n\n"
        if len(description + block) > MAX_DESCRIPTION_LENGTH:
            embed = discord.Embed(title="Тикеты, ожидающие ответа", description=description, color=discord.Color.orange())
            msg = await channel.send(embed=embed, view=UpdateView())
            embed_messages.append(msg)
            description = ""
        description += block

    if description:
        embed = discord.Embed(title="Тикеты, ожидающие ответа", description=description, color=discord.Color.orange())
        msg = await channel.send(embed=embed, view=UpdateView())
        embed_messages.append(msg)

bot.run(TOKEN)
