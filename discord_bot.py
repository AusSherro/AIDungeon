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
from utils.voice_parser import extract_voice_tag, clean_text, clean_for_tts
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
    save_character,
    set_stat,
    set_class,
    set_race,
    add_inventory,
    remove_inventory,
    get_character_summary,
    damage_character,
    heal_character,
    long_rest,
    short_rest,
    death_save,
    SKILLS,
    calculate_skill_bonus,
    get_ability_modifier,
)
from utils.combat_manager import (
    start_combat, roll_initiative, next_turn, 
    get_active_combatant, end_combat, attack,
    get_combat_status, load_combat
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
        # Clean text for TTS - remove suggestions and formatting
        tts_text = clean_for_tts(text)
        if not tts_text:
            return
            
        voice_id = get_voice_id(voice_tag)
        audio_bytes = await text_to_speech_async(tts_text, voice_id)
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

    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return

    # Check turn order (if not free-form mode)
    turn_order = state.get("turn_order", [])
    current_index = state.get("current_turn_index", 0)
    
    if not state.get("free_form", True) and turn_order:
        current_player_id = turn_order[current_index]
        if str(interaction.user.id) != current_player_id:
            current_player = f"<@{current_player_id}>"
            await interaction.response.send_message(f"⏳ It's {current_player}'s turn right now.", ephemeral=True)
            return

    await interaction.response.defer()

    # Get character info
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name

    # Process inline dice rolls [1d20+5]
    rolls = extract_inline_rolls(action)
    for notation, result in rolls.items():
        action = action.replace(f"[{notation}]", f"**{result}** ({notation})")

    # Build system prompt and get AI response
    system_prompt = build_system_prompt(state)
    narration, updated_state = get_dm_response(action, state, user_id, system_prompt=system_prompt)
    
    # Process loot
    loot_items = updated_state.pop('recent_loot', [])
    voice_tag = extract_voice_tag(narration)
    text = clean_text(narration)

    # Format output
    output = f"**{char_name}:** *{action}*\n\n{text}"
    
    # Add loot notifications
    for item in loot_items:
        add_inventory(user_id, item)
        output += f"\n\n🎒 *{char_name} obtained: {item}*"

    # Check if AI is asking for a skill check
    pending = updated_state.get('pending_roll')
    if pending and pending.get('skill'):
        skill_name = pending['skill'].replace('_', ' ').title()
        dc_text = f" (DC {pending['dc']})" if pending.get('dc') else ""
        output += f"\n\n🎲 **Roll {skill_name}{dc_text}!** Use `/roll {pending['skill']}`"

    await interaction.followup.send(output)
    
    # Play TTS (narration only, not the roll prompt)
    await play_tts(interaction, text, voice_tag)
    
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

# D&D 5e Classes and Races for autocomplete
DND_CLASSES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"
]
DND_RACES = [
    "Human", "Elf", "Dwarf", "Halfling", "Dragonborn", "Gnome",
    "Half-Elf", "Half-Orc", "Tiefling"
]

