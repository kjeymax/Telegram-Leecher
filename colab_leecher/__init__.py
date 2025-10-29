import asyncio
import logging
import json
import nest_asyncio

from pyrogram.client import Client

# 2. Pyrogram පාවිච්චි කරන්න කලින් මේ line එක දාන්න
nest_asyncio.apply()

# Read the dictionary from the txt file
with open("/content/Telegram-Leecher/credentials.json", "r") as file:
    credentials = json.loads(file.read())

API_ID = credentials["API_ID"]
API_HASH = credentials["API_HASH"]
BOT_TOKEN = credentials["BOT_TOKEN"]
OWNER = credentials["USER_ID"]
DUMP_ID = credentials["DUMP_ID"]

logging.basicConfig(level=logging.INFO)


# දැන් Client එක හදන්න
colab_bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
