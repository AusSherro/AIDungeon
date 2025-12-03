"""
AI Dungeon Master Discord Bot
A voice-enabled D&D 5e experience using GPT-4o and TTS
"""

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
from services.elevenlabs_service import text_to_speech_async
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
from utils.dice_roller import roll_dice, extract_inline_rolls
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
from utils.combat_manager import (
    start_combat, roll_initiative, next_turn, 
    get_active_combatant, end_combat, attack
)

load_dotenv()
Config.validate()

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Voice client manager
voice_manager = VoiceClientManager()


async def play_tts(interaction, text: str, voice_tag: str = "Narrator"):
    """Play TTS if enabled and user is in voice channel."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("tts_enabled", True):
        return
    
    if not (interaction.user.voice and interaction.user.voice.channel):
        return
    
    try:
        voice_id = get_voice_id(voice_tag)
        audio_bytes = await text_to_speech_async(text, voice_id)
        if audio_bytes:
            await voice_manager.play(interaction.user.voice.channel, audio_bytes)
    except Exception as e:
        print(f"TTS Error: {e}")


# =============================================================================
# CAMPAIGN COMMANDS
# =============================================================================

@bot.tree.command(name="campaign", description="Start a new D&D campaign")
@app_commands.describe(theme="Optional theme like 'pirates', 'horror', 'mystery in a castle'")
async def campaign_start(interaction: discord.Interaction, theme: str = ""):
    """Start a new campaign with players in your voice channel."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    await interaction.response.defer()
    
    # Check voice channel
    if not (interaction.user.voice and interaction.user.voice.channel):
        await interaction.followup.send("🎤 Join a voice channel first, then start the campaign!")
        return
    
    # Get players from voice channel
    members = [m for m in interaction.user.voice.channel.members if not m.bot]
    if not members:
        await interaction.followup.send("👥 No players found in your voice channel.")
        return
    
    # Randomize turn order
    random.shuffle(members)
    turn_order = [str(m.id) for m in members]
    
    # Generate campaign
    display_text, tts_text, state = generate_campaign(state, theme if theme else None)
    
    # Update state
    set_turn_order(state, turn_order)
    set_current_turn_index(state, 0)
    state["players"] = turn_order
    state["tts_enabled"] = state.get("tts_enabled", True)
    save_state(channel_id, state)
    
    # Build player list
    player_names = []
    for pid in turn_order:
        char = load_character(pid)
        if char:
            player_names.append(f"<@{pid}> as **{char['name']}**")
        else:
            player_names.append(f"<@{pid}>")
    
    # Send campaign intro
    first_player = f"<@{turn_order[0]}>"
    output = (
        f"{display_text}\n\n"
        f"───────────────────────\n"
        f"**Party:** {' • '.join(player_names)}\n\n"
        f"🎲 {first_player}, you're up first! Use `/do` to take an action."
    )
    
    await interaction.followup.send(output)
    log_message(channel_id, "DM", f"Campaign started: {state.get('campaign_title')}")
    
    # Play TTS
    await play_tts(interaction, tts_text, "Narrator")


@bot.tree.command(name="do", description="Describe what your character does")
@app_commands.describe(action="What does your character do?")
async def do_action(interaction: discord.Interaction, action: str):
    """Take an action in the campaign."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    turn_order = state.get("turn_order", [])
    current_index = state.get("current_turn_index", 0)

    if not turn_order:
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return

    # Check if it's this player's turn
    current_player_id = turn_order[current_index]
    if str(interaction.user.id) != current_player_id:
        current_player = f"<@{current_player_id}>"
        await interaction.response.send_message(f"⏳ It's {current_player}'s turn right now.", ephemeral=True)
        return

    await interaction.response.defer()

    # Process inline dice rolls [1d20+5]
    rolls = extract_inline_rolls(action)
    for notation, result in rolls.items():
        action = action.replace(f"[{notation}]", f"**{result}** ({notation})")

    # Get character name
    char = load_character(str(interaction.user.id))
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name

    # Build system prompt and get AI response
    system_prompt = build_system_prompt(state)
    narration, updated_state = get_dm_response(action, state, str(interaction.user.id), system_prompt=system_prompt)
    
    # Process loot
    loot_items = updated_state.pop('recent_loot', [])
    voice_tag = extract_voice_tag(narration)
    text = clean_text(narration)

    # Format output
    output = f"**{char_name}:** *{action}*\n\n{text}"
    
    # Add loot notifications
    for item in loot_items:
        add_inventory(str(interaction.user.id), item)
        output += f"\n\n🎒 *{char_name} obtained: {item}*"

    await interaction.followup.send(output)
    
    # Play TTS
    await play_tts(interaction, text, voice_tag)

    # Auto-advance or remind about /done
    if state.get("auto_advance"):
        next_idx = (current_index + 1) % len(turn_order)
        set_current_turn_index(updated_state, next_idx)
        next_player = f"<@{turn_order[next_idx]}>"
        await interaction.followup.send(f"➡️ {next_player}, your turn!")
    
    save_state(channel_id, updated_state)
    log_message(channel_id, char_name, action)
    log_message(channel_id, "DM", text)


@bot.tree.command(name="say", description="Say something in character")
@app_commands.describe(speech="What does your character say?")
async def say_action(interaction: discord.Interaction, speech: str):
    """Speak as your character."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start!")
        return
    
    char = load_character(str(interaction.user.id))
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
    
    await interaction.response.send_message(f'**{char_name}:** "{speech}"')
    log_message(channel_id, char_name, f'"{speech}"')


