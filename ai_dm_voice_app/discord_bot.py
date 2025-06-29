import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import random
import asyncio
import tempfile
import zipfile
import json
from typing import Optional
from dotenv import load_dotenv
from config import Config

from services.openai_service import get_dm_response, generate_campaign, summarize_history
from services.elevenlabs_service import text_to_speech
from utils.voice_parser import extract_voice_tag, clean_text
from utils.voice_map import get_voice_id
from utils.voice_manager import VoiceClientManager
from utils.state_manager import (
    load_state,
    save_state,
    get_turn_order,
    set_turn_order,
    get_current_turn_index,
    set_current_turn_index,
)
from utils.prompt_builder import build_system_prompt
from utils.dice_roller import roll_dice
from utils.logger import log_message, get_log_file
from utils.character_manager import (
    register_character,
    load_character,
    set_stat,
    add_inventory,
    remove_inventory,
    get_character_summary,
    SKILLS,
    calculate_skill_bonus,
    get_ability_modifier,
)
from utils.combat_manager import start_combat, roll_initiative, next_turn, get_active_combatant, end_combat, load_combat, save_combat

load_dotenv()
Config.validate()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Voice client manager to handle per-guild connections
voice_manager = VoiceClientManager()

async def play_audio_in_voice(channel, audio_bytes):
    """Play audio in the given voice channel using the manager."""
    try:
        await voice_manager.play(channel, audio_bytes)
    except Exception as e:
        print(f"Voice error: {e}")

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

# ---- Inventory Commands ----
inventory_group = app_commands.Group(name="inventory", description="Manage your inventory")