@bot.tree.command(name="character", description="Create or view your character")
@app_commands.describe(
    name="Character name (leave blank to view current)",
    char_class="Your class (Fighter, Wizard, etc.)",
    race="Your race (Human, Elf, etc.)"
)
@app_commands.choices(char_class=[app_commands.Choice(name=c, value=c) for c in DND_CLASSES])
@app_commands.choices(race=[app_commands.Choice(name=r, value=r) for r in DND_RACES])
async def character_cmd(
    interaction: discord.Interaction, 
    name: str = "",
    char_class: str = "",
    race: str = ""
):
    """Create a new character or view your current one."""
    user_id = str(interaction.user.id)
    
    if name:
        # Create new character
        class_choice = char_class if char_class else "Fighter"
        race_choice = race if race else "Human"
        register_character(user_id, name, class_choice, race_choice)
        
        char = load_character(user_id)
        hp = char.get('max_hp', 10)
        
        await interaction.response.send_message(
            f"✨ **{name}** the {race_choice} {class_choice} is ready for adventure!\n"
            f"HP: {hp} | Use `/stats` to set your ability scores."
        )
    elif char_class or race:
        # Update existing character
        char = load_character(user_id)
        if not char:
            await interaction.response.send_message("Create a character first with `/character <name>`", ephemeral=True)
            return
        
        updates = []
        if char_class:
            set_class(user_id, char_class)
            updates.append(f"Class: {char_class}")
        if race:
            set_race(user_id, race)
            updates.append(f"Race: {race}")
        
        await interaction.response.send_message(f"📝 Updated: {', '.join(updates)}")
    else:
        # View character
        summary = get_character_summary(user_id)
        if summary:
            await interaction.response.send_message(summary)
        else:
            await interaction.response.send_message(
                "No character yet! Create one:\n"
                "`/character name:Gandalf char_class:Wizard race:Human`"
            )


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
    channel_id = str(interaction.channel.id)
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
    skill = dice.lower().replace(' ', '_')
    
    # Check for pending roll from AI
    state = load_state(channel_id)
    pending = state.get('pending_roll')
    dc = None
    
    if pending and pending.get('player_id') == user_id:
        dc = pending.get('dc')
    
    result = None
    total = None
    mod = 0
    skill_name = dice
    
    # Check if it's a skill/ability check
    if skill in SKILLS or skill.upper() in ['STR','DEX','CON','INT','WIS','CHA']:
        if not char:
            await interaction.response.send_message("Create a character first to use skill checks!")
            return
        
        if skill in SKILLS:
            mod = calculate_skill_bonus(char, skill)
            skill_name = skill.replace('_', ' ').title()
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
        crit = " 🌟 **Natural 20!**" if result == 20 else " 💀 **Natural 1!**" if result == 1 else ""
        
        msg = f"🎲 **{char_name}** rolls {skill_name}: **{total}** {roll_info} {mod_str}{crit}"
        
        # If there's a DC, show success/failure
        if dc:
            if result == 20:
                msg += " ✅ **SUCCESS!**"
            elif result == 1:
                msg += " ❌ **FAILURE!**"
            elif total >= dc:
                msg += f" ✅ **SUCCESS!** (DC {dc})"
            else:
                msg += f" ❌ **FAILURE!** (DC {dc})"
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
    log_message(channel_id, char_name, msg)
    
    # If there was a pending roll, resolve it with the AI
    if pending and pending.get('player_id') == user_id and total is not None:
        await interaction.followup.send("*Resolving action...*", ephemeral=True)
        
        # Build result message for AI
        success = (result == 20) or (dc and total >= dc and result != 1)
        result_text = f"I rolled {total} for {skill_name}"
        if dc:
            result_text += f" against DC {dc}. {'Success!' if success else 'Failure.'}"
        
        # Get AI's response to the roll result
        system_prompt = build_system_prompt(state)
        narration, updated_state = get_dm_response(result_text, state, user_id, system_prompt=system_prompt)
        
        # Clear the pending roll
        updated_state['pending_roll'] = None
        save_state(channel_id, updated_state)
        
        # Send the outcome
        voice_tag = extract_voice_tag(narration)
        text = clean_text(narration)
        await interaction.followup.send(f"**Outcome:**\n{text}")
        await play_tts(interaction, text, voice_tag)
        log_message(channel_id, "DM", text)


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
            try:
                enemy_list.append({
                    'name': parts[0].title(),
                    'hp': int(parts[1]),
                    'ac': int(parts[2])
                })
            except ValueError:
                continue
    
    if not enemy_list:
        await interaction.response.send_message(
            "**Format:** `/fight goblin:15:13 orc:25:14`\n"
            "• goblin = enemy name\n"
            "• 15 = hit points\n"  
            "• 13 = armor class\n\n"
            "Add `*2` for multiples: `goblin*3:15:13` = 3 goblins",
            ephemeral=True
        )
        return
    
    # Get players from campaign
    state = load_state(channel_id)
    
    if not state.get('campaign_title'):
        await interaction.response.send_message("Start a campaign first with `/campaign`!", ephemeral=True)
        return
    
    players = [(pid, load_character(pid).get('name', 'Adventurer') if load_character(pid) else 'Adventurer') 
               for pid in state.get('players', [])]
    
    if not players:
        # Use whoever started the fight
        char = load_character(str(interaction.user.id))
        char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
        players = [(str(interaction.user.id), char_name)]
    
    # Start combat
    combat_state = start_combat(channel_id, players, enemy_list)
    
    # Roll initiative
    init_state = roll_initiative(channel_id)
    
    # Mark campaign as in combat
    state['in_combat'] = True
    state['free_form'] = False  # Combat uses strict turn order
    save_state(channel_id, state)
    
    # Build initiative display
    order_display = []
    for c in init_state['turn_order']:
        hp_str = f"{c['hp']}/{c.get('max_hp', c['hp'])}"
        order_display.append(f"**{c['name']}** (Init: {c['initiative']}, HP: {hp_str}, AC: {c['ac']})")
    
    first = init_state['turn_order'][0]
    enemy_names = ', '.join(e['name'] for e in enemy_list)
    
    msg = (
        f"⚔️ **COMBAT BEGINS!**\n"
        f"───────────────────────\n"
        f"**Enemies:** {enemy_names}\n\n"
        f"**Initiative Order:**\n" + "\n".join(f"• {o}" for o in order_display) + "\n\n"
        f"───────────────────────\n"
        f"🎯 **{first['name']}**, you're up! Use `/attack` or `/do` for your action."
    )
    
    await interaction.response.send_message(msg)
    log_message(channel_id, "DM", f"Combat started: {enemy_names}")
    await play_tts(interaction, f"Roll for initiative! {first['name']}, you're up first!", "Narrator")


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
    
    # Build attack message with crit/fumble info
    if result.get('fumble'):
        msg = f"⚔️ **{char_name}** attacks **{target}**... 💀 **Critical Miss!** (Rolled 1)"
    elif result.get('crit'):
        msg = f"⚔️ **{char_name}** 🌟 **CRITICAL HIT** on **{target}** for **{result['damage']}** damage! ({result['target_hp']}/{result['target_max_hp']} HP)"
    elif result['hit']:
        msg = f"⚔️ **{char_name}** hits **{target}** for **{result['damage']}** damage! ({result['target_hp']}/{result['target_max_hp']} HP)"
    else:
        msg = f"⚔️ **{char_name}** attacks **{target}**... and misses! (Rolled {result['total']} vs AC)"
    
    # Check if target is down
    if result['target_hp'] == 0:
        msg += f"\n💀 **{target}** is down!"
    
    await interaction.response.send_message(msg)
    log_message(channel_id, char_name, msg)