@bot.tree.command(name="done", description="End your turn")
async def end_turn(interaction: discord.Interaction):
    """Pass the turn to the next player."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    turn_order = get_turn_order(state)
    idx = get_current_turn_index(state)
    
    if not turn_order:
        await interaction.response.send_message("No campaign running.")
        return
    
    current_player_id = turn_order[idx]
    if str(interaction.user.id) != current_player_id:
        await interaction.response.send_message("It's not your turn!", ephemeral=True)
        return
    
    # Advance turn
    next_idx = (idx + 1) % len(turn_order)
    set_current_turn_index(state, next_idx)
    save_state(channel_id, state)
    
    next_player_id = turn_order[next_idx]
    next_char = load_character(next_player_id)
    char_name = next_char.get('name', 'adventurer') if next_char else 'adventurer'
    
    await interaction.response.send_message(f"➡️ <@{next_player_id}>, it's your turn! What does **{char_name}** do?")
    log_message(channel_id, "DM", f"Turn passed to {char_name}")
    
    await play_tts(interaction, f"Your turn, {char_name}. What do you do?", "Narrator")


@bot.tree.command(name="status", description="Show current campaign status")
async def status(interaction: discord.Interaction):
    """Display campaign and party status."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return
    
    turn_order = state.get("turn_order", [])
    current_idx = state.get("current_turn_index", 0)
    current_player = turn_order[current_idx] if turn_order else None
    
    # Build party status
    party_status = []
    for i, pid in enumerate(turn_order):
        char = load_character(pid)
        if char:
            hp = f"HP: {char.get('hp', '?')}/{char.get('max_hp', '?')}"
            indicator = "▶️ " if i == current_idx else "  "
            party_status.append(f"{indicator}**{char['name']}** - {hp}")
        else:
            indicator = "▶️ " if i == current_idx else "  "
            party_status.append(f"{indicator}<@{pid}>")
    
    output = (
        f"# 📜 {state.get('campaign_title')}\n"
        f"*{state.get('realm')} • {state.get('location')}*\n\n"
        f"**Party:**\n" + "\n".join(party_status) + "\n\n"
        f"🎲 Current turn: <@{current_player}>" if current_player else ""
    )
    
    await interaction.response.send_message(output)


