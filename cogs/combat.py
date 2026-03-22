"""Combat Cog — All combat-related slash commands."""
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import logging
from typing import Optional

from utils.state_manager import load_state, save_state
from utils.character_manager import (
    load_character, save_character, damage_character, heal_character, death_save
)
from utils.combat_manager import (
    start_combat, roll_initiative, next_turn, end_combat, attack,
    get_combat_status, load_combat, save_combat,
    use_legendary_action, reset_legendary_actions,
    damage_combatant
)
from utils.enemy_ai import (
    execute_enemy_turn, select_legendary_action,
    should_use_legendary_action, process_lair_actions
)
from utils.combat_flow import (
    combat_timer, CombatFlowConfig,
    process_end_of_turn_effects, process_start_of_turn_effects,
    process_round_transition, check_combat_end, CombatEndReason,
    build_turn_announcement, execute_auto_pass, process_post_combat
)
from utils.combat_trigger import EnemySpec, build_enemy_list
from utils.reaction_manager import reset_reactions, reset_all_reactions_new_round
from utils.loot_manager import format_loot_display
from utils.logger import log_message
from services.openai_service import (
    narrate_enemy_action, narrate_legendary_action, narrate_lair_action
)
from utils.voice_parser import extract_voice_tag, clean_for_tts
from cogs.shared import _active_channels, play_tts

logger = logging.getLogger(__name__)


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

    result = execute_auto_pass(channel_id, combatant_name)

    if result.get('error'):
        return

    await channel.send(result['message'])

    state = next_turn(channel_id)
    if state:
        current = state['turn_order'][state['current_turn']]

        if current.get('type') == 'enemy' and CombatFlowConfig.AUTO_EXECUTE_ENEMY_TURNS:
            await channel.send(f"⚔️ **{current['name']}** is up next...")
        else:
            announcement = build_turn_announcement(channel_id, current)
            await channel.send(announcement['message'])

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
# COMBAT HELPERS (only used by combat commands)
# =============================================================================

async def execute_and_narrate_enemy_turn(interaction: discord.Interaction,
                                          channel_id: str, enemy: dict,
                                          combat_state: dict):
    """Execute an enemy's turn and narrate the results."""
    turn_result = execute_enemy_turn(channel_id, enemy, combat_state)

    for action in turn_result.get('actions', []):
        if action.get('type') == 'attack' and action.get('hit'):
            target_name = action.get('target')
            damage = action.get('damage', 0)
            damage_type = action.get('damage_type', 'bludgeoning')
            if target_name and damage > 0:
                damage_combatant(channel_id, target_name, damage, damage_type)

    try:
        narration = await narrate_enemy_action(turn_result, combat_state)
    except Exception as e:
        logger.error(f"Enemy narration error: {e}")
        # Build a mechanical fallback description from the turn results
        parts = []
        for action in turn_result.get('actions', []):
            if action.get('type') == 'attack':
                target = action.get('target', 'an enemy')
                if action.get('hit'):
                    parts.append(f"**{enemy['name']}** attacks **{target}** and deals {action.get('damage', 0)} damage!")
                else:
                    parts.append(f"**{enemy['name']}** attacks **{target}** but misses!")
            elif action.get('description'):
                parts.append(action['description'])
        narration = " ".join(parts) if parts else f"**{enemy['name']}** takes their turn."

    lines = [f"⚔️ **{enemy['name']}'s Turn**"]
    lines.append("───────────────────────")

    movement = turn_result.get('movement', {})
    if movement.get('description'):
        lines.append(f"🏃 {movement['description']}")

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

    if turn_result.get('damage_dealt', 0) > 0:
        lines.append(f"💥 Total damage: **{turn_result['damage_dealt']}**")

    lines.append("───────────────────────")
    lines.append(f"*{narration}*")

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

    voice_tag = extract_voice_tag(narration) if '[Voice:' in narration else enemy['name']
    tts_text = clean_for_tts(narration)
    await play_tts(interaction, tts_text, voice_tag)

    log_message(channel_id, enemy['name'], narration)

    end_check = check_combat_end(channel_id)
    if end_check.should_end:
        await interaction.followup.send(end_check.summary)
        if end_check.reason == CombatEndReason.VICTORY:
            await interaction.followup.send("Use `/endcombat` to collect rewards and end the encounter.")
        return

    await asyncio.sleep(CombatFlowConfig.DELAY_BETWEEN_ENEMY_TURNS)

    next_state = next_turn(channel_id)
    if next_state:
        next_combatant = next_state['turn_order'][next_state['current_turn']]

        start_result = process_start_of_turn_effects(channel_id, next_combatant)
        if start_result.narration:
            await interaction.followup.send(f"📋 {start_result.narration}")

        if next_combatant.get('type') == 'enemy':
            await execute_and_narrate_enemy_turn(interaction, channel_id, next_combatant, next_state)
        else:
            announcement = build_turn_announcement(channel_id, next_combatant)

            await check_legendary_actions(interaction, channel_id, next_state)

            await interaction.followup.send(
                announcement['message'] + f"\n⏰ *Timer: {CombatFlowConfig.TURN_TIMEOUT_SECONDS}s*"
            )

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
        try:
            narration = await narrate_legendary_action(
                enemy['name'], action, result.get('remaining', 0), combat_state
            )
        except Exception as e:
            logger.error(f"Legendary action narration failed: {e}")
            narration = f"**{enemy['name']}** uses **{action.get('name', 'a legendary action')}**!"

        await interaction.followup.send(
            f"⚡ **LEGENDARY ACTION!**\n"
            f"{narration}\n"
            f"*({result.get('remaining', 0)} legendary actions remaining)*"
        )

        tts_text = clean_for_tts(narration)
        await play_tts(interaction, tts_text, enemy['name'])


