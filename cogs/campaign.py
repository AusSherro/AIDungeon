"""Campaign core commands — the heart of the game loop."""
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import logging
from typing import Optional

from services.openai_service import (
    get_dm_response, generate_campaign, summarize_history,
    generate_campaign_summary, extract_npcs_and_quests
)
from utils.voice_parser import extract_voice_tag, clean_text
from utils.state_manager import (
    load_state, save_state,
    get_turn_order, set_turn_order,
    get_current_turn_index, set_current_turn_index,
    get_context_summary, update_campaign_summary,
    add_key_event, add_or_update_npc, add_quest,
)
from utils.prompt_builder import build_system_prompt
from utils.dice_roller import extract_inline_rolls
from utils.logger import log_message
from utils.character_manager import load_character, add_inventory
from utils.resource_manager import process_narrative_for_resources
from utils.environment_manager import check_trap_triggers
from utils.combat_trigger import detect_player_attack_intent, detect_combat_trigger
from utils.npc_manager import process_npc_from_narration, record_npc_interaction
from utils.quest_manager import process_narration_for_quests
from utils.world_map import process_narration_for_travel, start_travel_from_intent, complete_travel
from utils.skill_check_manager import parse_skill_check_request
from utils.combat_manager import load_combat, start_combat, roll_initiative
from utils.reaction_manager import reset_all_reactions_new_round
from utils.session_manager import start_session, record_activity, auto_save_manager

from cogs.shared import play_tts, prompt_skill_check, SkillCheckConfig

logger = logging.getLogger(__name__)


class CampaignCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # /campaign
    # =================================================================
    @app_commands.command(name="campaign", description="Start a new D&D campaign")
    @app_commands.describe(theme="Optional theme like 'pirates', 'horror', 'mystery in a castle'")
    async def campaign_start(self, interaction: discord.Interaction, theme: str = ""):
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

    # =================================================================
    # /do  — THE core game loop
    # =================================================================
    @app_commands.command(name="do", description="Describe what your character does")
    @app_commands.describe(action="What does your character do?")
    async def do_action(self, interaction: discord.Interaction, action: str):
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

        user_id = str(interaction.user.id)
        char = load_character(user_id)
        char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
        notifications = []  # Collect all subsystem notifications
        updated_state = state  # Will be replaced after AI call
        narration = None
        combat_started = False
        skill_check_pending = None

        try:
            # Process inline dice rolls [1d20+5]
            rolls = extract_inline_rolls(action)
            for notation, result in rolls.items():
                action = action.replace(f"[{notation}]", f"**{result}** ({notation})")

            # ==== PHASE 4: Resource Auto-Consumption ====
            resource_summary = ""
            try:
                resource_result = process_narrative_for_resources(user_id, action, auto_consume=True)
                resource_summary = resource_result.get('summary', '')
            except Exception as e:
                logger.error(f"Resource consumption failed: {e}", exc_info=True)

            # ==== PHASE 7: Environment Hazard Checks ====
            try:
                movement_keywords = ['move', 'walk', 'run', 'step', 'approach', 'enter', 'open', 'touch', 'cross', 'advance']
                if any(kw in action.lower() for kw in movement_keywords):
                    trap_results = check_trap_triggers(channel_id, char_name, trigger_type="movement")
                    for result in trap_results:
                        if result.get("triggered"):
                            trap = result["trap"]
                            notifications.append(
                                f"💥 **TRAP TRIGGERED!** {trap.name}\n"
                                f"*{trap.description}*\n"
                                f"⚠️ Make a {trap.save_type.upper()} saving throw DC {trap.save_dc}!\n"
                                f"Damage on fail: {trap.damage_dice} {trap.damage_type}"
                            )
            except Exception as e:
                logger.error(f"Trap detection failed: {e}", exc_info=True)

            # ==== PHASE 11: Check player attack intent BEFORE sending to AI ====
            player_attack_trigger = None
            try:
                player_attack_trigger = detect_player_attack_intent(action)
            except Exception as e:
                logger.error(f"Attack intent detection failed: {e}", exc_info=True)

            # ==== Build system prompt and get AI response ====
            try:
                system_prompt = build_system_prompt(state, channel_id)
                narration, updated_state = get_dm_response(action, state, user_id, system_prompt=system_prompt)
            except Exception as e:
                logger.error(f"AI response generation failed: {e}", exc_info=True)
                await interaction.followup.send(
                    "⚠️ The mystical energies are disrupted... The DM couldn't respond. Please try again."
                )
                return

            current_location = updated_state.get('location', '')

            # ==== PHASE 5: Auto-detect NPCs from narration ====
            try:
                detected_npc = process_npc_from_narration(channel_id, narration, current_location)
                if detected_npc and detected_npc.memory.interaction_count <= 1:
                    char_names = []
                    for pid in updated_state.get('turn_order', [user_id]):
                        pchar = load_character(pid)
                        if pchar:
                            char_names.append(pchar.get('name', ''))
                    if char_names:
                        record_npc_interaction(channel_id, detected_npc.name, char_names)
                    notifications.append(
                        f"👤 *New NPC met: **{detected_npc.name}** ({detected_npc.role.replace('_', ' ').title()})*"
                    )
            except Exception as e:
                logger.error(f"NPC detection failed: {e}", exc_info=True)

            # ==== PHASE 6+13: Auto-detect quest progress from narration ====
            try:
                quest_events = process_narration_for_quests(channel_id, narration)
                for event in quest_events:
                    etype = event["type"]
                    if etype == "objective_complete":
                        notifications.append(f"✅ *Objective complete: {event['message']}*")
                    elif etype == "objective_progress":
                        notifications.append(f"📊 *{event['message']}*")
                    elif etype == "quest_complete":
                        quest = event["quest"]
                        rewards = event.get("rewards")
                        parts = [f"🎉 **Quest Complete: {quest.name}!**"]
                        if rewards:
                            if rewards.xp > 0:
                                parts.append(f"⭐ +{rewards.xp} XP")
                            if rewards.gold > 0:
                                parts.append(f"💰 +{rewards.gold} gp")
                        notifications.append("\n".join(parts))
                    elif etype == "quest_failed":
                        notifications.append(f"❌ *{event['message']}*")
                    elif etype in ("quest_created", "quest_unlocked", "quest_hook",
                                   "rumor_heard", "objective_added", "quest_chain",
                                   "quest_offer_detected"):
                        notifications.append(event['message'])
            except Exception as e:
                logger.error(f"Quest processing failed: {e}", exc_info=True)

            # ==== PHASE 12: Dynamic Environment Detection ====
            try:
                from utils.world_generator import process_narration_for_environment
                env_changes, env_results = process_narration_for_environment(
                    channel_id, narration, current_location
                )
                if env_results:
                    notifications.extend(env_results)
            except Exception as e:
                logger.error(f"Environment detection failed: {e}", exc_info=True)

            # ==== PHASE 14: Intelligent Travel & Exploration Detection ====
            try:
                travel_events = process_narration_for_travel(channel_id, action, narration)

                if travel_events.get("travel_started"):
                    intent = travel_events["travel_started"]
                    travel_result = start_travel_from_intent(channel_id, intent)
                    parts = [f"🚶 **Journey Begun**", f"→ Destination: {intent.destination}"]
                    if travel_result.get("distance"):
                        parts.append(f"📏 Distance: {travel_result['distance']:.1f} miles")
                    if travel_result.get("terrain"):
                        parts.append(f"🌲 Terrain: {travel_result['terrain'].title()}")
                    notifications.append("\n".join(parts))

                if travel_events.get("arrival"):
                    arrival_loc = travel_events["arrival"]
                    complete_travel(channel_id, arrival_loc)
                    notifications.append(f"🏁 **Arrived at {arrival_loc}!**")
                    updated_state['location'] = arrival_loc

                for discovery in travel_events.get("locations_discovered", []):
                    poi_star = "⭐ " if discovery.is_poi else ""
                    suffix = f" ({discovery.terrain})" if discovery.terrain != "wilderness" else ""
                    notifications.append(f"📍 *New location discovered: {poi_star}**{discovery.name}***{suffix}")

                for from_loc, to_loc, miles in travel_events.get("distances_revealed", []):
                    notifications.append(f"🗺️ *Distance revealed: {from_loc} → {to_loc}: {miles:.0f} miles*")
            except Exception as e:
                logger.error(f"Travel detection failed: {e}", exc_info=True)

            # ==== Process loot ====
            try:
                loot_items = updated_state.pop('recent_loot', [])
                for item in loot_items:
                    add_inventory(user_id, item)
                    notifications.append(f"🎒 *{char_name} obtained: {item}*")
            except Exception as e:
                logger.error(f"Loot processing failed: {e}", exc_info=True)

            # ==== Format output ====
            voice_tag = extract_voice_tag(narration)
            text = clean_text(narration)
            output = f"**{char_name}:** *{action}*\n\n{text}"

            if resource_summary:
                notifications.insert(0, resource_summary)

            # Append all collected notifications
            if notifications:
                output += "\n\n" + "\n\n".join(notifications)

            # ==== Skill check detection ====
            try:
                player_char_names = []
                for pid in updated_state.get('turn_order', []):
                    pchar = load_character(pid)
                    if pchar:
                        player_char_names.append(pchar.get('name', ''))

                skill_check_request = parse_skill_check_request(narration, player_char_names)

                if skill_check_request:
                    skill_check_request.context = action

                    if skill_check_request.is_group_check:
                        target_player_ids = updated_state.get('turn_order', [user_id])
                    elif skill_check_request.target_players:
                        target_player_ids = []
                        for pid in updated_state.get('turn_order', []):
                            pchar = load_character(pid)
                            if pchar and pchar.get('name', '') in skill_check_request.target_players:
                                target_player_ids.append(pid)
                        if not target_player_ids:
                            target_player_ids = [user_id]
                    else:
                        target_player_ids = [user_id]

                    player_mentions = [f"<@{pid}>" for pid in target_player_ids]
                    skill_name = skill_check_request.skill_or_ability.replace('_', ' ').title()
                    dc_text = f" (DC {skill_check_request.dc})" if skill_check_request.dc else ""

                    if skill_check_request.is_group_check:
                        output += f"\n\n🎲 **Everyone, roll {skill_name}{dc_text}!**"
                    else:
                        output += f"\n\n🎲 **Roll {skill_name}{dc_text}!**"

                    updated_state['pending_roll'] = {
                        'player_id': user_id,
                        'skill': skill_check_request.skill_or_ability,
                        'dc': skill_check_request.dc,
                        'action': action
                    }
                    skill_check_pending = (skill_check_request, target_player_ids, player_mentions)
                else:
                    pending = updated_state.get('pending_roll')
                    if pending and pending.get('skill'):
                        skill_name = pending['skill'].replace('_', ' ').title()
                        dc_text = f" (DC {pending['dc']})" if pending.get('dc') else ""
                        output += f"\n\n🎲 **Roll {skill_name}{dc_text}!** Use `/roll {pending['skill']}`"
            except Exception as e:
                logger.error(f"Skill check detection failed: {e}", exc_info=True)

            # ==== PHASE 11: Enhanced Combat Trigger Detection ====
            try:
                combat_trigger_result = detect_combat_trigger(narration, player_action=action, is_ai_response=True)

                if not combat_trigger_result and player_attack_trigger:
                    combat_trigger_result = player_attack_trigger

                if combat_trigger_result and combat_trigger_result.triggered:
                    existing_combat = load_combat(channel_id)
                    if not existing_combat or not existing_combat.get('active'):
                        if combat_trigger_result.enemies:
                            player_list = []
                            for pid in updated_state.get('turn_order', [str(interaction.user.id)]):
                                pchar = load_character(pid)
                                if pchar:
                                    player_list.append((pid, pchar.get('name', f'Player_{pid}')))
                                else:
                                    player_list.append((pid, f'Player_{pid}'))

                            enemy_list = []
                            for enemy in combat_trigger_result.enemies:
                                enemy_list.append({
                                    'name': enemy.get('name', 'Enemy'),
                                    'hp': enemy.get('hp', 10),
                                    'ac': enemy.get('ac', 12)
                                })

                            if player_list and enemy_list:
                                combat_state = start_combat(channel_id, player_list, enemy_list)
                                init_state = roll_initiative(channel_id)
                                reset_all_reactions_new_round(channel_id)

                                updated_state['in_combat'] = True
                                updated_state['free_form'] = False
                                combat_started = True

                                enemy_names = ', '.join(e['name'] for e in enemy_list)
                                combat_lines = ["\n⚔️ **COMBAT INITIATED!**"]

                                if combat_trigger_result.surprise_round == 'party':
                                    combat_lines.append("🎯 *The party has surprise!*")
                                elif combat_trigger_result.surprise_round == 'enemies':
                                    combat_lines.append("💀 *Ambush! The enemies have surprise!*")

                                combat_lines.append(f"\n**Enemies:** {enemy_names}\n")
                                combat_lines.append("**Initiative Order:**")

                                for i, c in enumerate(init_state['turn_order']):
                                    marker = "➤ " if i == 0 else "  "
                                    hp_str = f"{c['hp']}/{c.get('max_hp', c['hp'])}"
                                    combat_lines.append(f"{marker}**{c['initiative']}** - {c['name']} (HP: {hp_str}, AC: {c['ac']})")

                                first = init_state['turn_order'][0]
                                combat_lines.append(f"\n🎯 **{first['name']}**, you're up!")
                                combat_lines.append("*Use `/attack <target>` to attack, `/nextturn` when done.*")

                                output += "\n".join(combat_lines)
                        else:
                            if combat_trigger_result.error:
                                output += f"\n\n⚔️ **Combat imminent!** {combat_trigger_result.error}\n*DM, use `/fight <enemies>` to specify opponents.*"
                            else:
                                output += "\n\n⚔️ **Combat seems imminent!** DM, use `/fight <enemies>` to start the encounter."
            except Exception as e:
                logger.error(f"Combat trigger detection failed: {e}", exc_info=True)

            updated_state['pending_combat'] = None

            await interaction.followup.send(output)

            # Send skill check button prompt if needed
            if skill_check_pending:
                request, target_ids, mentions = skill_check_pending
                await prompt_skill_check(interaction.channel, channel_id, request, target_ids, mentions)

            # Play TTS (narration only, not the roll prompt)
            if narration:
                await play_tts(interaction, text, voice_tag)

            log_message(channel_id, char_name, action)
            if narration:
                log_message(channel_id, "DM", text)

            # Track session activity (Phase 15)
            activity_type = "combat" if combat_started else "action"
            record_activity(channel_id, activity_type, user_id)

        finally:
            save_state(channel_id, updated_state)

    # =================================================================
    # /context
    # =================================================================
    @app_commands.command(name="context", description="Show what the AI remembers about your campaign")
    async def context_cmd(self, interaction: discord.Interaction):
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

    # =================================================================
    # /summarize
    # =================================================================
    @app_commands.command(name="summarize", description="Save current events to campaign memory")
    async def summarize_cmd(self, interaction: discord.Interaction):
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

    # =================================================================
    # /remember
    # =================================================================
    @app_commands.command(name="remember", description="Add a note to campaign memory")
    @app_commands.describe(
        note="Important event or detail to remember",
        npc="Add an NPC (format: Name - Description)",
        quest="Add a quest (format: Quest Name - Description)"
    )
    async def remember_cmd(
        self,
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

    # =================================================================
    # /help
    # =================================================================
    @app_commands.command(name="help", description="Show available commands")
    async def help_cmd(self, interaction: discord.Interaction):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CampaignCog(bot))