@bot.tree.command(name="recap", description="Get a summary of recent events")
async def recap(interaction: discord.Interaction):
    """Summarize what happened recently."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running.")
        return
    
    await interaction.response.defer()
    summary = summarize_history(state)
    await interaction.followup.send(f"📖 **Previously...**\n\n{summary}")


# =============================================================================
# CHARACTER COMMANDS
# =============================================================================

@bot.tree.command(name="character", description="Create or view your character")
@app_commands.describe(name="Character name (leave blank to view current)")
async def character_cmd(interaction: discord.Interaction, name: str = ""):
    """Create a new character or view your current one."""
    user_id = str(interaction.user.id)
    
    if name:
        # Create/update character
        register_character(user_id, name)
        await interaction.response.send_message(f"✨ Character **{name}** created! Use `/stats` to set your abilities.")
    else:
        # View character
        summary = get_character_summary(user_id)
        if summary:
            await interaction.response.send_message(summary)
        else:
            await interaction.response.send_message("No character yet. Use `/character <name>` to create one!")


@bot.tree.command(name="stats", description="Set your character's stats")
@app_commands.describe(
    strength="STR (1-20)", dexterity="DEX (1-20)", constitution="CON (1-20)",
    intelligence="INT (1-20)", wisdom="WIS (1-20)", charisma="CHA (1-20)"
)
async def set_stats(
    interaction: discord.Interaction,
    strength: Optional[int] = None,
    dexterity: Optional[int] = None, 
    constitution: Optional[int] = None,
    intelligence: Optional[int] = None,
    wisdom: Optional[int] = None,
    charisma: Optional[int] = None
):
    """Set multiple stats at once."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first with `/character <name>`")
        return
    
    updates = []
    if strength: set_stat(user_id, "STR", strength); updates.append(f"STR: {strength}")
    if dexterity: set_stat(user_id, "DEX", dexterity); updates.append(f"DEX: {dexterity}")
    if constitution: set_stat(user_id, "CON", constitution); updates.append(f"CON: {constitution}")
    if intelligence: set_stat(user_id, "INT", intelligence); updates.append(f"INT: {intelligence}")
    if wisdom: set_stat(user_id, "WIS", wisdom); updates.append(f"WIS: {wisdom}")
    if charisma: set_stat(user_id, "CHA", charisma); updates.append(f"CHA: {charisma}")
    
    if updates:
        await interaction.response.send_message(f"📊 Updated: {', '.join(updates)}")
    else:
        await interaction.response.send_message("Provide at least one stat to update!", ephemeral=True)


# =============================================================================
# DICE COMMANDS
# =============================================================================

@bot.tree.command(name="roll", description="Roll dice (e.g., 1d20, 2d6+3, athletics)")
@app_commands.describe(dice="Dice notation or skill name", advantage="Roll with advantage", disadvantage="Roll with disadvantage")
async def roll_cmd(interaction: discord.Interaction, dice: str, advantage: bool = False, disadvantage: bool = False):
    """Roll dice or make a skill check."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
    skill = dice.lower()
    
    # Check if it's a skill/ability check
    if skill in SKILLS or skill.upper() in ['STR','DEX','CON','INT','WIS','CHA']:
        if not char:
            await interaction.response.send_message("Create a character first to use skill checks!")
            return
        
        if skill in SKILLS:
            mod = calculate_skill_bonus(char, skill)
            skill_name = skill.title()
        else:
            mod = get_ability_modifier(char.get(skill.upper(), 10))
            skill_name = skill.upper()
        
        # Roll with advantage/disadvantage
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20) if (advantage or disadvantage) else roll1
        
        if advantage:
            result = max(roll1, roll2)
            roll_info = f"({roll1}, {roll2} → {result})"
        elif disadvantage:
            result = min(roll1, roll2)
            roll_info = f"({roll1}, {roll2} → {result})"
        else:
            result = roll1
            roll_info = f"({result})"
        
        total = result + mod
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        
        # Check for nat 20/1
        crit = " 🌟 **Critical!**" if result == 20 else " 💀 **Critical Fail!**" if result == 1 else ""
        
        msg = f"🎲 **{char_name}** rolls {skill_name}: **{total}** {roll_info} {mod_str}{crit}"
    else:
        # Regular dice roll
        try:
            total, rolls, modifier = roll_dice(dice)
            rolls_str = ', '.join(map(str, rolls))
            mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
            msg = f"🎲 **{char_name}** rolls {dice}: **{total}** ({rolls_str}{mod_str})"
        except:
            await interaction.response.send_message(f"❌ Invalid dice: {dice}", ephemeral=True)
            return
    
    await interaction.response.send_message(msg)
    log_message(str(interaction.channel.id), char_name, msg)


# =============================================================================
# COMBAT COMMANDS
# =============================================================================

@bot.tree.command(name="fight", description="Start combat with enemies")
@app_commands.describe(enemies="Enemies in format: goblin:15:13 orc:25:14 (name:hp:ac)")
async def fight_start(interaction: discord.Interaction, enemies: str):
    """Start a combat encounter."""
    channel_id = str(interaction.channel.id)
    
    # Parse enemies
    enemy_list = []
    for enemy in enemies.split():
        parts = enemy.split(':')
        if len(parts) >= 3:
            enemy_list.append({
                'name': parts[0].title(),
                'hp': int(parts[1]),
                'ac': int(parts[2])
            })
    
    if not enemy_list:
        await interaction.response.send_message("Format: `/fight goblin:15:13 orc:25:14`", ephemeral=True)
        return
    
    # Get players
    state = load_state(channel_id)
    players = [(pid, load_character(pid).get('name', f'Player') if load_character(pid) else 'Player') 
               for pid in state.get('players', [])]
    
    combat_state = start_combat(channel_id, players, enemy_list)
    
    # Roll initiative
    init_state = roll_initiative(channel_id)
    order = [f"{c['name']} ({c['initiative']})" for c in init_state['turn_order']]
    
    enemy_names = ', '.join(e['name'] for e in enemy_list)
    await interaction.response.send_message(
        f"⚔️ **COMBAT BEGINS!**\n"
        f"Enemies: {enemy_names}\n\n"
        f"**Initiative:** {' → '.join(order)}\n\n"
        f"First up: **{init_state['turn_order'][0]['name']}**!"
    )


@bot.tree.command(name="attack", description="Attack a target")
@app_commands.describe(target="Target name", bonus="Attack bonus (e.g., 5)", damage="Damage dice (e.g., 1d8+3)")
async def attack_cmd(interaction: discord.Interaction, target: str, bonus: int, damage: str):
    """Make an attack roll against a target."""
    channel_id = str(interaction.channel.id)
    char = load_character(str(interaction.user.id))
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
    
    result = attack(channel_id, str(interaction.user.id), target, bonus, damage)
    
    if not result:
        await interaction.response.send_message("No combat or target not found!", ephemeral=True)
        return
    
    if result['hit']:
        msg = f"⚔️ **{char_name}** hits **{target}** for **{result['damage']}** damage! ({result['target_hp']} HP remaining)"
    else:
        msg = f"⚔️ **{char_name}** attacks **{target}**... and misses! (Rolled {result['roll']})"
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="endcombat", description="End the current combat")
async def end_combat_cmd(interaction: discord.Interaction):
    """End the combat encounter."""
    channel_id = str(interaction.channel.id)
    end_combat(channel_id)
    await interaction.response.send_message("⚔️ Combat has ended.")


# =============================================================================
# SETTINGS COMMANDS
# =============================================================================

@bot.tree.command(name="voice", description="Toggle voice narration on/off")
@app_commands.describe(enabled="Enable or disable voice")
async def voice_toggle(interaction: discord.Interaction, enabled: bool):
    """Toggle TTS for this channel."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    state["tts_enabled"] = enabled
    save_state(channel_id, state)
    
    status = "🔊 **enabled**" if enabled else "🔇 **disabled**"
    await interaction.response.send_message(f"Voice narration is now {status}")


