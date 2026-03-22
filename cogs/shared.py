"""Shared state and helpers used across multiple cogs."""
import discord
from typing import Dict
import logging

from services.openai_service import (
    get_dm_response, narrate_skill_check_outcome,
    narrate_group_check_outcome, narrate_passive_notice
)
from services.elevenlabs_service import text_to_speech_async
from utils.voice_parser import extract_voice_tag, clean_text, clean_for_tts
from utils.voice_map import get_voice_id, get_voice_for_npc, extract_npc_from_tag
from utils.voice_manager import VoiceClientManager
from utils.state_manager import load_state, save_state
from utils.prompt_builder import build_system_prompt
from utils.character_manager import load_character
from utils.skill_check_manager import (
    SkillCheckRequest, SkillCheckResult,
    roll_skill_check, resolve_group_check, GroupCheckResult,
    calculate_passive_score, create_pending_check, get_pending_check,
    add_check_result, complete_pending_check, get_missing_players,
    format_check_result, format_group_check_result, build_roll_prompt
)
from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared mutable state
# ---------------------------------------------------------------------------
_active_channels: Dict[str, discord.TextChannel] = {}

# Voice client manager (singleton)
voice_manager = VoiceClientManager()


# ---------------------------------------------------------------------------
# TTS helper
# ---------------------------------------------------------------------------
async def play_tts(interaction, text: str, voice_tag: str = "Narrator"):
    """Play TTS if enabled and user is in voice channel."""
    from config import Config
    from services.elevenlabs_service import TTS_PROVIDER

    # Quick exit if TTS is disabled via config or provider
    if not Config.TTS_ENABLED or TTS_PROVIDER == 'disabled':
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
        logger.warning(f"TTS error (non-blocking): {e}")


# ---------------------------------------------------------------------------
# Skill check system
# ---------------------------------------------------------------------------
class SkillCheckConfig:
    """Configuration for skill check handling."""
    ROLL_TIMEOUT_SECONDS = Config.SKILL_CHECK_TIMEOUT  # Time to wait for player rolls
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
            except discord.HTTPException as e:
                logger.warning(f"Failed to edit skill check message: {e}")

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
                except discord.HTTPException as e:
                    logger.warning(f"Failed to edit skill check message: {e}")

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
                logger.error(f"Group check narration error: {e}")
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
                        logger.warning(f"TTS error (non-blocking): {tts_err}")

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
                        logger.error(f"Story continuation error: {cont_err}")

                    # Update state to clear pending roll
                    state['pending_roll'] = None
                    save_state(channel_id, state)
                except Exception as e:
                    logger.error(f"Skill check narration error: {e}")


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
            logger.error(f"Passive notice error: {e}")
            await channel.send(f"👁️ **{name}** notices {what}.")
