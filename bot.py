
import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

ticket_tracking = {}

@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    check_tickets.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if "ticket" in message.channel.name.lower():
        ticket_tracking[message.channel.id] = {
            "user": message.author.name,
            "last_message": datetime.utcnow()
        }
    await bot.process_commands(message)

@tasks.loop(minutes=5)
async def check_tickets():
    now = datetime.utcnow()
    for channel_id, data in ticket_tracking.items():
        delta = now - data["last_message"]
        if delta > timedelta(minutes=15):
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(f"⏰ **{data['user']} ждёт уже {delta.seconds // 60} минут** без ответа!")

@bot.command()
async def статус(ctx):
    embed = discord.Embed(title="⏳ Ожидающие тикеты", color=0xffc300)
    now = datetime.utcnow()
    for channel_id, data in ticket_tracking.items():
        delta = now - data["last_message"]
        embed.add_field(
            name=f"<#{channel_id}>",
            value=f"{data['user']} ждёт уже {delta.seconds // 60} мин.",
            inline=False
        )
    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
