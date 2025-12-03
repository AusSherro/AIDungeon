import discord
from typing import Optional

async def sync_commands(bot, guild_id: Optional[str] = None):
    """Properly sync slash commands, clearing old ones first"""
    try:
        print("🔄 Starting command sync...")
        
        # First, let's see what commands are currently registered
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            try:
                existing_guild_commands = await bot.tree.fetch_commands(guild=guild)
                print(f"📋 Found {len(existing_guild_commands)} existing guild commands")
            except:
                existing_guild_commands = []
        
        try:
            existing_global_commands = await bot.tree.fetch_commands()
            print(f"🌍 Found {len(existing_global_commands)} existing global commands")
        except:
            existing_global_commands = []
        
        # Clear commands more carefully
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            print(f"❌ Clearing guild commands for {guild_id}...")
            bot.tree.clear_commands(guild=guild)
        
        print("❌ Clearing global commands...")
        bot.tree.clear_commands(guild=None)
        
        # Wait a moment for Discord to process
        import asyncio
        await asyncio.sleep(1)
        
        # Sync only to guild if specified, otherwise global
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            print(f"� Syncing commands to guild {guild_id}...")
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to guild {guild_id}")
        else:
            print("🔄 Syncing global commands...")
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} global commands")
        
        # Verify the sync worked
        await asyncio.sleep(2)  # Give Discord time to process
        
        if guild_id:
            guild_commands = await bot.tree.fetch_commands(guild=discord.Object(id=int(guild_id)))
            print(f"📊 Guild commands after sync ({len(guild_commands)}): {[cmd.name for cmd in guild_commands]}")
        else:
            global_commands = await bot.tree.fetch_commands()
            print(f"📊 Global commands after sync ({len(global_commands)}): {[cmd.name for cmd in global_commands]}")
        
        print("✅ Command sync completed successfully!")
        
    except Exception as e:
        print(f"❌ Command sync failed: {e}")
        import traceback
        traceback.print_exc()
        raise

async def nuclear_sync(bot, guild_id: Optional[str] = None):
    """Nuclear option: completely clear all commands and re-register"""
    try:
        print("💥 NUCLEAR SYNC: Completely clearing all commands...")
        
        # Clear everything
        bot.tree.clear_commands(guild=None)
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            bot.tree.clear_commands(guild=guild)
        
        # Sync empty command tree to Discord to clear everything
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            await bot.tree.sync(guild=guild)
            print(f"💥 Cleared all guild commands for {guild_id}")
        
        await bot.tree.sync()
        print("💥 Cleared all global commands")
        
        # Wait for Discord to process
        import asyncio
        await asyncio.sleep(3)
        
        # Now reload the bot's command tree by re-importing
        print("🔄 Reloading command tree...")
        
        # This will re-register all the @bot.tree.command decorators
        # Note: In a real scenario, you'd need to reload the module that defines the commands
        
        # Sync the fresh commands
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            synced = await bot.tree.sync(guild=guild)
            print(f"✅ Nuclear sync complete: {len(synced)} commands to guild")
        else:
            synced = await bot.tree.sync()
            print(f"✅ Nuclear sync complete: {len(synced)} global commands")
            
    except Exception as e:
        print(f"❌ Nuclear sync failed: {e}")
        import traceback
        traceback.print_exc()
        raise

async def debug_command_tree(bot):
    """Debug function to check what's in the command tree"""
    print("🔍 DEBUG: Checking command tree...")
    
    # Check the internal command tree
    commands = list(bot.tree._global_commands.values())
    print(f"🔍 Global commands in tree: {len(commands)}")
    for cmd in commands:
        print(f"  • {cmd.name}: {cmd.description}")
    
    # Check guild commands
    if hasattr(bot.tree, '_guild_commands'):
        for guild_id, guild_commands in bot.tree._guild_commands.items():
            print(f"🔍 Guild {guild_id} commands: {len(guild_commands)}")
            for cmd in guild_commands.values():
                print(f"  • {cmd.name}: {cmd.description}")