@bot.tree.command(name="leave", description="Disconnect bot from voice")
async def leave_voice(interaction: discord.Interaction):
    """Disconnect from voice channel."""
    if interaction.guild:
        await voice_manager.disconnect(interaction.guild.id)
        await interaction.response.send_message("👋 Left voice channel.")
    else:
        await interaction.response.send_message("Not in a server.", ephemeral=True)


# =============================================================================
# UTILITY COMMANDS  
# =============================================================================

@bot.tree.command(name="help", description="Show available commands")
async def help_cmd(interaction: discord.Interaction):
    """Display help information."""
    help_text = """
# 🎲 AI Dungeon Master

**Getting Started:**
1. `/character <name>` - Create your character
2. `/stats` - Set your ability scores
3. Join a voice channel
4. `/campaign` - Start an adventure!

**During Play:**
• `/do <action>` - Describe what you do
• `/say <speech>` - Speak in character
• `/roll <dice>` - Roll dice (1d20, 2d6+3, athletics)
• `/done` - End your turn

**Campaign:**
• `/status` - View party and campaign info
• `/recap` - Get a summary of recent events

**Combat:**
• `/fight <enemies>` - Start combat (e.g., goblin:15:13)
• `/attack <target> <bonus> <damage>` - Attack!
• `/endcombat` - End combat

**Settings:**
• `/voice <on/off>` - Toggle voice narration
• `/leave` - Disconnect bot from voice
"""
    await interaction.response.send_message(help_text)


@bot.tree.command(name="exportlog", description="Export session log")
async def export_log(interaction: discord.Interaction):
    """Export the session log as a file."""
    session_id = str(interaction.channel.id)
    log_path = get_log_file(session_id)
    
    if not log_path or not os.path.exists(log_path):
        await interaction.response.send_message("No log found for this session.", ephemeral=True)
        return
    
    await interaction.response.send_message(file=discord.File(log_path))


# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    print(f'🎲 {bot.user} has connected to Discord!')
    
    await asyncio.sleep(2)
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} commands')
        for cmd in synced:
            print(f'  • /{cmd.name}')
    except Exception as e:
        print(f'❌ Sync failed: {e}')


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
