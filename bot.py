
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime

TOKEN = "MTM2MzY5MDAwMjQyODQ2MTE1OA.GZuQbR.r7IEfK-Jez39lRHro5GtYuOoa-b4h7nn3KKjZo"
CHANNEL_ID = 1361521776760328253
SUPPORT_ROLE_NAME = "support"
COOLDOWN_SECONDS = 10
EMBED_REFRESH_INTERVAL = 2  # in minutes

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
        if last_manual_update and (now - last_manual_update).total_seconds() < COOLDOWN_SECONDS:
            await interaction.response.send_message("⏱ Подожди немного перед повторным обновлением.", ephemeral=True)
            return
        last_manual_update = now
        await interaction.response.defer(ephemeral=True)
        await update_tickets(interaction.guild, interaction.channel)
        await interaction.followup.send("✅ Обновление выполнено!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")
    update_loop.start()

@tasks.loop(minutes=EMBED_REFRESH_INTERVAL)
async def update_loop():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await update_tickets(channel.guild, channel)

async def update_tickets(guild, channel):
    global embed_messages
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)

    ticket_channels = [ch for ch in guild.text_channels if "ticket" in ch.name]
    grouped = {
        "🔥 Старше 3 часов (180+ мин)": [],
        "🟡 От 1 до 3 часов (60–180 мин)": [],
        "🟢 Менее часа": [],
    }

    for ch in ticket_channels:
        try:
            messages = [m async for m in ch.history(limit=1)]
            if not messages:
                continue
            msg = messages[0]
            author = msg.author

            try:
                member = guild.get_member(author.id) or await guild.fetch_member(author.id)
            except:
                continue

            if member.bot or support_role in member.roles:
                continue

            minutes = int((datetime.utcnow() - msg.created_at).total_seconds() // 60)
            link = f"[#{ch.name}](https://discord.com/channels/{guild.id}/{ch.id}) — {minutes} мин назад"

            if minutes >= 180:
                grouped["🔥 Старше 1 дня (1440+ мин)"].append(link)
            elif minutes >= 60:
                grouped["🟡 От 1 до 3 часов (60–180 мин)"].append(link)
            else:
                grouped["🟢 Менее часа"].append(link)

        except Exception as e:
            print(f"Ошибка в канале {ch.name}: {e}")

    for msg in embed_messages:
        try:
            await msg.delete()
        except:
            pass
    embed_messages.clear()

    description = ""
    for group, items in grouped.items():
        if not items:
            continue
        block = f"**{group}**\n" + "\n".join(items) + "\n\n"
        if len(description + block) > 4000:
            embed = discord.Embed(title="⏳ Тикеты, ожидающие ответа", description=description, color=discord.Color.orange())
            msg = await channel.send(embed=embed, view=UpdateView())
            embed_messages.append(msg)
            description = ""
        description += block

    if description:
        embed = discord.Embed(title="⏳ Тикеты, ожидающие ответа", description=description, color=discord.Color.orange())
        msg = await channel.send(embed=embed, view=UpdateView())
        embed_messages.append(msg)

bot.run(TOKEN)