@inventory_group.command(name="view", description="View your inventory")
async def inventory_view(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    if not char:
        await interaction.response.send_message("No character found. Use /register <name> first.")
        return
    items = char.get('inventory', [])
    if items:
        await interaction.response.send_message("\n".join(f"- {i}" for i in items))
    else:
        await interaction.response.send_message("Inventory is empty.")


@inventory_group.command(name="add", description="Add an item to your inventory")
async def inventory_add_cmd(interaction: discord.Interaction, item: str):
    user_id = str(interaction.user.id)
    data = add_inventory(user_id, item)
    if data:
        await interaction.response.send_message(f"Added '{item}' to inventory.")
        log_message(str(interaction.channel.id), interaction.user.display_name, f"Added to inventory: {item}")
    else:
        await interaction.response.send_message("No character found. Use /register <name> first.")


@inventory_group.command(name="remove", description="Remove an item from your inventory")
async def inventory_remove_cmd(interaction: discord.Interaction, item: str):
    user_id = str(interaction.user.id)
    data = remove_inventory(user_id, item)
    if data:
        await interaction.response.send_message(f"Removed '{item}' from inventory.")
        log_message(str(interaction.channel.id), interaction.user.display_name, f"Removed from inventory: {item}")
    else:
        await interaction.response.send_message("Item not found or no character registered.")

bot.tree.add_command(inventory_group)

@bot.tree.command(name="roll", description="Roll dice or a skill check")
@app_commands.describe(query="Dice notation (2d6+1) or skill name")
async def roll_slash(interaction: discord.Interaction, query: str, adv: Optional[bool] = False, disadv: Optional[bool] = False):
    user_id = str(interaction.user.id)
    skill = query.lower()
    if skill in SKILLS or skill.upper() in ['STR','DEX','CON','INT','WIS','CHA']:
        char = load_character(user_id)
        if not char:
            await interaction.response.send_message("No character found. Use /register <name> first.")
            return
        if skill in SKILLS:
            stat = SKILLS[skill]
            mod = calculate_skill_bonus(char, skill)
        else:
            stat = skill.upper()
            mod = get_ability_modifier(char.get(stat,10))

        roll1 = random.randint(1,20)
        if adv or disadv:
            roll2 = random.randint(1,20)
            result_roll = max(roll1, roll2) if adv else min(roll1, roll2)
            rolls = f"{roll1} & {roll2}" + (" (adv)" if adv else " (disadv)")
        else:
            result_roll = roll1
            rolls = str(roll1)

        total = result_roll + mod
        mod_str = f"+{mod}" if mod >=0 else str(mod)
        msg = f"🎲 {interaction.user.display_name} rolls for {query.title()}: {total} (rolled {result_roll} {mod_str})"
        await interaction.response.send_message(msg)
        log_message(str(interaction.channel.id), interaction.user.display_name, msg)
    else:
        try:
            total, rolls, modifier = roll_dice(query)
            mod_str = f" {'+' if modifier >= 0 else '-'} {abs(modifier)} modifier" if modifier else ''
            msg = f"**🎲 You rolled [{query}]: [{total}] (rolls: {', '.join(map(str, rolls))}{mod_str})**"
            await interaction.response.send_message(msg)
            log_message(str(interaction.channel.id), interaction.user.display_name, msg)
        except Exception:
            await interaction.response.send_message(f"Invalid dice or skill: {query}")

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


@bot.tree.command(name="save", description="Make a saving throw vs a DC")
@app_commands.describe(stat="Ability", dc="Difficulty Class")
async def save_slash(interaction: discord.Interaction, stat: str, dc: int, adv: Optional[bool] = False, disadv: Optional[bool] = False):
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    if not char:
        await interaction.response.send_message("No character found. Use /register <name> first.")
        return

    stat_up = stat.upper()
    if stat_up not in ['STR','DEX','CON','INT','WIS','CHA']:
        await interaction.response.send_message("Invalid ability. Use STR/DEX/CON/INT/WIS/CHA.")
        return
    mod = get_ability_modifier(char.get(stat_up,10))
    roll1 = random.randint(1,20)
    if adv or disadv:
        roll2 = random.randint(1,20)
        result_roll = max(roll1, roll2) if adv else min(roll1, roll2)
    else:
        result_roll = roll1
    total = result_roll + mod
    success = total >= dc
    mod_str = f"+{mod}" if mod >=0 else str(mod)
    status = "Success" if success else "Failure"
    msg = f"🛡️ {interaction.user.display_name} makes a {stat_up} saving throw vs DC {dc}: {total} (rolled {result_roll} {mod_str}) → {status}!"
    await interaction.response.send_message(msg)
    log_message(str(interaction.channel.id), interaction.user.display_name, msg)

@bot.tree.command(name="attack", description="Attack a target in combat")
@app_commands.describe(target="Target name", bonus="Attack bonus", damage="Damage dice e.g. 1d8+2")
async def attack_slash(interaction: discord.Interaction, target: str, bonus: int, damage: str):
    channel_id = str(interaction.channel.id)
    from utils.combat_manager import attack
    result = attack(channel_id, str(interaction.user.id), target, bonus, damage)
    if not result:
        await interaction.response.send_message("No combat in progress or target not found.")
        return
    if result['hit']:
        msg = f"{interaction.user.display_name} hits {target} for {result['damage']} damage! ({result['target_hp']} HP left)"
    else:
        msg = f"{interaction.user.display_name} misses {target}! (Roll {result['roll']})"
    await interaction.response.send_message(msg)
    log_message(channel_id, interaction.user.display_name, msg)

@bot.tree.command(name="cast", description="Cast a spell at a target")
@app_commands.describe(spell="Spell name", target="Target name", bonus="Spell attack bonus", damage="Damage dice")
async def cast_slash(interaction: discord.Interaction, spell: str, target: str, bonus: int, damage: str):
    channel_id = str(interaction.channel.id)
    from utils.combat_manager import attack
    result = attack(channel_id, str(interaction.user.id), target, bonus, damage)
    if not result:
        await interaction.response.send_message("No combat in progress or target not found.")
        return
    if result['hit']:
        msg = f"{interaction.user.display_name} casts {spell} and hits {target} for {result['damage']} damage! ({result['target_hp']} HP left)"
    else:
        msg = f"{interaction.user.display_name} casts {spell} but misses {target}! (Roll {result['roll']})"
    await interaction.response.send_message(msg)
    log_message(channel_id, interaction.user.display_name, msg)

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
    state["players"] = turn_order
    
    # Generate campaign intro and state details
    campaign_text, state = generate_campaign(state, prompt if prompt else None)

    # Save campaign and turn order
    save_state(channel_id, state)
    
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
    await interaction.followup.send(
        f"{campaign_text}\n\n{first_player_mention}, it's your turn. What do you do?"
    )
    
    # Play audio if possible
    if audio_bytes and interaction.user.voice and interaction.user.voice.channel:
        await play_audio_in_voice(interaction.user.voice.channel, audio_bytes)


@bot.tree.command(name="whereami", description="Show your current campaign location")
async def whereami(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign in progress. Use /new_campaign to start one.")
        return

    msg = (
        f"\U0001F5FA\uFE0F You're currently in the campaign {state.get('campaign_title')}, "
        f"located in {state.get('realm')}, at {state.get('location')}."
    )
    await interaction.response.send_message(msg)


@bot.tree.command(name="recap", description="Summarize recent campaign events")
async def recap_slash(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign in progress.")
        return
    summary = summarize_history(state)
    await interaction.response.send_message(f"📘 {summary}")


@bot.tree.command(name="campaignstate", description="Dump internal campaign state (debug)")
async def campaignstate(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    await interaction.response.send_message(f"```json\n{json.dumps(state, indent=2)}\n```", ephemeral=True)


@bot.tree.command(name="set-difficulty", description="Set campaign difficulty")
async def set_difficulty(interaction: discord.Interaction, level: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admins only.", ephemeral=True)
        return
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    level = level.lower()
    if level not in ["easy", "normal", "hard"]:
        await interaction.response.send_message("Level must be easy, normal, or hard.", ephemeral=True)
        return
    state["difficulty"] = level
    save_state(channel_id, state)
    await interaction.response.send_message(f"Difficulty set to {level}.")


@bot.tree.command(name="set_auto_advance", description="Toggle automatic turn advancement")
async def set_auto_advance(interaction: discord.Interaction, enabled: bool):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admins only.", ephemeral=True)
        return
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    state["auto_advance"] = enabled
    save_state(channel_id, state)
    await interaction.response.send_message(f"Auto-advance set to {enabled}")

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

    # Inline dice rolls like "I strike for [1d8+2] damage"
    from utils.dice_roller import extract_inline_rolls
    rolls = extract_inline_rolls(action)
    for notation, result in rolls.items():
        action = action.replace(f"[{notation}]", f"[{notation}={result}]")

    # Build system prompt from current state
    system_prompt = build_system_prompt(state)

    # Get the AI narration using get_dm_response
    narration, updated_state = get_dm_response(action, state, current_player_id, system_prompt=system_prompt)
    loot_items = updated_state.pop('recent_loot', [])
    voice_tag = extract_voice_tag(narration)
    text = clean_text(narration)

    # Format output in the required style
    output = (
        "Narrator: " + text + "\n\n"
    )
    next_player = turn_order[(current_index + 1) % len(turn_order)] if turn_order else current_player_id
    output += f"<@{current_player_id}>, it's still your turn. What do you do next?\n\n"
    output += f"🎲 Next up: <@{next_player}>"

    await interaction.followup.send(output)
    for item in loot_items:
        add_inventory(current_player_id, item)

    if state.get("auto_advance"):
        idx = get_current_turn_index(updated_state)
        next_idx = (idx + 1) % len(turn_order)
        set_current_turn_index(updated_state, next_idx)
        next_player_id = turn_order[next_idx]
        next_player_mention = f"<@{next_player_id}>"
        await interaction.followup.send(f"{next_player_mention}, it's your turn.")
        voice_id = get_voice_id("Narrator")
        try:
            audio_bytes = text_to_speech(f"It's your turn, {next_player_mention}", voice_id)
            if interaction.user.voice and interaction.user.voice.channel:
                await play_audio_in_voice(interaction.user.voice.channel, audio_bytes)
        except Exception as e:
            print(f"TTS Error: {e}")

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
    campaign_text, state = generate_campaign(state, prompt if prompt else None)
    save_state(channel_id, state)
    
    # Clean and prepare text for TTS
    tts_text = clean_text(campaign_text)
    voice_id = get_voice_id("Narrator")
    
    try:
        audio_bytes = text_to_speech(tts_text, voice_id)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_bytes = None
    
    await interaction.followup.send(campaign_text)
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