@bot.tree.command(name="combatinfo", description="Show current combat status")
async def combat_info(interaction: discord.Interaction):
    """Display combat status and turn order."""
    channel_id = str(interaction.channel.id)
    status = get_combat_status(channel_id)
    
    if not status:
        await interaction.response.send_message("No active combat.", ephemeral=True)
        return
    
    # Build turn order display
    turn_display = []
    for i, c in enumerate(status['turn_order']):
        hp_str = f"{c['hp']}/{c.get('max_hp', c['hp'])}"
        indicator = "▶️ " if i == status['current_index'] else "   "
        status_str = f" [{', '.join(c['status'])}]" if c.get('status') else ""
        turn_display.append(f"{indicator}**{c['name']}** - HP: {hp_str}{status_str}")
    
    current = status['current_combatant']
    output = (
        f"⚔️ **COMBAT** - Round {status['round']}\n"
        f"───────────────────────\n"
        + "\n".join(turn_display) + "\n"
        f"───────────────────────\n"
        f"Current turn: **{current['name']}**"
    )
    
    await interaction.response.send_message(output)


@bot.tree.command(name="nextturn", description="Advance to next combatant's turn")
async def next_turn_cmd(interaction: discord.Interaction):
    """Move to the next turn in combat."""
    channel_id = str(interaction.channel.id)
    state = next_turn(channel_id)
    
    if not state:
        await interaction.response.send_message("No active combat.", ephemeral=True)
        return
    
    current = state['turn_order'][state['current_turn']]
    
    # Check if it's an enemy's turn
    if current.get('type') == 'enemy':
        await interaction.response.send_message(
            f"➡️ **{current['name']}** (Enemy) takes their turn!\n"
            f"*The DM controls this enemy. Use `/nextturn` again after their action.*"
        )
    else:
        player_id = current.get('id')
        await interaction.response.send_message(
            f"➡️ <@{player_id}> (**{current['name']}**), it's your turn!\n"
            f"Use `/attack` to strike or `/do` for other actions."
        )


