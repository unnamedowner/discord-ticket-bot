
import discord
from discord.ext import tasks, commands
import os
import asyncio
from datetime import datetime, timezone
from collections import defaultdict

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1361521776760328253
SUPPORT_ROLE_NAME = "support"
UPDATE_INTERVAL = 120
UPDATE_COOLDOWN = 10

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
last_manual_update = 0

def group_by_age(ticket_data):
    now = datetime.now(timezone.utc)
    groups = {
        "🔥 Старше 1 дня (1440+ мин)": [],
        "🟡 От 1 до 3 часов (60–180 мин)": [],
        "🟢 Менее часа": []
    }
    for channel, author, minutes in sorted(ticket_data, key=lambda x: x[2], reverse=True):
        if minutes >= 1440:
            groups["🔥 Старше 1 дня (1440+ мин)"].append((channel, author, minutes))
        elif 60 <= minutes < 1440:
            groups["🟡 От 1 до 3 часов (60–180 мин)"].append((channel, author, minutes))
        else:
            groups["🟢 Менее часа"].append((channel, author, minutes))
    return groups

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    update_tickets.start()

@bot.command()
async def обновить(ctx):
    global last_manual_update
    now = asyncio.get_event_loop().time()
    if now - last_manual_update < UPDATE_COOLDOWN:
        await ctx.send("⏳ Подожди немного перед следующим обновлением.")
        return
    last_manual_update = now
    await send_or_update_embed(ctx.channel)

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_tickets():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await send_or_update_embed(channel)

async def send_or_update_embed(channel):
    guild = channel.guild
    ticket_channels = [c for c in guild.text_channels if c.name.startswith("ticket")]
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
    ticket_data = []

    for c in ticket_channels:
        messages = [m async for m in c.history(limit=1)]
        if not messages:
            continue
        last_message = messages[0]

        member = guild.get_member(last_message.author.id)
        if member is None:
            continue
        if support_role in member.roles or member.bot:
            continue

        minutes_ago = int((datetime.now(timezone.utc) - last_message.created_at).total_seconds() // 60)
        ticket_data.append((c, last_message.author, minutes_ago))

    grouped = group_by_age(ticket_data)

    embeds = []
    page = 1
    description = ""
    for group, items in grouped.items():
        if not items:
            continue
        block = f"**{group}**\n"
        for c, author, min_ago in items:
            block += f"<#{c.id}> — {min_ago} мин назад\n"
        if len(description + block) > 4000:
            embeds.append(discord.Embed(title=f"Тикеты, ожидающие ответа ({page})", description=description, color=0xffcc00))
            page += 1
            description = ""
        description += block + "\n"
    embeds.append(discord.Embed(title=f"Тикеты, ожидающие ответа ({page})", description=description, color=0xffcc00))

    if not hasattr(channel, "last_embed_msg"):
        channel.last_embed_msg = await channel.send(embeds=embeds, view=UpdateView())
    else:
        await channel.last_embed_msg.edit(embeds=embeds, view=UpdateView())

class UpdateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(UpdateButton())

class UpdateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.blurple, label="🔄 Обновить вручную")

    async def callback(self, interaction: discord.Interaction):
        await send_or_update_embed(interaction.channel)
        await interaction.response.send_message("✅ Обновлено!", ephemeral=True)

bot.run(TOKEN)
