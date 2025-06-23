import discord
# slash_commands.py
from discord import app_commands
from discord.ext.commands import Bot
from utils.state_manager import load_state, save_state
import random

def register_commands(bot: Bot):
    @bot.tree.command(name="sync-now", description="Manually sync slash commands (admin only)")
    async def sync_now(interaction):
        await interaction.response.send_message("Slash commands synced!")

    @bot.tree.command(name="new-campaign", description="Start a new campaign and set turn order.")
    async def new_campaign(interaction, prompt: str = ""):
        await interaction.response.send_message("Campaign started.")

    @bot.tree.command(name="act", description="Take your turn in the campaign.")
    @app_commands.describe(action="What your character attempts to do")
    async def act(interaction, action: str):
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        state['session_id'] = channel_id
        turn_order = state.get("turn_order", [])
        current_index = state.get("current_turn_index", 0)
        if not turn_order:
            await interaction.response.send_message("No campaign found. Use /new-campaign to start one.")
            return
        current_player_id = turn_order[current_index]
        if str(interaction.user.id) != current_player_id:
            await interaction.response.send_message(f"It's not your turn. It's <@{current_player_id}>'s turn.")
            return
        await interaction.response.defer()
        user_action = action
        from utils.logger import log_message
        log_message(channel_id, interaction.user.display_name, f"/act {user_action}")
        from services.openai_service import get_dm_response
        from utils.voice_parser import extract_voice_tag, clean_text
        narration, updated_state = get_dm_response(user_action, state, current_player_id)
        voice_tag = extract_voice_tag(narration)
        text = clean_text(narration)
        pending = updated_state.get('pending_roll')
        if pending and str(pending.get('player_id')) == str(current_player_id):
            output = f"Narrator: {text}\n\nYou must now /roll your {pending['type']} check."
        else:
            output = f"Narrator: {text}\n\nWhat do you do next?"
        log_message(channel_id, voice_tag or 'Narrator', text)
        await interaction.followup.send(output)
        save_state(channel_id, updated_state)

    @bot.tree.command(name="end-turn", description="End your turn and advance to the next player.")
    async def end_turn(interaction):
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        from utils.state_manager import get_turn_order, get_current_turn_index, set_current_turn_index
        turn_order = get_turn_order(state)
        idx = get_current_turn_index(state)
        if not turn_order or idx >= len(turn_order):
            await interaction.response.send_message("No active turn order. Start a campaign first.", ephemeral=True)
            return
        current_player_id = turn_order[idx]
        if str(interaction.user.id) != current_player_id:
            await interaction.response.send_message(f"⏳ Please wait your turn, <@{interaction.user.id}>.", ephemeral=True)
            return
        next_idx = (idx + 1) % len(turn_order)
        set_current_turn_index(state, next_idx)
        save_state(channel_id, state)
        next_player_id = turn_order[next_idx]
        next_player_mention = f"<@{next_player_id}>"
        msg = f"{next_player_mention}, it's your turn. What do you do?"
        await interaction.response.send_message(msg)
        from utils.voice_map import get_voice_id
        from services.elevenlabs_service import text_to_speech
        try:
            audio_bytes = text_to_speech(msg, get_voice_id("Narrator"))
        except Exception as e:
            print(f"TTS Error: {e}")
            audio_bytes = None
        if audio_bytes and interaction.user.voice and interaction.user.voice.channel:
            from discord.ext.commands import Bot
            bot_obj = interaction.client if isinstance(interaction.client, Bot) else None
            if bot_obj:
                await bot_obj.play_audio_in_voice(interaction.user.voice.channel, audio_bytes)

    @bot.tree.command(name="start-adventure", description="Generate a new campaign setup with an optional prompt")
    async def start_adventure(interaction, prompt: str = ""):
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        await interaction.response.defer()
        from services.openai_service import generate_campaign
        from utils.voice_parser import clean_text
        from utils.voice_map import get_voice_id
        from services.elevenlabs_service import text_to_speech
        campaign_text, updated_state = generate_campaign(state, prompt if prompt else None)
        save_state(channel_id, updated_state)
        tts_text = clean_text(campaign_text)
        voice_id = get_voice_id("Narrator")
        await interaction.followup.send(f"**New Adventure:**\n{campaign_text}")
        if interaction.user.voice and interaction.user.voice.channel:
            try:
                audio_bytes = text_to_speech(tts_text, voice_id)
                from discord.ext.commands import Bot
                bot_obj = interaction.client if isinstance(interaction.client, Bot) else None
                if bot_obj:
                    await bot_obj.play_audio_in_voice(interaction.user.voice.channel, audio_bytes)
            except Exception as e:
                print(f"TTS Error: {e}")

    @bot.tree.command(name="roll", description="Resolve a pending roll (e.g. /roll 17)")
    @app_commands.describe(result="The number you rolled on your dice")
    async def roll(interaction, result: int):
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        state['session_id'] = channel_id
        pending = state.get('pending_roll')
        if not pending:
            await interaction.response.send_message("No roll is currently pending.", ephemeral=True)
            return
        if str(interaction.user.id) != str(pending.get('player_id')):
            await interaction.response.send_message("It's not your turn to roll.", ephemeral=True)
            return
        import re
        roll_type = pending.get('type', 'check')
        dice_match = re.search(r'(\d*)d(\d+)', roll_type)
        if dice_match:
            num = int(dice_match.group(1)) if dice_match.group(1) else 1
            sides = int(dice_match.group(2))
            min_roll = num
            max_roll = num * sides
            if not (min_roll <= result <= max_roll):
                await interaction.response.send_message(f"Roll must be between {min_roll} and {max_roll} for {roll_type}.", ephemeral=True)
                return
        elif 'd20' in roll_type.lower() or 'check' in roll_type.lower() or 'save' in roll_type.lower() or 'to hit' in roll_type.lower():
            if not (1 <= result <= 20):
                await interaction.response.send_message("Roll must be between 1 and 20.", ephemeral=True)
                return
        from utils.logger import log_message
        player_name = interaction.user.display_name
        log_message(channel_id, player_name, f"/roll {result} for {roll_type}")
        roll_msg = f"The player rolled a {result} on their {roll_type}."
        turn_context = f"It is @{player_name}'s turn."
        gpt_input = turn_context + "\n" + roll_msg
        from services.openai_service import get_dm_response
        from utils.voice_parser import extract_voice_tag, clean_text
        try:
            narration, updated_state = get_dm_response(gpt_input, state, str(interaction.user.id))
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)
            return
        voice_tag = extract_voice_tag(narration)
        text = clean_text(narration)
        updated_state.pop('pending_roll', None)
        save_state(channel_id, updated_state)
        log_message(channel_id, voice_tag or 'Narrator', text)
        await interaction.response.send_message(f"Narrator: {text}\n\nWhat do you do next?")

    @bot.tree.command(name="reset-campaign", description="Reset the campaign for this channel (admin only)")
    async def reset_campaign(interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an admin to use this command.", ephemeral=True)
            return
        channel_id = str(interaction.channel.id)
        save_state(channel_id, {})
        await interaction.response.send_message("Campaign state has been reset for this channel.")

    @bot.tree.command(name="force-turn", description="Force the turn to a specific player (admin only, debugging)")
    @app_commands.describe(user="The user to set as the current turn")
    async def force_turn(interaction, user: discord.User):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an admin to use this command.", ephemeral=True)
            return
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        turn_order = state.get('turn_order', [])
        if not turn_order:
            await interaction.response.send_message("No turn order set for this channel.", ephemeral=True)
            return
        if str(user.id) not in turn_order:
            await interaction.response.send_message("That user is not in the turn order.", ephemeral=True)
            return
        idx = turn_order.index(str(user.id))
        from utils.state_manager import set_current_turn_index
        set_current_turn_index(state, idx)
        save_state(channel_id, state)
        await interaction.response.send_message(f"Turn forced to {user.mention}.")