async def process_and_send_lair_action(interaction: discord.Interaction,
                                        channel_id: str, combat_state: dict):
    """Process and narrate a lair action at initiative 20."""
    lair_result = process_lair_actions(channel_id, combat_state)

    if lair_result:
        combat_state['lair_action_used_this_round'] = True
        save_combat(channel_id, combat_state)

        try:
            narration = await narrate_lair_action(lair_result, combat_state)
        except Exception as e:
            logger.error(f"Lair action narration failed: {e}")
            narration = f"[Voice: Narrator] {lair_result.get('description', 'The lair shifts ominously...')}"

        await interaction.channel.send(
            f"🏰 **LAIR ACTION** (Initiative 20)\n"
            f"───────────────────────\n"
            f"{narration}"
        )

        tts_text = clean_for_tts(narration)
        await play_tts(interaction, tts_text, "Narrator")


# =============================================================================
# COMBAT COG
# =============================================================================

class CombatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fight", description="Start combat with enemies")
    @app_commands.describe(enemies="Enemies: 'goblin goblin orc' OR 'goblin:15:13 orc:25:14' (name:hp:ac)")
    async def fight_start(self, interaction: discord.Interaction, enemies: str):
        """Start a combat encounter."""
        channel_id = str(interaction.channel.id)

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
            else:
                enemy_name = parts[0].strip()
                if not enemy_name:
                    continue

                count = 1
                if '*' in enemy_name:
                    name_parts = enemy_name.split('*')
                    enemy_name = name_parts[0]
                    try:
                        count = int(name_parts[1])
                    except (ValueError, IndexError):
                        count = 1

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

        state = load_state(channel_id)

        if not state.get('campaign_title'):
            await interaction.response.send_message("Start a campaign first with `/campaign`!", ephemeral=True)
            return

        players = [(pid, load_character(pid).get('name', 'Adventurer') if load_character(pid) else 'Adventurer')
                   for pid in state.get('players', [])]

        if not players:
            char = load_character(str(interaction.user.id))
            char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name
            players = [(str(interaction.user.id), char_name)]

        combat_state = start_combat(channel_id, players, enemy_list)

        init_state = roll_initiative(channel_id)

        reset_all_reactions_new_round(channel_id)

        state['in_combat'] = True
        state['free_form'] = False
        save_state(channel_id, state)

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

        await setup_timer_callbacks(channel_id, interaction.channel)

        if first.get('type') == 'player' and first.get('id'):
            await combat_timer.start_turn_timer(
                channel_id,
                first['name'],
                first['id']
            )

        await play_tts(interaction, f"Roll for initiative! {first['name']}, you're up first!", "Narrator")

    @app_commands.command(name="attack", description="Attack a target")
    @app_commands.describe(target="Target name", bonus="Attack bonus (e.g., 5)", damage="Damage dice (e.g., 1d8+3)")
    async def attack_cmd(self, interaction: discord.Interaction, target: str, bonus: int, damage: str):
        """Make an attack roll against a target."""
        channel_id = str(interaction.channel.id)
        char = load_character(str(interaction.user.id))
        char_name = char.get('name', interaction.user.display_name) if char else interaction.user.display_name

        await combat_timer.cancel_timer(channel_id)

        result = attack(channel_id, str(interaction.user.id), target, bonus, damage)

        if not result:
            await interaction.response.send_message("No combat or target not found!", ephemeral=True)
            return

        if result.get('fumble'):
            msg = f"⚔️ **{char_name}** attacks **{target}**... 💀 **Critical Miss!** (Rolled 1)"
        elif result.get('crit'):
            msg = f"⚔️ **{char_name}** 🌟 **CRITICAL HIT** on **{target}** for **{result['damage']}** damage! ({result['target_hp']}/{result['target_max_hp']} HP)"
        elif result['hit']:
            msg = f"⚔️ **{char_name}** hits **{target}** for **{result['damage']}** damage! ({result['target_hp']}/{result['target_max_hp']} HP)"
        else:
            msg = f"⚔️ **{char_name}** attacks **{target}**... and misses! (Rolled {result['total']} vs AC)"

        if result['target_hp'] == 0:
            msg += f"\n💀 **{target}** is down!"

            end_check = check_combat_end(channel_id)
            if end_check.should_end and end_check.reason == CombatEndReason.VICTORY:
                msg += f"\n\n🎉 **Victory!** All enemies have been defeated! Use `/endcombat` to collect rewards."

        await interaction.response.send_message(msg)
        log_message(channel_id, char_name, msg)

        combat_state = load_combat(channel_id)
        if combat_state:
            await check_legendary_actions(interaction, channel_id, combat_state)

    @app_commands.command(name="combatinfo", description="Show current combat status")
    async def combat_info(self, interaction: discord.Interaction):
        """Display combat status and turn order."""
        channel_id = str(interaction.channel.id)
        status = get_combat_status(channel_id)

        if not status:
            await interaction.response.send_message("No active combat.", ephemeral=True)
            return

        turn_display = []
        for i, c in enumerate(status['turn_order']):
            hp = c.get('hp', 0)
            max_hp = c.get('max_hp', hp)
            hp_pct = hp / max_hp if max_hp > 0 else 0

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

            type_icon = "👤" if c.get('type') == 'player' else "👹"

            turn_display.append(
                f"{indicator}{type_icon} **{c['name']}** - {health_icon} {hp}/{max_hp}{status_str}"
            )

        current = status['current_combatant']

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

    @app_commands.command(name="nextturn", description="Advance to next combatant's turn")
    async def next_turn_cmd(self, interaction: discord.Interaction):
        """Move to the next turn in combat, auto-executing enemy turns."""
        channel_id = str(interaction.channel.id)

        await combat_timer.cancel_timer(channel_id)

        combat = load_combat(channel_id)
        if not combat or not combat.get('active'):
            await interaction.response.send_message("No active combat.", ephemeral=True)
            return

        current_turn_idx = combat.get('current_turn', 0)
        turn_order = combat.get('turn_order', [])
        if turn_order:
            current_combatant = turn_order[current_turn_idx]
            end_of_turn_result = process_end_of_turn_effects(channel_id, current_combatant)
            if end_of_turn_result.narration:
                await interaction.channel.send(f"📋 {end_of_turn_result.narration}")

        if current_turn_idx == len(turn_order) - 1:
            round_result = process_round_transition(channel_id)
            if round_result.get('effects'):
                effect_lines = [f"📋 {e['effect']}" for e in round_result['effects']]
                if effect_lines:
                    await interaction.channel.send("\n".join(effect_lines))

        combat = load_combat(channel_id)
        if combat and combat.get('lair_actions') and combat.get('current_turn', 0) == 0:
            if not combat.get('lair_action_used_this_round'):
                await process_and_send_lair_action(interaction, channel_id, combat)

        state = next_turn(channel_id)

        if not state:
            await interaction.response.send_message("No active combat.", ephemeral=True)
            return

        current = state['turn_order'][state['current_turn']]

        start_result = process_start_of_turn_effects(channel_id, current)
        if start_result.narration:
            await interaction.channel.send(f"📋 {start_result.narration}")

        reset_reactions(channel_id, current['name'])

        if current.get('legendary_actions'):
            reset_legendary_actions(channel_id, current['name'])

        end_check = check_combat_end(channel_id)
        if end_check.should_end:
            await interaction.response.send_message(end_check.summary)
            if end_check.reason == CombatEndReason.VICTORY:
                await interaction.followup.send("Use `/endcombat` to collect rewards and end the encounter.")
            return

        if current.get('type') == 'enemy':
            await interaction.response.defer()
            await execute_and_narrate_enemy_turn(interaction, channel_id, current, state)
        else:
            announcement = build_turn_announcement(channel_id, current)

            await interaction.response.send_message(
                announcement['message'] + f"\n⏰ *Timer: {CombatFlowConfig.TURN_TIMEOUT_SECONDS}s*"
            )

            if current.get('id'):
                await setup_timer_callbacks(channel_id, interaction.channel)
                await combat_timer.start_turn_timer(
                    channel_id,
                    current['name'],
                    current['id']
                )

            await play_tts(interaction, announcement['tts_text'], "Narrator")

    @app_commands.command(name="endcombat", description="End the current combat")
    async def end_combat_cmd(self, interaction: discord.Interaction):
        """End the combat encounter and award XP."""
        channel_id = str(interaction.channel.id)

        await combat_timer.cancel_timer(channel_id)

        combat = load_combat(channel_id)
        if not combat:
            await interaction.response.send_message("No active combat to end.", ephemeral=True)
            return

        end_check = check_combat_end(channel_id)

        state = load_state(channel_id)
        players = state.get('players', [])

        post_combat_result = process_post_combat(channel_id, players, end_check)

        end_combat(channel_id)

        state['in_combat'] = False
        state['free_form'] = True
        save_state(channel_id, state)

        _active_channels.pop(channel_id, None)

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

    @app_commands.command(name="hp", description="Manage HP - take damage or heal")
    @app_commands.describe(
        damage="Amount of damage to take (positive number)",
        heal="Amount to heal (positive number)",
        set_hp="Set HP to specific value"
    )
    async def hp_cmd(
        self,
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
                msg += f"\n⚠️ **{char_name}** is unconscious! Roll death saves with `/deathsave`"
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

    @app_commands.command(name="deathsave", description="Roll a death saving throw")
    async def death_save_cmd(self, interaction: discord.Interaction):
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
            char['hp'] = 1
            char['death_saves'] = {'successes': 0, 'failures': 0}
            save_character(user_id, char)
            msg = f"🎲 **{char_name}** rolls a **20**! 🌟 They regain consciousness with 1 HP!"
        elif roll == 1:
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

    @app_commands.command(name="turntimer", description="Configure combat turn timer")
    @app_commands.describe(
        seconds="Turn timeout in seconds (30-300, or 0 to disable)",
        warning="Seconds before timeout to show warning (default: 30)"
    )
    async def turn_timer_cmd(
        self,
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

    @app_commands.command(name="timeleft", description="Check remaining time on your turn")
    async def time_left_cmd(self, interaction: discord.Interaction):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
