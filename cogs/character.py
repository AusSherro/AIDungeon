"""Character Cog — character management, dice, skills, spells, inventory, XP."""
import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from typing import Optional

from utils.character_manager import (
    register_character, load_character, save_character, set_stat, set_class,
    set_race, add_inventory, remove_inventory, get_character_summary,
    long_rest, short_rest, SKILLS, calculate_skill_bonus, get_ability_modifier,
    learn_spell, learn_cantrip, prepare_spell, unprepare_spell, cast_spell,
    get_available_spells, get_spell_slots_remaining, level_up
)
from utils.dice_roller import roll_dice
from utils.state_manager import load_state, save_state
from utils.prompt_builder import build_system_prompt
from utils.logger import log_message
from utils.voice_parser import extract_voice_tag, clean_text
from utils.skill_check_manager import (
    SkillCheckRequest, SkillCheckResult, CheckType,
    roll_skill_check, resolve_group_check, calculate_passive_score,
    get_pending_check, add_check_result, get_missing_players,
    format_check_result
)
from utils.resource_manager import format_resource_status
from utils.xp_manager import award_xp, award_party_xp, get_xp_summary, format_xp_bar
from utils.combat_manager import load_combat
from utils.combat_flow import combat_timer
from services.openai_service import get_dm_response, narrate_skill_check_outcome, narrate_passive_notice
from cogs.shared import play_tts, prompt_skill_check, SkillCheckConfig, process_completed_skill_check

logger = logging.getLogger(__name__)

