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
from typing import Optional, Dict
from dotenv import load_dotenv
from config import Config

from services.openai_service import (
    get_dm_response, generate_campaign, summarize_history, generate_campaign_summary,
    extract_npcs_and_quests, narrate_enemy_action, narrate_legendary_action, narrate_lair_action,
    narrate_skill_check_outcome, narrate_group_check_outcome, narrate_passive_notice
)
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
    get_context_summary,
    update_campaign_summary,
    add_key_event,
    add_or_update_npc,
    add_quest,
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
    learn_spell,
    forget_spell,
    learn_cantrip,
    prepare_spell,
    unprepare_spell,
    cast_spell,
    get_available_spells,
    get_spell_slots_remaining,
    level_up,
    get_available_classes,
    get_available_races,
)
from utils.combat_manager import (
    start_combat, roll_initiative, next_turn, 
    get_active_combatant, end_combat, attack,
    get_combat_status, load_combat, save_combat,
    use_legendary_action, reset_legendary_actions,
    use_lair_action, damage_combatant
)
from utils.enemy_ai import (
    execute_enemy_turn, select_legendary_action,
    should_use_legendary_action, process_lair_actions,
    get_enemy_profile
)
from utils.combat_flow import (
    combat_timer, CombatTimerManager, CombatFlowConfig,
    process_end_of_turn_effects, process_start_of_turn_effects,
    process_round_transition, check_combat_end, CombatEndReason,
    build_turn_announcement, execute_auto_pass, get_combat_status_summary,
    process_post_combat
)
from utils.handout_manager import (
    create_handout, get_handout, get_handouts_for_player,
    get_all_handouts, reveal_handout, share_handout_with,
    mark_as_read, delete_handout, add_player_secret,
    get_player_secrets, get_unread_secrets, mark_secret_read,
    HANDOUT_TYPES, get_handout_emoji, format_handout_display
)
from utils.map_manager import (
    TacticalMap, Token, load_map, save_map, delete_map,
    create_from_template, TERRAIN_TYPES, TOKEN_SYMBOLS, MAP_TEMPLATES
)
from utils.xp_manager import (
    award_xp, award_party_xp, calculate_combat_xp, get_xp_summary,
    get_xp_to_next_level, format_xp_bar, milestone_level_up
)
from utils.loot_manager import (
    generate_treasure_hoard, generate_enemy_loot, roll_magic_item,
    format_loot_display, format_currency, Rarity
)
from utils.ambient_manager import (
    ambient_manager, AmbientMood, SoundEffect,
    auto_set_mood, play_action_sfx
)
from utils.reaction_manager import (
    has_reaction_available, use_reaction, reset_reactions,
    reset_all_reactions_new_round,
    check_opportunity_attack, resolve_opportunity_attack,
    cast_shield, cast_counterspell, use_uncanny_dodge,
    get_available_reactions, format_reaction_prompt, ReactionType
)
from utils.voice_map import get_voice_for_npc, extract_npc_from_tag
from utils.skill_check_manager import (
    parse_skill_check_request, SkillCheckRequest, SkillCheckResult,
    roll_skill_check, resolve_group_check, GroupCheckResult,
    calculate_passive_score, check_passive_perception, check_passive_insight,
    create_pending_check, get_pending_check, add_check_result, complete_pending_check,
    clear_pending_check, is_check_pending, get_missing_players,
    format_check_result, format_group_check_result, build_roll_prompt,
    CheckType, PendingCheck
)
from utils.resource_manager import (
    process_narrative_for_resources, format_resource_status,
    detect_spell_cast, detect_class_ability, detect_consumable_use,
    ResourceConsumption, DetectedSpell, DetectedAbility, DetectedConsumable
)
from utils.npc_manager import (
    NPC, Faction, NPCRole, Disposition,
    load_npcs, save_npcs, get_npc, create_npc,
    update_npc_disposition, update_npc_mood, record_npc_interaction,
    get_npc_context_for_ai, load_factions, save_factions, get_faction,
    create_faction, modify_faction_standing, get_faction_context_for_ai,
    create_merchant_shop, get_shop_inventory, buy_from_shop, sell_to_shop,
    format_shop_inventory, assign_voice_to_npc, list_all_npcs, list_all_factions,
    get_nearby_npcs, format_npc_summary, format_faction_summary,
    process_npc_from_narration, get_standing_title
)
from utils.quest_manager import (
    Quest, QuestObjective, QuestReward, QuestStatus, QuestType, QuestDifficulty,
    load_quests, save_quests, get_quest, get_quest_by_name,
    create_quest, update_quest, delete_quest,
    get_active_quests, get_completed_quests, get_available_quests,
    add_objective, update_objective_progress, complete_objective, fail_objective,
    complete_quest, fail_quest, abandon_quest, accept_quest,
    detect_quest_progress, detect_new_quest, process_narration_for_quests,
    format_quest_summary, format_quest_log, format_quest_rewards_message,
    get_quest_context_for_ai, QUEST_TEMPLATES, create_quest_from_template,
    add_note_to_quest,
    # Phase 13: Autonomous Quest Management
    detect_structured_quest_tags, detect_natural_language_quest_offer,
    load_rumors, get_uninvestigated_rumors, add_rumor, convert_rumor_to_quest,
    link_quests, get_next_quest_in_chain, activate_chain_quest
)
from utils.environment_manager import (
    Trap, Hazard, WeatherCondition, LightingCondition, EnvironmentState,
    TrapTrigger, TrapType, WeatherType, LightLevel, CoverType, TerrainType, HazardType,
    load_environment, save_environment,
    create_trap, create_trap_from_template, get_trap, get_traps_at_position,
    detect_trap, disarm_trap, trigger_trap, check_trap_triggers, remove_trap, list_traps,
    create_hazard, get_hazards_at_position, process_hazard_damage,
    tick_hazard_durations, remove_hazard, list_hazards,
    set_weather, get_weather, clear_weather, get_weather_effects,
    set_lighting, get_lighting, get_lighting_effects, check_vision,
    add_terrain_zone, get_terrain_at_position, get_movement_cost,
    check_terrain_effects, remove_terrain_zone, list_terrain_zones,
    get_cover_bonus, calculate_cover,
    get_environment_context_for_ai, format_environment_summary,
    format_trap_info, format_hazard_info, format_weather_info, format_lighting_info,
    TRAP_TEMPLATES, WEATHER_EFFECTS, LIGHT_EFFECTS, TERRAIN_EFFECTS, COVER_BONUSES
)
from utils.encounter_manager import (
    Encounter, TravelState, Monster,
    TerrainType as EncounterTerrainType, EncounterDifficulty, TravelPace, EventType,
    generate_combat_encounter, generate_social_encounter, generate_discovery_encounter,
    generate_random_event, roll_for_encounter, determine_encounter_type,
    start_travel, calculate_travel_time, advance_travel, get_travel_status, clear_travel_state,
    get_travel_context_for_ai, format_encounter_summary, format_travel_status, format_random_event,
    get_party_xp_threshold, calculate_encounter_difficulty, get_appropriate_cr_range,
    TERRAIN_ENCOUNTERS, TERRAIN_MODIFIERS, TRAVEL_SPEEDS, MONSTERS_BY_CR, CR_TO_XP, RANDOM_EVENTS
)
from utils.combat_trigger import (
    detect_combat_trigger, detect_structured_combat, detect_ai_combat_narration,
    detect_player_attack_intent, build_enemy_list, parse_enemy_list,
    CombatTriggerResult, CombatInitiator, EnemySpec,
    generate_loot_for_enemies, calculate_xp_from_combat,
    format_combat_start_message, format_post_combat_loot
)
from utils.world_map import (
    Location, TravelIntent, LocationDiscovery, WorldState,
    LocationType, DiscoveryStatus,
    load_world_state, save_world_state,
    add_location, get_location, get_current_location, set_current_location,
    connect_locations, get_distance, get_all_locations, get_visited_locations, get_known_locations,
    detect_travel_intent, detect_arrival_tag, detect_location_discovered_tag,
    process_narration_for_travel, start_travel_from_intent, complete_travel,
    can_fast_travel, get_fast_travel_options, fast_travel,
    get_world_context_for_ai as get_map_context,
    format_location, format_world_map, format_travel_result
)
from utils.session_manager import (
    SessionState, SessionSummary, SessionStatus, PacingPhase, PacingHint,
    load_session_state, save_session_state,
    start_session, end_session, pause_session, resume_session,
    record_activity, get_session_duration_minutes, check_inactivity,
    get_current_pacing_phase, get_pacing_hints, mark_hint_sent,
    get_pacing_context_for_ai, should_suggest_rest,
    check_for_resume, generate_session_recap, generate_quick_recap,
    format_session_status, format_recap, format_session_end_summary,
    load_session_summaries, save_session_summary,
    save_recovery_point, load_recovery_point, clear_recovery_point,
    auto_save_manager, AUTO_SAVE_INTERVAL, calculate_time_since
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

# Store active channel references for timer callbacks
_active_channels: Dict[str, discord.TextChannel] = {}


# =============================================================================
# COMBAT TIMER CALLBACKS
# =============================================================================

async def on_turn_warning(channel_id: str, player_id: str, seconds_remaining: int):
    """Called when a player's turn timer is running low."""
    channel = _active_channels.get(channel_id)
    if not channel:
        return
    
    await channel.send(
        f"⏰ <@{player_id}>, you have **{seconds_remaining} seconds** remaining!\n"
        f"Use `/attack`, `/cast`, `/do`, or `/nextturn` to complete your turn."
    )


async def on_turn_timeout(channel_id: str, combatant_name: str):
    """Called when a player's turn times out - auto-pass with Dodge action."""
    channel = _active_channels.get(channel_id)
    if not channel:
        return
    
    # Execute auto-pass (Dodge action)
    result = execute_auto_pass(channel_id, combatant_name)
    
    if result.get('error'):
        return
    
    await channel.send(result['message'])
    
    # Advance to next turn
    state = next_turn(channel_id)
    if state:
        current = state['turn_order'][state['current_turn']]
        
        # Check if next is an enemy and auto-execute
        if current.get('type') == 'enemy' and CombatFlowConfig.AUTO_EXECUTE_ENEMY_TURNS:
            # We need a fake interaction for enemy turn execution
            # For now, just announce - full enemy execution needs interaction context
            await channel.send(f"⚔️ **{current['name']}** is up next...")
        else:
            # Player turn - send announcement and start timer
            announcement = build_turn_announcement(channel_id, current)
            await channel.send(announcement['message'])
            
            # Start new timer
            await combat_timer.start_turn_timer(
                channel_id,
                current['name'],
                current.get('id', '')
            )


async def setup_timer_callbacks(channel_id: str, channel: discord.TextChannel):
    """Set up timer callbacks for a channel."""
    _active_channels[channel_id] = channel
    combat_timer.set_callbacks(channel_id, on_turn_warning, on_turn_timeout)


# =============================================================================
# SKILL CHECK CONFIGURATION AND BUTTON VIEW
# =============================================================================

class SkillCheckConfig:
    """Configuration for skill check handling."""
    ROLL_TIMEOUT_SECONDS = 60  # Time to wait for player rolls
    AUTO_ROLL_ON_TIMEOUT = True  # Auto-roll if player doesn't respond
    NARRATE_OUTCOMES = True  # Use AI to narrate outcomes
    CHECK_PASSIVE_PERCEPTION = True  # Auto-check passive perception
    GROUP_CHECK_MAJORITY = 0.5  # Fraction needed for group success (0.5 = majority)


class SkillCheckRollButton(discord.ui.View):
    """Button view for skill check rolls."""
    
    def __init__(self, channel_id: str, player_ids: list, skill: str, 
                 dc: int = None, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.channel_id = channel_id
        self.player_ids = player_ids
        self.skill = skill
        self.dc = dc
        self.rolled_players = set()
        self._message = None
    
    async def on_timeout(self):
        """Handle timeout - auto-roll for players who didn't respond."""
        if not SkillCheckConfig.AUTO_ROLL_ON_TIMEOUT:
            return
        
        pending = get_pending_check(self.channel_id)
        if not pending:
            return
        
        # Auto-roll for missing players
        missing = get_missing_players(self.channel_id)
        for player_id in missing:
            char = load_character(player_id)
            if not char:
                continue
            
            result = roll_skill_check(
                player_id,
                char.get('name', 'Unknown'),
                char,
                pending.request
            )
            add_check_result(self.channel_id, player_id, result)
        
        # Disable the button
        for item in self.children:
            item.disabled = True
        
        if self._message:
            try:
                await self._message.edit(view=self)
            except:
                pass
    
    @discord.ui.button(label="🎲 Roll", style=discord.ButtonStyle.primary, custom_id="skill_roll")
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle roll button press."""
        player_id = str(interaction.user.id)
        
        # Check if this player should roll
        if player_id not in self.player_ids:
            await interaction.response.send_message(
                "This roll isn't for you!", ephemeral=True
            )
            return
        
        # Check if already rolled
        if player_id in self.rolled_players:
            await interaction.response.send_message(
                "You've already rolled!", ephemeral=True
            )
            return
        
        # Get pending check
        pending = get_pending_check(self.channel_id)
        if not pending:
            await interaction.response.send_message(
                "This check has expired.", ephemeral=True
            )
            return
        
        # Get character and roll
        char = load_character(player_id)
        if not char:
            await interaction.response.send_message(
                "You need a character to roll!", ephemeral=True
            )
            return
        
        result = roll_skill_check(
            player_id,
            char.get('name', 'Unknown'),
            char,
            pending.request
        )
        
        # Add result and mark as rolled
        self.rolled_players.add(player_id)
        all_done = add_check_result(self.channel_id, player_id, result)
        
        # Send roll result
        result_msg = format_check_result(result)
        await interaction.response.send_message(result_msg)
        
        # Check if all players have rolled
        if all_done:
            # Disable button
            button.disabled = True
            if self._message:
                try:
                    await self._message.edit(view=self)
                except:
                    pass
            
            # Process results
            await process_completed_skill_check(
                interaction.channel,
                self.channel_id
            )


async def process_completed_skill_check(channel: discord.TextChannel, channel_id: str):
    """Process a completed skill check and generate AI narration."""
    pending = complete_pending_check(channel_id)
    if not pending:
        return
    
    state = load_state(channel_id)
    
    # Check if this was a group check
    if pending.request.is_group_check:
        results = list(pending.results.values())
        group_result = resolve_group_check(results, pending.request.dc)
        
        # Format result
        result_msg = format_group_check_result(group_result)
        await channel.send(result_msg)
        
        # AI narration if enabled
        if SkillCheckConfig.NARRATE_OUTCOMES:
            try:
                individual = [(r.player_name, r.total, r.success) for r in results]
                narration = await narrate_group_check_outcome(
                    group_result.skill_or_ability,
                    group_result.dc,
                    group_result.successes,
                    group_result.failures,
                    group_result.group_success,
                    individual,
                    pending.request.context or "the group check"
                )
                await channel.send(f"*{narration}*")
                
                # TTS
                voice_tag = extract_voice_tag(narration)
                tts_text = clean_for_tts(narration)
                # Note: We don't have an interaction here, so skip TTS
            except Exception as e:
                print(f"Group check narration error: {e}")
    else:
        # Single player check - get the one result
        if pending.results:
            result = list(pending.results.values())[0]
            
            # AI narration if enabled
            if SkillCheckConfig.NARRATE_OUTCOMES and result.dc is not None:
                try:
                    narration = await narrate_skill_check_outcome(
                        result.player_name,
                        result.skill_or_ability,
                        result.total,
                        result.dc,
                        result.success,
                        result.natural_20,
                        result.natural_1,
                        pending.request.context or "the action"
                    )
                    await channel.send(f"**Outcome:**\n*{narration}*")
                    
                    # Play TTS for the outcome
                    try:
                        voice_tag = extract_voice_tag(narration) or "Narrator"
                        tts_text = clean_for_tts(narration)
                        if tts_text:
                            voice_id = get_voice_id(voice_tag)
                            audio_bytes = await text_to_speech_async(tts_text, voice_id)
                            if audio_bytes:
                                # Find a voice channel with players
                                guild = channel.guild
                                for vc in guild.voice_channels:
                                    if any(not m.bot for m in vc.members):
                                        await voice_manager.play(vc, audio_bytes)
                                        break
                    except Exception as tts_err:
                        print(f"TTS error (non-blocking): {tts_err}")
                    
                    # Generate story continuation with new options
                    try:
                        outcome_desc = "succeeded" if result.success else "failed"
                        if result.natural_20:
                            outcome_desc = "critically succeeded"
                        elif result.natural_1:
                            outcome_desc = "critically failed"
                        
                        continuation_prompt = f"The player {outcome_desc} their {result.skill_or_ability} check (rolled {result.total} vs DC {result.dc}). Continue the story based on this outcome and present 3 new action options."
                        
                        system_prompt = build_system_prompt(state, channel_id)
                        continuation, updated_state = get_dm_response(
                            continuation_prompt, 
                            state, 
                            list(pending.results.keys())[0] if pending.results else None,
                            system_prompt=system_prompt
                        )
                        
                        # Clean and send continuation
                        cont_text = clean_text(continuation)
                        await channel.send(f"\n{cont_text}")
                        
                        # Play TTS for continuation
                        cont_voice = extract_voice_tag(continuation) or "Narrator"
                        cont_tts = clean_for_tts(continuation)
                        if cont_tts:
                            cont_voice_id = get_voice_id(cont_voice)
                            cont_audio = await text_to_speech_async(cont_tts, cont_voice_id)
                            if cont_audio:
                                for vc in guild.voice_channels:
                                    if any(not m.bot for m in vc.members):
                                        await voice_manager.play(vc, cont_audio)
                                        break
                        
                        save_state(channel_id, updated_state)
                    except Exception as cont_err:
                        print(f"Story continuation error: {cont_err}")
                    
                    # Update state to clear pending roll
                    state['pending_roll'] = None
                    save_state(channel_id, state)
                except Exception as e:
                    print(f"Skill check narration error: {e}")


async def prompt_skill_check(
    channel: discord.TextChannel,
    channel_id: str,
    request: SkillCheckRequest,
    player_ids: list,
    player_mentions: list
):
    """
    Send a skill check prompt with roll button.
    
    Args:
        channel: Discord channel to send to
        channel_id: Channel ID string
        request: The skill check request
        player_ids: List of player IDs who should roll
        player_mentions: List of player mentions (e.g., ["<@123>"])
    """
    # Create pending check
    create_pending_check(channel_id, request, player_ids, SkillCheckConfig.ROLL_TIMEOUT_SECONDS)
    
    # Build prompt message
    prompt_msg = build_roll_prompt(request, player_mentions)
    
    # Create button view
    view = SkillCheckRollButton(
        channel_id, 
        player_ids, 
        request.skill_or_ability,
        request.dc,
        SkillCheckConfig.ROLL_TIMEOUT_SECONDS
    )
    
    # Send message with button
    message = await channel.send(prompt_msg, view=view)
    view._message = message


async def check_and_prompt_passive_perception(
    channel: discord.TextChannel,
    channel_id: str,
    hidden_dc: int,
    hidden_description: str
):
    """
    Check passive perception for all players and announce notices.
    
    Args:
        channel: Discord channel
        channel_id: Channel ID
        hidden_dc: DC to notice the hidden thing
        hidden_description: What's hidden
    """
    if not SkillCheckConfig.CHECK_PASSIVE_PERCEPTION:
        return
    
    state = load_state(channel_id)
    players = state.get('players', [])
    
    notices = []
    for player_id in players:
        char = load_character(player_id)
        if not char:
            continue
        
        passive = calculate_passive_score(char, 'perception')
        if passive >= hidden_dc:
            notices.append((char.get('name', 'Someone'), player_id, hidden_description))
    
    # Narrate notices
    for name, player_id, what in notices:
        try:
            narration = await narrate_passive_notice(name, what, passive, hidden_dc)
            await channel.send(narration)
        except Exception as e:
            print(f"Passive notice error: {e}")
            await channel.send(f"👁️ **{name}** notices {what}.")


async def play_tts(interaction, text: str, voice_tag: str = "Narrator"):
    """Play TTS if enabled and user is in voice channel."""
    from services.elevenlabs_service import TTS_PROVIDER
    
    # Quick exit if TTS is disabled
    if TTS_PROVIDER == 'disabled':
        return
    
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
        
        # Check if this is an NPC voice (not a simple tag like "Narrator")
        npc_name, npc_description = extract_npc_from_tag(voice_tag)
        
        if npc_description and voice_tag.lower() != 'narrator':
            # Use NPC-specific voice based on description
            voice_tag = get_voice_for_npc(npc_description, npc_name)
        
        voice_id = get_voice_id(voice_tag)
        audio_bytes = await text_to_speech_async(tts_text, voice_id)
        if audio_bytes:
            await voice_manager.play(interaction.user.voice.channel, audio_bytes)
    except Exception as e:
        # Silently fail - don't let TTS errors break gameplay
        print(f"TTS Error (non-blocking): {e}")


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
    
    # Start session tracking (Phase 15)
    session = start_session(channel_id, turn_order)
    
    # Register auto-save callback
    def get_campaign_state(ch_id: str) -> dict:
        return load_state(ch_id)
    
    auto_save_manager.register_channel(channel_id, get_campaign_state)
    asyncio.create_task(auto_save_manager.start_auto_save(channel_id))
    
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

    # ==== PHASE 4: Resource Auto-Consumption ====
    # Detect and consume resources (spells, class abilities, consumables) from the action
    resource_result = process_narrative_for_resources(user_id, action, auto_consume=True)
    resource_summary = resource_result.get('summary', '')

    # ==== PHASE 7: Environment Hazard Checks ====
    # Check for trap triggers based on action keywords
    trap_notification = ""
    movement_keywords = ['move', 'walk', 'run', 'step', 'approach', 'enter', 'open', 'touch', 'cross', 'advance']
    if any(kw in action.lower() for kw in movement_keywords):
        # Check if player triggers any traps
        trap_results = check_trap_triggers(channel_id, char_name, trigger_type="movement")
        for result in trap_results:
            if result.get("triggered"):
                trap = result["trap"]
                trap_notification += f"\n\n💥 **TRAP TRIGGERED!** {trap.name}\n"
                trap_notification += f"*{trap.description}*\n"
                trap_notification += f"⚠️ Make a {trap.save_type.upper()} saving throw DC {trap.save_dc}!"
                trap_notification += f"\nDamage on fail: {trap.damage_dice} {trap.damage_type}"

    # ==== PHASE 11: Check player attack intent BEFORE sending to AI ====
    # This catches "I attack the goblin" type actions
    player_attack_trigger = detect_player_attack_intent(action)
    
    # Build system prompt and get AI response
    system_prompt = build_system_prompt(state, channel_id)
    narration, updated_state = get_dm_response(action, state, user_id, system_prompt=system_prompt)
    
    # ==== PHASE 5: Auto-detect NPCs from narration ====
    current_location = updated_state.get('location', '')
    detected_npc = process_npc_from_narration(channel_id, narration, current_location)
    npc_notification = ""
    if detected_npc and detected_npc.memory.interaction_count <= 1:
        # New NPC detected - record interaction
        char_names = []
        for pid in updated_state.get('turn_order', [user_id]):
            pchar = load_character(pid)
            if pchar:
                char_names.append(pchar.get('name', ''))
        if char_names:
            record_npc_interaction(channel_id, detected_npc.name, char_names)
        npc_notification = f"\n\n👤 *New NPC met: **{detected_npc.name}** ({detected_npc.role.replace('_', ' ').title()})*"
    
    # ==== PHASE 6+13: Auto-detect quest progress from narration ====
    quest_events = process_narration_for_quests(channel_id, narration)
    quest_notification = ""
    for event in quest_events:
        if event["type"] == "objective_complete":
            quest_notification += f"\n\n✅ *Objective complete: {event['message']}*"
        elif event["type"] == "objective_progress":
            quest_notification += f"\n\n📊 *{event['message']}*"
        elif event["type"] == "quest_complete":
            quest = event["quest"]
            rewards = event.get("rewards")
            quest_notification += f"\n\n🎉 **Quest Complete: {quest.name}!**"
            if rewards:
                if rewards.xp > 0:
                    quest_notification += f"\n⭐ +{rewards.xp} XP"
                if rewards.gold > 0:
                    quest_notification += f"\n💰 +{rewards.gold} gp"
        elif event["type"] == "quest_failed":
            quest_notification += f"\n\n❌ *{event['message']}*"
        elif event["type"] == "quest_created":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "quest_unlocked":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "quest_hook":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "rumor_heard":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "objective_added":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "quest_chain":
            quest_notification += f"\n\n{event['message']}"
        elif event["type"] == "quest_offer_detected":
            quest_notification += f"\n\n{event['message']}"
    
    # ==== PHASE 12: Dynamic Environment Detection ====
    env_notification = ""
    try:
        from utils.world_generator import process_narration_for_environment
        env_changes, env_results = process_narration_for_environment(
            channel_id, narration, current_location
        )
        if env_results:
            env_notification = "\n\n" + "\n".join(env_results)
    except Exception as e:
        pass  # If world generator fails, continue without it
    
    # ==== PHASE 14: Intelligent Travel & Exploration Detection ====
    travel_notification = ""
    try:
        travel_events = process_narration_for_travel(channel_id, action, narration)
        
        # Handle travel started
        if travel_events.get("travel_started"):
            intent = travel_events["travel_started"]
            travel_result = start_travel_from_intent(channel_id, intent)
            travel_notification += f"\n\n🚶 **Journey Begun**"
            travel_notification += f"\n→ Destination: {intent.destination}"
            if travel_result.get("distance"):
                travel_notification += f"\n📏 Distance: {travel_result['distance']:.1f} miles"
            if travel_result.get("terrain"):
                travel_notification += f"\n🌲 Terrain: {travel_result['terrain'].title()}"
        
        # Handle arrival
        if travel_events.get("arrival"):
            arrival_loc = travel_events["arrival"]
            complete_travel(channel_id, arrival_loc)
            travel_notification += f"\n\n🏁 **Arrived at {arrival_loc}!**"
            # Update campaign state location
            updated_state['location'] = arrival_loc
        
        # Handle discovered locations
        for discovery in travel_events.get("locations_discovered", []):
            poi_star = "⭐ " if discovery.is_poi else ""
            travel_notification += f"\n\n📍 *New location discovered: {poi_star}**{discovery.name}***"
            if discovery.terrain != "wilderness":
                travel_notification += f" ({discovery.terrain})"
        
        # Handle revealed distances
        for from_loc, to_loc, miles in travel_events.get("distances_revealed", []):
            travel_notification += f"\n\n🗺️ *Distance revealed: {from_loc} → {to_loc}: {miles:.0f} miles*"
    except Exception as e:
        pass  # If travel detection fails, continue without it
    
    # Process loot
    loot_items = updated_state.pop('recent_loot', [])
    voice_tag = extract_voice_tag(narration)
    text = clean_text(narration)

    # Format output
    output = f"**{char_name}:** *{action}*\n\n{text}"
    
    # Add resource consumption notifications
    if resource_summary:
        output += f"\n\n{resource_summary}"
    
    # Add NPC notification
    if npc_notification:
        output += npc_notification
    
    # Add quest notification
    if quest_notification:
        output += quest_notification
    
    # Add environment notification
    if env_notification:
        output += env_notification
    
    # Add travel notification
    if travel_notification:
        output += travel_notification
    
    # Add trap notification
    if trap_notification:
        output += trap_notification
    
    # Add loot notifications
    for item in loot_items:
        add_inventory(user_id, item)
        output += f"\n\n🎒 *{char_name} obtained: {item}*"

    # Check if AI is asking for a skill check - use enhanced detection
    # Get character names for target detection
    player_char_names = []
    for pid in updated_state.get('turn_order', []):
        pchar = load_character(pid)
        if pchar:
            player_char_names.append(pchar.get('name', ''))
    
    # Use enhanced skill check parsing
    skill_check_request = parse_skill_check_request(narration, player_char_names)
    
    if skill_check_request:
        # Store context for later
        skill_check_request.context = action
        
        # Determine who should roll
        if skill_check_request.is_group_check:
            # Everyone rolls
            target_player_ids = updated_state.get('turn_order', [user_id])
        elif skill_check_request.target_players:
            # Specific players named
            target_player_ids = []
            for pid in updated_state.get('turn_order', []):
                pchar = load_character(pid)
                if pchar and pchar.get('name', '') in skill_check_request.target_players:
                    target_player_ids.append(pid)
            if not target_player_ids:
                target_player_ids = [user_id]
        else:
            # Default to the player who took the action
            target_player_ids = [user_id]
        
        # Build mentions
        player_mentions = [f"<@{pid}>" for pid in target_player_ids]
        
        # Add skill check prompt to output
        skill_name = skill_check_request.skill_or_ability.replace('_', ' ').title()
        dc_text = f" (DC {skill_check_request.dc})" if skill_check_request.dc else ""
        
        if skill_check_request.is_group_check:
            output += f"\n\n🎲 **Everyone, roll {skill_name}{dc_text}!**"
        else:
            output += f"\n\n🎲 **Roll {skill_name}{dc_text}!**"
        
        # Update state with pending roll for backward compatibility
        updated_state['pending_roll'] = {
            'player_id': user_id,
            'skill': skill_check_request.skill_or_ability,
            'dc': skill_check_request.dc,
            'action': action
        }
        
        # We'll send the button prompt after the main message
        skill_check_pending = (skill_check_request, target_player_ids, player_mentions)
    else:
        skill_check_pending = None
        # Check old-style pending roll detection (fallback)
        pending = updated_state.get('pending_roll')
        if pending and pending.get('skill'):
            skill_name = pending['skill'].replace('_', ' ').title()
            dc_text = f" (DC {pending['dc']})" if pending.get('dc') else ""
            output += f"\n\n🎲 **Roll {skill_name}{dc_text}!** Use `/roll {pending['skill']}`"

    # Check if AI triggered combat automatically
    # ==== PHASE 11: Enhanced Combat Trigger Detection ====
    combat_started = False
    combat_notification = ""
    
    # First check for structured combat tag or AI narration trigger
    combat_trigger = detect_combat_trigger(narration, player_action=action, is_ai_response=True)
    
    # If no AI trigger but player declared attack intent, use that
    if not combat_trigger and player_attack_trigger:
        combat_trigger = player_attack_trigger
    
    if combat_trigger and combat_trigger.triggered:
        # Check if combat isn't already active
        existing_combat = load_combat(channel_id)
        if not existing_combat or not existing_combat.get('active'):
            if combat_trigger.enemies:
                # Build player list from turn_order or just current player
                player_list = []
                for pid in updated_state.get('turn_order', [str(interaction.user.id)]):
                    pchar = load_character(pid)
                    if pchar:
                        player_list.append((
                            pid,
                            pchar.get('name', f'Player_{pid}')
                        ))
                    else:
                        player_list.append((pid, f'Player_{pid}'))
                
                # Build enemy list - combat_trigger.enemies are already processed
                enemy_list = []
                for enemy in combat_trigger.enemies:
                    enemy_list.append({
                        'name': enemy.get('name', 'Enemy'),
                        'hp': enemy.get('hp', 10),
                        'ac': enemy.get('ac', 12)
                    })
                
                if player_list and enemy_list:
                    # Start combat!
                    combat_state = start_combat(channel_id, player_list, enemy_list)
                    init_state = roll_initiative(channel_id)
                    
                    # Reset all reactions at combat start
                    reset_all_reactions_new_round(channel_id)
                    
                    # Mark campaign as in combat
                    updated_state['in_combat'] = True
                    updated_state['free_form'] = False
                    
                    combat_started = True
                    
                    # Build combat start message
                    enemy_names = ', '.join(e['name'] for e in enemy_list)
                    combat_notification = f"\n\n⚔️ **COMBAT INITIATED!**\n"
                    
                    # Show surprise if applicable
                    if combat_trigger.surprise_round == 'party':
                        combat_notification += "🎯 *The party has surprise!*\n"
                    elif combat_trigger.surprise_round == 'enemies':
                        combat_notification += "💀 *Ambush! The enemies have surprise!*\n"
                    
                    combat_notification += f"\n**Enemies:** {enemy_names}\n\n"
                    combat_notification += "**Initiative Order:**\n"
                    
                    for i, c in enumerate(init_state['turn_order']):
                        marker = "➤ " if i == 0 else "  "
                        hp_str = f"{c['hp']}/{c.get('max_hp', c['hp'])}"
                        combat_notification += f"{marker}**{c['initiative']}** - {c['name']} (HP: {hp_str}, AC: {c['ac']})\n"
                    
                    first = init_state['turn_order'][0]
                    combat_notification += f"\n🎯 **{first['name']}**, you're up!"
                    combat_notification += f"\n*Use `/attack <target>` to attack, `/nextturn` when done.*"
            else:
                # Combat triggered but no enemies identified
                if combat_trigger.error:
                    combat_notification = f"\n\n⚔️ **Combat imminent!** {combat_trigger.error}\n*DM, use `/fight <enemies>` to specify opponents.*"
                else:
                    combat_notification = f"\n\n⚔️ **Combat seems imminent!** DM, use `/fight <enemies>` to start the encounter."
    
    # Add combat notification to output
    if combat_notification:
        output += combat_notification
    
    # Clear any old pending combat from state
    updated_state['pending_combat'] = None

    await interaction.followup.send(output)
    
    # Send skill check button prompt if needed
    if skill_check_pending:
        request, target_ids, mentions = skill_check_pending
        await prompt_skill_check(interaction.channel, channel_id, request, target_ids, mentions)
    
    # Play TTS (narration only, not the roll prompt)
    await play_tts(interaction, text, voice_tag)
    
    save_state(channel_id, updated_state)
    log_message(channel_id, char_name, action)
    log_message(channel_id, "DM", text)
    
    # Track session activity (Phase 15)
    activity_type = "combat" if combat_started else "action"
    record_activity(channel_id, activity_type, user_id)


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


@bot.tree.command(name="context", description="Show what the AI remembers about your campaign")
async def context_cmd(interaction: discord.Interaction):
    """Display the campaign context/memory."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return
    
    context = get_context_summary(state)
    history_count = len(state.get("prompt_history", []))
    
    output = (
        f"# 🧠 Campaign Memory\n\n"
        f"{context}\n\n"
        f"───────────────────────\n"
        f"*Recent history: {history_count}/10 messages*\n"
        f"*Use `/summarize` to save important events to long-term memory*"
    )
    
    await interaction.response.send_message(output)


@bot.tree.command(name="summarize", description="Save current events to campaign memory")
async def summarize_cmd(interaction: discord.Interaction):
    """Generate and save a campaign summary to preserve important events."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running.")
        return
    
    history = state.get("prompt_history", [])
    if len(history) < 2:
        await interaction.response.send_message("Not enough history to summarize yet. Play more first!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Generate new summary
    new_summary = generate_campaign_summary(state)
    update_campaign_summary(state, new_summary)
    
    # Also extract NPCs and quests from recent history
    recent_text = "\n".join([m.get("content", "") for m in history])
    extracted = extract_npcs_and_quests(state, recent_text)
    
    # Add extracted NPCs
    for npc in extracted.get("npcs", []):
        add_or_update_npc(state, npc["name"], npc.get("description", ""), npc.get("status", "alive"))
    
    # Add extracted quests
    for quest in extracted.get("quests", []):
        add_quest(state, quest["name"], quest.get("description", ""), quest.get("status", "active"))
    
    save_state(channel_id, state)
    
    # Show what was saved
    npc_names = [n["name"] for n in extracted.get("npcs", [])]
    quest_names = [q["name"] for q in extracted.get("quests", [])]
    
    output = f"📝 **Campaign memory updated!**\n\n**Summary:**\n{new_summary}"
    if npc_names:
        output += f"\n\n**NPCs remembered:** {', '.join(npc_names)}"
    if quest_names:
        output += f"\n\n**Quests tracked:** {', '.join(quest_names)}"
    
    await interaction.followup.send(output)


@bot.tree.command(name="remember", description="Add a note to campaign memory")
@app_commands.describe(
    note="Important event or detail to remember",
    npc="Add an NPC (format: Name - Description)",
    quest="Add a quest (format: Quest Name - Description)"
)
async def remember_cmd(
    interaction: discord.Interaction,
    note: Optional[str] = None,
    npc: Optional[str] = None,
    quest: Optional[str] = None
):
    """Manually add something to campaign memory."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running.")
        return
    
    messages = []
    
    if note:
        add_key_event(state, note)
        messages.append(f"📌 Added event: *{note}*")
    
    if npc:
        parts = npc.split(" - ", 1)
        name = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        add_or_update_npc(state, name, desc)
        messages.append(f"👤 Added NPC: **{name}**")
    
    if quest:
        parts = quest.split(" - ", 1)
        name = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        add_quest(state, name, desc)
        messages.append(f"📜 Added quest: **{name}**")
    
    if messages:
        save_state(channel_id, state)
        await interaction.response.send_message("\n".join(messages))
    else:
        await interaction.response.send_message(
            "Add something to remember:\n"
            "• `note:` An important event\n"
            "• `npc:` Name - Description\n"
            "• `quest:` Quest Name - Description",
            ephemeral=True
        )


# =============================================================================
# NPC & FACTION COMMANDS
# =============================================================================

NPC_ROLES = ["generic", "quest_giver", "merchant", "innkeeper", "guard", "noble", "villain", "ally", "informant"]
SHOP_TYPES = ["general", "weapons", "armor", "potions", "magic"]

@bot.tree.command(name="npc", description="View or manage NPCs in the campaign")
@app_commands.describe(
    name="NPC name to view or create",
    description="Description for new NPC",
    role="NPC's role in the world",
    location="Where the NPC is located"
)
@app_commands.choices(role=[app_commands.Choice(name=r.replace('_', ' ').title(), value=r) for r in NPC_ROLES])
async def npc_cmd(
    interaction: discord.Interaction,
    name: str = "",
    description: str = "",
    role: str = "",
    location: str = ""
):
    """View NPC list, details, or create/update an NPC."""
    channel_id = str(interaction.channel.id)
    
    if not name:
        # List all NPCs
        npcs = list_all_npcs(channel_id)
        if not npcs:
            await interaction.response.send_message(
                "📋 No NPCs registered yet.\n"
                "NPCs are auto-detected from AI narration, or use `/npc name:\"NPC Name\" description:\"...\"` to add manually.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Known NPCs",
            description=f"**{len(npcs)}** NPCs in this campaign",
            color=discord.Color.blue()
        )
        
        for npc in npcs[:25]:  # Discord limit
            disp_names = {-2: "⚔️", -1: "😠", 0: "😐", 1: "😊", 2: "💚"}
            disp_icon = disp_names.get(npc.disposition, "😐")
            role_text = npc.role.replace('_', ' ').title() if npc.role else "Unknown"
            
            value = f"{npc.race.title()} {role_text}"
            if npc.location:
                value += f"\n📍 {npc.location}"
            if npc.shop:
                value += f"\n🏪 {npc.shop.shop_name}"
            
            embed.add_field(
                name=f"{disp_icon} {npc.name}",
                value=value,
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    else:
        # View or create specific NPC
        npc = get_npc(channel_id, name)
        
        if npc and not description:
            # View existing NPC
            embed = discord.Embed(
                title=f"👤 {npc.name}",
                description=npc.description or "*No description*",
                color=discord.Color.green() if npc.disposition > 0 else 
                      discord.Color.red() if npc.disposition < 0 else 
                      discord.Color.light_grey()
            )
            
            disp_names = {-2: "Hostile", -1: "Unfriendly", 0: "Neutral", 1: "Friendly", 2: "Allied"}
            embed.add_field(name="Race", value=npc.race.title(), inline=True)
            embed.add_field(name="Role", value=npc.role.replace('_', ' ').title(), inline=True)
            embed.add_field(name="Status", value=npc.status.title(), inline=True)
            embed.add_field(name="Disposition", value=disp_names.get(npc.disposition, "Neutral"), inline=True)
            embed.add_field(name="Mood", value=npc.current_mood.title(), inline=True)
            
            if npc.location:
                embed.add_field(name="Location", value=npc.location, inline=True)
            
            if npc.memory.knows_names:
                embed.add_field(name="Knows Players", value=", ".join(npc.memory.knows_names), inline=False)
            
            if npc.memory.knows_facts:
                embed.add_field(name="Knows Facts", value="\n".join(f"• {f}" for f in npc.memory.knows_facts[-5:]), inline=False)
            
            if npc.factions:
                faction_text = "\n".join(f"• {f}: {get_standing_title(s)}" for f, s in npc.factions.items())
                embed.add_field(name="Faction Affiliations", value=faction_text, inline=False)
            
            if npc.dialogue_state.offered_quests:
                embed.add_field(name="Offered Quests", value=", ".join(npc.dialogue_state.offered_quests), inline=False)
            
            if npc.shop:
                embed.add_field(name="Shop", value=f"🏪 {npc.shop.shop_name} ({npc.shop.shop_type.title()})", inline=False)
            
            embed.set_footer(text=f"Interactions: {npc.memory.interaction_count} | Voice: {npc.voice_archetype or 'Default'}")
            
            await interaction.response.send_message(embed=embed)
        else:
            # Create or update NPC
            state = load_state(channel_id)
            current_location = location or state.get("location", "")
            
            npc = create_npc(
                channel_id,
                name=name,
                description=description,
                role=role or "generic",
                location=current_location
            )
            
            # Also add to legacy state for backwards compatibility
            add_or_update_npc(state, name, description)
            save_state(channel_id, state)
            
            await interaction.response.send_message(
                f"👤 **{npc.name}** registered!\n"
                f"Role: {npc.role.replace('_', ' ').title()} | Race: {npc.race.title()}\n"
                f"Voice: {npc.voice_archetype or 'Default'}"
            )


@bot.tree.command(name="npcdisposition", description="Change an NPC's disposition toward the party")
@app_commands.describe(
    name="NPC name",
    change="Amount to change disposition (-2 to +2)"
)
async def npc_disposition_cmd(
    interaction: discord.Interaction,
    name: str,
    change: int
):
    """Modify an NPC's disposition toward the party."""
    channel_id = str(interaction.channel.id)
    
    npc = update_npc_disposition(channel_id, name, change)
    if not npc:
        await interaction.response.send_message(f"❌ NPC **{name}** not found.", ephemeral=True)
        return
    
    disp_names = {-2: "Hostile ⚔️", -1: "Unfriendly 😠", 0: "Neutral 😐", 1: "Friendly 😊", 2: "Allied 💚"}
    direction = "improved" if change > 0 else "worsened"
    
    await interaction.response.send_message(
        f"💭 **{npc.name}**'s disposition has {direction}!\n"
        f"Now: **{disp_names.get(npc.disposition, 'Neutral 😐')}**"
    )


@bot.tree.command(name="faction", description="View or manage factions in the campaign")
@app_commands.describe(
    name="Faction name to view or create",
    description="Description for new faction",
    leader="Faction leader name",
    headquarters="Faction headquarters location"
)
async def faction_cmd(
    interaction: discord.Interaction,
    name: str = "",
    description: str = "",
    leader: str = "",
    headquarters: str = ""
):
    """View faction list, details, or create a faction."""
    channel_id = str(interaction.channel.id)
    
    if not name:
        # List all factions
        factions = list_all_factions(channel_id)
        if not factions:
            await interaction.response.send_message(
                "⚔️ No factions registered yet.\n"
                "Use `/faction name:\"Faction Name\" description:\"...\"` to add one.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚔️ Factions",
            description=f"**{len(factions)}** factions in this campaign",
            color=discord.Color.purple()
        )
        
        for faction in factions:
            standing_icon = "💚" if faction.party_standing >= 50 else "😊" if faction.party_standing >= 0 else "😠" if faction.party_standing > -50 else "⚔️"
            
            value = f"Standing: {faction.standing_title} ({faction.party_standing:+d})"
            if faction.leader:
                value += f"\n👑 {faction.leader}"
            if faction.headquarters:
                value += f"\n🏰 {faction.headquarters}"
            
            embed.add_field(
                name=f"{standing_icon} {faction.name}",
                value=value,
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    else:
        # View or create specific faction
        faction = get_faction(channel_id, name)
        
        if faction and not description:
            # View existing faction
            embed = discord.Embed(
                title=f"⚔️ {faction.name}",
                description=faction.description or "*No description*",
                color=discord.Color.green() if faction.party_standing >= 50 else
                      discord.Color.gold() if faction.party_standing >= 0 else
                      discord.Color.red()
            )
            
            embed.add_field(name="Standing", value=f"{faction.standing_title} ({faction.party_standing:+d})", inline=True)
            embed.add_field(name="Alignment", value=faction.alignment.title(), inline=True)
            
            if faction.leader:
                embed.add_field(name="Leader", value=faction.leader, inline=True)
            if faction.headquarters:
                embed.add_field(name="Headquarters", value=faction.headquarters, inline=True)
            
            if faction.allies:
                embed.add_field(name="Allies", value=", ".join(faction.allies), inline=False)
            if faction.enemies:
                embed.add_field(name="Enemies", value=", ".join(faction.enemies), inline=False)
            
            await interaction.response.send_message(embed=embed)
        else:
            # Create faction
            faction = create_faction(
                channel_id,
                name=name,
                description=description,
                leader=leader,
                headquarters=headquarters
            )
            
            await interaction.response.send_message(
                f"⚔️ **{faction.name}** faction created!\n"
                f"Starting standing: {faction.standing_title}"
            )


@bot.tree.command(name="reputation", description="Modify party reputation with a faction")
@app_commands.describe(
    faction="Faction name",
    change="Amount to change standing (-100 to +100)",
    reason="Reason for the change (optional)"
)
async def reputation_cmd(
    interaction: discord.Interaction,
    faction: str,
    change: int,
    reason: str = ""
):
    """Modify the party's standing with a faction."""
    channel_id = str(interaction.channel.id)
    
    result = modify_faction_standing(channel_id, faction, change, reason)
    if not result:
        await interaction.response.send_message(f"❌ Faction **{faction}** not found.", ephemeral=True)
        return
    
    updated_faction, message = result
    
    color = discord.Color.green() if change > 0 else discord.Color.red()
    embed = discord.Embed(
        title=f"📊 Reputation Change: {updated_faction.name}",
        description=message,
        color=color
    )
    embed.add_field(name="Current Standing", value=f"{updated_faction.standing_title} ({updated_faction.party_standing:+d})")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="shop", description="View a merchant's shop or create one")
@app_commands.describe(
    merchant="Merchant NPC name",
    shop_name="Name for the shop",
    shop_type="Type of shop inventory"
)
@app_commands.choices(shop_type=[app_commands.Choice(name=t.title(), value=t) for t in SHOP_TYPES])
async def shop_cmd(
    interaction: discord.Interaction,
    merchant: str,
    shop_name: str = "",
    shop_type: str = ""
):
    """View or create a merchant's shop."""
    channel_id = str(interaction.channel.id)
    
    npc = get_npc(channel_id, merchant)
    
    if npc and npc.shop and not shop_type:
        # View existing shop
        inventory_text = format_shop_inventory(npc)
        
        embed = discord.Embed(
            title=f"🏪 {npc.shop.shop_name}",
            description=f"Proprietor: **{npc.name}**",
            color=discord.Color.gold()
        )
        
        # Split inventory into chunks for embed
        items_text = []
        for item in npc.shop.items:
            if item['quantity'] > 0:
                items_text.append(f"• **{item['name']}** - {item['price']} gp (x{item['quantity']})")
        
        if items_text:
            embed.add_field(name="📦 Inventory", value="\n".join(items_text[:15]), inline=False)
            if len(items_text) > 15:
                embed.add_field(name="", value="\n".join(items_text[15:30]), inline=False)
        else:
            embed.add_field(name="📦 Inventory", value="*Shop is currently out of stock*", inline=False)
        
        embed.add_field(name="💰 Shop Gold", value=f"{npc.shop.gold_reserve} gp", inline=True)
        embed.add_field(name="📊 Buy Rate", value=f"{int(npc.shop.buy_rate * 100)}%", inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        # Create or update shop
        if not shop_type:
            shop_type = "general"
        
        npc = create_merchant_shop(
            channel_id,
            merchant,
            shop_name=shop_name or f"{merchant}'s Shop",
            shop_type=shop_type
        )
        
        if not npc:
            await interaction.response.send_message(f"❌ Could not create shop for **{merchant}**.", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"🏪 **{npc.shop.shop_name}** is now open!\n"
            f"Merchant: {npc.name}\n"
            f"Type: {shop_type.title()} Shop\n"
            f"Use `/shop merchant:{merchant}` to view inventory."
        )


@bot.tree.command(name="buy", description="Buy an item from a shop")
@app_commands.describe(
    merchant="Merchant NPC name",
    item="Item name to buy",
    quantity="Number to buy (default: 1)"
)
async def buy_cmd(
    interaction: discord.Interaction,
    merchant: str,
    item: str,
    quantity: int = 1
):
    """Buy an item from a merchant."""
    channel_id = str(interaction.channel.id)
    user_id = str(interaction.user.id)
    
    result = buy_from_shop(channel_id, merchant, item, quantity)
    if not result:
        await interaction.response.send_message(
            f"❌ Could not purchase **{item}**. Check that:\n"
            f"• The merchant **{merchant}** exists and has a shop\n"
            f"• The item is in stock\n"
            f"• You requested a valid quantity",
            ephemeral=True
        )
        return
    
    item_data, total_cost = result
    
    # Add to player inventory
    char = load_character(user_id)
    if char:
        for _ in range(quantity):
            add_inventory(user_id, item_data['name'])
        save_character(user_id, char)
    
    await interaction.response.send_message(
        f"💰 Purchased **{quantity}x {item_data['name']}** for **{total_cost} gp**!\n"
        f"*{item_data.get('description', '')}*"
    )


@bot.tree.command(name="sell", description="Sell an item to a shop")
@app_commands.describe(
    merchant="Merchant NPC name",
    item="Item name to sell",
    base_price="Base price of the item in gold",
    quantity="Number to sell (default: 1)"
)
async def sell_cmd(
    interaction: discord.Interaction,
    merchant: str,
    item: str,
    base_price: int,
    quantity: int = 1
):
    """Sell an item to a merchant."""
    channel_id = str(interaction.channel.id)
    user_id = str(interaction.user.id)
    
    # Check player has the item
    char = load_character(user_id)
    if char:
        inventory = char.get("inventory", [])
        item_count = sum(1 for i in inventory if i.lower() == item.lower())
        if item_count < quantity:
            await interaction.response.send_message(
                f"❌ You only have **{item_count}x {item}** in your inventory.",
                ephemeral=True
            )
            return
    
    gold_received = sell_to_shop(channel_id, merchant, item, base_price, quantity)
    if gold_received is None:
        await interaction.response.send_message(
            f"❌ Could not sell to **{merchant}**. The shop may not have enough gold.",
            ephemeral=True
        )
        return
    
    # Remove from player inventory
    if char:
        for _ in range(quantity):
            remove_inventory(user_id, item)
    
    await interaction.response.send_message(
        f"💰 Sold **{quantity}x {item}** for **{gold_received} gp**!"
    )


# =============================================================================
# QUEST COMMANDS
# =============================================================================

QUEST_TYPES = ["main", "side", "faction", "personal", "bounty", "fetch", "escort", "explore", "mystery"]
QUEST_DIFFICULTIES = ["trivial", "easy", "medium", "hard", "deadly", "legendary"]
QUEST_STATUSES = ["available", "active", "completed", "failed", "abandoned"]

@bot.tree.command(name="quests", description="View your quest log")
@app_commands.describe(
    show_completed="Include completed quests in the list"
)
async def quests_cmd(
    interaction: discord.Interaction,
    show_completed: bool = False
):
    """View active, available, and optionally completed quests."""
    channel_id = str(interaction.channel.id)
    
    quest_log = format_quest_log(channel_id, include_completed=show_completed)
    
    # Split into chunks if too long
    if len(quest_log) > 1900:
        # Send as embed for better formatting
        embed = discord.Embed(
            title="📜 Quest Log",
            color=discord.Color.gold()
        )
        
        active = get_active_quests(channel_id)
        available = get_available_quests(channel_id)
        
        if active:
            active_text = ""
            for q in active[:10]:  # Limit to 10
                progress = f"({q.get_progress()[0]}/{q.get_progress()[1]})"
                active_text += f"• **{q.name}** {progress}\n"
            embed.add_field(name="⚔️ Active Quests", value=active_text or "None", inline=False)
        
        if available:
            avail_text = "\n".join([f"• {q.name}" for q in available[:5]])
            embed.add_field(name="📋 Available Quests", value=avail_text, inline=False)
        
        if show_completed:
            completed = get_completed_quests(channel_id)
            if completed:
                comp_text = "\n".join([f"✅ {q.name}" for q in completed[-5:]])
                embed.add_field(name="✅ Completed", value=comp_text, inline=False)
        
        if not active and not available:
            embed.description = "*No active quests. Use `/quest create` to add one!*"
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(quest_log)


@bot.tree.command(name="quest", description="View details of a specific quest or create a new one")
@app_commands.describe(
    name="Quest name to view or create",
    description="Description for new quest",
    quest_type="Type of quest",
    difficulty="Quest difficulty",
    giver="NPC who gave the quest",
    objectives="Comma-separated list of objectives"
)
@app_commands.choices(
    quest_type=[app_commands.Choice(name=t.replace('_', ' ').title(), value=t) for t in QUEST_TYPES],
    difficulty=[app_commands.Choice(name=d.title(), value=d) for d in QUEST_DIFFICULTIES]
)
async def quest_cmd(
    interaction: discord.Interaction,
    name: str = "",
    description: str = "",
    quest_type: str = "side",
    difficulty: str = "medium",
    giver: str = "",
    objectives: str = ""
):
    """View quest details or create a new quest."""
    channel_id = str(interaction.channel.id)
    
    if not name:
        # Show help or list
        await interaction.response.send_message(
            "**Quest Commands:**\n"
            "• `/quests` - View all quests\n"
            "• `/quest <name>` - View specific quest\n"
            "• `/quest <name> description:<desc>` - Create new quest\n"
            "• `/questcomplete <name>` - Complete a quest\n"
            "• `/questabandon <name>` - Abandon a quest\n"
            "• `/questobjective <quest> <objective>` - Add objective\n"
            "• `/questnote <quest> <note>` - Add note to quest",
            ephemeral=True
        )
        return
    
    # Check if quest exists
    existing = get_quest_by_name(channel_id, name)
    
    if existing and not description:
        # View existing quest
        summary = format_quest_summary(existing, show_rewards=True)
        
        embed = discord.Embed(
            title=f"📜 {existing.name}",
            description=existing.description,
            color=discord.Color.gold() if existing.status == "active" else discord.Color.green()
        )
        
        # Status
        status_emoji = {"active": "⚔️", "completed": "✅", "failed": "❌", "available": "📋", "abandoned": "🚫"}
        embed.add_field(
            name="Status",
            value=f"{status_emoji.get(existing.status, '📜')} {existing.status.title()}",
            inline=True
        )
        embed.add_field(name="Type", value=existing.quest_type.title(), inline=True)
        embed.add_field(name="Difficulty", value=existing.difficulty.title(), inline=True)
        
        # Objectives
        objs = existing.get_objectives()
        if objs:
            obj_text = ""
            for obj in objs:
                if obj.is_hidden:
                    continue
                check = "☑️" if obj.is_complete() else "☐"
                opt = " *(optional)*" if obj.is_optional else ""
                if obj.required > 1:
                    obj_text += f"{check} {obj.description} ({obj.progress}/{obj.required}){opt}\n"
                else:
                    obj_text += f"{check} {obj.description}{opt}\n"
            if obj_text:
                embed.add_field(name="Objectives", value=obj_text, inline=False)
        
        # Rewards
        rewards = existing.get_rewards()
        reward_parts = []
        if rewards.xp > 0:
            reward_parts.append(f"⭐ {rewards.xp} XP")
        if rewards.gold > 0:
            reward_parts.append(f"💰 {rewards.gold} gp")
        if rewards.items:
            reward_parts.append(f"🎁 {', '.join(rewards.items)}")
        if reward_parts:
            embed.add_field(name="Rewards", value="\n".join(reward_parts), inline=False)
        
        # Quest giver
        if existing.giver_npc:
            embed.set_footer(text=f"Quest Giver: {existing.giver_npc}")
        
        # Notes
        if existing.notes:
            embed.add_field(name="Notes", value="\n".join(existing.notes[-3:]), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    elif description:
        # Create new quest
        obj_list = [o.strip() for o in objectives.split(",")] if objectives else None
        
        new_quest = create_quest(
            channel_id=channel_id,
            name=name,
            description=description,
            quest_type=quest_type,
            difficulty=difficulty,
            giver_npc=giver,
            objectives=obj_list
        )
        
        embed = discord.Embed(
            title="📜 New Quest Created!",
            description=f"**{new_quest.name}**\n{new_quest.description}",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=new_quest.quest_type.title(), inline=True)
        embed.add_field(name="Difficulty", value=new_quest.difficulty.title(), inline=True)
        
        rewards = new_quest.get_rewards()
        embed.add_field(name="Base Rewards", value=f"⭐ {rewards.xp} XP, 💰 {rewards.gold} gp", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    else:
        await interaction.response.send_message(
            f"❌ Quest **{name}** not found. Add a description to create it.",
            ephemeral=True
        )


@bot.tree.command(name="questcomplete", description="Mark a quest as completed")
@app_commands.describe(
    quest_name="Name of the quest to complete"
)
async def quest_complete_cmd(
    interaction: discord.Interaction,
    quest_name: str
):
    """Complete a quest and award rewards."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    if quest.status == "completed":
        await interaction.response.send_message(
            f"Quest **{quest.name}** is already completed!",
            ephemeral=True
        )
        return
    
    success, rewards, message = complete_quest(channel_id, quest.id)
    
    if success:
        embed = discord.Embed(
            title="🎉 Quest Complete!",
            description=f"**{quest.name}**",
            color=discord.Color.green()
        )
        
        if rewards:
            reward_text = []
            if rewards.xp > 0:
                reward_text.append(f"⭐ **{rewards.xp}** Experience Points")
            if rewards.gold > 0:
                reward_text.append(f"💰 **{rewards.gold}** Gold Pieces")
            if rewards.items:
                reward_text.append(f"🎁 **Items:** {', '.join(rewards.items)}")
            if rewards.reputation:
                for faction, change in rewards.reputation.items():
                    sign = "+" if change > 0 else ""
                    reward_text.append(f"🏛️ **{faction}:** {sign}{change} reputation")
            if rewards.special:
                reward_text.append(f"✨ {rewards.special}")
            
            if reward_text:
                embed.add_field(name="Rewards", value="\n".join(reward_text), inline=False)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


@bot.tree.command(name="questabandon", description="Abandon a quest")
@app_commands.describe(
    quest_name="Name of the quest to abandon"
)
async def quest_abandon_cmd(
    interaction: discord.Interaction,
    quest_name: str
):
    """Abandon a quest (player choice to give up)."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    if quest.status != "active":
        await interaction.response.send_message(
            f"Quest **{quest.name}** is not active (status: {quest.status}).",
            ephemeral=True
        )
        return
    
    if abandon_quest(channel_id, quest.id):
        await interaction.response.send_message(
            f"🚫 **Quest Abandoned:** {quest.name}\n*You can always pick it up again later if available.*"
        )
    else:
        await interaction.response.send_message("❌ Failed to abandon quest.", ephemeral=True)


@bot.tree.command(name="questobjective", description="Add an objective to a quest")
@app_commands.describe(
    quest_name="Name of the quest",
    objective="Description of the objective",
    required="Number required (for 'kill 5 goblins' style objectives)",
    is_optional="Whether this objective is optional"
)
async def quest_objective_cmd(
    interaction: discord.Interaction,
    quest_name: str,
    objective: str,
    required: int = 1,
    is_optional: bool = False
):
    """Add a new objective to an existing quest."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    new_obj = add_objective(
        channel_id=channel_id,
        quest_id=quest.id,
        description=objective,
        required=required,
        is_optional=is_optional
    )
    
    if new_obj:
        opt = " *(optional)*" if is_optional else ""
        req = f" (0/{required})" if required > 1 else ""
        await interaction.response.send_message(
            f"✅ Added objective to **{quest.name}**:\n☐ {objective}{req}{opt}"
        )
    else:
        await interaction.response.send_message("❌ Failed to add objective.", ephemeral=True)


@bot.tree.command(name="questprogress", description="Update progress on a quest objective")
@app_commands.describe(
    quest_name="Name of the quest",
    objective_number="Objective number (1, 2, 3...)",
    progress="Amount of progress to add"
)
async def quest_progress_cmd(
    interaction: discord.Interaction,
    quest_name: str,
    objective_number: int,
    progress: int = 1
):
    """Add progress to a quest objective."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    obj_id = f"obj_{objective_number}"
    completed, message = update_objective_progress(channel_id, quest.id, obj_id, progress)
    
    if message:
        if completed:
            # Check if quest is fully complete
            updated = get_quest(channel_id, quest.id)
            if updated and updated.is_complete():
                success, rewards, comp_msg = complete_quest(channel_id, quest.id)
                if success:
                    msg = f"{message}\n\n🎉 **Quest Complete: {quest.name}!**"
                    if rewards and rewards.xp > 0:
                        msg += f"\nRewards: ⭐ {rewards.xp} XP, 💰 {rewards.gold} gp"
                    await interaction.response.send_message(msg)
                    return
            
            await interaction.response.send_message(message)
        else:
            objectives = quest.get_objectives()
            for obj in objectives:
                if obj.id == obj_id:
                    await interaction.response.send_message(
                        f"📊 Progress updated: {obj.description} ({obj.progress}/{obj.required})"
                    )
                    return
            await interaction.response.send_message("Progress updated.", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"❌ Objective {objective_number} not found in quest **{quest.name}**.",
            ephemeral=True
        )


@bot.tree.command(name="questnote", description="Add a note to a quest")
@app_commands.describe(
    quest_name="Name of the quest",
    note="Note to add"
)
async def quest_note_cmd(
    interaction: discord.Interaction,
    quest_name: str,
    note: str
):
    """Add a player note to a quest."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    if add_note_to_quest(channel_id, quest.id, note):
        await interaction.response.send_message(
            f"📝 Note added to **{quest.name}**:\n*{note}*"
        )
    else:
        await interaction.response.send_message("❌ Failed to add note.", ephemeral=True)


@bot.tree.command(name="questtemplate", description="Create a quest from a template")
@app_commands.describe(
    template="Quest template to use",
    name="Name for the quest",
    description="Quest description",
    giver="NPC who gave the quest"
)
@app_commands.choices(template=[
    app_commands.Choice(name="Bounty - Hunt a target", value="bounty"),
    app_commands.Choice(name="Fetch - Retrieve an item", value="fetch"),
    app_commands.Choice(name="Rescue - Save someone", value="rescue"),
    app_commands.Choice(name="Investigate - Solve a mystery", value="investigate"),
    app_commands.Choice(name="Clear Dungeon - Clear all threats", value="clear_dungeon"),
    app_commands.Choice(name="Escort - Protect during journey", value="escort")
])
async def quest_template_cmd(
    interaction: discord.Interaction,
    template: str,
    name: str,
    description: str,
    giver: str = ""
):
    """Create a quest from a pre-defined template."""
    channel_id = str(interaction.channel.id)
    
    quest = create_quest_from_template(
        channel_id=channel_id,
        template_name=template,
        quest_name=name,
        description=description,
        giver_npc=giver
    )
    
    if quest:
        embed = discord.Embed(
            title=f"📜 Quest Created: {quest.name}",
            description=quest.description,
            color=discord.Color.gold()
        )
        
        objectives = quest.get_objectives()
        if objectives:
            obj_text = "\n".join([f"☐ {obj.description}" for obj in objectives])
            embed.add_field(name="Objectives", value=obj_text, inline=False)
        
        rewards = quest.get_rewards()
        embed.add_field(
            name="Rewards",
            value=f"⭐ {rewards.xp} XP, 💰 {rewards.gold} gp",
            inline=True
        )
        embed.add_field(name="Type", value=quest.quest_type.title(), inline=True)
        embed.add_field(name="Difficulty", value=quest.difficulty.title(), inline=True)
        
        if giver:
            embed.set_footer(text=f"Quest Giver: {giver}")
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            f"❌ Template **{template}** not found.",
            ephemeral=True
        )


# =============================================================================
# PHASE 13: RUMOR & QUEST CHAIN COMMANDS
# =============================================================================

@bot.tree.command(name="rumors", description="View all rumors the party has heard")
async def rumors_cmd(interaction: discord.Interaction):
    """Display all rumors the party has heard."""
    channel_id = str(interaction.channel.id)
    
    all_rumors = load_rumors(channel_id)
    
    if not all_rumors:
        await interaction.response.send_message(
            "👂 *No rumors heard yet. Talk to NPCs to learn about potential adventures!*",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="👂 Rumors & Gossip",
        description="*Whispers heard on your adventures...*",
        color=discord.Color.purple()
    )
    
    uninvestigated = [r for r in all_rumors if not r.get("investigated", False)]
    investigated = [r for r in all_rumors if r.get("investigated", False)]
    
    if uninvestigated:
        rumor_text = ""
        for r in uninvestigated[-10:]:  # Last 10
            source = f" *(from {r['source']})*" if r.get("source") else ""
            rumor_text += f"• \"{r['text']}\"{source}\n"
        embed.add_field(name="🔍 Uninvestigated", value=rumor_text, inline=False)
    
    if investigated:
        invest_text = ""
        for r in investigated[-5:]:  # Last 5
            quest_note = f" → Led to quest" if r.get("led_to_quest") else ""
            invest_text += f"• ~~{r['text']}~~{quest_note}\n"
        embed.add_field(name="✅ Investigated", value=invest_text, inline=False)
    
    embed.set_footer(text="Use /investigaterumor <id> to follow up on a rumor")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="investigaterumor", description="Investigate a rumor and create a quest from it")
@app_commands.describe(
    rumor_number="Number of the rumor to investigate (1, 2, 3...)",
    quest_name="Name for the new quest",
    description="Quest description"
)
async def investigate_rumor_cmd(
    interaction: discord.Interaction,
    rumor_number: int,
    quest_name: str,
    description: str = ""
):
    """Convert an investigated rumor into an active quest."""
    channel_id = str(interaction.channel.id)
    
    rumors = get_uninvestigated_rumors(channel_id)
    
    if not rumors:
        await interaction.response.send_message(
            "❌ No uninvestigated rumors available.",
            ephemeral=True
        )
        return
    
    if rumor_number < 1 or rumor_number > len(rumors):
        await interaction.response.send_message(
            f"❌ Invalid rumor number. You have {len(rumors)} uninvestigated rumors.",
            ephemeral=True
        )
        return
    
    rumor = rumors[rumor_number - 1]
    desc = description if description else f"Investigate: {rumor['text']}"
    
    quest = convert_rumor_to_quest(
        channel_id=channel_id,
        rumor_id=rumor["id"],
        quest_name=quest_name,
        description=desc
    )
    
    if quest:
        embed = discord.Embed(
            title="🔍 Rumor Investigated!",
            description=f"**{quest.name}**\n{quest.description}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Original Rumor",
            value=f"*\"{rumor['text']}\"*",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(
            "❌ Failed to create quest from rumor.",
            ephemeral=True
        )


@bot.tree.command(name="questchain", description="Link two quests in sequence")
@app_commands.describe(
    parent_quest="Name of the first quest (prerequisite)",
    child_quest="Name of the quest that unlocks after parent completes"
)
async def quest_chain_cmd(
    interaction: discord.Interaction,
    parent_quest: str,
    child_quest: str
):
    """Link two quests so child unlocks when parent completes."""
    channel_id = str(interaction.channel.id)
    
    parent = get_quest_by_name(channel_id, parent_quest)
    child = get_quest_by_name(channel_id, child_quest)
    
    if not parent:
        await interaction.response.send_message(
            f"❌ Quest **{parent_quest}** not found.",
            ephemeral=True
        )
        return
    
    if not child:
        await interaction.response.send_message(
            f"❌ Quest **{child_quest}** not found.",
            ephemeral=True
        )
        return
    
    if link_quests(channel_id, parent.id, child.id):
        await interaction.response.send_message(
            f"🔗 **Quest Chain Created!**\n"
            f"When **{parent.name}** completes, **{child.name}** will unlock automatically."
        )
    else:
        await interaction.response.send_message(
            "❌ Failed to link quests.",
            ephemeral=True
        )


@bot.tree.command(name="acceptquest", description="Accept an available quest")
@app_commands.describe(
    quest_name="Name of the quest to accept"
)
async def accept_quest_cmd(
    interaction: discord.Interaction,
    quest_name: str
):
    """Accept an available quest to make it active."""
    channel_id = str(interaction.channel.id)
    
    quest = get_quest_by_name(channel_id, quest_name)
    if not quest:
        await interaction.response.send_message(
            f"❌ Quest **{quest_name}** not found.",
            ephemeral=True
        )
        return
    
    if quest.status != "available":
        await interaction.response.send_message(
            f"Quest **{quest.name}** is not available (status: {quest.status}).",
            ephemeral=True
        )
        return
    
    if accept_quest(channel_id, quest.id):
        embed = discord.Embed(
            title="⚔️ Quest Accepted!",
            description=f"**{quest.name}**\n{quest.description}",
            color=discord.Color.green()
        )
        
        objectives = quest.get_objectives()
        if objectives:
            obj_text = "\n".join([f"☐ {obj.description}" for obj in objectives if not obj.is_hidden])
            if obj_text:
                embed.add_field(name="Objectives", value=obj_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Failed to accept quest.", ephemeral=True)


# =============================================================================
# ENVIRONMENT COMMANDS
# =============================================================================

@bot.tree.command(name="environment", description="View current environmental conditions")
async def environment_cmd(interaction: discord.Interaction):
    """Display the current environment status."""
    channel_id = str(interaction.channel.id)
    
    summary = format_environment_summary(channel_id)
    
    embed = discord.Embed(
        title="🌍 Environment Status",
        description=summary,
        color=discord.Color.dark_teal()
    )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="trap", description="Create, view, or manage traps")
@app_commands.describe(
    action="Action to perform",
    name="Name of the trap",
    template="Use a pre-defined trap template",
    dc="Detection DC",
    save_dc="Save DC when triggered",
    damage="Damage dice (e.g., 2d6)",
    damage_type="Type of damage",
    x="X position on map",
    y="Y position on map"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Create", value="create"),
    app_commands.Choice(name="List", value="list"),
    app_commands.Choice(name="View", value="view"),
    app_commands.Choice(name="Remove", value="remove"),
    app_commands.Choice(name="Trigger", value="trigger"),
])
@app_commands.choices(template=[
    app_commands.Choice(name="Pit Trap", value="pit_trap"),
    app_commands.Choice(name="Poison Dart", value="poison_dart"),
    app_commands.Choice(name="Flame Jet", value="flame_jet"),
    app_commands.Choice(name="Spike Trap", value="spike_trap"),
    app_commands.Choice(name="Poison Gas", value="poison_gas"),
    app_commands.Choice(name="Net Trap", value="net_trap"),
    app_commands.Choice(name="Swinging Blade", value="blade_trap"),
    app_commands.Choice(name="Lightning Rune", value="lightning_rune"),
    app_commands.Choice(name="Alarm", value="alarm"),
    app_commands.Choice(name="Collapsing Ceiling", value="collapsing_ceiling"),
])
async def trap_cmd(
    interaction: discord.Interaction,
    action: str,
    name: str = "",
    template: str = "",
    dc: int = 15,
    save_dc: int = 13,
    damage: str = "2d6",
    damage_type: str = "piercing",
    x: int = -1,
    y: int = -1
):
    """Manage traps in the environment."""
    channel_id = str(interaction.channel.id)
    
    if action == "list":
        traps = list_traps(channel_id, include_triggered=True)
        if not traps:
            await interaction.response.send_message("No traps in this area.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚙️ Traps",
            color=discord.Color.orange()
        )
        
        for trap in traps:
            status = "❓ Hidden"
            if trap.disarmed:
                status = "✅ Disarmed"
            elif trap.triggered:
                status = "💥 Triggered"
            elif trap.detected:
                status = "👁️ Detected"
            
            pos = f" ({trap.x}, {trap.y})" if trap.x >= 0 else ""
            embed.add_field(
                name=f"{status} {trap.name}{pos}",
                value=f"{trap.trap_type} | DC {trap.dc} | {trap.damage_dice} {trap.damage_type}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    elif action == "create":
        if not name and not template:
            await interaction.response.send_message(
                "Provide a name or choose a template.",
                ephemeral=True
            )
            return
        
        if template:
            trap = create_trap_from_template(channel_id, template, x, y)
            if trap:
                await interaction.response.send_message(
                    f"⚙️ Created trap from template: **{trap.name}**\n"
                    f"DC {trap.dc} | Save {trap.save_type} DC {trap.save_dc} | {trap.damage_dice} {trap.damage_type}"
                )
            else:
                await interaction.response.send_message(f"Unknown template: {template}", ephemeral=True)
        else:
            trap = create_trap(
                channel_id=channel_id,
                name=name,
                dc=dc,
                save_dc=save_dc,
                damage_dice=damage,
                damage_type=damage_type,
                x=x,
                y=y
            )
            await interaction.response.send_message(
                f"⚙️ Created trap: **{trap.name}**\n"
                f"DC {trap.dc} | Save {trap.save_type} DC {trap.save_dc} | {trap.damage_dice} {trap.damage_type}"
            )
    
    elif action == "view":
        if not name:
            await interaction.response.send_message("Specify a trap name.", ephemeral=True)
            return
        
        trap = get_trap(channel_id, name)
        if trap:
            await interaction.response.send_message(format_trap_info(trap))
        else:
            await interaction.response.send_message(f"Trap '{name}' not found.", ephemeral=True)
    
    elif action == "remove":
        if not name:
            await interaction.response.send_message("Specify a trap name.", ephemeral=True)
            return
        
        if remove_trap(channel_id, name):
            await interaction.response.send_message(f"✅ Removed trap: {name}")
        else:
            await interaction.response.send_message(f"Trap '{name}' not found.", ephemeral=True)
    
    elif action == "trigger":
        if not name:
            await interaction.response.send_message("Specify a trap name.", ephemeral=True)
            return
        
        result = trigger_trap(channel_id, name, [])
        if "error" in result:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        else:
            trap = result["trap"]
            await interaction.response.send_message(
                f"💥 **{trap.name} TRIGGERED!**\n"
                f"*{trap.description}*\n\n"
                f"Save: {trap.save_type} DC {trap.save_dc}\n"
                f"Damage: {trap.damage_dice} {trap.damage_type}"
            )


@bot.tree.command(name="detecttrap", description="Roll Perception to detect a trap")
@app_commands.describe(
    trap_name="Name of the trap (DM use)",
    roll="Perception roll result"
)
async def detect_trap_cmd(
    interaction: discord.Interaction,
    trap_name: str,
    roll: int
):
    """Attempt to detect a hidden trap."""
    channel_id = str(interaction.channel.id)
    
    result = detect_trap(channel_id, trap_name, roll)
    
    if "error" in result:
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
    elif result.get("already_detected"):
        await interaction.response.send_message(
            f"👁️ The trap **{trap_name}** was already detected!",
            ephemeral=True
        )
    elif result["success"]:
        trap = result["trap"]
        await interaction.response.send_message(
            f"👁️ **Trap Detected!**\n"
            f"You notice a {trap.trap_type} trap: **{trap.name}**\n"
            f"*{trap.description}*"
        )
    else:
        await interaction.response.send_message(
            f"You don't notice anything unusual. (Rolled {roll} vs DC {result['dc']})",
            ephemeral=True
        )


@bot.tree.command(name="disarmtrap", description="Attempt to disarm a trap")
@app_commands.describe(
    trap_name="Name of the trap",
    roll="Thieves' Tools or DEX check result"
)
async def disarm_trap_cmd(
    interaction: discord.Interaction,
    trap_name: str,
    roll: int
):
    """Attempt to disarm a detected trap."""
    channel_id = str(interaction.channel.id)
    
    result = disarm_trap(channel_id, trap_name, roll)
    
    if "error" in result:
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
    elif result.get("already_disarmed"):
        await interaction.response.send_message(
            f"✅ The trap **{trap_name}** is already disarmed!",
            ephemeral=True
        )
    elif result.get("triggered"):
        # Critical failure - trap triggers!
        trap = result["trap"]
        trigger_result = trigger_trap(channel_id, trap_name, [interaction.user.display_name])
        await interaction.response.send_message(
            f"💥 **CRITICAL FAILURE!** The trap triggers!\n"
            f"*{trap.description}*\n\n"
            f"Save: {trap.save_type} DC {trap.save_dc}\n"
            f"Damage: {trap.damage_dice} {trap.damage_type}"
        )
    elif result["success"]:
        await interaction.response.send_message(
            f"✅ **Trap Disarmed!**\n"
            f"You carefully disarm the {result['trap'].name}."
        )
    else:
        await interaction.response.send_message(
            f"❌ Disarm failed! (Rolled {roll} vs DC {result['dc']})\n"
            f"The trap remains active. Try again carefully...",
            ephemeral=True
        )


@bot.tree.command(name="weather", description="Set weather conditions")
@app_commands.describe(
    weather_type="Type of weather",
    intensity="Weather intensity (1-3)",
    duration="Duration in hours (-1 for indefinite)"
)
@app_commands.choices(weather_type=[
    app_commands.Choice(name="Clear", value="clear"),
    app_commands.Choice(name="Cloudy", value="cloudy"),
    app_commands.Choice(name="Rain", value="rain"),
    app_commands.Choice(name="Heavy Rain", value="heavy_rain"),
    app_commands.Choice(name="Thunderstorm", value="thunderstorm"),
    app_commands.Choice(name="Fog", value="fog"),
    app_commands.Choice(name="Dense Fog", value="dense_fog"),
    app_commands.Choice(name="Snow", value="snow"),
    app_commands.Choice(name="Blizzard", value="blizzard"),
    app_commands.Choice(name="Sandstorm", value="sandstorm"),
    app_commands.Choice(name="Extreme Heat", value="extreme_heat"),
    app_commands.Choice(name="Extreme Cold", value="extreme_cold"),
    app_commands.Choice(name="Wind", value="wind"),
    app_commands.Choice(name="Strong Wind", value="strong_wind"),
])
async def weather_cmd(
    interaction: discord.Interaction,
    weather_type: str = "",
    intensity: int = 1,
    duration: int = -1
):
    """Set or view current weather conditions."""
    channel_id = str(interaction.channel.id)
    
    if not weather_type:
        # View current weather
        weather = get_weather(channel_id)
        if weather:
            await interaction.response.send_message(format_weather_info(weather))
        else:
            await interaction.response.send_message("🌤️ Weather is clear.")
        return
    
    if weather_type == "clear":
        clear_weather(channel_id)
        await interaction.response.send_message("🌤️ Weather cleared.")
        return
    
    weather = set_weather(channel_id, weather_type, intensity, duration)
    if weather:
        info = format_weather_info(weather)
        await interaction.response.send_message(f"🌦️ Weather Changed!\n\n{info}")
    else:
        await interaction.response.send_message(f"Unknown weather type: {weather_type}", ephemeral=True)


@bot.tree.command(name="lighting", description="Set lighting conditions")
@app_commands.describe(
    light_level="Lighting level",
    source="Source of light (torch, sunlight, etc.)",
    radius="Radius in feet (0 for entire area)"
)
@app_commands.choices(light_level=[
    app_commands.Choice(name="Bright Light", value="bright"),
    app_commands.Choice(name="Dim Light", value="dim"),
    app_commands.Choice(name="Darkness", value="darkness"),
    app_commands.Choice(name="Magical Darkness", value="magical_darkness"),
])
async def lighting_cmd(
    interaction: discord.Interaction,
    light_level: str = "",
    source: str = "",
    radius: int = 0
):
    """Set or view current lighting conditions."""
    channel_id = str(interaction.channel.id)
    
    if not light_level:
        # View current lighting
        lighting = get_lighting(channel_id)
        await interaction.response.send_message(format_lighting_info(lighting))
        return
    
    lighting = set_lighting(channel_id, light_level, source, radius)
    info = format_lighting_info(lighting)
    
    emoji = "🔦" if light_level == "dim" else ("🌑" if "dark" in light_level else "☀️")
    await interaction.response.send_message(f"{emoji} Lighting Changed!\n\n{info}")


# ============================================================================
# TIME MANAGEMENT COMMANDS (Phase 12)
# ============================================================================

@bot.tree.command(name="time", description="View or set in-game time")
@app_commands.describe(
    action="Action to perform",
    hours="Hours to advance (for advance action)",
    period="Time period to set (for set action)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="View Current Time", value="view"),
    app_commands.Choice(name="Advance Time", value="advance"),
    app_commands.Choice(name="Set Time Period", value="set"),
])
@app_commands.choices(period=[
    app_commands.Choice(name="Dawn (6 AM)", value="dawn"),
    app_commands.Choice(name="Morning (8 AM)", value="morning"),
    app_commands.Choice(name="Midday (12 PM)", value="midday"),
    app_commands.Choice(name="Afternoon (2 PM)", value="afternoon"),
    app_commands.Choice(name="Evening (6 PM)", value="evening"),
    app_commands.Choice(name="Dusk (8 PM)", value="dusk"),
    app_commands.Choice(name="Night (10 PM)", value="night"),
    app_commands.Choice(name="Midnight (12 AM)", value="midnight"),
])
async def time_cmd(
    interaction: discord.Interaction,
    action: str = "view",
    hours: int = 1,
    period: str = ""
):
    """View or manipulate in-game time."""
    channel_id = str(interaction.channel.id)
    
    try:
        from utils.world_generator import (
            get_time_state, set_time_state, period_to_hour,
            update_lighting_for_time
        )
        
        time_state = get_time_state(channel_id)
        
        if action == "view":
            time_of_day = time_state.get_time_of_day()
            emoji = {"dawn": "🌅", "morning": "☀️", "midday": "🌞", 
                     "afternoon": "🌤️", "evening": "🌆", "dusk": "🌇", 
                     "night": "🌙"}.get(time_of_day, "⏰")
            await interaction.response.send_message(
                f"{emoji} **Current Time**\n\n"
                f"**Period:** {time_of_day.title()}\n"
                f"**Time:** {time_state.format_time()}"
            )
        
        elif action == "advance":
            time_state.advance(hours)
            set_time_state(channel_id, time_state)
            update_lighting_for_time(channel_id, time_state)
            
            time_of_day = time_state.get_time_of_day()
            await interaction.response.send_message(
                f"⏰ **Time Advanced by {hours} hour(s)!**\n\n"
                f"**Period:** {time_of_day.title()}\n"
                f"**Time:** {time_state.format_time()}"
            )
        
        elif action == "set":
            if not period:
                await interaction.response.send_message(
                    "⚠️ Please specify a time period to set!", ephemeral=True
                )
                return
            
            hour = period_to_hour(period)
            time_state.hour = hour
            set_time_state(channel_id, time_state)
            update_lighting_for_time(channel_id, time_state)
            
            await interaction.response.send_message(
                f"⏰ **Time Set to {period.title()}!**\n\n"
                f"**Time:** {time_state.format_time()}"
            )
    
    except Exception as e:
        await interaction.response.send_message(
            f"⚠️ Error managing time: {str(e)}", ephemeral=True
        )


@bot.tree.command(name="location", description="Set or view current location with environment presets")
@app_commands.describe(
    location="Location name (cave, dungeon, forest, tavern, etc.)"
)
async def location_cmd(
    interaction: discord.Interaction,
    location: str = ""
):
    """Set or view current location with automatic environment presets."""
    channel_id = str(interaction.channel.id)
    
    try:
        from utils.world_generator import (
            get_current_location, set_current_location,
            apply_location_preset, get_location_memory,
            LOCATION_PRESETS
        )
        
        if not location:
            # View current location
            current = get_current_location(channel_id)
            memory = get_location_memory(channel_id, current) if current else None
            
            if not current:
                await interaction.response.send_message(
                    "📍 **Current Location:** Unknown\n\n"
                    f"*Available presets:* {', '.join(LOCATION_PRESETS.keys())}"
                )
                return
            
            msg = f"📍 **Current Location:** {current}\n"
            if memory:
                msg += f"**Type:** {'Outdoor' if memory.is_outdoor else 'Indoor'}\n"
                msg += f"**Lighting:** {memory.lighting_level}\n"
                if memory.weather_type:
                    msg += f"**Weather:** {memory.weather_type}\n"
            
            await interaction.response.send_message(msg)
        else:
            # Set new location
            results = apply_location_preset(channel_id, location)
            
            if results:
                await interaction.response.send_message("\n".join(results))
            else:
                set_current_location(channel_id, location)
                await interaction.response.send_message(f"📍 Location set to: {location}")
    
    except Exception as e:
        await interaction.response.send_message(
            f"⚠️ Error managing location: {str(e)}", ephemeral=True
        )


@bot.tree.command(name="hazard", description="Create or manage environmental hazards")
@app_commands.describe(
    action="Action to perform",
    name="Name of the hazard",
    hazard_type="Type of hazard",
    damage="Damage dice (e.g., 2d6)",
    damage_type="Type of damage",
    save_dc="DC for saving throw",
    duration="Duration in rounds (-1 for permanent)",
    x="X position",
    y="Y position",
    width="Width of hazard area",
    height="Height of hazard area"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Create", value="create"),
    app_commands.Choice(name="List", value="list"),
    app_commands.Choice(name="Remove", value="remove"),
])
@app_commands.choices(hazard_type=[
    app_commands.Choice(name="Fire", value="fire"),
    app_commands.Choice(name="Lava", value="lava"),
    app_commands.Choice(name="Acid", value="acid"),
    app_commands.Choice(name="Poison Cloud", value="poison_cloud"),
    app_commands.Choice(name="Magical Zone", value="magical_zone"),
])
async def hazard_cmd(
    interaction: discord.Interaction,
    action: str,
    name: str = "",
    hazard_type: str = "fire",
    damage: str = "2d6",
    damage_type: str = "fire",
    save_dc: int = 15,
    duration: int = -1,
    x: int = -1,
    y: int = -1,
    width: int = 1,
    height: int = 1
):
    """Manage environmental hazards."""
    channel_id = str(interaction.channel.id)
    
    if action == "list":
        hazards = list_hazards(channel_id)
        if not hazards:
            await interaction.response.send_message("No hazards in this area.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="☠️ Environmental Hazards",
            color=discord.Color.red()
        )
        
        for h in hazards:
            dur = f" [{h.rounds_remaining}r]" if h.duration_rounds > 0 else " [permanent]"
            embed.add_field(
                name=f"💀 {h.name}{dur}",
                value=f"{h.hazard_type} | {h.damage_dice} {h.damage_type} | DC {h.save_dc}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    elif action == "create":
        if not name:
            await interaction.response.send_message("Provide a hazard name.", ephemeral=True)
            return
        
        hazard = create_hazard(
            channel_id=channel_id,
            name=name,
            hazard_type=hazard_type,
            damage_dice=damage,
            damage_type=damage_type,
            save_dc=save_dc,
            duration_rounds=duration,
            x=x,
            y=y,
            width=width,
            height=height
        )
        
        await interaction.response.send_message(
            f"☠️ Created hazard: **{hazard.name}**\n"
            f"Type: {hazard.hazard_type} | {hazard.damage_dice} {hazard.damage_type} | DC {save_dc}"
        )
    
    elif action == "remove":
        if not name:
            await interaction.response.send_message("Specify a hazard name.", ephemeral=True)
            return
        
        if remove_hazard(channel_id, name):
            await interaction.response.send_message(f"✅ Removed hazard: {name}")
        else:
            await interaction.response.send_message(f"Hazard '{name}' not found.", ephemeral=True)


@bot.tree.command(name="terrain", description="Create or manage terrain zones")
@app_commands.describe(
    action="Action to perform",
    name="Name of the terrain zone",
    terrain_type="Type of terrain",
    x="X position",
    y="Y position",
    width="Width of zone",
    height="Height of zone"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Create", value="create"),
    app_commands.Choice(name="List", value="list"),
    app_commands.Choice(name="Remove", value="remove"),
])
@app_commands.choices(terrain_type=[
    app_commands.Choice(name="Difficult Terrain", value="difficult"),
    app_commands.Choice(name="Shallow Water", value="water_shallow"),
    app_commands.Choice(name="Deep Water", value="water_deep"),
    app_commands.Choice(name="Ice", value="ice"),
    app_commands.Choice(name="Lava", value="lava"),
    app_commands.Choice(name="Acid Pool", value="acid"),
    app_commands.Choice(name="Rubble", value="rubble"),
    app_commands.Choice(name="Mud", value="mud"),
    app_commands.Choice(name="Webs", value="webs"),
])
async def terrain_cmd(
    interaction: discord.Interaction,
    action: str,
    name: str = "",
    terrain_type: str = "difficult",
    x: int = 0,
    y: int = 0,
    width: int = 1,
    height: int = 1
):
    """Manage terrain zones."""
    channel_id = str(interaction.channel.id)
    
    if action == "list":
        zones = list_terrain_zones(channel_id)
        if not zones:
            await interaction.response.send_message("No special terrain zones.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏔️ Terrain Zones",
            color=discord.Color.dark_green()
        )
        
        for zone in zones:
            effects = zone.get("effects", {})
            embed.add_field(
                name=f"🗺️ {zone['name']}",
                value=f"{effects.get('name', zone['terrain_type'])} | ({zone['x']},{zone['y']}) {zone['width']}x{zone['height']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    elif action == "create":
        if not name:
            await interaction.response.send_message("Provide a terrain zone name.", ephemeral=True)
            return
        
        result = add_terrain_zone(
            channel_id=channel_id,
            name=name,
            terrain_type=terrain_type,
            x=x,
            y=y,
            width=width,
            height=height
        )
        
        if "error" in result:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        else:
            effects = result.get("effects", {})
            await interaction.response.send_message(
                f"🏔️ Created terrain zone: **{name}**\n"
                f"Type: {effects.get('name', terrain_type)} | Area: ({x},{y}) to ({x+width-1},{y+height-1})"
            )
    
    elif action == "remove":
        if not name:
            await interaction.response.send_message("Specify a terrain zone name.", ephemeral=True)
            return
        
        if remove_terrain_zone(channel_id, name):
            await interaction.response.send_message(f"✅ Removed terrain zone: {name}")
        else:
            await interaction.response.send_message(f"Terrain zone '{name}' not found.", ephemeral=True)


@bot.tree.command(name="cover", description="Calculate cover between positions")
@app_commands.describe(
    attacker_x="Attacker X position",
    attacker_y="Attacker Y position",
    target_x="Target X position",
    target_y="Target Y position"
)
async def cover_cmd(
    interaction: discord.Interaction,
    attacker_x: int,
    attacker_y: int,
    target_x: int,
    target_y: int
):
    """Calculate cover between two positions."""
    channel_id = str(interaction.channel.id)
    
    # Get obstacles from terrain zones
    zones = list_terrain_zones(channel_id)
    obstacles = []
    for zone in zones:
        effects = zone.get("effects", {})
        cover = effects.get("cover")
        if cover:
            for dx in range(zone["width"]):
                for dy in range(zone["height"]):
                    obstacles.append({
                        "x": zone["x"] + dx,
                        "y": zone["y"] + dy,
                        "cover_type": cover
                    })
    
    cover_type = calculate_cover(attacker_x, attacker_y, target_x, target_y, obstacles)
    bonus = get_cover_bonus(cover_type)
    
    if cover_type == "none":
        await interaction.response.send_message("🎯 No cover between these positions.")
    elif cover_type == "full":
        await interaction.response.send_message("🧱 **Full Cover** - Target cannot be directly targeted.")
    else:
        await interaction.response.send_message(
            f"🛡️ **{cover_type.replace('_', ' ').title()} Cover**\n"
            f"+{bonus['ac']} AC, +{bonus['dex_save']} Dex saves"
        )


# =============================================================================
# TRAVEL & ENCOUNTER COMMANDS
# =============================================================================

@bot.tree.command(name="travel", description="Start traveling to a destination")
@app_commands.describe(
    destination="Where you're traveling to",
    distance="Distance in miles",
    terrain="Type of terrain you're traveling through",
    pace="Travel pace (slow/normal/fast)",
    origin="Where you're starting from (defaults to current location)"
)
@app_commands.choices(terrain=[
    app_commands.Choice(name="Road", value="road"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Plains", value="plains"),
    app_commands.Choice(name="Mountains", value="mountains"),
    app_commands.Choice(name="Hills", value="hills"),
    app_commands.Choice(name="Swamp", value="swamp"),
    app_commands.Choice(name="Desert", value="desert"),
    app_commands.Choice(name="Arctic", value="arctic"),
    app_commands.Choice(name="Coastal", value="coastal"),
    app_commands.Choice(name="Underground", value="underground"),
    app_commands.Choice(name="Jungle", value="jungle"),
])
@app_commands.choices(pace=[
    app_commands.Choice(name="Slow (Stealth possible)", value="slow"),
    app_commands.Choice(name="Normal", value="normal"),
    app_commands.Choice(name="Fast (-5 Passive Perception)", value="fast"),
])
async def travel_cmd(
    interaction: discord.Interaction,
    destination: str,
    distance: float,
    terrain: str = "road",
    pace: str = "normal",
    origin: str = ""
):
    """Start traveling between locations."""
    channel_id = str(interaction.channel.id)
    
    # Get origin from campaign state if not specified
    if not origin:
        state = load_state(channel_id)
        origin = state.get("location", "Current Location")
    
    # Calculate travel time
    travel_info = calculate_travel_time(distance, terrain, pace)
    
    # Start travel
    travel_state = start_travel(
        channel_id=channel_id,
        origin=origin,
        destination=destination,
        distance_miles=distance,
        terrain=terrain,
        pace=pace
    )
    
    embed = discord.Embed(
        title="🗺️ Journey Begun",
        description=f"Traveling from **{origin}** to **{destination}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Distance", value=f"{distance} miles", inline=True)
    embed.add_field(name="Terrain", value=terrain.title(), inline=True)
    embed.add_field(name="Pace", value=pace.title(), inline=True)
    embed.add_field(name="Estimated Time", value=f"{travel_info['days_required']} days", inline=True)
    embed.add_field(name="Miles/Day", value=f"{travel_info['miles_per_day']:.1f}", inline=True)
    
    if travel_info['stealth_possible']:
        embed.add_field(name="Stealth", value="✅ Possible", inline=True)
    if travel_info['perception_mod'] != 0:
        embed.add_field(name="Perception", value=f"{travel_info['perception_mod']:+d}", inline=True)
    
    embed.set_footer(text="Use /traveladvance to move forward, or /travelstatus to check progress")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="travelstatus", description="Check current travel progress")
async def travel_status_cmd(interaction: discord.Interaction):
    """Show current travel status."""
    channel_id = str(interaction.channel.id)
    
    status = get_travel_status(channel_id)
    if not status:
        await interaction.response.send_message(
            "🏠 Not currently traveling. Use `/travel` to begin a journey.",
            ephemeral=True
        )
        return
    
    # Build progress bar
    percent = status['progress_percent']
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    embed = discord.Embed(
        title="🗺️ Travel Status",
        description=f"**{status['origin']}** → **{status['destination']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Terrain", value=status['terrain'].title(), inline=True)
    embed.add_field(name="Pace", value=status['pace'].title(), inline=True)
    embed.add_field(name="Day", value=str(status['days_traveled'] + 1), inline=True)
    embed.add_field(
        name="Progress",
        value=f"[{bar}] {percent:.0f}%\n{status['traveled_miles']:.1f} / {status['total_miles']:.1f} miles",
        inline=False
    )
    embed.add_field(name="Hours Today", value=f"{status['hours_today']:.1f}/8", inline=True)
    embed.add_field(name="Remaining", value=f"{status['remaining_miles']:.1f} miles", inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="traveladvance", description="Advance travel by hours")
@app_commands.describe(hours="Number of hours to travel (1-8)")
async def travel_advance_cmd(
    interaction: discord.Interaction,
    hours: int = 1
):
    """Advance travel and check for encounters."""
    channel_id = str(interaction.channel.id)
    
    status = get_travel_status(channel_id)
    if not status:
        await interaction.response.send_message(
            "🏠 Not currently traveling. Use `/travel` to begin a journey.",
            ephemeral=True
        )
        return
    
    hours = max(1, min(8, hours))  # Clamp to 1-8 hours
    
    result = advance_travel(channel_id, hours)
    
    if result.get('error'):
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        return
    
    # Build response
    lines = [
        f"⏰ **{hours} hour(s) pass...**",
        f"Traveled: {result['miles_traveled']:.1f} miles",
    ]
    
    # Check if arrived
    if result['arrived']:
        lines.append(f"\n🎉 **Arrived at {result['destination']}!**")
        
        # Update campaign location
        state = load_state(channel_id)
        state["location"] = result['destination']
        save_state(channel_id, state)
    else:
        lines.append(f"Progress: {result['progress_percent']:.0f}% ({result['remaining']:.1f} miles remaining)")
    
    await interaction.response.send_message("\n".join(lines))
    
    # Handle encounter if one occurred
    if result.get('encounter'):
        enc = result['encounter']
        
        if enc.get('needs_generation'):
            # Need party info to generate combat encounter
            await interaction.followup.send(
                "⚔️ **Random Encounter!** Use `/randomencounter` to generate the combat encounter."
            )
        elif enc.get('event_type') == 'combat':
            # Pre-generated combat encounter
            await interaction.followup.send(format_encounter_summary(Encounter.from_dict(enc)))
        else:
            # Non-combat event
            await interaction.followup.send(format_random_event(enc))


@bot.tree.command(name="travelcancel", description="Cancel current travel")
async def travel_cancel_cmd(interaction: discord.Interaction):
    """Cancel the current journey."""
    channel_id = str(interaction.channel.id)
    
    status = get_travel_status(channel_id)
    if not status:
        await interaction.response.send_message(
            "🏠 Not currently traveling.",
            ephemeral=True
        )
        return
    
    clear_travel_state(channel_id)
    await interaction.response.send_message(
        f"🛑 Journey to **{status['destination']}** cancelled.\n"
        f"Party remains in the wilderness ({status['traveled_miles']:.1f} miles from {status['origin']})."
    )


@bot.tree.command(name="randomencounter", description="Generate a random encounter")
@app_commands.describe(
    difficulty="Encounter difficulty",
    terrain="Terrain type for the encounter"
)
@app_commands.choices(difficulty=[
    app_commands.Choice(name="Easy", value="easy"),
    app_commands.Choice(name="Medium", value="medium"),
    app_commands.Choice(name="Hard", value="hard"),
    app_commands.Choice(name="Deadly", value="deadly"),
])
@app_commands.choices(terrain=[
    app_commands.Choice(name="Road", value="road"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Plains", value="plains"),
    app_commands.Choice(name="Mountains", value="mountains"),
    app_commands.Choice(name="Hills", value="hills"),
    app_commands.Choice(name="Swamp", value="swamp"),
    app_commands.Choice(name="Desert", value="desert"),
    app_commands.Choice(name="Arctic", value="arctic"),
    app_commands.Choice(name="Coastal", value="coastal"),
    app_commands.Choice(name="Underground", value="underground"),
    app_commands.Choice(name="Jungle", value="jungle"),
    app_commands.Choice(name="Ruins", value="ruins"),
])
async def random_encounter_cmd(
    interaction: discord.Interaction,
    difficulty: str = "medium",
    terrain: str = "plains"
):
    """Generate a random combat encounter for the party."""
    channel_id = str(interaction.channel.id)
    
    # Get party levels from registered characters
    state = load_state(channel_id)
    party_levels = []
    
    for player_data in state.get("players", []):
        user_id = player_data.get("id")
        if user_id:
            char = load_character(str(user_id))
            if char:
                party_levels.append(char.get("level", 1))
    
    if not party_levels:
        # Default to level 1 party of 4
        party_levels = [1, 1, 1, 1]
    
    # Use terrain from travel state if available
    travel_status = get_travel_status(channel_id)
    if travel_status and terrain == "plains":
        terrain = travel_status.get('terrain', terrain)
    
    # Generate encounter
    encounter = generate_combat_encounter(party_levels, terrain, difficulty)
    
    embed = discord.Embed(
        title=f"⚔️ {encounter.name}",
        description=encounter.description,
        color=discord.Color.red()
    )
    
    # Difficulty badge
    diff_colors = {"trivial": "🟢", "easy": "🟡", "medium": "🟠", "hard": "🔴", "deadly": "💀"}
    embed.add_field(
        name="Difficulty",
        value=f"{diff_colors.get(encounter.difficulty, '⚪')} {encounter.difficulty.title()}",
        inline=True
    )
    embed.add_field(name="Terrain", value=terrain.title(), inline=True)
    embed.add_field(name="XP Reward", value=str(encounter.xp_reward), inline=True)
    
    # List enemies
    enemy_text = ""
    for monster in encounter.monsters:
        enemy_text += f"• **{monster['name']}** (HP: {monster['hp']}, AC: {monster['ac']})\n"
    
    if enemy_text:
        embed.add_field(name="Enemies", value=enemy_text, inline=False)
    
    embed.set_footer(text=f"Use /combat to start combat with these enemies")
    
    # Store encounter for /combat command
    state["pending_encounter"] = encounter.to_dict()
    save_state(channel_id, state)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="encounter", description="Generate a random non-combat encounter")
@app_commands.describe(
    event_type="Type of event to generate",
    terrain="Terrain type for the encounter"
)
@app_commands.choices(event_type=[
    app_commands.Choice(name="Social (NPCs)", value="social"),
    app_commands.Choice(name="Discovery", value="discovery"),
    app_commands.Choice(name="Weather Change", value="weather"),
    app_commands.Choice(name="Rest Site", value="rest_site"),
    app_commands.Choice(name="Random", value="random"),
])
@app_commands.choices(terrain=[
    app_commands.Choice(name="Road", value="road"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Plains", value="plains"),
    app_commands.Choice(name="Mountains", value="mountains"),
    app_commands.Choice(name="Hills", value="hills"),
    app_commands.Choice(name="Swamp", value="swamp"),
    app_commands.Choice(name="Desert", value="desert"),
    app_commands.Choice(name="Coastal", value="coastal"),
    app_commands.Choice(name="Underground", value="underground"),
])
async def non_combat_encounter_cmd(
    interaction: discord.Interaction,
    event_type: str = "random",
    terrain: str = "road"
):
    """Generate a random non-combat encounter."""
    channel_id = str(interaction.channel.id)
    
    # Use terrain from travel state if available
    travel_status = get_travel_status(channel_id)
    if travel_status and terrain == "road":
        terrain = travel_status.get('terrain', terrain)
    
    if event_type == "random":
        event_type = determine_encounter_type()
        # If it rolled combat, re-roll for non-combat
        while event_type == "combat":
            event_type = determine_encounter_type()
    
    if event_type == "social":
        encounter = generate_social_encounter(terrain)
        embed = discord.Embed(
            title=f"👥 {encounter.name}",
            description=encounter.description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Type", value="Social Encounter", inline=True)
        embed.add_field(name="Terrain", value=terrain.title(), inline=True)
        embed.set_footer(text="Roleplay this encounter or use /do to interact")
        
    elif event_type == "discovery":
        encounter = generate_discovery_encounter(terrain)
        embed = discord.Embed(
            title=f"🔍 {encounter.name}",
            description=encounter.description,
            color=discord.Color.gold()
        )
        embed.add_field(name="Type", value="Discovery", inline=True)
        embed.add_field(name="Terrain", value=terrain.title(), inline=True)
        embed.set_footer(text="Investigate with /do or continue on your way")
        
    else:
        # Weather, rest_site, or other
        event = generate_random_event(event_type)
        emoji_map = {"weather": "🌦️", "discovery": "🔍", "rest_site": "🏕️", "social": "👥", "hazard": "⚠️"}
        embed = discord.Embed(
            title=f"{emoji_map.get(event_type, '❓')} {event['name']}",
            description=event['description'],
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=event_type.replace("_", " ").title(), inline=True)
        if event.get('effect'):
            embed.add_field(name="Effect", value=event['effect'], inline=False)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="encountercheck", description="Roll for a random encounter")
@app_commands.describe(
    hours="Hours of travel/activity to check",
    terrain="Terrain type",
    is_night="Is it nighttime?",
    stealthy="Is the party being stealthy?"
)
@app_commands.choices(terrain=[
    app_commands.Choice(name="Road", value="road"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Plains", value="plains"),
    app_commands.Choice(name="Mountains", value="mountains"),
    app_commands.Choice(name="Swamp", value="swamp"),
    app_commands.Choice(name="Underground", value="underground"),
])
async def encounter_check_cmd(
    interaction: discord.Interaction,
    hours: int = 1,
    terrain: str = "road",
    is_night: bool = False,
    stealthy: bool = False
):
    """Roll to see if a random encounter occurs."""
    channel_id = str(interaction.channel.id)
    
    # Use terrain from travel state if available
    travel_status = get_travel_status(channel_id)
    if travel_status:
        terrain = travel_status.get('terrain', terrain)
    
    base_chance = TERRAIN_MODIFIERS.get(terrain, {}).get("encounter_chance", 0.15)
    
    # Roll
    encounter_occurred = roll_for_encounter(terrain, hours, is_night, stealthy)
    
    if encounter_occurred:
        event_type = determine_encounter_type()
        
        await interaction.response.send_message(
            f"🎲 **Encounter Check:** Something happens!\n"
            f"Event Type: **{event_type.title()}**\n"
            f"Use `/randomencounter` for combat or `/encounter` for non-combat."
        )
    else:
        await interaction.response.send_message(
            f"🎲 **Encounter Check:** The journey continues uneventfully.\n"
            f"(Base chance: {base_chance*100:.0f}%, checked for {hours} hour(s))"
        )


# =============================================================================
# WORLD MAP COMMANDS (Phase 14)
# =============================================================================

@bot.tree.command(name="worldmap", description="View the world map and known locations")
async def worldmap_cmd(interaction: discord.Interaction):
    """View all known locations and travel connections."""
    channel_id = str(interaction.channel.id)
    
    world_state = load_world_state(channel_id)
    current = world_state.current_location
    
    embed = discord.Embed(
        title="🗺️ World Map",
        description=f"Current Location: **{current}**",
        color=discord.Color.blue()
    )
    
    if not world_state.locations:
        embed.add_field(
            name="No Locations Discovered",
            value="Explore the world to discover new locations!\nLocations are discovered through narration and NPC conversations.",
            inline=False
        )
    else:
        # Group locations by status
        explored = [l for l in world_state.locations.values() if l.status == "explored"]
        visited = [l for l in world_state.locations.values() if l.status == "visited"]
        known = [l for l in world_state.locations.values() if l.status == "known"]
        heard_of = [l for l in world_state.locations.values() if l.status == "heard_of"]
        
        if explored:
            loc_text = "\n".join([f"🗺️ {l.name} ({l.terrain})" for l in explored[:10]])
            embed.add_field(name="Fully Explored", value=loc_text, inline=False)
        
        if visited:
            loc_text = "\n".join([f"✅ {'⭐ ' if l.is_poi else ''}{l.name} ({l.terrain})" for l in visited[:10]])
            embed.add_field(name="Visited Locations", value=loc_text, inline=False)
        
        if known:
            loc_text = "\n".join([f"📍 {'⭐ ' if l.is_poi else ''}{l.name}" for l in known[:10]])
            embed.add_field(name="Known Locations", value=loc_text, inline=False)
        
        if heard_of:
            loc_text = "\n".join([f"👂 {l.name}" for l in heard_of[:10]])
            embed.add_field(name="Rumors & Hearsay", value=loc_text, inline=False)
        
        # Show current location's connections
        current_loc = world_state.locations.get(current)
        if current_loc and current_loc.connections:
            conn_text = "\n".join([
                f"→ {dest}: {dist:.0f} miles"
                for dest, dist in sorted(current_loc.connections.items(), key=lambda x: x[1])
            ][:10])
            embed.add_field(name="Nearby Destinations", value=conn_text, inline=False)
    
    embed.add_field(
        name="Total Miles Traveled",
        value=f"{world_state.total_miles_traveled:.0f} miles",
        inline=True
    )
    
    embed.set_footer(text="Use /fasttravel to travel to visited locations, or /addlocation to add new ones")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="fasttravel", description="Fast travel to a visited location")
@app_commands.describe(destination="The location to travel to")
async def fasttravel_cmd(
    interaction: discord.Interaction,
    destination: str
):
    """Fast travel to a previously visited location."""
    channel_id = str(interaction.channel.id)
    
    # Check if fast travel is possible
    if not can_fast_travel(channel_id, destination):
        # Show available options
        options = get_fast_travel_options(channel_id)
        if options:
            opt_text = "\n".join([f"• {opt['name']}" for opt in options[:10]])
            await interaction.response.send_message(
                f"❌ Cannot fast travel to **{destination}**.\n"
                f"You can only fast travel to visited locations.\n\n"
                f"**Available Destinations:**\n{opt_text}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No fast travel destinations available.\n"
                f"Explore the world to discover and visit new locations!",
                ephemeral=True
            )
        return
    
    # Execute fast travel
    result = fast_travel(channel_id, destination)
    
    if result.get("error"):
        await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
        return
    
    # Update campaign location
    state = load_state(channel_id)
    state["location"] = destination
    save_state(channel_id, state)
    
    embed = discord.Embed(
        title="⚡ Fast Travel Complete",
        description=f"Traveled from **{result['previous_location']}** to **{result['new_location']}**",
        color=discord.Color.green()
    )
    embed.add_field(name="Distance", value=f"{result['distance']:.1f} miles", inline=True)
    embed.add_field(name="Travel Time", value=f"{result['travel_time_days']} day(s)", inline=True)
    embed.set_footer(text="The journey was uneventful along familiar roads")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="addlocation", description="Manually add a location to the world map")
@app_commands.describe(
    name="Location name",
    terrain="Terrain type",
    location_type="Type of location",
    description="Brief description",
    distance_from_current="Distance from current location (miles)",
    is_poi="Is this a point of interest?"
)
@app_commands.choices(terrain=[
    app_commands.Choice(name="Road", value="road"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Plains", value="plains"),
    app_commands.Choice(name="Mountains", value="mountains"),
    app_commands.Choice(name="Hills", value="hills"),
    app_commands.Choice(name="Swamp", value="swamp"),
    app_commands.Choice(name="Desert", value="desert"),
    app_commands.Choice(name="Arctic", value="arctic"),
    app_commands.Choice(name="Coastal", value="coastal"),
    app_commands.Choice(name="Urban", value="urban"),
    app_commands.Choice(name="Underground", value="underground"),
    app_commands.Choice(name="Jungle", value="jungle"),
])
@app_commands.choices(location_type=[
    app_commands.Choice(name="City", value="city"),
    app_commands.Choice(name="Town", value="town"),
    app_commands.Choice(name="Village", value="village"),
    app_commands.Choice(name="Dungeon", value="dungeon"),
    app_commands.Choice(name="Cave", value="cave"),
    app_commands.Choice(name="Ruins", value="ruins"),
    app_commands.Choice(name="Tower", value="tower"),
    app_commands.Choice(name="Castle", value="castle"),
    app_commands.Choice(name="Temple", value="temple"),
    app_commands.Choice(name="Inn", value="inn"),
    app_commands.Choice(name="Camp", value="camp"),
    app_commands.Choice(name="Landmark", value="landmark"),
    app_commands.Choice(name="Unknown", value="unknown"),
])
async def addlocation_cmd(
    interaction: discord.Interaction,
    name: str,
    terrain: str = "wilderness",
    location_type: str = "unknown",
    description: str = "",
    distance_from_current: float = 0,
    is_poi: bool = False
):
    """Add a new location to the world map."""
    channel_id = str(interaction.channel.id)
    
    # Add the location
    location = add_location(
        channel_id=channel_id,
        name=name,
        terrain=terrain,
        location_type=location_type,
        description=description,
        is_poi=is_poi,
        status="known"
    )
    
    # Connect to current location if distance provided
    if distance_from_current > 0:
        current = get_current_location(channel_id)
        if current:
            connect_locations(channel_id, current, name, distance_from_current)
    
    embed = discord.Embed(
        title="📍 Location Added",
        description=f"**{name}** has been added to the world map",
        color=discord.Color.green()
    )
    embed.add_field(name="Type", value=location_type.title(), inline=True)
    embed.add_field(name="Terrain", value=terrain.title(), inline=True)
    if is_poi:
        embed.add_field(name="Point of Interest", value="⭐ Yes", inline=True)
    if description:
        embed.add_field(name="Description", value=description, inline=False)
    if distance_from_current > 0:
        embed.add_field(
            name="Distance",
            value=f"{distance_from_current:.0f} miles from current location",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setlocation", description="Set the party's current location")
@app_commands.describe(location="The location name to set as current")
async def setlocation_cmd(
    interaction: discord.Interaction,
    location: str
):
    """Set the party's current location on the world map."""
    channel_id = str(interaction.channel.id)
    
    # Update world map
    set_current_location(channel_id, location)
    
    # Update campaign state
    state = load_state(channel_id)
    state["location"] = location
    save_state(channel_id, state)
    
    # Get location info if it exists
    loc = get_location(channel_id, location)
    
    embed = discord.Embed(
        title="📍 Location Updated",
        description=f"Party is now at **{location}**",
        color=discord.Color.blue()
    )
    
    if loc:
        if loc.terrain != "wilderness":
            embed.add_field(name="Terrain", value=loc.terrain.title(), inline=True)
        if loc.location_type != "unknown":
            embed.add_field(name="Type", value=loc.location_type.title(), inline=True)
        if loc.visited_count > 0:
            embed.add_field(name="Visits", value=str(loc.visited_count), inline=True)
        if loc.connections:
            conn_text = ", ".join([
                f"{dest} ({dist:.0f} mi)"
                for dest, dist in sorted(loc.connections.items(), key=lambda x: x[1])[:5]
            ])
            embed.add_field(name="Nearby", value=conn_text, inline=False)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="locationinfo", description="View detailed information about a location")
@app_commands.describe(location="The location to view (leave blank for current)")
async def locationinfo_cmd(
    interaction: discord.Interaction,
    location: str = ""
):
    """View detailed information about a location."""
    channel_id = str(interaction.channel.id)
    
    if not location:
        location = get_current_location(channel_id)
    
    loc = get_location(channel_id, location)
    
    if not loc:
        await interaction.response.send_message(
            f"❌ Location **{location}** not found on the world map.",
            ephemeral=True
        )
        return
    
    status_emoji = {
        "unknown": "❓",
        "heard_of": "👂",
        "known": "📍",
        "visited": "✅",
        "explored": "🗺️"
    }
    
    embed = discord.Embed(
        title=f"{status_emoji.get(loc.status, '❓')} {'⭐ ' if loc.is_poi else ''}{loc.name}",
        description=loc.description if loc.description else "*No description available*",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Type", value=loc.location_type.title(), inline=True)
    embed.add_field(name="Terrain", value=loc.terrain.title(), inline=True)
    embed.add_field(name="Status", value=loc.status.replace("_", " ").title(), inline=True)
    
    if loc.visited_count > 0:
        embed.add_field(name="Times Visited", value=str(loc.visited_count), inline=True)
        if loc.first_visited:
            embed.add_field(name="First Visit", value=loc.first_visited[:10], inline=True)
    
    if loc.connections:
        conn_text = "\n".join([
            f"→ {dest}: {dist:.0f} miles"
            for dest, dist in sorted(loc.connections.items(), key=lambda x: x[1])
        ])
        embed.add_field(name="Connected Locations", value=conn_text, inline=False)
    
    if loc.tags:
        embed.add_field(name="Tags", value=", ".join(loc.tags), inline=False)
    
    if loc.notes:
        notes_text = "\n".join([f"• {note}" for note in loc.notes[-5:]])
        embed.add_field(name="Notes", value=notes_text, inline=False)
    
    await interaction.response.send_message(embed=embed)


# =============================================================================
# SESSION MANAGEMENT COMMANDS (Phase 15)
# =============================================================================

@bot.tree.command(name="session", description="View current session status or manage session")
@app_commands.describe(
    action="Action to perform (view, end, pause)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="view", value="view"),
    app_commands.Choice(name="end", value="end"),
    app_commands.Choice(name="pause", value="pause")
])
async def session_cmd(
    interaction: discord.Interaction,
    action: str = "view"
):
    """View or manage the current session."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if action == "view":
        # Show session status
        status_text = format_session_status(channel_id)
        
        # Add pacing info if session is active
        session = load_session_state(channel_id)
        if session.status == SessionStatus.ACTIVE.value:
            phase = get_current_pacing_phase(channel_id)
            duration = get_session_duration_minutes(channel_id)
            status_text += f"\n\n**Pacing:** {phase.value.title()} phase"
            
            # Check for pacing hints
            hints = get_pacing_hints(channel_id)
            if hints:
                status_text += f"\n💡 *Hint: {hints[0].hint}*"
        
        await interaction.response.send_message(status_text)
    
    elif action == "end":
        # End the session
        session = load_session_state(channel_id)
        if session.status == SessionStatus.INACTIVE.value:
            await interaction.response.send_message("❌ No active session to end.")
            return
        
        await interaction.response.defer()
        
        # Stop auto-save
        await auto_save_manager.stop_auto_save(channel_id)
        auto_save_manager.unregister_channel(channel_id)
        
        # End session and generate summary
        summary = end_session(channel_id, state)
        
        if summary:
            summary_text = format_session_end_summary(summary)
            await interaction.followup.send(summary_text)
            
            # Play ending TTS
            await play_tts(
                interaction,
                f"Session complete! You played for {summary.duration_minutes} minutes. See you next time!",
                "Narrator"
            )
        else:
            await interaction.followup.send("📊 Session ended.")
    
    elif action == "pause":
        session = load_session_state(channel_id)
        if session.status != SessionStatus.ACTIVE.value:
            await interaction.response.send_message("❌ No active session to pause.")
            return
        
        pause_session(channel_id)
        await interaction.response.send_message(
            "⏸️ **Session Paused**\n"
            "Your progress has been saved. Resume anytime!"
        )


@bot.tree.command(name="sessionrecap", description="Get a recap of the previous session")
async def session_recap_cmd(interaction: discord.Interaction):
    """Generate a recap of the last session."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    await interaction.response.defer()
    
    # Check for session summaries
    summaries = load_session_summaries(channel_id)
    
    if not summaries:
        await interaction.followup.send(
            "📖 No previous session found.\n"
            "*Start a new campaign with `/campaign`!*"
        )
        return
    
    # Generate recap
    recap_text = generate_session_recap(channel_id, state)
    
    embed = discord.Embed(
        title="📖 Session Recap",
        description=recap_text,
        color=discord.Color.purple()
    )
    
    last_session = summaries[-1]
    embed.add_field(
        name="Last Session Stats",
        value=f"⏱️ Duration: {last_session.duration_minutes} min\n"
              f"⚔️ Combats: {last_session.combat_count}\n"
              f"🎯 Actions: {last_session.action_count}",
        inline=True
    )
    
    if last_session.active_quests:
        embed.add_field(
            name="Active Quests",
            value="\n".join([f"• {q}" for q in last_session.active_quests[:3]]),
            inline=True
        )
    
    await interaction.followup.send(embed=embed)
    
    # Play recap TTS
    tts_text = clean_for_tts(recap_text)
    if len(tts_text) > 500:
        tts_text = tts_text[:500] + "..."
    await play_tts(interaction, tts_text, "Narrator")


@bot.tree.command(name="sessionhistory", description="View past session summaries")
async def session_history_cmd(interaction: discord.Interaction):
    """View history of past sessions."""
    channel_id = str(interaction.channel.id)
    
    summaries = load_session_summaries(channel_id)
    
    if not summaries:
        await interaction.response.send_message(
            "📚 No session history found.\n"
            "*Sessions are saved when you use `/session end`.*"
        )
        return
    
    embed = discord.Embed(
        title="📚 Session History",
        description=f"Showing last {min(len(summaries), 10)} sessions",
        color=discord.Color.blue()
    )
    
    for i, summary in enumerate(reversed(summaries[-10:])):
        started = summary.started_at[:10] if summary.started_at else "Unknown"
        embed.add_field(
            name=f"Session {len(summaries) - i}",
            value=f"📅 {started}\n"
                  f"⏱️ {summary.duration_minutes} min | ⚔️ {summary.combat_count} combats\n"
                  f"📍 {summary.final_location}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="recover", description="Recover from a crashed session")
async def recover_session_cmd(interaction: discord.Interaction):
    """Attempt to recover from a crashed session."""
    channel_id = str(interaction.channel.id)
    
    recovery = load_recovery_point(channel_id)
    
    if not recovery:
        await interaction.response.send_message(
            "❌ No recovery point found.\n"
            "*Recovery points are automatically saved during sessions.*"
        )
        return
    
    await interaction.response.defer()
    
    saved_at = recovery.get("saved_at", "Unknown time")
    campaign_state = recovery.get("campaign_state", {})
    
    if not campaign_state:
        await interaction.followup.send("❌ Recovery point is empty or corrupted.")
        return
    
    # Offer to restore
    campaign_title = campaign_state.get("campaign_title", "Unknown Campaign")
    location = campaign_state.get("location", "Unknown")
    
    embed = discord.Embed(
        title="🔄 Recovery Point Found",
        description=f"**Campaign:** {campaign_title}\n"
                    f"**Location:** {location}\n"
                    f"**Saved:** {saved_at}",
        color=discord.Color.orange()
    )
    embed.add_field(
        name="Restore?",
        value="React with ✅ to restore this state, or ❌ to discard it.",
        inline=False
    )
    
    msg = await interaction.followup.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user == interaction.user and
            str(reaction.emoji) in ["✅", "❌"] and
            reaction.message.id == msg.id
        )
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        if str(reaction.emoji) == "✅":
            # Restore the state
            save_state(channel_id, campaign_state)
            clear_recovery_point(channel_id)
            
            # Start a new session
            player_ids = campaign_state.get("players", [str(interaction.user.id)])
            start_session(channel_id, player_ids)
            
            await interaction.channel.send(
                f"✅ **Recovery Complete!**\n"
                f"Welcome back to **{campaign_title}**!\n"
                f"You're in {location}. Use `/recap` to refresh your memory."
            )
            
            # Play welcome back TTS
            await play_tts(
                interaction,
                f"Welcome back adventurers! You're in {location}.",
                "Narrator"
            )
        else:
            clear_recovery_point(channel_id)
            await interaction.channel.send("🗑️ Recovery point discarded.")
            
    except asyncio.TimeoutError:
        await interaction.channel.send("⏱️ Recovery timed out. Use `/recover` again when ready.")


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
    
    # Check if there's a pending skill check from the button system
    pending_check = get_pending_check(channel_id)
    if pending_check and user_id in pending_check.players_needed:
        # Build result for the pending check system
        if skill in SKILLS or skill.upper() in ['STR','DEX','CON','INT','WIS','CHA']:
            check_result = SkillCheckResult(
                player_id=user_id,
                player_name=char_name,
                skill_or_ability=skill_name,
                roll=result,
                modifier=mod,
                total=total,
                dc=pending_check.request.dc or dc,
                success=(result == 20) or (dc and total >= dc and result != 1),
                natural_20=(result == 20),
                natural_1=(result == 1),
                advantage=advantage,
                disadvantage=disadvantage,
                rolls=[roll1, roll2] if (advantage or disadvantage) else [roll1]
            )
            
            # Add result to pending check
            all_done = add_check_result(channel_id, user_id, check_result)
            
            if all_done:
                # All players have rolled - process the check
                await process_completed_skill_check(interaction.channel, channel_id)
                return  # Skip old-style pending roll handling
    
    # If there was a pending roll (old style), resolve it with the AI
    if pending and pending.get('player_id') == user_id and total is not None:
        # Use new narration system if enabled
        if SkillCheckConfig.NARRATE_OUTCOMES and dc:
            try:
                success = (result == 20) or (dc and total >= dc and result != 1)
                narration = await narrate_skill_check_outcome(
                    char_name,
                    skill_name,
                    total,
                    dc,
                    success,
                    result == 20,
                    result == 1,
                    pending.get('action', 'the action')
                )
                
                # Clear the pending roll
                updated_state = state.copy()
                updated_state['pending_roll'] = None
                save_state(channel_id, updated_state)
                
                # Send the outcome
                voice_tag = extract_voice_tag(narration)
                text = clean_text(narration)
                await interaction.followup.send(f"**Outcome:**\n{text}")
                await play_tts(interaction, text, voice_tag)
                log_message(channel_id, "DM", text)
                return
            except Exception as e:
                print(f"Skill check narration error, falling back: {e}")
        
        # Fallback to old-style AI response
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


# Skill check choices for autocomplete
SKILL_CHOICES = [
    app_commands.Choice(name=skill.replace('_', ' ').title(), value=skill)
    for skill in ['acrobatics', 'animal_handling', 'arcana', 'athletics', 'deception',
                  'history', 'insight', 'intimidation', 'investigation', 'medicine',
                  'nature', 'perception', 'performance', 'persuasion', 'religion',
                  'sleight_of_hand', 'stealth', 'survival']
]

ABILITY_CHOICES = [
    app_commands.Choice(name="Strength", value="strength"),
    app_commands.Choice(name="Dexterity", value="dexterity"),
    app_commands.Choice(name="Constitution", value="constitution"),
    app_commands.Choice(name="Intelligence", value="intelligence"),
    app_commands.Choice(name="Wisdom", value="wisdom"),
    app_commands.Choice(name="Charisma", value="charisma"),
]


@bot.tree.command(name="groupcheck", description="Request a group skill check from all players")
@app_commands.describe(
    skill="Skill to check",
    dc="Difficulty class (optional)"
)
@app_commands.choices(skill=SKILL_CHOICES)
async def group_check_cmd(
    interaction: discord.Interaction,
    skill: str,
    dc: Optional[int] = None
):
    """Request a group skill check from all party members."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return
    
    players = state.get('players', [])
    if not players:
        await interaction.response.send_message("No players in the campaign!", ephemeral=True)
        return
    
    # Build skill check request
    request = SkillCheckRequest(
        check_type=CheckType.SKILL,
        skill_or_ability=skill,
        dc=dc,
        is_group_check=True,
        context="group skill check"
    )
    
    # Build mentions
    player_mentions = [f"<@{pid}>" for pid in players]
    
    skill_name = skill.replace('_', ' ').title()
    dc_text = f" (DC {dc})" if dc else ""
    
    await interaction.response.send_message(
        f"📋 **Group {skill_name} Check{dc_text}**\n"
        f"Everyone in the party needs to roll!"
    )
    
    # Send button prompt
    await prompt_skill_check(interaction.channel, channel_id, request, players, player_mentions)


@bot.tree.command(name="savingthrow", description="Request a saving throw")
@app_commands.describe(
    ability="Ability for the save",
    dc="Difficulty class",
    player="Specific player (leave blank for all)"
)
@app_commands.choices(ability=ABILITY_CHOICES)
async def saving_throw_cmd(
    interaction: discord.Interaction,
    ability: str,
    dc: int,
    player: Optional[discord.Member] = None
):
    """Request a saving throw from one or all players."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
        return
    
    # Determine who should roll
    if player:
        target_ids = [str(player.id)]
        player_mentions = [f"<@{player.id}>"]
        is_group = False
    else:
        target_ids = state.get('players', [])
        player_mentions = [f"<@{pid}>" for pid in target_ids]
        is_group = len(target_ids) > 1
    
    if not target_ids:
        await interaction.response.send_message("No players to roll!", ephemeral=True)
        return
    
    # Build saving throw request
    request = SkillCheckRequest(
        check_type=CheckType.SAVING_THROW,
        skill_or_ability=ability,
        dc=dc,
        is_group_check=is_group,
        context=f"{ability.title()} saving throw"
    )
    
    ability_name = ability.title()
    
    if is_group:
        await interaction.response.send_message(
            f"⚡ **{ability_name} Saving Throw (DC {dc})**\n"
            f"Everyone make a save!"
        )
    else:
        char = load_character(str(player.id))
        char_name = char.get('name', player.display_name) if char else player.display_name
        await interaction.response.send_message(
            f"⚡ **{char_name}, make a {ability_name} Saving Throw (DC {dc})!**"
        )
    
    # Send button prompt
    await prompt_skill_check(interaction.channel, channel_id, request, target_ids, player_mentions)


@bot.tree.command(name="passivecheck", description="Check all players' passive perception against a DC")
@app_commands.describe(
    dc="The DC to beat",
    description="What's hidden (only revealed to those who notice)"
)
async def passive_check_cmd(
    interaction: discord.Interaction,
    dc: int,
    description: str
):
    """DM tool: Check passive perception for all players."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get("campaign_title"):
        await interaction.response.send_message("No campaign running.", ephemeral=True)
        return
    
    players = state.get('players', [])
    if not players:
        await interaction.response.send_message("No players in the campaign!", ephemeral=True)
        return
    
    # Check each player's passive perception
    notices = []
    for player_id in players:
        char = load_character(player_id)
        if not char:
            continue
        
        passive = calculate_passive_score(char, 'perception')
        if passive >= dc:
            notices.append((char.get('name', 'Someone'), player_id, passive))
    
    await interaction.response.defer()
    
    if notices:
        # Send notices
        for name, player_id, passive in notices:
            try:
                narration = await narrate_passive_notice(name, description, passive, dc)
                await interaction.channel.send(narration)
            except Exception as e:
                print(f"Passive notice error: {e}")
                await interaction.channel.send(f"👁️ **{name}** notices {description}.")
        
        await interaction.followup.send(
            f"*{len(notices)} player(s) noticed something (DC {dc})*",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"*No one noticed (DC {dc}). Highest passive: {max([calculate_passive_score(load_character(pid), 'perception') for pid in players if load_character(pid)])}*",
            ephemeral=True
        )


# =============================================================================
# COMBAT COMMANDS
# =============================================================================

@bot.tree.command(name="fight", description="Start combat with enemies")
@app_commands.describe(enemies="Enemies: 'goblin goblin orc' OR 'goblin:15:13 orc:25:14' (name:hp:ac)")
async def fight_start(interaction: discord.Interaction, enemies: str):
    """Start a combat encounter."""
    channel_id = str(interaction.channel.id)
    
    # Parse enemies - support both formats:
    # 1. Simple: "goblin goblin orc" (uses database stats)
    # 2. Custom: "goblin:15:13 orc:25:14" (manual stats)
    enemy_list = []
    
    for enemy in enemies.split():
        parts = enemy.split(':')
        if len(parts) >= 3:
            # Custom format: name:hp:ac
            try:
                enemy_list.append({
                    'name': parts[0].title(),
                    'hp': int(parts[1]),
                    'ac': int(parts[2])
                })
            except ValueError:
                continue
        else:
            # Simple format: just the name - use database or defaults
            enemy_name = parts[0].strip()
            if not enemy_name:
                continue
            
            # Parse count (e.g., "goblin*3" = 3 goblins)
            count = 1
            if '*' in enemy_name:
                name_parts = enemy_name.split('*')
                enemy_name = name_parts[0]
                try:
                    count = int(name_parts[1])
                except:
                    count = 1
            
            # Build enemy specs and use database lookup
            from utils.combat_trigger import EnemySpec, build_enemy_list
            specs = [EnemySpec(name=enemy_name, count=count)]
            built_enemies = build_enemy_list(specs)
            enemy_list.extend(built_enemies)
    
    if not enemy_list:
        await interaction.response.send_message(
            "**Format Options:**\n"
            "• **Simple:** `/fight goblin goblin orc` *(uses D&D 5e stats)*\n"
            "• **Multiple:** `/fight goblin*3 orc*2` *(3 goblins, 2 orcs)*\n"
            "• **Custom:** `/fight goblin:15:13 orc:25:14` *(name:hp:ac)*\n\n"
            "Known monsters: Goblin, Orc, Skeleton, Zombie, Kobold, Hobgoblin, Bugbear, etc.",
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
    
    # Reset all reactions at combat start
    reset_all_reactions_new_round(channel_id)
    
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
        f"🎯 **{first['name']}**, you're up! Use `/attack` or `/do` for your action.\n"
        f"⏰ *Turn timer: {CombatFlowConfig.TURN_TIMEOUT_SECONDS} seconds*"
    )
    
    await interaction.response.send_message(msg)
    log_message(channel_id, "DM", f"Combat started: {enemy_names}")
    
    # Set up timer callbacks for this channel
    await setup_timer_callbacks(channel_id, interaction.channel)
    
    # If first combatant is a player, start their turn timer
    if first.get('type') == 'player' and first.get('id'):
        await combat_timer.start_turn_timer(
            channel_id,
            first['name'],
            first['id']
        )
    
    await play_tts(interaction, f"Roll for initiative! {first['name']}, you're up first!", "Narrator")


@bot.tree.command(name="attack", description="Attack a target")
@app_commands.describe(target="Target name", bonus="Attack bonus (e.g., 5)", damage="Damage dice (e.g., 1d8+3)")
async def attack_cmd(interaction: discord.Interaction, target: str, bonus: int, damage: str):
    """Make an attack roll against a target."""
    channel_id = str(interaction.channel.id)
    char = load_character(str(interaction.user.id))
    char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
    
    # Player took action - cancel their turn timer
    await combat_timer.cancel_timer(channel_id)
    
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
        
        # Check for combat end after a kill
        end_check = check_combat_end(channel_id)
        if end_check.should_end and end_check.reason == CombatEndReason.VICTORY:
            msg += f"\n\n🎉 **Victory!** All enemies have been defeated! Use `/endcombat` to collect rewards."
    
    await interaction.response.send_message(msg)
    log_message(channel_id, char_name, msg)
    
    # Check for legendary action opportunities after player attacks
    combat_state = load_combat(channel_id)
    if combat_state:
        await check_legendary_actions(interaction, channel_id, combat_state)


@bot.tree.command(name="combatinfo", description="Show current combat status")
async def combat_info(interaction: discord.Interaction):
    """Display combat status and turn order."""
    channel_id = str(interaction.channel.id)
    status = get_combat_status(channel_id)
    
    if not status:
        await interaction.response.send_message("No active combat.", ephemeral=True)
        return
    
    # Build turn order display with enhanced status info
    turn_display = []
    for i, c in enumerate(status['turn_order']):
        hp = c.get('hp', 0)
        max_hp = c.get('max_hp', hp)
        hp_pct = hp / max_hp if max_hp > 0 else 0
        
        # Health indicator
        if hp <= 0:
            health_icon = "💀"
        elif hp_pct <= 0.25:
            health_icon = "❤️"
        elif hp_pct <= 0.5:
            health_icon = "💛"
        else:
            health_icon = "💚"
        
        indicator = "▶️ " if i == status['current_index'] else "   "
        status_str = f" [{', '.join(c['status'])}]" if c.get('status') else ""
        
        # Type indicator
        type_icon = "👤" if c.get('type') == 'player' else "👹"
        
        turn_display.append(
            f"{indicator}{type_icon} **{c['name']}** - {health_icon} {hp}/{max_hp}{status_str}"
        )
    
    current = status['current_combatant']
    
    # Timer info
    remaining = combat_timer.get_remaining_time(channel_id)
    timer_str = f"\n⏰ Time remaining: **{remaining}s**" if remaining else ""
    
    output = (
        f"⚔️ **COMBAT** - Round {status['round']}\n"
        f"───────────────────────\n"
        + "\n".join(turn_display) + "\n"
        f"───────────────────────\n"
        f"Current turn: **{current['name']}**{timer_str}"
    )
    
    await interaction.response.send_message(output)


@bot.tree.command(name="nextturn", description="Advance to next combatant's turn")
async def next_turn_cmd(interaction: discord.Interaction):
    """Move to the next turn in combat, auto-executing enemy turns."""
    channel_id = str(interaction.channel.id)
    
    # Cancel any active turn timer (player took action before timeout)
    await combat_timer.cancel_timer(channel_id)
    
    # Check for lair actions at initiative 20 (start of round)
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        await interaction.response.send_message("No active combat.", ephemeral=True)
        return
    
    # Process end-of-turn effects for the current combatant
    current_turn_idx = combat.get('current_turn', 0)
    turn_order = combat.get('turn_order', [])
    if turn_order:
        current_combatant = turn_order[current_turn_idx]
        end_of_turn_result = process_end_of_turn_effects(channel_id, current_combatant)
        if end_of_turn_result.narration:
            await interaction.channel.send(f"📋 {end_of_turn_result.narration}")
    
    # Check if we're at the end of the round (about to loop back)
    if current_turn_idx == len(turn_order) - 1:
        round_result = process_round_transition(channel_id)
        if round_result.get('effects'):
            effect_lines = [f"📋 {e['effect']}" for e in round_result['effects']]
            if effect_lines:
                await interaction.channel.send("\n".join(effect_lines))
    
    # Check for lair actions at initiative 20 (start of round)
    combat = load_combat(channel_id)  # Reload after potential updates
    if combat and combat.get('lair_actions') and combat.get('current_turn', 0) == 0:
        if not combat.get('lair_action_used_this_round'):
            await process_and_send_lair_action(interaction, channel_id, combat)
    
    state = next_turn(channel_id)
    
    if not state:
        await interaction.response.send_message("No active combat.", ephemeral=True)
        return
    
    current = state['turn_order'][state['current_turn']]
    
    # Process start-of-turn effects
    start_result = process_start_of_turn_effects(channel_id, current)
    if start_result.narration:
        await interaction.channel.send(f"📋 {start_result.narration}")
    
    # Reset reactions for the combatant whose turn just started
    reset_reactions(channel_id, current['name'])
    
    # Reset legendary actions if this is a legendary creature's turn
    if current.get('legendary_actions'):
        reset_legendary_actions(channel_id, current['name'])
    
    # Check for combat end before continuing
    end_check = check_combat_end(channel_id)
    if end_check.should_end:
        await interaction.response.send_message(end_check.summary)
        if end_check.reason == CombatEndReason.VICTORY:
            await interaction.followup.send("Use `/endcombat` to collect rewards and end the encounter.")
        return
    
    # Check if it's an enemy's turn - auto-execute!
    if current.get('type') == 'enemy':
        await interaction.response.defer()
        await execute_and_narrate_enemy_turn(interaction, channel_id, current, state)
    else:
        # Player turn - use enhanced turn announcement
        announcement = build_turn_announcement(channel_id, current)
        
        await interaction.response.send_message(
            announcement['message'] + f"\n⏰ *Timer: {CombatFlowConfig.TURN_TIMEOUT_SECONDS}s*"
        )
        
        # Start turn timer for this player
        if current.get('id'):
            await setup_timer_callbacks(channel_id, interaction.channel)
            await combat_timer.start_turn_timer(
                channel_id,
                current['name'],
                current['id']
            )
        
        await play_tts(interaction, announcement['tts_text'], "Narrator")


async def execute_and_narrate_enemy_turn(interaction: discord.Interaction, 
                                          channel_id: str, enemy: dict, 
                                          combat_state: dict):
    """Execute an enemy's turn and narrate the results."""
    # Execute the enemy AI
    turn_result = execute_enemy_turn(channel_id, enemy, combat_state)
    
    # Apply damage to targets
    for action in turn_result.get('actions', []):
        if action.get('type') == 'attack' and action.get('hit'):
            target_name = action.get('target')
            damage = action.get('damage', 0)
            damage_type = action.get('damage_type', 'bludgeoning')
            if target_name and damage > 0:
                damage_combatant(channel_id, target_name, damage, damage_type)
    
    # Generate AI narration
    try:
        narration = await narrate_enemy_action(turn_result, combat_state)
    except Exception as e:
        print(f"Narration error: {e}")
        # Fallback narration from the turn result
        narration = " ".join([a.get('description', '') for a in turn_result.get('actions', [])])
        if not narration:
            narration = f"{enemy['name']} takes their turn."
    
    # Build the combat message
    lines = [f"⚔️ **{enemy['name']}'s Turn**"]
    lines.append("───────────────────────")
    
    # Movement
    movement = turn_result.get('movement', {})
    if movement.get('description'):
        lines.append(f"🏃 {movement['description']}")
    
    # Actions
    for action in turn_result.get('actions', []):
        if action.get('type') == 'attack':
            if action.get('fumble'):
                lines.append(f"💀 **Critical Miss!** {action.get('description', '')}")
            elif action.get('crit'):
                lines.append(f"🌟 **CRITICAL HIT!** {action.get('description', '')}")
            elif action.get('hit'):
                lines.append(f"⚔️ {action.get('description', '')}")
            else:
                lines.append(f"❌ {action.get('description', '')}")
        elif action.get('type') == 'ability':
            lines.append(f"✨ {action.get('description', '')}")
        elif action.get('type') == 'flee':
            lines.append(f"💨 {action.get('description', '')}")
        elif action.get('type') == 'dodge':
            lines.append(f"🛡️ {action.get('description', '')}")
    
    # Summary
    if turn_result.get('damage_dealt', 0) > 0:
        lines.append(f"💥 Total damage: **{turn_result['damage_dealt']}**")
    
    lines.append("───────────────────────")
    
    # AI Narration
    lines.append(f"*{narration}*")
    
    # Show updated combat state
    updated_combat = load_combat(channel_id)
    if updated_combat:
        wounded = []
        for c in updated_combat.get('combatants', []):
            if c.get('type') == 'player':
                hp = c.get('hp', 0)
                max_hp = c.get('max_hp', 1)
                if hp <= 0:
                    wounded.append(f"💀 {c['name']} is DOWN!")
                elif hp < max_hp * 0.25:
                    wounded.append(f"⚠️ {c['name']}: {hp}/{max_hp} HP")
        if wounded:
            lines.append("")
            lines.extend(wounded)
    
    await interaction.followup.send("\n".join(lines))
    
    # Play TTS with enemy voice
    voice_tag = extract_voice_tag(narration) if '[Voice:' in narration else enemy['name']
    tts_text = clean_for_tts(narration)
    await play_tts(interaction, tts_text, voice_tag)
    
    log_message(channel_id, enemy['name'], narration)
    
    # Check if combat should end using the new combat flow system
    end_check = check_combat_end(channel_id)
    if end_check.should_end:
        await interaction.followup.send(end_check.summary)
        if end_check.reason == CombatEndReason.VICTORY:
            await interaction.followup.send("Use `/endcombat` to collect rewards and end the encounter.")
        return
    
    # Auto-advance to next turn
    await asyncio.sleep(CombatFlowConfig.DELAY_BETWEEN_ENEMY_TURNS)  # Configurable pause for readability
    
    next_state = next_turn(channel_id)
    if next_state:
        next_combatant = next_state['turn_order'][next_state['current_turn']]
        
        # Process start-of-turn effects for next combatant
        start_result = process_start_of_turn_effects(channel_id, next_combatant)
        if start_result.narration:
            await interaction.followup.send(f"📋 {start_result.narration}")
        
        if next_combatant.get('type') == 'enemy':
            # Another enemy - recursively execute their turn
            await execute_and_narrate_enemy_turn(interaction, channel_id, next_combatant, next_state)
        else:
            # Player's turn - use enhanced turn announcement
            announcement = build_turn_announcement(channel_id, next_combatant)
            
            # Check for legendary actions from enemies before player acts
            await check_legendary_actions(interaction, channel_id, next_state)
            
            await interaction.followup.send(
                announcement['message'] + f"\n⏰ *Timer: {CombatFlowConfig.TURN_TIMEOUT_SECONDS}s*"
            )
            
            # Start turn timer for this player
            if next_combatant.get('id'):
                await setup_timer_callbacks(channel_id, interaction.channel)
                await combat_timer.start_turn_timer(
                    channel_id,
                    next_combatant['name'],
                    next_combatant['id']
                )
            
            await play_tts(interaction, announcement['tts_text'], "Narrator")


async def check_legendary_actions(interaction: discord.Interaction, 
                                   channel_id: str, combat_state: dict):
    """Check if any legendary creatures should use legendary actions."""
    for combatant in combat_state.get('combatants', []):
        if combatant.get('type') != 'enemy':
            continue
        
        legendary_remaining = combatant.get('legendary_actions_remaining', 0)
        legendary_actions = combatant.get('legendary_actions', [])
        
        if legendary_remaining > 0 and legendary_actions:
            if should_use_legendary_action(combatant, combat_state):
                selected = select_legendary_action(combatant, combat_state)
                if selected:
                    await execute_legendary_action(interaction, channel_id, 
                                                   combatant, selected, combat_state)


async def execute_legendary_action(interaction: discord.Interaction,
                                    channel_id: str, enemy: dict, 
                                    action: dict, combat_state: dict):
    """Execute and narrate a legendary action."""
    result = use_legendary_action(channel_id, enemy['name'], 
                                   enemy.get('legendary_actions', []).index(action) 
                                   if action in enemy.get('legendary_actions', []) else 0)
    
    if result and not result.get('error'):
        # Generate narration
        try:
            narration = await narrate_legendary_action(
                enemy['name'], action, result.get('remaining', 0), combat_state
            )
        except:
            narration = f"**{enemy['name']}** uses **{action.get('name', 'a legendary action')}**!"
        
        await interaction.followup.send(
            f"⚡ **LEGENDARY ACTION!**\n"
            f"{narration}\n"
            f"*({result.get('remaining', 0)} legendary actions remaining)*"
        )
        
        # TTS
        tts_text = clean_for_tts(narration)
        await play_tts(interaction, tts_text, enemy['name'])


async def process_and_send_lair_action(interaction: discord.Interaction,
                                        channel_id: str, combat_state: dict):
    """Process and narrate a lair action at initiative 20."""
    lair_result = process_lair_actions(channel_id, combat_state)
    
    if lair_result:
        # Mark as used
        combat_state['lair_action_used_this_round'] = True
        save_combat(channel_id, combat_state)
        
        # Generate narration
        try:
            narration = await narrate_lair_action(lair_result, combat_state)
        except:
            narration = f"[Voice: Narrator] {lair_result.get('description', 'The lair shifts ominously...')}"
        
        await interaction.channel.send(
            f"🏰 **LAIR ACTION** (Initiative 20)\n"
            f"───────────────────────\n"
            f"{narration}"
        )
        
        # TTS
        tts_text = clean_for_tts(narration)
        await play_tts(interaction, tts_text, "Narrator")


@bot.tree.command(name="endcombat", description="End the current combat")
async def end_combat_cmd(interaction: discord.Interaction):
    """End the combat encounter and award XP."""
    channel_id = str(interaction.channel.id)
    
    # Cancel any active turn timer
    await combat_timer.cancel_timer(channel_id)
    
    # Get combat info before ending
    combat = load_combat(channel_id)
    if not combat:
        await interaction.response.send_message("No active combat to end.", ephemeral=True)
        return
    
    # Get the combat end status
    end_check = check_combat_end(channel_id)
    
    # Get players for post-combat processing
    state = load_state(channel_id)
    players = state.get('players', [])
    
    # Process post-combat (XP, loot, level-ups)
    post_combat_result = process_post_combat(channel_id, players, end_check)
    
    # End the combat
    end_combat(channel_id)
    
    # Restore free-form mode
    state['in_combat'] = False
    state['free_form'] = True
    save_state(channel_id, state)
    
    # Clean up channel reference
    if channel_id in _active_channels:
        del _active_channels[channel_id]
    
    # Build response message
    lines = ["⚔️ **Combat has ended!**"]
    
    if post_combat_result.summary_lines:
        lines.extend(post_combat_result.summary_lines)
    
    if post_combat_result.loot:
        lines.append("")
        lines.append(format_loot_display(post_combat_result.loot))
    
    lines.append("")
    lines.append("🎭 Back to free-form exploration. Anyone can `/do` actions.")
    
    await interaction.response.send_message("\n".join(lines))
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
# ATTUNEMENT & ENCUMBRANCE COMMANDS
# =============================================================================

@bot.tree.command(name="attune", description="Attune to a magic item (requires short rest)")
@app_commands.describe(item="Name of the magic item to attune to")
async def attune_cmd(interaction: discord.Interaction, item: str):
    """Attune to a magic item from your inventory."""
    from utils.inventory_manager import attune_item, get_attunement_slots
    
    user_id = str(interaction.user.id)
    success, message = attune_item(user_id, item)
    await interaction.response.send_message(message)


@bot.tree.command(name="unattune", description="End attunement to a magic item")
@app_commands.describe(item="Name of the magic item to unattune from")
async def unattune_cmd(interaction: discord.Interaction, item: str):
    """End attunement to a magic item."""
    from utils.inventory_manager import unattune_item
    
    user_id = str(interaction.user.id)
    success, message = unattune_item(user_id, item)
    await interaction.response.send_message(message)


@bot.tree.command(name="attunement", description="View your attunement slots")
async def attunement_cmd(interaction: discord.Interaction):
    """View currently attuned items."""
    from utils.inventory_manager import get_attunement_slots
    
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    slots = get_attunement_slots(user_id)
    char_name = char.get('name', 'Character')
    
    lines = [f"✨ **{char_name}'s Attunement** ({slots['slots_used']}/{slots['slots_max']} slots)"]
    
    if slots['items']:
        for item in slots['items']:
            lines.append(f"  🔮 {item}")
    else:
        lines.append("  *No items attuned*")
    
    slots_free = slots['slots_max'] - slots['slots_used']
    if slots_free > 0:
        lines.append(f"\n*{slots_free} slot{'s' if slots_free != 1 else ''} available*")
    
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="encumbrance", description="Check your carrying capacity")
async def encumbrance_cmd(interaction: discord.Interaction):
    """View your encumbrance status."""
    from utils.inventory_manager import format_encumbrance_status
    
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    status = format_encumbrance_status(user_id)
    await interaction.response.send_message(status)


@bot.tree.command(name="identify", description="Attempt to identify a magic item")
@app_commands.describe(
    item="The unidentified item to identify",
    method="How to identify: arcana (DC 15 check), identify (spell), or rest (short rest)"
)
@app_commands.choices(method=[
    app_commands.Choice(name="Arcana Check (DC 15)", value="arcana"),
    app_commands.Choice(name="Identify Spell", value="identify"),
    app_commands.Choice(name="Short Rest with Item", value="short_rest"),
])
async def identify_cmd(
    interaction: discord.Interaction, 
    item: str,
    method: str = "arcana"
):
    """Attempt to identify a magic item."""
    from utils.inventory_manager import identify_item
    
    user_id = str(interaction.user.id)
    
    if method == "arcana":
        await interaction.response.send_message(
            f"🔍 **Examining {item}...**\n"
            f"Roll an Arcana check (DC 15) using `/roll arcana` to identify this item.\n"
            f"On success, use `/identify {item} method:identify` to reveal the item."
        )
        return
    
    success, message, item_data = identify_item(user_id, item, method)
    await interaction.response.send_message(message)


# =============================================================================
# LOOT DISTRIBUTION COMMANDS
# =============================================================================

@bot.tree.command(name="lootpile", description="View unclaimed loot")
async def lootpile_cmd(interaction: discord.Interaction):
    """View the current loot pile available to claim."""
    from utils.inventory_manager import format_pending_loot
    
    channel_id = str(interaction.channel_id)
    display = format_pending_loot(channel_id)
    await interaction.response.send_message(display)


@bot.tree.command(name="claimloot", description="Claim an item from the loot pile")
@app_commands.describe(item="Name of the item to claim")
async def claimloot_cmd(interaction: discord.Interaction, item: str):
    """Claim an item from pending loot."""
    from utils.inventory_manager import claim_loot_item
    
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)
    
    success, message = claim_loot_item(channel_id, user_id, item)
    await interaction.response.send_message(message)


@bot.tree.command(name="claimgold", description="Claim gold from the loot pile")
@app_commands.describe(amount="Amount of gold to claim (leave empty for all)")
async def claimgold_cmd(interaction: discord.Interaction, amount: Optional[int] = None):
    """Claim gold from pending loot."""
    from utils.inventory_manager import claim_loot_gold
    
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)
    
    success, message = claim_loot_gold(channel_id, user_id, amount)
    await interaction.response.send_message(message)


@bot.tree.command(name="splitgold", description="Split loot gold evenly among party")
async def splitgold_cmd(interaction: discord.Interaction):
    """Split loot pile gold evenly among all registered characters."""
    from utils.inventory_manager import get_pending_loot, clear_pending_loot
    from utils.state_manager import load_state
    
    channel_id = str(interaction.channel_id)
    loot = get_pending_loot(channel_id)
    
    if not loot:
        await interaction.response.send_message("No pending loot to split.", ephemeral=True)
        return
    
    total_gp = loot.currency.get("gp", 0)
    if total_gp <= 0:
        await interaction.response.send_message("No gold in the loot pile.", ephemeral=True)
        return
    
    state = load_state(channel_id)
    players = state.get("players", [])
    
    if not players:
        await interaction.response.send_message("No players registered.", ephemeral=True)
        return
    
    share = total_gp // len(players)
    remainder = total_gp % len(players)
    
    lines = [f"💰 **Gold Split:** {total_gp} gp ÷ {len(players)} = {share} gp each"]
    
    for pid in players:
        char = load_character(pid)
        if char:
            char["gold"] = char.get("gold", 0) + share
            save_character(pid, char)
            lines.append(f"  {char.get('name', 'Unknown')}: +{share} gp")
    
    if remainder > 0:
        lines.append(f"\n*{remainder} gp remainder left in pile*")
        loot.currency["gp"] = remainder
    else:
        loot.currency["gp"] = 0
    
    await interaction.response.send_message("\n".join(lines))


# =============================================================================
# SPELL COMMANDS
# =============================================================================

@bot.tree.command(name="spells", description="View your known and prepared spells")
async def spells_cmd(interaction: discord.Interaction):
    """Display your character's spells and spell slots."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    spells = get_available_spells(user_id)
    slots = get_spell_slots_remaining(user_id)
    
    output = f"# ✨ {char_name}'s Spellbook\n\n"
    
    # Show cantrips
    cantrips = spells.get('cantrips', [])
    if cantrips:
        output += f"**Cantrips:** {', '.join(cantrips)}\n\n"
    
    # Show spell slots
    if slots:
        slot_display = []
        for level, info in sorted(slots.items(), key=lambda x: int(x[0])):
            remaining = info['remaining']
            total = info['total']
            # Use filled/empty circles to show slots
            filled = '●' * remaining
            empty = '○' * (total - remaining)
            slot_display.append(f"**Level {level}:** {filled}{empty} ({remaining}/{total})")
        output += "**Spell Slots:**\n" + "\n".join(slot_display) + "\n\n"
    
    # Show prepared spells
    prepared = spells.get('prepared', [])
    if prepared:
        output += f"**Prepared Spells:** {', '.join(prepared)}\n\n"
    elif not cantrips and not slots:
        output += "*No spellcasting ability*\n"
    
    # Show known spells (for classes that learn spells like Bard, Sorcerer)
    known = spells.get('known', [])
    if known:
        # Group by level if we have spell data
        output += f"**Known Spells:** {', '.join(known)}\n"
    
    await interaction.response.send_message(output)


@bot.tree.command(name="cast", description="Cast a spell")
@app_commands.describe(
    spell="Name of the spell to cast",
    slot_level="Spell slot level to use (for upcasting)"
)
async def cast_cmd(
    interaction: discord.Interaction,
    spell: str,
    slot_level: Optional[int] = None
):
    """Cast a spell, consuming a spell slot."""
    user_id = str(interaction.user.id)
    channel_id = str(interaction.channel.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    # Player took action - cancel their turn timer
    await combat_timer.cancel_timer(channel_id)
    
    char_name = char.get('name', 'Character')
    
    success, message, spell_data = cast_spell(user_id, spell, slot_level)
    
    if not success:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)
        return
    
    # Build casting message
    output = f"✨ **{char_name}** casts **{spell}**!"
    
    if spell_data:
        desc = spell_data.get('description', '')
        if desc:
            output += f"\n*{desc}*"
        if spell_data.get('concentration'):
            output += "\n⚡ *Concentration required*"
    
    # Show remaining slots
    slots = get_spell_slots_remaining(user_id)
    if slots and slot_level:
        slot_key = str(slot_level)
        if slot_key in slots:
            remaining = slots[slot_key]['remaining']
            total = slots[slot_key]['total']
            output += f"\n(Level {slot_level} slots: {remaining}/{total})"
    
    await interaction.response.send_message(output)
    log_message(channel_id, char_name, f"Cast {spell}")
    
    # Check for legendary action opportunities after player casts
    combat_state = load_combat(channel_id)
    if combat_state:
        await check_legendary_actions(interaction, channel_id, combat_state)


@bot.tree.command(name="resources", description="View your character's resources (spell slots, class abilities, consumables)")
async def resources_cmd(interaction: discord.Interaction):
    """Display your character's current resource status."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    status = format_resource_status(user_id)
    
    output = f"# 📊 {char_name}'s Resources\n\n{status}"
    await interaction.response.send_message(output)


@bot.tree.command(name="prepare", description="Prepare or unprepare a spell")
@app_commands.describe(
    spell="Name of the spell",
    remove="Remove spell from prepared list instead of adding"
)
async def prepare_cmd(
    interaction: discord.Interaction,
    spell: str,
    remove: bool = False
):
    """Prepare or unprepare a spell for casting."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    
    if remove:
        result, message = unprepare_spell(user_id, spell)
        if result:
            await interaction.response.send_message(f"📖 **{char_name}** unprepared **{spell}**")
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
    else:
        result, message = prepare_spell(user_id, spell)
        if result:
            await interaction.response.send_message(f"📖 **{char_name}** prepared **{spell}**!")
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


@bot.tree.command(name="learn", description="Learn a new spell or cantrip")
@app_commands.describe(
    spell="Name of the spell to learn",
    cantrip="Set to True if learning a cantrip"
)
async def learn_cmd(
    interaction: discord.Interaction,
    spell: str,
    cantrip: bool = False
):
    """Learn a new spell or cantrip."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    
    if cantrip:
        result, message = learn_cantrip(user_id, spell)
    else:
        result, message = learn_spell(user_id, spell)
    
    if result:
        spell_type = "cantrip" if cantrip else "spell"
        await interaction.response.send_message(f"📚 **{char_name}** learned the {spell_type} **{spell}**!")
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


@bot.tree.command(name="levelup", description="Level up your character")
@app_commands.describe(
    average_hp="Use average HP instead of rolling"
)
async def levelup_cmd(
    interaction: discord.Interaction,
    average_hp: bool = False
):
    """Level up your character, gaining HP and new features."""
    user_id = str(interaction.user.id)
    char = load_character(user_id)
    
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    old_level = char.get('level', 1)
    
    result = level_up(user_id, roll_hp=not average_hp)
    
    if not result:
        await interaction.response.send_message("❌ Could not level up", ephemeral=True)
        return
    
    new_level = result['data']['level']
    hp_gained = result['hp_gained']
    new_features = result['new_features']
    
    output = (
        f"🎉 **{char_name}** leveled up!\n"
        f"───────────────────────\n"
        f"**Level:** {old_level} → {new_level}\n"
        f"**HP:** +{hp_gained} (now {result['data']['hp']}/{result['data']['max_hp']})\n"
        f"**Proficiency Bonus:** +{result['data']['proficiency']}\n"
    )
    
    if new_features:
        output += f"\n**New Features:**\n" + "\n".join(f"• {f}" for f in new_features)
    
    # Check for new spell slots
    char = load_character(user_id)
    slots = get_spell_slots_remaining(user_id)
    if slots:
        slot_info = []
        for level, info in sorted(slots.items(), key=lambda x: int(x[0])):
            slot_info.append(f"Level {level}: {info['total']}")
        if slot_info:
            output += f"\n\n**Spell Slots:** {', '.join(slot_info)}"
    
    await interaction.response.send_message(output)


# =============================================================================
# HANDOUT COMMANDS (DM Tools)
# =============================================================================

HANDOUT_TYPE_CHOICES = [
    app_commands.Choice(name="📝 Note", value="note"),
    app_commands.Choice(name="✉️ Letter", value="letter"),
    app_commands.Choice(name="🗺️ Map", value="map"),
    app_commands.Choice(name="🖼️ Image", value="image"),
    app_commands.Choice(name="📦 Item Description", value="item"),
    app_commands.Choice(name="📚 Lore", value="lore"),
    app_commands.Choice(name="🔍 Clue", value="clue"),
    app_commands.Choice(name="📖 Journal Entry", value="journal"),
]

@bot.tree.command(name="handout", description="Create a handout to share with players")
@app_commands.describe(
    title="Title of the handout",
    content="Text content of the handout",
    handout_type="Type of handout",
    image_url="URL to an image (optional)",
    player="Share only with this player (optional, leave blank for all)"
)
@app_commands.choices(handout_type=HANDOUT_TYPE_CHOICES)
async def handout_cmd(
    interaction: discord.Interaction,
    title: str,
    content: str,
    handout_type: str = "note",
    image_url: Optional[str] = None,
    player: Optional[discord.Member] = None
):
    """Create and share a handout with players."""
    channel_id = str(interaction.channel.id)
    
    # Determine visibility
    visible_to = [str(player.id)] if player else None
    
    handout = create_handout(
        channel_id=channel_id,
        title=title,
        content=content,
        handout_type=handout_type,
        image_url=image_url,
        visible_to=visible_to,
        created_by=str(interaction.user.id)
    )
    
    emoji = get_handout_emoji(handout_type)
    
    if player:
        # Private handout - send to DM and notify player
        await interaction.response.send_message(
            f"{emoji} **Handout created for {player.display_name}:**\n"
            f"*{title}*\n\n"
            f"They can view it with `/viewhandouts`",
            ephemeral=True
        )
        
        # DM the player about the new handout
        try:
            await player.send(
                f"{emoji} **New Handout: {title}**\n"
                f"───────────────────────\n"
                f"{content}\n"
                + (f"\n🖼️ {image_url}" if image_url else "")
            )
        except:
            # Can't DM player, they'll see it with /viewhandouts
            pass
    else:
        # Public handout - share with everyone
        output = (
            f"{emoji} **{title}**\n"
            f"───────────────────────\n"
            f"{content}"
        )
        if image_url:
            output += f"\n\n🖼️ {image_url}"
        
        await interaction.response.send_message(output)


@bot.tree.command(name="secret", description="Send a secret message to a specific player")
@app_commands.describe(
    player="The player to receive the secret",
    message="The secret message (only they will see it)",
    title="Optional title for the secret"
)
async def secret_cmd(
    interaction: discord.Interaction,
    player: discord.Member,
    message: str,
    title: Optional[str] = None
):
    """Send a secret message only visible to one player."""
    channel_id = str(interaction.channel.id)
    player_id = str(player.id)
    
    # Add the secret
    secret = add_player_secret(channel_id, player_id, message, title)
    
    # Confirm to DM
    await interaction.response.send_message(
        f"🤫 Secret sent to **{player.display_name}**:\n"
        f"*\"{message[:50]}{'...' if len(message) > 50 else ''}\"*",
        ephemeral=True
    )
    
    # Try to DM the player
    try:
        char = load_character(player_id)
        char_name = char.get('name', player.display_name) if char else player.display_name
        
        await player.send(
            f"🤫 **Secret for {char_name}:**\n"
            f"───────────────────────\n"
            f"{message}\n\n"
            f"*Only you can see this message.*"
        )
    except:
        # Can't DM, they'll see it with /mysecrets
        pass


@bot.tree.command(name="viewhandouts", description="View handouts shared with you")
async def viewhandouts_cmd(interaction: discord.Interaction):
    """View all handouts visible to you."""
    channel_id = str(interaction.channel.id)
    player_id = str(interaction.user.id)
    
    handouts = get_handouts_for_player(channel_id, player_id)
    
    if not handouts:
        await interaction.response.send_message(
            "📜 No handouts available yet.\n"
            "*The DM can create handouts with `/handout`*",
            ephemeral=True
        )
        return
    
    # Mark all as read
    for h in handouts:
        mark_as_read(channel_id, h["id"], player_id)
    
    # Format handout list
    output = "# 📜 Your Handouts\n\n"
    
    for handout in handouts:
        emoji = get_handout_emoji(handout["type"])
        output += f"{emoji} **{handout['title']}** (ID: {handout['id']})\n"
        # Show preview of content
        preview = handout["content"][:100]
        if len(handout["content"]) > 100:
            preview += "..."
        output += f"*{preview}*\n\n"
    
    output += "*Use `/readhandout <id>` to view the full handout*"
    
    await interaction.response.send_message(output, ephemeral=True)


@bot.tree.command(name="readhandout", description="Read a specific handout")
@app_commands.describe(handout_id="The ID of the handout to read")
async def readhandout_cmd(interaction: discord.Interaction, handout_id: int):
    """Read the full content of a specific handout."""
    channel_id = str(interaction.channel.id)
    player_id = str(interaction.user.id)
    
    # Get handouts visible to this player
    visible_handouts = get_handouts_for_player(channel_id, player_id)
    handout = None
    
    for h in visible_handouts:
        if h["id"] == handout_id:
            handout = h
            break
    
    if not handout:
        await interaction.response.send_message(
            "❌ Handout not found or you don't have access to it.",
            ephemeral=True
        )
        return
    
    # Mark as read
    mark_as_read(channel_id, handout_id, player_id)
    
    # Format and display
    output = format_handout_display(handout)
    
    if handout.get("image_url"):
        output += f"\n\n🖼️ {handout['image_url']}"
    
    await interaction.response.send_message(output, ephemeral=True)


@bot.tree.command(name="mysecrets", description="View secrets shared with you")
async def mysecrets_cmd(interaction: discord.Interaction):
    """View all secret messages sent to you."""
    channel_id = str(interaction.channel.id)
    player_id = str(interaction.user.id)
    
    secrets = get_player_secrets(channel_id, player_id)
    
    if not secrets:
        await interaction.response.send_message(
            "🤫 No secrets for you... yet.\n"
            "*The DM may share secrets with you during the game.*",
            ephemeral=True
        )
        return
    
    # Mark all as read
    for s in secrets:
        mark_secret_read(channel_id, player_id, s["id"])
    
    output = "# 🤫 Your Secrets\n\n"
    
    for secret in secrets:
        title = secret.get("title", "Secret")
        output += f"**{title}:**\n"
        output += f"*{secret['content']}*\n\n"
    
    output += "*Only you can see these messages.*"
    
    await interaction.response.send_message(output, ephemeral=True)


@bot.tree.command(name="dmhandouts", description="[DM] View all handouts in this campaign")
async def dmhandouts_cmd(interaction: discord.Interaction):
    """View all handouts (DM only view with visibility info)."""
    channel_id = str(interaction.channel.id)
    
    handouts = get_all_handouts(channel_id)
    
    if not handouts:
        await interaction.response.send_message(
            "📜 No handouts created yet.\n"
            "Use `/handout` to create one!",
            ephemeral=True
        )
        return
    
    output = "# 📜 All Campaign Handouts\n\n"
    
    for handout in handouts:
        emoji = get_handout_emoji(handout["type"])
        
        # Visibility info
        if handout["visible_to"] is None:
            visibility = "👁️ Everyone"
        else:
            count = len(handout["visible_to"])
            visibility = f"🔒 {count} player(s)"
        
        # Read status
        read_count = len(handout.get("read_by", []))
        
        output += (
            f"{emoji} **{handout['title']}** (ID: {handout['id']})\n"
            f"   Type: {handout['type']} | {visibility} | Read by: {read_count}\n\n"
        )
    
    output += (
        "───────────────────────\n"
        "**Commands:**\n"
        "• `/handout` - Create new handout\n"
        "• `/revealhandout <id>` - Reveal to all players\n"
        "• `/sharehandout <id> <player>` - Share with specific player\n"
        "• `/deletehandout <id>` - Delete a handout"
    )
    
    await interaction.response.send_message(output, ephemeral=True)


@bot.tree.command(name="revealhandout", description="[DM] Reveal a handout to all players")
@app_commands.describe(handout_id="The ID of the handout to reveal")
async def revealhandout_cmd(interaction: discord.Interaction, handout_id: int):
    """Reveal a previously private handout to all players."""
    channel_id = str(interaction.channel.id)
    
    handout = reveal_handout(channel_id, handout_id)
    
    if not handout:
        await interaction.response.send_message(
            "❌ Handout not found.",
            ephemeral=True
        )
        return
    
    # Show the handout to everyone
    output = format_handout_display(handout)
    
    if handout.get("image_url"):
        output += f"\n\n🖼️ {handout['image_url']}"
    
    await interaction.response.send_message(
        f"📜 **The DM reveals a handout!**\n\n{output}"
    )


@bot.tree.command(name="sharehandout", description="[DM] Share a handout with a specific player")
@app_commands.describe(
    handout_id="The ID of the handout",
    player="The player to share with"
)
async def sharehandout_cmd(
    interaction: discord.Interaction,
    handout_id: int,
    player: discord.Member
):
    """Share a handout with a specific player."""
    channel_id = str(interaction.channel.id)
    
    handout = share_handout_with(channel_id, handout_id, [str(player.id)])
    
    if not handout:
        await interaction.response.send_message(
            "❌ Handout not found.",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(
        f"📜 Shared **{handout['title']}** with {player.display_name}",
        ephemeral=True
    )
    
    # Try to notify the player
    try:
        emoji = get_handout_emoji(handout["type"])
        await player.send(
            f"{emoji} **New Handout: {handout['title']}**\n"
            f"───────────────────────\n"
            f"{handout['content']}\n"
            + (f"\n🖼️ {handout['image_url']}" if handout.get('image_url') else "")
        )
    except:
        pass


@bot.tree.command(name="deletehandout", description="[DM] Delete a handout")
@app_commands.describe(handout_id="The ID of the handout to delete")
async def deletehandout_cmd(interaction: discord.Interaction, handout_id: int):
    """Delete a handout permanently."""
    channel_id = str(interaction.channel.id)
    
    if delete_handout(channel_id, handout_id):
        await interaction.response.send_message(
            f"🗑️ Handout #{handout_id} deleted.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Handout not found.",
            ephemeral=True
        )


# =============================================================================
# TACTICAL MAP COMMANDS
# =============================================================================

MAP_TEMPLATE_CHOICES = [
    app_commands.Choice(name="🏰 Dungeon Room", value="dungeon"),
    app_commands.Choice(name="🌲 Forest Clearing", value="forest"),
    app_commands.Choice(name="🍺 Tavern", value="tavern"),
    app_commands.Choice(name="🕳️ Cave", value="cave"),
]

@bot.tree.command(name="map", description="View the current tactical map")
async def map_cmd(interaction: discord.Interaction):
    """Display the current tactical map."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message(
            "🗺️ No map active.\n"
            "Use `/newmap` to create one!",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(map_obj.render_discord())


@bot.tree.command(name="newmap", description="Create a new tactical map")
@app_commands.describe(
    template="Map template to use",
    width="Map width in squares (5-30)",
    height="Map height in squares (5-25)",
    name="Name of the map"
)
@app_commands.choices(template=MAP_TEMPLATE_CHOICES)
async def newmap_cmd(
    interaction: discord.Interaction,
    template: str = "dungeon",
    width: int = 20,
    height: int = 15,
    name: str = "Battle Map"
):
    """Create a new tactical battle map."""
    channel_id = str(interaction.channel.id)
    
    # Clamp dimensions
    width = max(5, min(30, width))
    height = max(5, min(25, height))
    
    # Create from template
    map_obj = create_from_template(template, width=width, height=height, name=name)
    if not map_obj:
        map_obj = TacticalMap(width, height, name)
    
    save_map(channel_id, map_obj)
    
    await interaction.response.send_message(
        f"🗺️ **New map created!**\n\n{map_obj.render_discord()}"
    )


@bot.tree.command(name="addtoken", description="Add a token to the map")
@app_commands.describe(
    name="Name of the character/creature",
    x="X position (column)",
    y="Y position (row)",
    token_type="Type of token"
)
@app_commands.choices(token_type=[
    app_commands.Choice(name="🔵 Player", value="player"),
    app_commands.Choice(name="🔴 Enemy", value="enemy"),
    app_commands.Choice(name="🟢 NPC", value="npc"),
    app_commands.Choice(name="🟣 Boss", value="boss"),
    app_commands.Choice(name="⬜ Object", value="object"),
])
async def addtoken_cmd(
    interaction: discord.Interaction,
    name: str,
    x: int,
    y: int,
    token_type: str = "player"
):
    """Add a token to the tactical map."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message(
            "No map active. Use `/newmap` first!",
            ephemeral=True
        )
        return
    
    token = map_obj.add_token(name, x, y, token_type)
    if not token:
        await interaction.response.send_message(
            f"❌ Position ({x},{y}) is out of bounds!",
            ephemeral=True
        )
        return
    
    save_map(channel_id, map_obj)
    
    emoji = TOKEN_SYMBOLS.get(token_type, TOKEN_SYMBOLS["player"])["color"]
    await interaction.response.send_message(
        f"{emoji} **{name}** placed at ({x},{y})\n\n{map_obj.render_discord()}"
    )


@bot.tree.command(name="movetoken", description="Move a token on the map")
@app_commands.describe(
    name="Name of the token to move",
    x="New X position",
    y="New Y position"
)
async def movetoken_cmd(
    interaction: discord.Interaction,
    name: str,
    x: int,
    y: int
):
    """Move a token to a new position."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message(
            "No map active.",
            ephemeral=True
        )
        return
    
    old_pos = map_obj.move_token(name, x, y)
    if old_pos is None:
        await interaction.response.send_message(
            f"❌ Token '{name}' not found or position out of bounds!",
            ephemeral=True
        )
        return
    
    save_map(channel_id, map_obj)
    
    # Calculate distance moved
    distance = max(abs(x - old_pos[0]), abs(y - old_pos[1])) * map_obj.scale
    
    await interaction.response.send_message(
        f"🏃 **{name}** moved from ({old_pos[0]},{old_pos[1]}) to ({x},{y}) [{distance}ft]\n\n"
        f"{map_obj.render_discord()}"
    )


@bot.tree.command(name="removetoken", description="Remove a token from the map")
@app_commands.describe(name="Name of the token to remove")
async def removetoken_cmd(interaction: discord.Interaction, name: str):
    """Remove a token from the map."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message("No map active.", ephemeral=True)
        return
    
    if map_obj.remove_token(name):
        save_map(channel_id, map_obj)
        await interaction.response.send_message(
            f"🗑️ **{name}** removed from the map.\n\n{map_obj.render_discord()}"
        )
    else:
        await interaction.response.send_message(
            f"❌ Token '{name}' not found.",
            ephemeral=True
        )


@bot.tree.command(name="distance", description="Measure distance between two tokens")
@app_commands.describe(
    token1="First token name",
    token2="Second token name"
)
async def distance_cmd(
    interaction: discord.Interaction,
    token1: str,
    token2: str
):
    """Measure the distance between two tokens in feet."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message("No map active.", ephemeral=True)
        return
    
    distance = map_obj.get_distance(token1, token2)
    if distance is None:
        await interaction.response.send_message(
            "❌ One or both tokens not found.",
            ephemeral=True
        )
        return
    
    t1 = map_obj.get_token(token1)
    t2 = map_obj.get_token(token2)
    
    await interaction.response.send_message(
        f"📏 Distance from **{token1}** ({t1.x},{t1.y}) to **{token2}** ({t2.x},{t2.y}): **{distance} feet**"
    )


@bot.tree.command(name="inrange", description="Find all tokens within range of a target")
@app_commands.describe(
    name="Token to check from",
    range_feet="Range in feet"
)
async def inrange_cmd(
    interaction: discord.Interaction,
    name: str,
    range_feet: int = 30
):
    """Find all tokens within a certain range."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message("No map active.", ephemeral=True)
        return
    
    center = map_obj.get_token(name)
    if not center:
        await interaction.response.send_message(
            f"❌ Token '{name}' not found.",
            ephemeral=True
        )
        return
    
    in_range = map_obj.get_tokens_in_range(name, range_feet)
    
    if not in_range:
        await interaction.response.send_message(
            f"📏 No tokens within {range_feet}ft of **{name}**"
        )
        return
    
    token_list = []
    for token in in_range:
        dist = map_obj.get_distance(name, token.name)
        emoji = TOKEN_SYMBOLS.get(token.token_type, TOKEN_SYMBOLS["player"])["color"]
        token_list.append(f"{emoji} **{token.name}** - {dist}ft")
    
    await interaction.response.send_message(
        f"📏 Tokens within {range_feet}ft of **{name}**:\n" +
        "\n".join(token_list)
    )


@bot.tree.command(name="setterrain", description="Set terrain at a position")
@app_commands.describe(
    x="X position",
    y="Y position",
    terrain="Terrain type"
)
@app_commands.choices(terrain=[
    app_commands.Choice(name=". Floor", value="floor"),
    app_commands.Choice(name="# Wall", value="wall"),
    app_commands.Choice(name="~ Water", value="water"),
    app_commands.Choice(name=": Difficult Terrain", value="difficult"),
    app_commands.Choice(name="+ Door", value="door"),
    app_commands.Choice(name="X Locked Door", value="door_locked"),
    app_commands.Choice(name="O Pillar", value="pillar"),
    app_commands.Choice(name="T Tree", value="tree"),
    app_commands.Choice(name="^ Rubble", value="rubble"),
])
async def setterrain_cmd(
    interaction: discord.Interaction,
    x: int,
    y: int,
    terrain: str
):
    """Set the terrain at a specific position."""
    channel_id = str(interaction.channel.id)
    
    map_obj = load_map(channel_id)
    if not map_obj:
        await interaction.response.send_message("No map active.", ephemeral=True)
        return
    
    if map_obj.set_terrain(x, y, terrain):
        save_map(channel_id, map_obj)
        terrain_name = TERRAIN_TYPES.get(terrain, {}).get("name", terrain)
        await interaction.response.send_message(
            f"🗺️ Set ({x},{y}) to **{terrain_name}**\n\n{map_obj.render_discord()}"
        )
    else:
        await interaction.response.send_message(
            f"❌ Position ({x},{y}) is out of bounds!",
            ephemeral=True
        )


@bot.tree.command(name="clearmap", description="Delete the current map")
async def clearmap_cmd(interaction: discord.Interaction):
    """Delete the current tactical map."""
    channel_id = str(interaction.channel.id)
    
    if delete_map(channel_id):
        await interaction.response.send_message("🗑️ Map deleted.")
    else:
        await interaction.response.send_message("No map to delete.", ephemeral=True)


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


@bot.tree.command(name="turntimer", description="Configure combat turn timer")
@app_commands.describe(
    seconds="Turn timeout in seconds (30-300, or 0 to disable)",
    warning="Seconds before timeout to show warning (default: 30)"
)
async def turn_timer_cmd(
    interaction: discord.Interaction, 
    seconds: int,
    warning: Optional[int] = None
):
    """Configure the turn timer for combat encounters."""
    if seconds < 0 or seconds > 300:
        await interaction.response.send_message(
            "Timer must be between 0 and 300 seconds. Use 0 to disable.", 
            ephemeral=True
        )
        return
    
    # Update the config
    CombatFlowConfig.TURN_TIMEOUT_SECONDS = seconds
    if warning is not None:
        CombatFlowConfig.WARNING_SECONDS = min(warning, seconds - 5) if seconds > 5 else 0
    
    if seconds == 0:
        await interaction.response.send_message("⏰ **Turn timer disabled.** Players have unlimited time per turn.")
    else:
        warning_text = f" (warning at {CombatFlowConfig.WARNING_SECONDS}s)" if CombatFlowConfig.WARNING_SECONDS > 0 else ""
        await interaction.response.send_message(
            f"⏰ **Turn timer set to {seconds} seconds**{warning_text}\n"
            f"*If a player doesn't act in time, they will automatically Dodge.*"
        )


@bot.tree.command(name="timeleft", description="Check remaining time on your turn")
async def time_left_cmd(interaction: discord.Interaction):
    """Check how much time is left on the current turn."""
    channel_id = str(interaction.channel.id)
    
    remaining = combat_timer.get_remaining_time(channel_id)
    
    if remaining is None:
        await interaction.response.send_message(
            "⏰ No active turn timer.", 
            ephemeral=True
        )
        return
    
    timer_state = combat_timer.get_timer_state(channel_id)
    combatant_name = timer_state.combatant_name if timer_state else "Unknown"
    
    if remaining <= 30:
        emoji = "⚠️"
    elif remaining <= 60:
        emoji = "⏰"
    else:
        emoji = "✅"
    
    await interaction.response.send_message(
        f"{emoji} **{combatant_name}** has **{remaining} seconds** remaining.",
        ephemeral=True
    )


@bot.tree.command(name="leave", description="Disconnect bot from voice")
async def leave_voice(interaction: discord.Interaction):
    """Disconnect from voice channel."""
    if interaction.guild:
        await voice_manager.disconnect(interaction.guild.id)
        await interaction.response.send_message("👋 Left voice channel.")
    else:
        await interaction.response.send_message("Not in a server.", ephemeral=True)


@bot.tree.command(name="joinvoice", description="Join your voice channel for TTS narration")
async def join_voice(interaction: discord.Interaction):
    """Connect bot to user's voice channel."""
    if not interaction.guild:
        await interaction.response.send_message("Not in a server.", ephemeral=True)
        return
    
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        channel = interaction.user.voice.channel
        await voice_manager.get_or_create(channel)
        
        # Enable TTS for this channel
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        state["tts_enabled"] = True
        save_state(channel_id, state)
        
        await interaction.followup.send(f"🔊 Joined **{channel.name}**! Voice narration is now enabled.")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to join voice: {e}")


@bot.tree.command(name="reconnect", description="Fix voice connection issues")
async def reconnect_voice(interaction: discord.Interaction):
    """Force reconnect to voice channel."""
    if not interaction.guild:
        await interaction.response.send_message("Not in a server.", ephemeral=True)
        return
    
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        # Force disconnect first
        await voice_manager.disconnect(interaction.guild.id)
        await asyncio.sleep(1)  # Brief pause
        
        # Reconnect
        channel = interaction.user.voice.channel
        await voice_manager.get_or_create(channel)
        
        await interaction.followup.send(f"🔄 Reconnected to **{channel.name}**!")
    except Exception as e:
        await interaction.followup.send(f"❌ Reconnection failed: {e}")


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
• `/levelup` - Level up your character
• `/xp` - View or award XP

**Party & XP:**
• `/party` - View party dashboard with HP, AC, spells
• `/xp` - View your XP progress
• `/awardparty xp:500` - Award XP to all party members

**Spells & Magic:**
• `/spells` - View your spells and spell slots
• `/learn spell:Fireball` - Learn a new spell
• `/prepare spell:Shield` - Prepare a spell for casting
• `/cast spell:Magic Missile` - Cast a spell

**Combat:**
• `/fight goblin:15:13 orc:25:14` - Start combat (name:hp:ac)
• `/attack target:Goblin bonus:5 damage:1d8+3` - Attack!
• `/combatinfo` - View turn order and HP
• `/nextturn` - Advance to next combatant
• `/reaction` - Use your reaction (Shield, Counterspell, etc.)
• `/deathsave` - Roll death saving throw
• `/endcombat` - End combat (auto-awards XP!)

**Loot & Treasure:**
• `/loot` - Generate random loot by CR
• `/treasure cr:5` - Generate a treasure hoard

**Tactical Maps:**
• `/newmap` - Create a new battle map
• `/map` - View the current map
• `/addtoken` - Add character/enemy to map
• `/movetoken` - Move a token
• `/distance` - Measure distance between tokens
• `/inrange` - Find tokens in range

**Handouts & Secrets:**
• `/viewhandouts` - View handouts shared with you
• `/readhandout <id>` - Read a specific handout
• `/mysecrets` - View secret messages for you

**DM Tools:**
• `/handout` - Create a new handout
• `/secret` - Send secret to one player
• `/dmhandouts` - View all handouts

**Campaign Memory:**
• `/status` - View party info
• `/recap` - AI summary of recent events
• `/context` - See what the AI remembers
• `/summarize` - Save events to long-term memory
• `/remember` - Manually add notes/NPCs/quests

**Ambient & Voice:**
• `/voice` - Toggle TTS on/off
• `/ambient` - Set ambient music mood
• `/sfx` - Play sound effects
• `/joinvoice` - Connect bot to voice

**Settings:**
• `/turns` - Toggle free-form vs strict turns
• `/leave` - Disconnect from voice
"""
    await interaction.response.send_message(help_text)


# =============================================================================
# PARTY DASHBOARD
# =============================================================================

@bot.tree.command(name="party", description="View party status dashboard")
async def party_dashboard(interaction: discord.Interaction):
    """Display a comprehensive party status dashboard."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    if not state.get('campaign_title'):
        await interaction.response.send_message("No active campaign. Use `/campaign` to start!", ephemeral=True)
        return
    
    players = state.get('players', [])
    if not players:
        await interaction.response.send_message("No players in the party yet.", ephemeral=True)
        return
    
    # Build party display
    lines = [
        f"# 🎭 Party Dashboard",
        f"**Campaign:** {state.get('campaign_title', 'Untitled')}",
        f"**Location:** {state.get('current_location', 'Unknown')}",
        "───────────────────────",
    ]
    
    total_hp = 0
    total_max_hp = 0
    
    for pid in players:
        char = load_character(pid)
        if not char:
            lines.append(f"<@{pid}> - *No character*")
            continue
        
        name = char.get('name', 'Unknown')
        level = char.get('level', 1)
        char_class = char.get('class', 'Adventurer')
        hp = char.get('hp', 0)
        max_hp = char.get('max_hp', 10)
        ac = char.get('ac', 10)
        
        total_hp += hp
        total_max_hp += max_hp
        
        # HP bar
        hp_pct = hp / max_hp if max_hp > 0 else 0
        hp_bar_len = 10
        hp_filled = int(hp_bar_len * hp_pct)
        hp_bar = '█' * hp_filled + '░' * (hp_bar_len - hp_filled)
        
        # Status icons
        status_icons = ""
        conditions = char.get('conditions', [])
        if hp <= 0:
            status_icons += "💀 "
        elif hp <= max_hp // 4:
            status_icons += "⚠️ "
        if 'poisoned' in conditions:
            status_icons += "🤢 "
        if 'stunned' in conditions or 'paralyzed' in conditions:
            status_icons += "😵 "
        if char.get('concentration'):
            status_icons += "🔮 "
        
        # Spell slots
        spell_slots = char.get('spell_slots', {})
        spell_slots_used = char.get('spell_slots_used', {})
        slots_info = ""
        for lvl in ['1', '2', '3', '4', '5']:
            total = spell_slots.get(lvl, 0)
            used = spell_slots_used.get(lvl, 0)
            if total > 0:
                remaining = total - used
                slots_info += f"L{lvl}:{remaining}/{total} "
        
        # XP progress
        xp = char.get('xp', 0)
        xp_bar = format_xp_bar(xp, level, 8)
        
        lines.append(f"**{name}** - Level {level} {char_class}")
        lines.append(f"  ❤️ [{hp_bar}] {hp}/{max_hp} HP  |  🛡️ AC {ac}  {status_icons}")
        if slots_info:
            lines.append(f"  ✨ Slots: {slots_info.strip()}")
        lines.append(f"  📊 XP: {xp_bar}")
        if conditions:
            lines.append(f"  ⚡ Conditions: {', '.join(conditions)}")
        lines.append("")
    
    # Party summary
    party_hp_pct = total_hp / total_max_hp if total_max_hp > 0 else 0
    party_status = "💚 Healthy" if party_hp_pct > 0.5 else "💛 Injured" if party_hp_pct > 0.25 else "❤️ Critical"
    
    lines.append("───────────────────────")
    lines.append(f"**Party Status:** {party_status} ({total_hp}/{total_max_hp} total HP)")
    
    # Combat status
    combat = load_combat(channel_id)
    if combat and combat.get('active'):
        current = combat['turn_order'][combat['current_turn']]
        lines.append(f"⚔️ **In Combat** - Round {combat.get('round', 1)} - {current['name']}'s turn")
    
    await interaction.response.send_message("\n".join(lines))


# =============================================================================
# XP & LEVELING COMMANDS
# =============================================================================

@bot.tree.command(name="xp", description="View or award XP")
@app_commands.describe(
    award="Amount of XP to award (leave empty to view)",
    target="Target player (leave empty for self)"
)
async def xp_cmd(
    interaction: discord.Interaction,
    award: Optional[int] = None,
    target: Optional[discord.Member] = None
):
    """View or award experience points."""
    user_id = str(target.id if target else interaction.user.id)
    
    if award is not None and award > 0:
        # Award XP
        result = award_xp(user_id, award)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        msg = f"✨ **{result['character']}** gained **{award} XP**!\n"
        msg += f"📊 Total XP: {result['new_xp']}\n"
        msg += f"{format_xp_bar(result['new_xp'], result['new_level'])}\n"
        
        if result.get('level_up'):
            msg += f"\n🎉 **LEVEL UP!** {result['old_level']} → {result['new_level']}!\n"
            msg += f"Use `/levelup` to apply your new level benefits!"
        else:
            msg += f"XP to next level: {result['xp_to_next']}"
        
        await interaction.response.send_message(msg)
    else:
        # View XP
        summary = get_xp_summary(user_id)
        if summary.get('error'):
            await interaction.response.send_message(summary['error'], ephemeral=True)
            return
        
        msg = f"📊 **{summary['name']}** - Level {summary['level']}\n"
        msg += f"XP: {summary['xp']}\n"
        msg += f"{summary['progress_bar']}\n"
        
        if summary['at_max_level']:
            msg += "🏆 Maximum level reached!"
        else:
            msg += f"XP to level {summary['level'] + 1}: {summary['xp_to_next']}"
        
        await interaction.response.send_message(msg)


@bot.tree.command(name="awardparty", description="Award XP to all party members")
@app_commands.describe(xp="Total XP to distribute", split="Split evenly among party?")
async def award_party_cmd(interaction: discord.Interaction, xp: int, split: bool = True):
    """Award XP to all party members."""
    channel_id = str(interaction.channel.id)
    state = load_state(channel_id)
    
    players = state.get('players', [])
    if not players:
        await interaction.response.send_message("No players in the party!", ephemeral=True)
        return
    
    results = award_party_xp(players, xp, split)
    
    xp_each = xp // len(players) if split else xp
    lines = [f"✨ **Party XP Award** - {xp} XP {'split among' if split else 'each for'} {len(players)} players"]
    lines.append("───────────────────────")
    
    level_ups = []
    for result in results:
        if result.get('error'):
            continue
        line = f"• **{result['character']}**: +{xp_each} XP ({result['new_xp']} total)"
        if result.get('level_up'):
            line += f" 🎉 **LEVEL {result['new_level']}!**"
            level_ups.append(result['character'])
        lines.append(line)
    
    if level_ups:
        lines.append("───────────────────────")
        lines.append(f"🎊 Level ups: {', '.join(level_ups)}! Use `/levelup` to apply!")
    
    await interaction.response.send_message("\n".join(lines))


# =============================================================================
# LOOT COMMANDS
# =============================================================================

@bot.tree.command(name="loot", description="Generate random loot")
@app_commands.describe(cr="Challenge Rating for loot scaling", loot_type="Type of loot to generate")
@app_commands.choices(loot_type=[
    app_commands.Choice(name="Treasure Hoard", value="hoard"),
    app_commands.Choice(name="Enemy Drop", value="enemy"),
    app_commands.Choice(name="Magic Item", value="magic"),
])
async def loot_cmd(
    interaction: discord.Interaction, 
    cr: int = 1,
    loot_type: str = "enemy"
):
    """Generate random loot based on CR."""
    from utils.inventory_manager import create_loot_distribution
    
    channel_id = str(interaction.channel_id)
    
    if loot_type == "hoard":
        loot = generate_treasure_hoard(cr)
        msg = f"💰 **Treasure Hoard (CR {cr})**\n"
        msg += format_loot_display(loot)
        
        # Create loot pile for claiming
        items = loot.get('mundane', [])
        for gem, value in loot.get('gems', []):
            items.append(f"{gem} ({value} gp)")
        for obj, value in loot.get('art_objects', []):
            items.append(f"{obj} ({value} gp)")
        for magic_item in loot.get('magic_items', []):
            items.append(magic_item['name'])
        
        if items or loot.get('currency'):
            create_loot_distribution(channel_id, items, loot.get('currency', {}))
            msg += "\n\n*Use `/claimloot <item>` or `/splitgold` to claim!*"
        
    elif loot_type == "magic":
        max_rarity = Rarity.UNCOMMON if cr < 5 else Rarity.RARE if cr < 11 else Rarity.VERY_RARE if cr < 17 else Rarity.LEGENDARY
        item = roll_magic_item(max_rarity)
        if item:
            msg = f"✨ **Magic Item Found!**\n"
            msg += f"{item['rarity_icon']} **{item['name']}** ({item['rarity'].replace('_', ' ').title()})\n"
            msg += f"*{item['effect']}*"
            
            # Create loot pile
            create_loot_distribution(channel_id, [item['name']], {})
            msg += "\n\n*Use `/claimloot <item>` to claim!*"
        else:
            msg = "No magic item generated."
    else:
        loot = generate_enemy_loot("Defeated Enemy", cr)
        msg = f"🗡️ **Enemy Loot (CR {cr})**\n"
        msg += format_loot_display(loot)
        
        # Create loot pile
        items = loot.get('items', [])
        if items or loot.get('currency'):
            create_loot_distribution(channel_id, items, loot.get('currency', {}))
            msg += "\n\n*Use `/claimloot <item>` or `/claimgold` to claim!*"
    
    await interaction.response.send_message(msg)


@bot.tree.command(name="treasure", description="Generate a treasure hoard")
@app_commands.describe(cr="Challenge Rating of the encounter")
async def treasure_cmd(interaction: discord.Interaction, cr: int = 5):
    """Generate a full treasure hoard."""
    loot = generate_treasure_hoard(cr, include_magic=True)
    
    lines = [f"💎 **Treasure Hoard** (CR {cr})"]
    lines.append("═══════════════════════")
    
    # Currency
    if loot.get('currency'):
        lines.append(f"🪙 **Coins:** {format_currency(loot['currency'])}")
    
    # Gems
    if loot.get('gems'):
        lines.append(f"💎 **Gems:**")
        for gem, value in loot['gems']:
            lines.append(f"  • {gem} ({value} gp)")
    
    # Art
    if loot.get('art_objects'):
        lines.append(f"🖼️ **Art Objects:**")
        for obj, value in loot['art_objects']:
            lines.append(f"  • {obj} ({value} gp)")
    
    # Magic Items
    if loot.get('magic_items'):
        lines.append(f"✨ **Magic Items:**")
        for item in loot['magic_items']:
            lines.append(f"  {item['rarity_icon']} **{item['name']}**")
            lines.append(f"    *{item['effect']}*")
    
    # Mundane
    if loot.get('mundane'):
        lines.append(f"📦 **Other Items:** {', '.join(loot['mundane'])}")
    
    await interaction.response.send_message("\n".join(lines))


# =============================================================================
# AMBIENT MUSIC COMMANDS
# =============================================================================

@bot.tree.command(name="ambient", description="Set ambient music mood")
@app_commands.describe(mood="The ambient mood to set")
@app_commands.choices(mood=[
    app_commands.Choice(name="🎵 Combat - Epic battle music", value="combat"),
    app_commands.Choice(name="🌲 Exploration - Adventure themes", value="exploration"),
    app_commands.Choice(name="🍺 Tavern - Jovial inn music", value="tavern"),
    app_commands.Choice(name="🏰 Dungeon - Dark, ominous", value="dungeon"),
    app_commands.Choice(name="🌳 Forest - Nature sounds", value="forest"),
    app_commands.Choice(name="🏘️ Town - Marketplace bustle", value="town"),
    app_commands.Choice(name="✨ Mysterious - Magical ambiance", value="mysterious"),
    app_commands.Choice(name="👹 Boss - Intense battle", value="boss"),
    app_commands.Choice(name="🏆 Victory - Triumphant", value="victory"),
    app_commands.Choice(name="😰 Tension - Suspenseful", value="tension"),
    app_commands.Choice(name="🛏️ Rest - Calm, peaceful", value="rest"),
])
async def ambient_cmd(interaction: discord.Interaction, mood: str):
    """Set the ambient music mood."""
    if not interaction.guild:
        await interaction.response.send_message("Must be in a server.", ephemeral=True)
        return
    
    try:
        ambient_mood = AmbientMood(mood)
    except ValueError:
        await interaction.response.send_message("Invalid mood.", ephemeral=True)
        return
    
    # Get voice client if available
    voice_client = interaction.guild.voice_client
    
    if voice_client:
        await ambient_manager.set_mood(voice_client, ambient_mood)
        await interaction.response.send_message(f"🎵 Ambient mood set to **{mood.title()}**")
    else:
        # Just update the state for when voice connects
        state = ambient_manager.get_state(interaction.guild.id)
        state['current_mood'] = ambient_mood
        await interaction.response.send_message(f"🎵 Ambient mood queued: **{mood.title()}** (join voice to hear)")


@bot.tree.command(name="sfx", description="Play a sound effect")
@app_commands.describe(effect="Sound effect to play")
@app_commands.choices(effect=[
    app_commands.Choice(name="🎲 Dice Roll", value="dice_roll"),
    app_commands.Choice(name="⚔️ Critical Hit", value="critical_hit"),
    app_commands.Choice(name="💀 Critical Miss", value="critical_miss"),
    app_commands.Choice(name="⬆️ Level Up", value="level_up"),
    app_commands.Choice(name="💚 Healing", value="healing"),
    app_commands.Choice(name="🪙 Gold Coins", value="gold_coins"),
    app_commands.Choice(name="🚪 Door Open", value="door_open"),
    app_commands.Choice(name="⚔️ Combat Start", value="combat_start"),
    app_commands.Choice(name="🏆 Victory Fanfare", value="victory_fanfare"),
])
async def sfx_cmd(interaction: discord.Interaction, effect: str):
    """Play a sound effect."""
    if not interaction.guild:
        await interaction.response.send_message("Must be in a server.", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client
    if not voice_client:
        await interaction.response.send_message("Bot must be in a voice channel. Use `/joinvoice`", ephemeral=True)
        return
    
    try:
        sfx = SoundEffect(effect)
        await ambient_manager.play_sfx(voice_client, sfx)
        await interaction.response.send_message(f"🔊 Playing: {effect.replace('_', ' ').title()}")
    except Exception as e:
        await interaction.response.send_message(f"Could not play sound effect: {e}", ephemeral=True)


# =============================================================================
# REACTION COMMANDS
# =============================================================================

@bot.tree.command(name="reaction", description="Use your reaction in combat")
@app_commands.describe(
    reaction_type="Type of reaction to use",
    target="Target of the reaction (if applicable)"
)
@app_commands.choices(reaction_type=[
    app_commands.Choice(name="⚔️ Opportunity Attack", value="opportunity_attack"),
    app_commands.Choice(name="🛡️ Shield (+5 AC)", value="shield"),
    app_commands.Choice(name="🚫 Counterspell", value="counterspell"),
    app_commands.Choice(name="🌀 Absorb Elements", value="absorb_elements"),
    app_commands.Choice(name="🔥 Hellish Rebuke", value="hellish_rebuke"),
    app_commands.Choice(name="🎭 Cutting Words", value="cutting_words"),
    app_commands.Choice(name="⚡ Uncanny Dodge", value="uncanny_dodge"),
    app_commands.Choice(name="🏹 Deflect Missiles", value="deflect_missiles"),
])
async def reaction_cmd(
    interaction: discord.Interaction,
    reaction_type: str,
    target: Optional[str] = None
):
    """Use your reaction in combat."""
    channel_id = str(interaction.channel.id)
    user_id = str(interaction.user.id)
    
    char = load_character(user_id)
    if not char:
        await interaction.response.send_message("Create a character first!", ephemeral=True)
        return
    
    char_name = char.get('name', 'Character')
    
    # Check if in combat
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        await interaction.response.send_message("No active combat!", ephemeral=True)
        return
    
    # Check if reaction is available
    if not has_reaction_available(channel_id, char_name):
        await interaction.response.send_message("You've already used your reaction this round!", ephemeral=True)
        return
    
    try:
        rtype = ReactionType(reaction_type)
    except ValueError:
        await interaction.response.send_message("Invalid reaction type.", ephemeral=True)
        return
    
    # Handle specific reactions
    if rtype == ReactionType.SHIELD:
        result = cast_shield(channel_id, char_name)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"🛡️ **{char_name}** casts **Shield**!\n"
            f"AC increased by {result['ac_bonus']} (now {result['new_ac']}) until start of next turn."
        )
    
    elif rtype == ReactionType.COUNTERSPELL:
        if not target:
            await interaction.response.send_message("Specify the spell level being countered!", ephemeral=True)
            return
        
        try:
            spell_level = int(target)
        except ValueError:
            spell_level = 3  # Default assumption
        
        result = cast_counterspell(channel_id, char_name, spell_level)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        msg = f"🚫 **{char_name}** casts **Counterspell**!\n"
        if result['check_roll']:
            msg += f"Ability check: {result['check_roll']} + 4 = {result['check_roll'] + 4}\n"
        msg += result['message']
        
        await interaction.response.send_message(msg)
    
    elif rtype == ReactionType.UNCANNY_DODGE:
        if not target:
            await interaction.response.send_message("Specify the damage amount to halve!", ephemeral=True)
            return
        
        try:
            damage = int(target)
        except ValueError:
            await interaction.response.send_message("Enter a number for damage.", ephemeral=True)
            return
        
        result = use_uncanny_dodge(channel_id, char_name, damage)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"⚡ **{char_name}** uses **Uncanny Dodge**!\n"
            f"Damage reduced from {result['original_damage']} to {result['reduced_damage']} "
            f"({result['damage_prevented']} prevented)"
        )
    
    elif rtype == ReactionType.OPPORTUNITY_ATTACK:
        if not target:
            await interaction.response.send_message("Specify the target of your opportunity attack!", ephemeral=True)
            return
        
        # Get attack bonus from character
        attack_bonus = get_ability_modifier(char.get('STR', 10)) + char.get('proficiency', 2)
        
        # Get weapon damage (default 1d8+STR)
        weapon = char.get('equipment', {}).get('weapon')
        if weapon:
            damage_dice = weapon.get('damage', '1d8') + f"+{get_ability_modifier(char.get('STR', 10))}"
        else:
            damage_dice = f"1d8+{get_ability_modifier(char.get('STR', 10))}"
        
        result = resolve_opportunity_attack(channel_id, char_name, target, attack_bonus, damage_dice)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        if result.get('fumble'):
            msg = f"⚔️ **{char_name}** takes an opportunity attack on **{target}**... 💀 Critical Miss!"
        elif result.get('crit'):
            msg = f"⚔️ **{char_name}** 🌟 **CRITICAL** opportunity attack on **{target}** for **{result['damage']}** damage!"
        elif result['hit']:
            msg = f"⚔️ **{char_name}** opportunity attack hits **{target}** for **{result['damage']}** damage! ({result['target_hp']} HP remaining)"
        else:
            msg = f"⚔️ **{char_name}** opportunity attack on **{target}** misses! ({result['total']} vs AC {result['target_ac']})"
        
        await interaction.response.send_message(msg)
    
    else:
        # Generic reaction use
        result = use_reaction(channel_id, char_name, rtype)
        if result.get('error'):
            await interaction.response.send_message(result['error'], ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"⚡ **{char_name}** uses **{reaction_type.replace('_', ' ').title()}**!"
        )


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


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):
    """
    Detect when players join voice channels.
    Offer session resume if they have an active campaign.
    (Phase 15: Session Continuity & Auto-Resume)
    """
    # Ignore bots
    if member.bot:
        return
    
    # Only trigger when someone JOINS a voice channel (not leave/switch)
    if before.channel == after.channel:
        return  # No change in channel
    
    if after.channel is None:
        return  # User left voice, don't trigger
    
    # User joined a voice channel - check for resumable sessions
    # Look for a text channel in the same guild where they have a campaign
    guild = member.guild
    user_id = str(member.id)
    
    # Check if this user has a character
    char = load_character(user_id)
    if not char:
        return  # No character, nothing to resume
    
    # Look for campaigns in text channels where this user is a player
    for text_channel in guild.text_channels:
        channel_id = str(text_channel.id)
        
        try:
            state = load_state(channel_id)
            if not state.get("campaign_title"):
                continue
            
            # Check if user is part of this campaign
            players = state.get("players", [])
            if user_id not in players:
                continue
            
            # Check for resumable session
            resume_info = check_for_resume(channel_id)
            
            # If there's a paused session or recovery available
            if resume_info.get("has_paused_session") or resume_info.get("has_recovery"):
                session = load_session_state(channel_id)
                
                # Don't spam - only notify once per session
                if session.status == SessionStatus.ACTIVE.value:
                    continue  # Already active, no need to prompt
                
                # Get other players in the same voice channel
                voice_members = [m for m in after.channel.members if not m.bot]
                voice_player_ids = [str(m.id) for m in voice_members]
                
                # Count how many campaign players are in voice
                players_in_voice = [p for p in players if p in voice_player_ids]
                
                if len(players_in_voice) >= 1:  # At least one player
                    # Send resume prompt
                    campaign_title = state.get("campaign_title", "Your Campaign")
                    location = state.get("location", "Unknown")
                    
                    embed = discord.Embed(
                        title="🎮 Resume Session?",
                        description=f"**{campaign_title}**\n"
                                    f"📍 Last location: {location}",
                        color=discord.Color.green()
                    )
                    
                    if resume_info.get("has_recovery"):
                        embed.add_field(
                            name="Recovery Available",
                            value="A recovery point was saved. Use `/recover` to restore.",
                            inline=False
                        )
                    
                    if resume_info.get("last_session"):
                        last = resume_info["last_session"]
                        time_ago = calculate_time_since(last.ended_at) if hasattr(last, 'ended_at') else 'recently'
                        embed.add_field(
                            name="Last Session",
                            value=f"Played {time_ago}\n"
                                  f"Duration: {last.duration_minutes} min",
                            inline=True
                        )
                    
                    embed.add_field(
                        name="Commands",
                        value="• `/sessionrecap` - Hear what happened last time\n"
                              "• `/do <action>` - Jump back into the action\n"
                              "• `/recover` - Restore from crash",
                        inline=False
                    )
                    
                    embed.set_footer(text=f"{len(players_in_voice)} player(s) in voice")
                    
                    try:
                        await text_channel.send(
                            f"👋 <@{user_id}> joined voice!",
                            embed=embed
                        )
                        
                        # Resume the session automatically
                        resume_session(channel_id, voice_player_ids)
                        
                        # Re-register for auto-save
                        def get_campaign_state(ch_id: str) -> dict:
                            return load_state(ch_id)
                        
                        auto_save_manager.register_channel(channel_id, get_campaign_state)
                        asyncio.create_task(auto_save_manager.start_auto_save(channel_id))
                        
                    except discord.Forbidden:
                        pass  # Can't send to that channel
                    
                    return  # Only send one prompt per join
                    
        except Exception as e:
            # Log but don't crash on individual channel errors
            continue


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
