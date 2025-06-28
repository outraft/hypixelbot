import discord
from bot_commands import BotCommands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from ah import ah

load_dotenv()

client = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

async def setup_hook():
	await bot.add_cog(BotCommands(bot))
	await bot.add_cog(ah(bot))

@bot.event
async def on_ready():
	sync = await bot.tree.sync()
	print(f"{len(sync)} tane global komut(lar)ı sync edildi.")
	print(f"{bot.user} olarak giriş yapıldı!")

bot.setup_hook = setup_hook
bot.run(os.getenv("TOKEN"))