# =============================================================================
# MODULE-LEVEL CONSTANTS
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


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # CHARACTER COMMANDS
    # =================================================================

    @app_commands.command(name="character", description="Create or view your character")
    @app_commands.describe(
        name="Character name (leave blank to view current)",
        char_class="Your class (Fighter, Wizard, etc.)",
        race="Your race (Human, Elf, etc.)"
    )
    @app_commands.choices(char_class=[app_commands.Choice(name=c, value=c) for c in DND_CLASSES])
    @app_commands.choices(race=[app_commands.Choice(name=r, value=r) for r in DND_RACES])
    async def character_cmd(
        self,
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

    @app_commands.command(name="stats", description="Set your character's stats")
    @app_commands.describe(
        strength="STR (1-20)", dexterity="DEX (1-20)", constitution="CON (1-20)",
        intelligence="INT (1-20)", wisdom="WIS (1-20)", charisma="CHA (1-20)"
    )
    async def set_stats(
        self,
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

    # =================================================================
    # DICE COMMANDS
    # =================================================================

    @app_commands.command(name="roll", description="Roll dice (e.g., 1d20, 2d6+3, athletics)")
    @app_commands.describe(dice="Dice notation or skill name", advantage="Roll with advantage", disadvantage="Roll with disadvantage")
    async def roll_cmd(self, interaction: discord.Interaction, dice: str, advantage: bool = False, disadvantage: bool = False):
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
            except (ValueError, IndexError) as e:
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
                    logger.error(f"Skill check narration error, falling back: {e}")

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

    @app_commands.command(name="groupcheck", description="Request a group skill check from all players")
    @app_commands.describe(
        skill="Skill to check",
        dc="Difficulty class (optional)"
    )
    @app_commands.choices(skill=SKILL_CHOICES)
    async def group_check_cmd(
        self,
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

    @app_commands.command(name="savingthrow", description="Request a saving throw")
    @app_commands.describe(
        ability="Ability for the save",
        dc="Difficulty class",
        player="Specific player (leave blank for all)"
    )
    @app_commands.choices(ability=ABILITY_CHOICES)
    async def saving_throw_cmd(
        self,
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

    @app_commands.command(name="passivecheck", description="Check all players' passive perception against a DC")
    @app_commands.describe(
        dc="The DC to beat",
        description="What's hidden (only revealed to those who notice)"
    )
    async def passive_check_cmd(
        self,
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
                    logger.error(f"Passive notice error: {e}")
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

    # =================================================================
    # HP & REST COMMANDS
    # =================================================================

    @app_commands.command(name="rest", description="Take a short or long rest")
    @app_commands.describe(rest_type="Type of rest")
    @app_commands.choices(rest_type=[
        app_commands.Choice(name="Short Rest (1 hour)", value="short"),
        app_commands.Choice(name="Long Rest (8 hours)", value="long")
    ])
    async def rest_cmd(self, interaction: discord.Interaction, rest_type: str):
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

    @app_commands.command(name="inventory", description="View or manage your inventory")
    @app_commands.describe(
        add="Item to add to inventory",
        remove="Item to remove from inventory"
    )
    async def inventory_cmd(
        self,
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

    # =================================================================
    # ATTUNEMENT & ENCUMBRANCE COMMANDS
    # =================================================================

    @app_commands.command(name="attune", description="Attune to a magic item (requires short rest)")
    @app_commands.describe(item="Name of the magic item to attune to")
    async def attune_cmd(self, interaction: discord.Interaction, item: str):
        """Attune to a magic item from your inventory."""
        from utils.inventory_manager import attune_item, get_attunement_slots

        user_id = str(interaction.user.id)
        success, message = attune_item(user_id, item)
        await interaction.response.send_message(message)

    @app_commands.command(name="unattune", description="End attunement to a magic item")
    @app_commands.describe(item="Name of the magic item to unattune from")
    async def unattune_cmd(self, interaction: discord.Interaction, item: str):
        """End attunement to a magic item."""
        from utils.inventory_manager import unattune_item

        user_id = str(interaction.user.id)
        success, message = unattune_item(user_id, item)
        await interaction.response.send_message(message)

    @app_commands.command(name="attunement", description="View your attunement slots")
    async def attunement_cmd(self, interaction: discord.Interaction):
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

    @app_commands.command(name="encumbrance", description="Check your carrying capacity")
    async def encumbrance_cmd(self, interaction: discord.Interaction):
        """View your encumbrance status."""
        from utils.inventory_manager import format_encumbrance_status

        user_id = str(interaction.user.id)
        char = load_character(user_id)

        if not char:
            await interaction.response.send_message("Create a character first!", ephemeral=True)
            return

        status = format_encumbrance_status(user_id)
        await interaction.response.send_message(status)

    # =================================================================
    # SPELL COMMANDS
    # =================================================================

    @app_commands.command(name="spells", description="View your known and prepared spells")
    async def spells_cmd(self, interaction: discord.Interaction):
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

    @app_commands.command(name="cast", description="Cast a spell")
    @app_commands.describe(
        spell="Name of the spell to cast",
        slot_level="Spell slot level to use (for upcasting)"
    )
    async def cast_cmd(
        self,
        interaction: discord.Interaction,
        spell: str,
        slot_level: Optional[int] = None
    ):
        """Cast a spell, consuming a spell slot."""
        from cogs.combat import check_legendary_actions

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

    @app_commands.command(name="resources", description="View your character's resources (spell slots, class abilities, consumables)")
    async def resources_cmd(self, interaction: discord.Interaction):
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

    @app_commands.command(name="prepare", description="Prepare or unprepare a spell")
    @app_commands.describe(
        spell="Name of the spell",
        remove="Remove spell from prepared list instead of adding"
    )
    async def prepare_cmd(
        self,
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

    @app_commands.command(name="learn", description="Learn a new spell or cantrip")
    @app_commands.describe(
        spell="Name of the spell to learn",
        cantrip="Set to True if learning a cantrip"
    )
    async def learn_cmd(
        self,
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

    @app_commands.command(name="levelup", description="Level up your character")
    @app_commands.describe(
        average_hp="Use average HP instead of rolling"
    )
    async def levelup_cmd(
        self,
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

    # =================================================================
    # XP & LEVELING COMMANDS
    # =================================================================

    @app_commands.command(name="xp", description="View or award XP")
    @app_commands.describe(
        award="Amount of XP to award (leave empty to view)",
        target="Target player (leave empty for self)"
    )
    async def xp_cmd(
        self,
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

    @app_commands.command(name="awardparty", description="Award XP to all party members")
    @app_commands.describe(xp="Total XP to distribute", split="Split evenly among party?")
    async def award_party_cmd(self, interaction: discord.Interaction, xp: int, split: bool = True):
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