@bot.tree.command(name="endcombat", description="End the current combat")
async def end_combat_cmd(interaction: discord.Interaction):
    """End the combat encounter."""
    channel_id = str(interaction.channel.id)
    
    # End the combat
    end_combat(channel_id)
    
    # Restore free-form mode
    state = load_state(channel_id)
    state['in_combat'] = False
    state['free_form'] = True
    save_state(channel_id, state)
    
    await interaction.response.send_message(
        "⚔️ **Combat has ended.**\n"
        "Back to free-form exploration. Anyone can `/do` actions."
    )
    await play_tts(interaction, "Combat has ended. What do you do now?", "Narrator")


# =============================================================================
# HP & REST COMMANDS
# =============================================================================

@bot.tree.command(name="hp", description="Manage HP - take damage or heal")
@app_commands.describe(
    damage="Amount of damage to take (positive number)",
    heal="Amount to heal (positive number)",
    set_hp="Set HP to specific value"
)
async def hp_cmd(
    interaction: discord.Interaction,
    damage: Optional[int] = None,
    heal: Optional[int] = None,
    set_hp: Optional[int] = None
):
    """Manage your character's HP."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    
    if damage:
        damage_character(user_id, damage)
        char = load_character(user_id)
        msg = f"💔 **{char_name}** takes **{damage}** damage! (HP: {char['hp']}/{char['max_hp']})"
        if char['hp'] == 0:
            msg += "\n⚠️ **{char_name}** is unconscious! Roll death saves with `/deathsave`"
    elif heal:
        heal_character(user_id, heal)
        char = load_character(user_id)
        msg = f"💚 **{char_name}** heals **{heal}** HP! (HP: {char['hp']}/{char['max_hp']})"
    elif set_hp is not None:
        char['hp'] = max(0, min(set_hp, char['max_hp']))
        save_character(user_id, char)
        msg = f"❤️ **{char_name}** HP set to {char['hp']}/{char['max_hp']}"
    else:
        msg = f"❤️ **{char_name}**: {char['hp']}/{char['max_hp']} HP"
        if char.get('temp_hp', 0) > 0:
            msg += f" (+{char['temp_hp']} temp)"
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="deathsave", description="Roll a death saving throw")
async def death_save_cmd(interaction: discord.Interaction):
    """Roll a death saving throw when at 0 HP."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    if char['hp'] > 0:
        await interaction.response.send_message("You're not dying! (HP > 0)", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    roll = random.randint(1, 20)
    
    if roll == 20:
        # Nat 20 = regain 1 HP
        char['hp'] = 1
        char['death_saves'] = {'successes': 0, 'failures': 0}
        save_character(user_id, char)
        msg = f"🎲 **{char_name}** rolls a **20**! 🌟 They regain consciousness with 1 HP!"
    elif roll == 1:
        # Nat 1 = 2 failures
        death_save(user_id, False)
        death_save(user_id, False)
        char = load_character(user_id)
        fails = char['death_saves']['failures']
        msg = f"🎲 **{char_name}** rolls a **1**! 💀 Two death save failures! ({fails}/3 failures)"
        if fails >= 3:
            msg += f"\n☠️ **{char_name}** has died..."
    elif roll >= 10:
        death_save(user_id, True)
        char = load_character(user_id)
        successes = char['death_saves']['successes']
        msg = f"🎲 **{char_name}** rolls **{roll}**. ✓ Success! ({successes}/3 successes)"
        if successes >= 3:
            char['hp'] = 1
            char['death_saves'] = {'successes': 0, 'failures': 0}
            save_character(user_id, char)
            msg += f"\n💚 **{char_name}** stabilizes!"
    else:
        death_save(user_id, False)
        char = load_character(user_id)
        fails = char['death_saves']['failures']
        msg = f"🎲 **{char_name}** rolls **{roll}**. ✗ Failure! ({fails}/3 failures)"
        if fails >= 3:
            msg += f"\n☠️ **{char_name}** has died..."
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="rest", description="Take a short or long rest")
@app_commands.describe(rest_type="Type of rest")
@app_commands.choices(rest_type=[
    app_commands.Choice(name="Short Rest (1 hour)", value="short"),
    app_commands.Choice(name="Long Rest (8 hours)", value="long")
])
async def rest_cmd(interaction: discord.Interaction, rest_type: str):
    """Take a rest to recover HP and abilities."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    old_hp = char['hp']
    
    if rest_type == "long":
        long_rest(user_id)
        char = load_character(user_id)
        msg = (
            f"🌙 **{char_name}** takes a long rest...\n"
            f"💚 HP restored: {old_hp} → {char['hp']}/{char['max_hp']}\n"
            f"✨ Spell slots and abilities restored!"
        )
    else:
        # For short rest, use half of available hit dice
        available = char['level'] - char.get('hit_dice_used', 0)
        dice_to_use = min(1, available)  # Use 1 hit die by default
        short_rest(user_id, dice_to_use)
        char = load_character(user_id)
        msg = (
            f"☀️ **{char_name}** takes a short rest...\n"
            f"💚 HP: {old_hp} → {char['hp']}/{char['max_hp']}"
        )
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="inventory", description="View or manage your inventory")
@app_commands.describe(
    add="Item to add to inventory",
    remove="Item to remove from inventory"
)
async def inventory_cmd(
    interaction: discord.Interaction,
    add: Optional[str] = None,
    remove: Optional[str] = None
):
    """Manage your character's inventory."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    
    if add:
        add_inventory(user_id, add)
        await interaction.response.send_message(f"🎒 **{char_name}** obtained: {add}")
    elif remove:
        result = remove_inventory(user_id, remove)
        if result:
            await interaction.response.send_message(f"🎒 **{char_name}** dropped: {remove}")
        else:
            await interaction.response.send_message(f"❌ {remove} not found in inventory", ephemeral=True)
    else:
        # Display inventory
        char = load_character(user_id)
        items = char.get('inventory', [])
        if items:
            item_list = '\n'.join(f"• {item}" for item in items)
            msg = f"🎒 **{char_name}'s Inventory:**\n{item_list}"
        else:
            msg = f"🎒 **{char_name}'s** inventory is empty."
        await interaction.response.send_message(msg)


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


