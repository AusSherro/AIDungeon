import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import random
import asyncio
import tempfile
import zipfile
from typing import Optional
from dotenv import load_dotenv

from services.openai_service import get_dm_response, generate_campaign
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.state_manager import load_state, save_state, get_turn_order, set_turn_order, get_current_turn_index, set_current_turn_index
from utils.dice_roller import roll_dice
from utils.logger import log_message, get_log_file
from utils.character_manager import register_character, load_character, set_stat, add_inventory, get_character_summary
from utils.combat_manager import start_combat, roll_initiative, next_turn, get_active_combatant, end_combat, load_combat, save_combat

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variable to track voice client
voice_client = None

async def play_audio_in_voice(channel, audio_bytes):
    """Helper function to manage voice connections and play audio"""
    global voice_client
    
    try:
        # Disconnect existing voice client if it exists
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
        
        # Connect to the new channel
        voice_client = await channel.connect()
        
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Play audio
        voice_client.play(discord.FFmpegPCMAudio(tmp_path))
        while voice_client.is_playing():
            await asyncio.sleep(1)
        
        # Disconnect after playing
        await voice_client.disconnect()
        voice_client = None
        
        # Clean up temp file
        os.unlink(tmp_path)
        
    except Exception as e:
        print(f"Voice error: {e}")
        if voice_client:
            try:
                await voice_client.disconnect()
            except:
                pass
            voice_client = None

DICE_PATTERN = re.compile(r'roll (a |an )?(\d*d\d+([+-]\d+)?)', re.IGNORECASE)

# --- User-Facing Slash Commands ---

@bot.tree.command(name="register", description="Register your character.")
async def register_slash(interaction: discord.Interaction, character_name: str):
    user_id = str(interaction.user.id)
    data = register_character(user_id, character_name)
    await interaction.response.send_message(f"Character '{character_name}' registered for {interaction.user.display_name}.")
    log_message(str(interaction.channel.id), interaction.user.display_name, f"Registered character: {character_name}")

@bot.tree.command(name="setstat", description="Set a stat for your character.")
async def setstat_slash(interaction: discord.Interaction, stat: str, value: int):
    user_id = str(interaction.user.id)
    result = set_stat(user_id, stat, value)
    if result:
        await interaction.response.send_message(f"Set {stat.upper()} to {value} for {interaction.user.display_name}.")
        log_message(str(interaction.channel.id), interaction.user.display_name, f"Set {stat.upper()} to {value}")
    else:
        await interaction.response.send_message("Failed to set stat. Make sure you're registered and the stat is valid (STR/DEX/CON/INT/WIS/CHA).")

