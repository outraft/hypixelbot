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
from collections import defaultdict

#!GENERAL/GLOBAL VARIABLES!#
PAGE_SIZE = 3
AHINTERVAL = 5 #seconds
#!GENERAL/GLOBAL VARIABLES - OVER!#

load_dotenv()

hypixelkey = genv("APIKEY")
uuids = genv("SET_PLAYER_UUIDS")
mongo_client = MongoClient(genv("MONGO"), server_api = ServerApi('1'))
db = mongo_client["cache"]
ahcache = db["ahcache"]

intents = discord.Intents.default()
intents.message_content = True

reforge_words = [
	"Gentle", "Odd", "Fast", "Fair", "Epic", "Sharp", "Heroic", "Spicy",
	"Legendary", "Deadly", "Fine", "Grand", "Hasty", "Neat", "Rapid", "Unreal",
	"Awkward", "Rich", "Clean", "Fierce", "Heavy", "Light", "Mythic", "Pure",
	"Smart", "Titanic", "Wise", "Double-Bit", "Lumberjack's", "Great", "Rugged",
	"Lush", "Green Thumb", "Peasant's", "Robust", "Zooming", "Unyielding",
	"Prospector's", "Excellent", "Sturdy", "Fortunate", "Stained", "Menacing",
	"Hefty", "Soft", "Honored", "Blended", "Astute", "Colossal", "Brilliant",
	"Waxed", "Fortified", "Strengthened", "Glistening", "Blooming", "Rooted",
	"Snowy", "Royal", "Blood-Soaked", "Blazing", "Very", "Highly", "Extremely",
	"Not So", "Thicc", "Absolutely", "Even More", "Silky", "Bloody", "Shaded", "Sweet"
]

exceptions = ["Wise Dragon Armor", "Strong Dragon Armor", "Superior Dragon Armor", "Heavy Armor", "Super Heavy Armor", "Perfect Armor", "Refined Mithril Pickaxe", "Polished Titanium Pickaxe"]
def remove_minecraft_formatting(text):
	return re.sub(r'§[0-9a-fk-or]', '', text, flags=re.IGNORECASE)

def clean_name(name):
	name = remove_minecraft_formatting(name)
	name = re.sub(r'\[.*?\]\s*', '', name)
	name = name.strip()
	lowered_name = name.lower()
	for exc in exceptions:
		if exc in lowered_name:
			first_word = name.split(' ')[0].lower()
			if first_word in reforge_words:
				name = ' '.join(name.split(' ')[1:]).strip()
			return re.sub(r'\s+', ' ', name)

	first_word = name.split(' ')[0].lower()
	if first_word in reforge_words:
		name = ' '.join(name.split(' ')[1:]).strip()

	return re.sub(r'\s+', ' ', name)

