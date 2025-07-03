from dotenv import load_dotenv
import discord
from discord import app_commands
from uuid import uuid4
from discord.ext import commands
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from os import getenv as genv
import requests as req
import re
from datetime import datetime, timedelta, timezone
import asyncio

#!GENERAL/GLOBAL VARIABLES!#
PAGE_SIZE = 5

load_dotenv()

hypixelkey = genv("APIKEY")
uuids = genv("SET_PLAYER_UUIDS")
mongo_client = MongoClient(genv("MONGO"), server_api = ServerApi('1'))
db = mongo_client["cache"]
uuidcache = db["uuidcache"]
#!GENERAL/GLOBAL VARIABLES - OVER!#

intents = discord.Intents.default()
intents.message_content = True

def remove_minecraft_formatting(text):
    return re.sub(r'§[0-9a-fk-or]', '', text, flags=re.IGNORECASE)

class BotCommands(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
	@app_commands.command(name="importantplayers", description="shows important players set!")
	async def importantplayers(self, interaction: discord.Interaction):
		results = uuidcache.find().limit(5)
		embed = discord.Embed()
		embed.title = "Important player(s)"
		for i, uuid in enumerate(results, 1):
			embed.add_field(
				name=f"{i} #will pull player user.",
				value=f"UUID: {uuid.get('uuid', 'N/A')}\n"
				f"Username: {uuid.get('username', 'N/A (will be integrated)')}",
				inline=False
			)
		await interaction.response.send_message(embed=embed)

	@app_commands.command(name="addplayer", description="Adds to the important players list!")
	async def addplayer(self, interaction: discord.Interaction, uuid: str, username: str = None):
		if username is None:
			url = f"https://api.hypixel.net/v2/player"
			params = {
				"key": hypixelkey,
				"uuid": uuid
			}
			res = req.get(url, params=params)
			if res.status_code == 200:
				data = res.json()
				if data["success"] == True and data["player"]:
					username = data["player"].get("displayname")
				else:
					return await interaction.response.send_message(f"We couldn't gather the data, are you sure the UUID is true and exists?")
		existing = uuidcache.find_one({"uuid":uuid})
		if existing:
			return await interaction.response.send_message(f"The user with {uuid} | {username} already exists!")
		uuidcache.insert_one({
			"uuid": uuid,
			"username": username
		})
		await interaction.response.send_message(f"Added {uuid} | {username} to the list!")

	@app_commands.command(name="mayor", description="mayor data for skyblock")
	async def mayor(self, interaction: discord.Interaction):
		cache_mayor = db['mayor']
		COLORCATEGORY = {
			"farming": ("🟩", "🌾"),
			"fishing": ("🟦", "🎣"),
			"pets": ("🌸", "🐾"),
			"economist": ("🟨", "💰"),
			"events": ("🟥", "🎉"),
			"dungeons": ("🟪", "🗝️"),
			"mining": ("🟫","⛏️")
		}

		cached = cache_mayor.find_one({"_id": "mayor"})
		cached_ts = cached['timestamp']
		if cached_ts.tzinfo is None:
			cached_ts = cached_ts.replace(tzinfo=timezone.utc)

		if cached and datetime.now(timezone.utc) - cached_ts < timedelta(minutes=5):
			data = cached['data']
			print("pulled cached data!")
		else:
			url = "https://api.hypixel.net/v2/resources/skyblock/election"
			params = {"key": hypixelkey}
			res = req.get(url, params=params)
			if res.status_code != 200:
				return await interaction.response.send_message("Couldn't fetch election data from Hypixel.")
			data = res.json()
			cache_mayor.replace_one(
				{"_id": "mayor"},
				{
					"_id": "mayor",
					"data": data,
					"timestamp": datetime.now(timezone.utc)
				},
				upsert=True
			)
			print("refreshed the data!")

		if not data['current']:
			embed = discord.Embed(title="Mayor of the Skyblock", color=discord.Color.gold())

			embed.add_field(
				name=f"The mayor (currently) is: {data['mayor']['name']}",
				value=f"It is the {data['mayor']['key']} season! The perks are:\n"
			)

			perks = data['mayor'].get('perks', [])
			minister = ""
			for i, perk in enumerate(perks, 1):
				embed.add_field(
					name=f"Perk {i}:",
					value=f"{minister}{perk['description']}",
					inline=False
				)
		else:
			def make_bar(percent, size=20, emoji='🟩'):
				filled = int((percent / 100) * size)
				return emoji * filled + '⬛' * (size - filled)

			embed = discord.Embed(title=f"Election: Year {data['current']['year']}!", color=discord.Color.red())
			candidates = data['current'].get('candidates', [])
			total_votes = sum(c.get('votes', 0) for c in candidates) if candidates else 0

			for i, candidate in enumerate(candidates, 1):
				name = candidate.get('name', 'Unknown')
				perks = candidate.get('perks', [])
				key = candidate.get('key', '')
				emoji_bar, icon = COLORCATEGORY.get(key, ("🟥", "❓"))

				votes = candidate.get('votes')
				if votes is None:
					perc = None
					votes = 0
				else:
					perc = (votes / total_votes * 100) if total_votes > 0 else 0

				perk_list = ""
				for perk in perks:
					title = perk.get('name', 'No Name')
					desc = remove_minecraft_formatting(perk.get('description', ''))
					minister = "👑 " if perk.get('minister') else ""
					perk_list += f"{minister}**{title}**: {desc}\n"

				if perc is None:
					perc_text = "CLOSED VOTE!"
					bar = '⬛' * 20
				else:
					perc_text = f"{perc:.2f}%"
					bar = make_bar(perc, emoji=emoji_bar)

				embed.add_field(
					name=f"Candidate {i}: {name} {icon}",
					value=f"{perk_list}\n{bar}\n{votes} votes ({perc_text})",
					inline=False
				)
		embed.set_footer(text="Vote wisely, adventurer 🗳️")
		await interaction.response.send_message(embed=embed)


	@app_commands.command(name="news", description="Skyblock news!")
	async def news(self, interaction: discord.Interaction):
		url = "https://api.hypixel.net/v2/skyblock/news"
		params = {
			"key": hypixelkey
		}
		res = req.get(url, params=params)
		if res.status_code == 403:
			await interaction.response.send_message("Access is forbidden, due likely to invalid API. Notify a admin!", ephemeral=True)
		elif res.status_code == 429:
			await interaction.response.send_message("Request limit have been reached, please wait a few seconds! If not fixed, there might be a throttle.", ephemeral=True)
		elif res.status_code == 200:
			data = res.json()
			items = data.get('items', [])
			if not items:
				await interaction.response.send_message(f"There are no news!")
				return
			if not data['success'] == True:
				await interaction.response.send_message(f"The API did not give a succesful response, try again!")
				return
			pages = [items[i:i+PAGE_SIZE] for i in range(0, len(items),PAGE_SIZE)]
			current_page = 0
			def make_embed(page_index):
				embed = discord.Embed(title=f"📰 Skyblock News (Page {page_index+1}/{len(pages)})", color=discord.Color.blue())
				for item in pages[page_index]:
					material = item['item'].get('material', 'Unknown')
					title = item.get('title', 'No Title')
					text = item.get('text', '')
					link = item.get('link', '')
					embed.add_field(
						name=f"{title} [{material}]",
						value=f"{text}\n[Read More]({link})",
						inline=False
					)
				return embed
			await interaction.response.send_message(embed=make_embed(current_page))
			message = await interaction.original_response()

			await message.add_reaction("⬅️")
			await message.add_reaction("➡️")
			def check(reaction, user):
				return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
			while True:
				try:
					reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
					if str(reaction.emoji) == "➡️":
						current_page = (current_page + 1) % len(pages)
					elif str(reaction.emoji) == "⬅️":
						current_page = (current_page - 1) % len(pages)

					await message.edit(embed=make_embed(current_page))
					await message.remove_reaction(reaction.emoji, user)
				except asyncio.TimeoutError:
					await message.clear_reactions()
					break