@bot.tree.command(name="mystats", description="View your character's stats and inventory.")
async def mystats_slash(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    summary = get_character_summary(user_id)
    if summary:
        await interaction.response.send_message(summary)
    else:
        await interaction.response.send_message("No character found. Use /register <name> first.")

@bot.tree.command(name="inventory", description="Add an item to your inventory.")
async def inventory_slash(interaction: discord.Interaction, item: str):
    user_id = str(interaction.user.id)
    data = add_inventory(user_id, item)
    if data:
        await interaction.response.send_message(f"Added '{item}' to inventory.")
        log_message(str(interaction.channel.id), interaction.user.display_name, f"Added to inventory: {item}")
    else:
        await interaction.response.send_message("No character found. Use /register <name> first.")

@bot.tree.command(name="roll", description="Roll dice using standard notation, e.g. 2d6+1")
async def roll_slash(interaction: discord.Interaction, dice: str):
    try:
        total, rolls, modifier = roll_dice(dice)
        mod_str = f" {'+' if modifier >= 0 else '-'} {abs(modifier)} modifier" if modifier else ''
        msg = f"**🎲 You rolled [{dice}]: [{total}] (rolls: {', '.join(map(str, rolls))}{mod_str})**"
        await interaction.response.send_message(msg)
        log_message(str(interaction.channel.id), interaction.user.display_name, msg)
    except Exception as e:
        await interaction.response.send_message(f"Invalid dice format: {dice}")

@bot.tree.command(name="d20", description="Roll a d20 for skill checks")
async def d20_slash(interaction: discord.Interaction):
    """Roll a simple d20 for skill checks"""
    result = random.randint(1, 20)
    if result == 20:
        msg = f"🎲 **Natural 20!** Critical Success!"
    elif result == 1:
        msg = f"🎲 **Natural 1!** Critical Failure!"
    else:
        msg = f"🎲 You rolled: **{result}**"
    
    await interaction.response.send_message(msg)
    log_message(str(interaction.channel.id), interaction.user.display_name, f"d20 roll: {result}")

@bot.tree.command(name="attack", description="Roll to attack")
async def attack_slash(interaction: discord.Interaction):
    """Roll a d20 for attacks"""
    result = random.randint(1, 20)
    if result == 20:
        msg = f"⚔️ **CRITICAL HIT!** Attack roll: **{result}**"
    elif result == 1:
        msg = f"⚔️ **CRITICAL MISS!** Attack roll: **{result}**"
    else:
        msg = f"⚔️ Attack roll: **{result}**"
    
    await interaction.response.send_message(msg)
    log_message(str(interaction.channel.id), interaction.user.display_name, f"Attack roll: {result}")

@bot.tree.command(name="exportlog", description="Export the session log as a zip file.")
async def exportlog_slash(interaction: discord.Interaction):
    session_id = str(interaction.channel.id)
    log_path = get_log_file(session_id)
    if not log_path:
        await interaction.response.send_message("No log found for this session.")
        return
    zip_path = log_path + '.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(log_path, os.path.basename(log_path))
    await interaction.response.send_message(file=discord.File(zip_path))
    os.unlink(zip_path)

@bot.tree.command(name="combat", description="Start or end combat. Usage: /combat start enemy1:20:12 enemy2:15:10 or /combat end")
async def combat_slash(interaction: discord.Interaction, action: str, enemies: Optional[str] = None):
    channel_id = str(interaction.channel.id)
    if action == 'start':
        # Example: /combat start enemy1:20:12 enemy2:15:10
        players = [(str(m.id), m.display_name) for m in interaction.channel.members if not m.bot]
        enemies_list = []
        if enemies:
            for arg in enemies.split():
                parts = arg.split(':')
                if len(parts) == 3:
                    enemies_list.append({'name': parts[0], 'hp': int(parts[1]), 'ac': int(parts[2])})
        state = start_combat(channel_id, players, enemies_list)
        await interaction.response.send_message(f"Combat started! Players: {', '.join(p[1] for p in players)}. Enemies: {', '.join(e['name'] for e in enemies_list)}.")
        log_message(channel_id, "DM", f"Combat started with {len(players)} players and {len(enemies_list)} enemies")
    elif action == 'end':
        end_combat(channel_id)
        await interaction.response.send_message("Combat ended.")
        log_message(channel_id, "DM", "Combat ended")
    else:
        await interaction.response.send_message("Usage: /combat start [enemy1:hp:ac ...] or /combat end")

@bot.tree.command(name="initiative", description="Roll initiative for all combatants.")
async def initiative_slash(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = roll_initiative(channel_id)
    if not state:
        await interaction.response.send_message("No combat in progress.")
        return
    order = [f"{c['name']} ({c['initiative']})" for c in state['turn_order']]
    await interaction.response.send_message(f"Initiative order: {', '.join(order)}. {state['turn_order'][0]['name']}'s turn!")
    log_message(channel_id, "DM", f"Initiative rolled: {', '.join(order)}")

@bot.tree.command(name="next", description="Advance to the next combatant's turn.")
async def next_turn_slash(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = next_turn(channel_id)
    if not state:
        await interaction.response.send_message("No combat in progress.")
        return
    active = get_active_combatant(channel_id)
    if not active:
        await interaction.response.send_message("No active combatant.")
        return
    await interaction.response.send_message(f"It's now {active['name']}'s turn! HP: {active.get('hp', '?')} | AC: {active.get('ac', '?')} | Status: {', '.join(active.get('status', [])) if active.get('status') else 'None'}")
    log_message(channel_id, "DM", f"Turn advanced to {active['name']}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Wait a moment for all commands to be registered
    import asyncio
    await asyncio.sleep(2)
    
    # Check how many commands we have
    global_commands = list(bot.tree._global_commands.values())
    print(f"📋 Commands in tree: {len(global_commands)}")
    for cmd in global_commands:
        print(f"  • {cmd.name}: {cmd.description}")
    
    # Use GLOBAL sync instead of guild sync to avoid "Unknown Integration" errors
    try:
        print("🌍 Syncing commands globally...")
        synced = await bot.tree.sync()
        print(f"✅ Successfully synced {len(synced)} global commands!")
        
        for cmd in synced:
            print(f"  ✅ {cmd.name}")
            
        print("🎉 All commands should now work in all servers!")
        
    except Exception as e:
        print(f"❌ Global sync failed: {e}")
        import traceback
        traceback.print_exc()

@bot.tree.command(name="sync_now", description="Manually sync slash commands (admin only)")
async def sync_now(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("You must be an admin to use this command.", ephemeral=True)
        return
    
    try:
        print("🔄 Manual sync triggered...")
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Successfully synced {len(synced)} global commands!", ephemeral=True)
        print(f"✅ Manual sync complete: {len(synced)} commands")
    except Exception as e:
        await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)
        print(f"❌ Manual sync failed: {e}")

@bot.tree.command(name="nuclear_sync", description="Nuclear option: completely clear and re-sync commands (admin only)")
async def nuclear_sync_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("You must be an admin to use this command.", ephemeral=True)
        return
    
    try:
        from utils.command_sync import nuclear_sync
        await nuclear_sync(bot, DEV_GUILD_ID)
        await interaction.followup.send("💥 Nuclear sync completed! All commands cleared and re-registered.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Nuclear sync failed: {e}", ephemeral=True)

@bot.tree.command(name="new_campaign", description="Start a new campaign and set turn order.")
async def new_campaign(interaction: discord.Interaction, prompt: str = ""):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    await interaction.response.defer()
    
    # Detect all users in the initiator's voice channel (ignore bots)
    if not (interaction.user.voice and interaction.user.voice.channel):
        await interaction.followup.send("You must be in a voice channel to start a campaign.")
        return
    
    members = [m for m in interaction.user.voice.channel.members if not m.bot]
    if not members:
        await interaction.followup.send("No players in your voice channel.")
        return
    
    random.shuffle(members)
    turn_order = [str(m.id) for m in members]
    set_turn_order(state, turn_order)
    set_current_turn_index(state, 0)
    
    # Generate campaign intro
    campaign_text, updated_state = generate_campaign(state, prompt if prompt else None)
    
    # Save campaign and turn order
    save_state(channel_id, updated_state)
    save_state(channel_id, state)  # ensure turn order is saved
    
    # Announce campaign and first player
    tts_text = clean_text(campaign_text)
    voice_id = get_voice_id("Narrator")
    
    try:
        audio_bytes = text_to_speech(tts_text, voice_id)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_bytes = None
    
    first_player_id = turn_order[0]
    first_player_mention = f"<@{first_player_id}>"
    await interaction.followup.send(f"**New Campaign:**\n{campaign_text}\n\n{first_player_mention}, it's your turn. What do you do?")
    
    # Play audio if possible
    if audio_bytes and interaction.user.voice and interaction.user.voice.channel:
        await play_audio_in_voice(interaction.user.voice.channel, audio_bytes)

@bot.tree.command(name="act", description="Take your turn in the campaign.")
async def act(interaction: discord.Interaction, action: str):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    turn_order = state.get("turn_order", [])
    current_index = state.get("current_turn_index", 0)

    if not turn_order:
        await interaction.response.send_message("No campaign in progress. Use /new_campaign to start.")
        return

    current_player_id = turn_order[current_index]
    if str(interaction.user.id) != current_player_id:
        await interaction.response.send_message("It's not your turn!")
        return

    await interaction.response.defer()

    # Get the AI narration using get_dm_response
    narration, updated_state = get_dm_response(action, state)
    voice_tag = extract_voice_tag(narration)
    text = clean_text(narration)

    # Format output in the required style
    output = (
        "Narrator: " + text + "\n\n"
    )
    output += f"<@{current_player_id}>, it's still your turn. What do you do next?"

    await interaction.followup.send(output)
    save_state(channel_id, updated_state)
    log_message(channel_id, interaction.user.display_name, action)
    log_message(channel_id, "Narrator", text)

@bot.tree.command(name="end_turn", description="End your turn and advance to the next player.")
async def end_turn(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    turn_order = get_turn_order(state)
    idx = get_current_turn_index(state)
    
    if not turn_order or idx >= len(turn_order):
        await interaction.response.send_message("No campaign in progress.")
        return
    
    current_player_id = turn_order[idx]
    if str(interaction.user.id) != current_player_id:
        await interaction.response.send_message("It's not your turn!")
        return
    
    # Advance turn
    next_idx = (idx + 1) % len(turn_order)
    set_current_turn_index(state, next_idx)
    save_state(channel_id, state)
    next_player_id = turn_order[next_idx]
    next_player_mention = f"<@{next_player_id}>"
    msg = f"{next_player_mention}, it's your turn. What do you do?"
    
    await interaction.response.send_message(msg)
    log_message(channel_id, "DM", f"Turn passed to {next_player_mention}")
    
    # Play voice line if possible
    voice_id = get_voice_id("Narrator")
    try:
        audio_bytes = text_to_speech(f"It's your turn, {next_player_mention}", voice_id)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_bytes = None
    
    if audio_bytes and interaction.user.voice and interaction.user.voice.channel:
        await play_audio_in_voice(interaction.user.voice.channel, audio_bytes)

@bot.tree.command(name="start_adventure", description="Generate a new campaign setup with an optional prompt")
async def start_adventure(interaction: discord.Interaction, prompt: str = ""):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    await interaction.response.defer()
    
    # Generate campaign
    campaign_text, updated_state = generate_campaign(state, prompt if prompt else None)
    save_state(channel_id, updated_state)
    
    # Clean and prepare text for TTS
    tts_text = clean_text(campaign_text)
    voice_id = get_voice_id("Narrator")
    
    try:
        audio_bytes = text_to_speech(tts_text, voice_id)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_bytes = None
    
    await interaction.followup.send(f"**New Adventure:**\n{campaign_text}")
    log_message(channel_id, "DM", f"New adventure started: {campaign_text}")
    
    # Play audio if possible
    if audio_bytes and interaction.user.voice and interaction.user.voice.channel:
        await play_audio_in_voice(interaction.user.voice.channel, audio_bytes)

@bot.tree.command(name="check_commands", description="Check current command registration status (admin only)")
async def check_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("You must be an admin to use this command.", ephemeral=True)
        return
    
    try:
        # Check guild commands
        guild_commands = []
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            guild_commands = await bot.tree.fetch_commands(guild=guild)
        
        # Check global commands
        global_commands = await bot.tree.fetch_commands()
        
        # Build status message
        status_msg = "📊 **Command Registration Status**\n\n"
        
        if DEV_GUILD_ID:
            status_msg += f"**Guild Commands ({len(guild_commands)}):**\n"
            if guild_commands:
                for cmd in guild_commands:
                    status_msg += f"• {cmd.name}\n"
            else:
                status_msg += "• No guild commands registered\n"
            status_msg += "\n"
        
        status_msg += f"**Global Commands ({len(global_commands)}):**\n"
        if global_commands:
            for cmd in global_commands:
                status_msg += f"• {cmd.name}\n"
        else:
            status_msg += "• No global commands registered\n"
        
        await interaction.followup.send(status_msg, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to check commands: {e}", ephemeral=True)

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)