@bot.tree.command(name="turns", description="Toggle turn order mode")
@app_commands.describe(mode="Turn order mode")
@app_commands.choices(mode=[
    app_commands.Choice(name="Free-form (anyone can act)", value="free"),
    app_commands.Choice(name="Strict (follow turn order)", value="strict")
])
async def turns_mode(interaction: discord.Interaction, mode: str):
    """Toggle between free-form and strict turn order."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    state["free_form"] = (mode == "free")
    save_state(channel_id, state)
    
    if mode == "free":
        await interaction.response.send_message("🎭 **Free-form mode** - Anyone can `/do` actions anytime!")
    else:
        await interaction.response.send_message("📋 **Strict turn order** - Must follow turn order. Use `/done` to pass turn.")


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
1. `/character name:Gandalf char_class:Wizard race:Human`
2. `/stats strength:14 dexterity:16 ...`
3. Join a voice channel
4. `/campaign` - Start an adventure!

**During Play:**
• `/do <action>` - Describe what you do
• `/say <speech>` - Speak in character  
• `/roll <dice>` - Roll dice (1d20, 2d6+3) or skills (athletics, stealth)
• `/done` - End your turn

**Character:**
• `/character` - View your character sheet
• `/stats` - Set ability scores
• `/hp damage:5` or `/hp heal:10` - Manage HP
• `/inventory` - View/add/remove items
• `/rest` - Short or long rest

**Combat:**
• `/fight goblin:15:13 orc:25:14` - Start combat (name:hp:ac)
• `/attack target:Goblin bonus:5 damage:1d8+3` - Attack!
• `/combatinfo` - View turn order and HP
• `/nextturn` - Advance to next combatant
• `/deathsave` - Roll death saving throw
• `/endcombat` - End combat

**Campaign:**
• `/status` - View party info
• `/recap` - AI summary of recent events

**Settings:**
• `/voice` - Toggle TTS on/off
• `/leave` - Disconnect from voice
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
