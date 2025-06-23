#!/usr/bin/env python3
"""
Simple test to see if we can register and sync commands properly
"""
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Add a simple test command
@bot.tree.command(name="test", description="A simple test command")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Test command works!")

@bot.tree.command(name="debug_sync", description="Debug command sync")
async def debug_sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Check current commands
    guild_id = os.getenv("DEV_GUILD_ID")
    
    # Get commands in the tree
    global_commands = list(bot.tree._global_commands.values())
    message = f"**Commands in tree:** {len(global_commands)}\n"
    for cmd in global_commands:
        message += f"• {cmd.name}: {cmd.description}\n"
    
    # Check what's registered on Discord
    try:
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            registered_guild = await bot.tree.fetch_commands(guild=guild)
            message += f"\n**Registered guild commands:** {len(registered_guild)}\n"
            for cmd in registered_guild:
                message += f"• {cmd.name}\n"
        
        registered_global = await bot.tree.fetch_commands()
        message += f"\n**Registered global commands:** {len(registered_global)}\n"
        for cmd in registered_global:
            message += f"• {cmd.name}\n"
            
    except Exception as e:
        message += f"\n❌ Error fetching: {e}"
    
    await interaction.followup.send(message, ephemeral=True)

@bot.tree.command(name="force_sync", description="Force sync commands")
async def force_sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_id = os.getenv("DEV_GUILD_ID")
        
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)
            await interaction.followup.send(f"✅ Synced {len(synced)} commands to guild!", ephemeral=True)
        else:
            synced = await bot.tree.sync()
            await interaction.followup.send(f"✅ Synced {len(synced)} global commands!", ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Check what commands are in the tree
    global_commands = list(bot.tree._global_commands.values())
    print(f"Commands in tree: {len(global_commands)}")
    for cmd in global_commands:
        print(f"  • {cmd.name}: {cmd.description}")
      # Simple sync without clearing - try global first
    guild_id = os.getenv("DEV_GUILD_ID")
    try:
        # Try global sync first
        print("🌍 Trying global sync...")
        synced = await bot.tree.sync()
        print(f"✅ Global sync: {len(synced)} commands")
        
        for cmd in synced:
            print(f"  • Synced globally: {cmd.name}")
        
        # Then try guild sync if we have a guild ID
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            print(f"🏠 Trying guild sync to {guild_id}...")
            synced_guild = await bot.tree.sync(guild=guild)
            print(f"✅ Guild sync: {len(synced_guild)} commands")
            
            for cmd in synced_guild:
                print(f"  • Synced to guild: {cmd.name}")
            
    except Exception as e:
        print(f"❌ Initial sync failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ No Discord bot token found!")
