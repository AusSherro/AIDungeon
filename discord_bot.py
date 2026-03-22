"""AI Dungeon Master Discord Bot"""
import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv
from config import Config
from utils.logger import setup_logging
from cogs import COGS

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

Config.validate()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} connected to Discord')
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded: {cog}")
        except Exception as e:
            logger.error(f"Failed to load {cog}: {e}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Sync failed: {e}")

if __name__ == "__main__":
    bot.run(Config.DISCORD_TOKEN)