class ah(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="ah", description="Check the current AH!")
	async def ah(self, interaction: discord.Interaction):
		await interaction.response.defer()
		cached = ahcache.find_one({"_id": "ah"})

		cached_ts = cached['timestamp']
		if cached_ts.tzinfo is None:
			cached_ts = cached_ts.replace(tzinfo=timezone.utc)
		if datetime.now(timezone.utc) - cached_ts < timedelta(seconds=AHINTERVAL):
			data = cached['data']
			print("pulled cached data!")

		else:
			url = "https://api.hypixel.net/v2/skyblock/auctions"
			params = {
				"key": hypixelkey
			}
			res = req.get(url, params=params)
			if res.status_code == 404:
				await interaction.edit_original_response(content="The provided page does not exist!", ephemeral=True)
			elif res.status_code == 422:
				await interaction.edit_original_response(content="The page provided is invalid", ephemeral=True)
			elif res.status_code == 503:
				await interaction.edit_original_response(content="The data is not ready yet, please try again later!")
			else:
				data = res.json()
				ahcache.replace_one(
					{"_id": "ah"},
					{
						"_id": "ah",
						"data": data,
						"timestamp": datetime.now(timezone.utc)
					},
					upsert=True
				)
				print("pulled data")
		# data problem with respect to cache is solved above
		pages = [data['auctions'][i:i+PAGE_SIZE] for i in range(0, data['totalAuctions'], PAGE_SIZE)]
		curr = 0
		price_groups = defaultdict(list)
		for auction in data['auctions']:
			name = auction.get('item_name')
			cleaned_name = clean_name(name)
			#print(f"[DEBUG] Original: {name} => Cleaned: {cleaned_name}") works, could not care less about something that works!!!!1!!
			isbin = auction.get('bin', False)
			sbid = auction.get('starting_bid', "N/A")
			if isbin:
				price = sbid
			else:
				bids = auction.get('bids', [])
				if bids:
					price = bids[-1]['amount']
				else:
					price = sbid
			price_groups[cleaned_name].append(price)
		summary_lines = {}
		for aname, aprice in price_groups.items():
			avg_price = sum(aprice)/len(aprice)
			summary_lines[aname] = f"**{aname}** average price: {avg_price:,.0f} coins (per {len(aprice)} units)"


		def make_embed(page_index, summary_lines):
			embed = discord.Embed(title="Available Auctions:", color=discord.Color.darker_grey())
			start_idx = page_index * PAGE_SIZE + 1
			for idx,auctions in enumerate(pages[page_index], start=start_idx):
				name = auctions.get('item_name', "N/A")
				cleaned_name = clean_name(name)
				stats = remove_minecraft_formatting(auctions.get('item_lore', "No stats found!"))
				sbid = auctions.get('starting_bid', "N/A")
				tier = remove_minecraft_formatting(auctions.get('tier', "No tier information"))
				isbin = auctions.get('bin', False)
				category = auctions.get('category', "No category information")
				item_uuid = auctions.get('item_uuid', "No item UUID information")
				isbin_str = "BIN" if isbin else "Auction"
				if isbin:
					price = sbid
				else:
					bids = auctions.get('bids', [])
					if bids:
						price = bids[-1]['amount']
					else:
						price = sbid


				value = f"{stats}\nCost: {price}\nThis is a {category} piece.\nItem UUID for the nerds: {item_uuid}\n{summary_lines.get(cleaned_name, "No average info.")}"

				if idx < start_idx + len(pages[page_index]) - 1 :
					value += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

				embed.add_field(
					name=f"Auction {idx}: {name} | {tier} | {isbin_str}",
					value=value,
					inline=False
				)
			embed.set_footer(text="Do buy stuff! Never farm shall we!")
			return embed
		await interaction.edit_original_response(embed=make_embed(curr, summary_lines))
		message = await interaction.original_response()

		await message.add_reaction("⬅️")
		await message.add_reaction("➡️")
		def check(reaction, user):
			return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
		while True:
			try:
				reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
				if str(reaction.emoji) == "➡️":
					curr = (curr + 1) % len(pages)
				elif str(reaction.emoji) == "⬅️":
					curr = (curr - 1) % len(pages)

				await interaction.edit_original_response(embed=make_embed(curr, summary_lines))
				await message.remove_reaction(reaction.emoji, user)
			except asyncio.TimeoutError:
				await message.clear_reactions()
				break
	@app_commands.command(name="dah", description="Check a single auction!")
	async def dah(self, interaction: discord.Interaction, playerUUID: str = None, profileUUID: str = None, auctionUUID: str = None):
		filled = [bool(playerUUID), bool(profileUUID), bool(auctionUUID)]
		if sum(filled) != 1:
			await interaction.response.send_message("Please enter only **ONE** arguments", ephemeral = True)
			return
		await interaction.response.defer()
		cached_data = ahcache.find_one({"_id":"ah"})
		cached = cached_data['data']
		cached_ts = cached_data['timestamp']
		if cached_ts.tzinfo is None:
			cached_ts.replace(tzinfo=timezone.utc)
		if datetime.now(timezone.utc) - cached_ts < timedelta(seconds=5):
			data = cached
		else:
			url = "https://api.hypixel.net/v2/skyblock/auction"
			params = {
				"key": hypixelkey
			}
			res = req.get(url, params=params)
			if res.status_code in [400, 403, 422, 449]:
				await interaction.edit_original_response(content=
					f"A error occured! Possible causes are:\n"
					f"Data missing, are you sure you added a single field?\n"
					f"Access is forbidden, likely due to a invalid API key.\n"
					f"Some data provided are invalid, are you sure that you used the correct UUID?\n"
					f"A request limit has been reached, please try again later."
				)
			else:
				data = res.json()
		if playerUUID:
			playerauctions = []
			for auctions in data['auctions']:
				if auctions['auctioneer'] == playerUUID:
					playerauctions.append(auctions)
			if len(playerauctions) == 0:
				await interaction.edit_original_response(content=f"No auction found with the current player UUID ({playerUUID})")
				return
			pages = [playerauctions[i:i+PAGE_SIZE] for i in range(0, len(playerauctions), PAGE_SIZE)]
			curr = 0
			def make_embed(page_index):
				embed = discord.Embed(title=f"{playerUUID}'s auctions | Page {page_index+1} out of {len(pages)}")
				page = pages[page_index]
				start_idx = page_index * PAGE_SIZE + 1
				for idx, auct in enumerate(page, start=start_idx):
					item_name = auct.get("item_name", "Unknown")
					item_desc = auct.get("item_lore", "No description for item!")
					clear_name = remove_minecraft_formatting(item_name)
					clear_desc = remove_minecraft_formatting(item_desc)
					sbid = auct.get("starting_bid")
					tier = auct.get("tier", "NULL")
					isbin = auct.get("bin", False)
					if isbin:
						price = sbid
					else:
						bids = auct.get("bids", [])
						if bids:
							price = bids[-1]['amount']
						else:
							price = sbid
					value = f"{clear_desc}\n{price}"
					if idx < start_idx + len(pages[page_index]) - 1 :
						value += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
					embed.add_field(
						name=f"Auction {idx}:{clear_name} | {tier}",
						value=value
					)
				return embed
			await interaction.edit_original_response(embed=make_embed(curr))
		elif profileUUID:
			playerauctions = []
			for auction in data['auctions']:
				if auction.get("profile_id") == profileUUID:
					playerauctions.append(auction)
			if len(playerauctions) == 0:
				await interaction.edit_original_response(content=f"No auctions found for the given profile UUID ({profileUUID})")
				return
			pages = [playerauctions[i:i+PAGE_SIZE] for i in range(0, len(playerauctions), PAGE_SIZE)]
			curr = 0
			def make_embed(page_index):
				embed = discord.Embed(title=f"Profile UUID: {profileUUID} | Page {(page_index+1)} out of {len(pages)}")
				page = pages[page_index]
				start_idx = page_index * PAGE_SIZE + 1
				for idx, auct in enumerate(page, start=start_idx):
					item_name = auct.get("item_name", "Unknown")
					item_desc = auct.get("item_lore", "No description for item!")
					clear_name = remove_minecraft_formatting(item_name)
					clear_desc = remove_minecraft_formatting(item_desc)
					sbid = auct.get("starting_bid")
					tier = auct.get("tier", "NULL")
					isbin = auct.get("bin", False)
					if isbin:
						price = sbid
					else:
						bids = auct.get("bids", [])
						if bids:
							price = bids[-1]['amount']
						else:
							price = sbid
					value = f"{clear_desc}\n{price}"
					if idx < start_idx + len(pages[page_index]) - 1 :
						value += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
					embed.add_field(
						name=f"Auction {idx}:{clear_name} | {tier}",
						value=value
					)
				return embed
			await interaction.edit_original_response(embed=make_embed(curr))
		elif auctionUUID:
			playerauctions = []
			for auction in data['auctions']:
				if auction.get('uuid') == auctionUUID:
					playerauctions.append(auction)
			if len(playerauctions) == 0:
				await interaction.edit_original_response(content=f"No auctions found for the given auction UUID ({auctionUUID})")
				return
			pages = [playerauctions[i:i+PAGE_SIZE] for i in range(0, len(playerauctions), PAGE_SIZE)]
			curr = 0
			def make_embed(page_index):
				embed = discord.Embed(title=f"Auction ID: {auctionUUID} | Page {(page_index+1)} out of {len(pages)}")
				page = pages[page_index]
				start_idx = page_index * PAGE_SIZE + 1
				for idx, auct in enumerate(page, start=start_idx):
					item_name = auct.get("item_name", "Unknown")
					item_desc = auct.get("item_lore", "No description for item!")
					clear_name = remove_minecraft_formatting(item_name)
					clear_desc = remove_minecraft_formatting(item_desc)
					sbid = auct.get("starting_bid")
					tier = auct.get("tier", "NULL")
					isbin = auct.get("bin", False)
					if isbin:
						price = sbid
					else:
						bids = auct.get("bids", [])
						if bids:
							price = bids[-1]['amount']
						else:
							price = sbid
					value = f"{clear_desc}\n{price}"
					if idx < start_idx + len(pages[page_index]) - 1 :
						value += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
					embed.add_field(
						name=f"Auction {idx}:{clear_name} | {tier}",
						value=value
					)
				return embed
			await interaction.edit_original_response(embed=make_embed(curr))
		message = await interaction.original_response()

		await message.add_reaction("⬅️")
		await message.add_reaction("➡️")
		def check(reaction, user):
			return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
		while True:
			try:
				reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
				if str(reaction.emoji) == "➡️":
					curr = (curr + 1) % len(pages)
				elif str(reaction.emoji) == "⬅️":
					curr = (curr - 1) % len(pages)

				await interaction.edit_original_response(embed=make_embed(curr))
				await message.remove_reaction(reaction.emoji, user)
			except asyncio.TimeoutError:
				await message.clear_reactions()
				break