"""Session management commands and voice state event listener."""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging

from utils.state_manager import load_state, save_state
from utils.character_manager import load_character
from utils.voice_parser import clean_for_tts
from utils.session_manager import (
    SessionState, SessionSummary, SessionStatus, PacingPhase, PacingHint,
    load_session_state, save_session_state,
    start_session, end_session, pause_session, resume_session,
    get_session_duration_minutes, get_current_pacing_phase, get_pacing_hints,
    check_for_resume, generate_session_recap,
    format_session_status, format_session_end_summary,
    load_session_summaries, save_recovery_point, load_recovery_point,
    clear_recovery_point, auto_save_manager, calculate_time_since,
)

from cogs.shared import play_tts

logger = logging.getLogger(__name__)


class SessionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # /session
    # =================================================================
    @app_commands.command(
        name="session",
        description="Manage session - view, end, pause, recap, history, recover",
    )
    @app_commands.describe(action="Action to perform")
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="end", value="end"),
        app_commands.Choice(name="pause", value="pause"),
        app_commands.Choice(name="recap", value="recap"),
        app_commands.Choice(name="history", value="history"),
        app_commands.Choice(name="recover", value="recover"),
    ])
    async def session_cmd(self, interaction: discord.Interaction, action: str = "view"):
        """Consolidated session management command."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)

        # === VIEW ===
        if action == "view":
            status_text = format_session_status(channel_id)

            session = load_session_state(channel_id)
            if session.status == SessionStatus.ACTIVE.value:
                phase = get_current_pacing_phase(channel_id)
                duration = get_session_duration_minutes(channel_id)
                status_text += f"\n\n**Pacing:** {phase.value.title()} phase"

                hints = get_pacing_hints(channel_id)
                if hints:
                    status_text += f"\n💡 *Hint: {hints[0].hint}*"

            await interaction.response.send_message(status_text)

        # === END ===
        elif action == "end":
            session = load_session_state(channel_id)
            if session.status == SessionStatus.INACTIVE.value:
                await interaction.response.send_message("❌ No active session to end.")
                return

            await interaction.response.defer()

            await auto_save_manager.stop_auto_save(channel_id)
            auto_save_manager.unregister_channel(channel_id)

            summary = end_session(channel_id, state)

            if summary:
                summary_text = format_session_end_summary(summary)
                await interaction.followup.send(summary_text)

                await play_tts(
                    interaction,
                    f"Session complete! You played for {summary.duration_minutes} minutes. See you next time!",
                    "Narrator",
                )
            else:
                await interaction.followup.send("📊 Session ended.")

        # === PAUSE ===
        elif action == "pause":
            session = load_session_state(channel_id)
            if session.status != SessionStatus.ACTIVE.value:
                await interaction.response.send_message("❌ No active session to pause.")
                return

            pause_session(channel_id)
            await interaction.response.send_message(
                "⏸️ **Session Paused**\nYour progress has been saved. Resume anytime!"
            )

        # === RECAP ===
        elif action == "recap":
            await interaction.response.defer()

            summaries = load_session_summaries(channel_id)

            if not summaries:
                await interaction.followup.send(
                    "📖 No previous session found.\n"
                    "*Start a new campaign with `/campaign`!*"
                )
                return

            recap_text = generate_session_recap(channel_id, state)

            embed = discord.Embed(
                title="📖 Session Recap",
                description=recap_text,
                color=discord.Color.purple(),
            )

            last_session = summaries[-1]
            embed.add_field(
                name="Last Session Stats",
                value=(
                    f"⏱️ Duration: {last_session.duration_minutes} min\n"
                    f"⚔️ Combats: {last_session.combat_count}\n"
                    f"🎯 Actions: {last_session.action_count}"
                ),
                inline=True,
            )

            if last_session.active_quests:
                embed.add_field(
                    name="Active Quests",
                    value="\n".join([f"• {q}" for q in last_session.active_quests[:3]]),
                    inline=True,
                )

            await interaction.followup.send(embed=embed)

            tts_text = clean_for_tts(recap_text)
            if len(tts_text) > 500:
                tts_text = tts_text[:500] + "..."
            await play_tts(interaction, tts_text, "Narrator")

        # === HISTORY ===
        elif action == "history":
            summaries = load_session_summaries(channel_id)

            if not summaries:
                await interaction.response.send_message(
                    "📚 No session history found.\n"
                    "*Sessions are saved when you use `/session action:end`.*"
                )
                return

            embed = discord.Embed(
                title="📚 Session History",
                description=f"Showing last {min(len(summaries), 10)} sessions",
                color=discord.Color.blue(),
            )

            for i, summary in enumerate(reversed(summaries[-10:])):
                started = summary.started_at[:10] if summary.started_at else "Unknown"
                embed.add_field(
                    name=f"Session {len(summaries) - i}",
                    value=(
                        f"📅 {started}\n"
                        f"⏱️ {summary.duration_minutes} min | ⚔️ {summary.combat_count} combats\n"
                        f"📍 {summary.final_location}"
                    ),
                    inline=True,
                )

            await interaction.response.send_message(embed=embed)

        # === RECOVER ===
        elif action == "recover":
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

            campaign_title = campaign_state.get("campaign_title", "Unknown Campaign")
            location = campaign_state.get("location", "Unknown")

            embed = discord.Embed(
                title="🔄 Recovery Point Found",
                description=(
                    f"**Campaign:** {campaign_title}\n"
                    f"**Location:** {location}\n"
                    f"**Saved:** {saved_at}"
                ),
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Restore?",
                value="React with ✅ to restore this state, or ❌ to discard it.",
                inline=False,
            )

            msg = await interaction.followup.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return (
                    user == interaction.user
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == msg.id
                )

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                if str(reaction.emoji) == "✅":
                    save_state(channel_id, campaign_state)
                    clear_recovery_point(channel_id)

                    player_ids = campaign_state.get("players", [str(interaction.user.id)])
                    start_session(channel_id, player_ids)

                    await interaction.channel.send(
                        f"✅ **Recovery Complete!**\n"
                        f"Welcome back to **{campaign_title}**!\n"
                        f"You're in {location}. Use `/recap` to refresh your memory."
                    )

                    await play_tts(
                        interaction,
                        f"Welcome back adventurers! You're in {location}.",
                        "Narrator",
                    )
                else:
                    clear_recovery_point(channel_id)
                    await interaction.channel.send("🗑️ Recovery point discarded.")

            except asyncio.TimeoutError:
                await interaction.channel.send(
                    "⏱️ Recovery timed out. Use `/session action:recover` again when ready."
                )

    # =================================================================
    # Voice state listener — auto-resume
    # =================================================================
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """
        Detect when players join voice channels.
        Offer session resume if they have an active campaign.
        """
        if member.bot:
            return

        if before.channel == after.channel:
            return

        if after.channel is None:
            return

        guild = member.guild
        user_id = str(member.id)

        char = load_character(user_id)
        if not char:
            return

        for text_channel in guild.text_channels:
            channel_id = str(text_channel.id)

            try:
                state = load_state(channel_id)
                if not state.get("campaign_title"):
                    continue

                players = state.get("players", [])
                if user_id not in players:
                    continue

                resume_info = check_for_resume(channel_id)

                if resume_info.get("has_paused_session") or resume_info.get("has_recovery"):
                    session = load_session_state(channel_id)

                    if session.status == SessionStatus.ACTIVE.value:
                        continue

                    voice_members = [m for m in after.channel.members if not m.bot]
                    voice_player_ids = [str(m.id) for m in voice_members]

                    players_in_voice = [p for p in players if p in voice_player_ids]

                    if len(players_in_voice) >= 1:
                        campaign_title = state.get("campaign_title", "Your Campaign")
                        location = state.get("location", "Unknown")

                        embed = discord.Embed(
                            title="🎮 Resume Session?",
                            description=(
                                f"**{campaign_title}**\n"
                                f"📍 Last location: {location}"
                            ),
                            color=discord.Color.green(),
                        )

                        if resume_info.get("has_recovery"):
                            embed.add_field(
                                name="Recovery Available",
                                value="A recovery point was saved. Use `/recover` to restore.",
                                inline=False,
                            )

                        if resume_info.get("last_session"):
                            last = resume_info["last_session"]
                            time_ago = (
                                calculate_time_since(last.ended_at)
                                if hasattr(last, 'ended_at')
                                else 'recently'
                            )
                            embed.add_field(
                                name="Last Session",
                                value=(
                                    f"Played {time_ago}\n"
                                    f"Duration: {last.duration_minutes} min"
                                ),
                                inline=True,
                            )

                        embed.add_field(
                            name="Commands",
                            value=(
                                "• `/sessionrecap` - Hear what happened last time\n"
                                "• `/do <action>` - Jump back into the action\n"
                                "• `/recover` - Restore from crash"
                            ),
                            inline=False,
                        )

                        embed.set_footer(text=f"{len(players_in_voice)} player(s) in voice")

                        try:
                            await text_channel.send(
                                f"👋 <@{user_id}> joined voice!",
                                embed=embed,
                            )

                            resume_session(channel_id, voice_player_ids)

                            def get_campaign_state(ch_id: str) -> dict:
                                return load_state(ch_id)

                            auto_save_manager.register_channel(
                                channel_id, get_campaign_state
                            )
                            asyncio.create_task(
                                auto_save_manager.start_auto_save(channel_id)
                            )

                        except discord.Forbidden:
                            pass

                        return

            except Exception:
                continue


async def setup(bot: commands.Bot):
    await bot.add_cog(SessionCog(bot))
