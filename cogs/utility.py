"""Utility commands — handouts, secrets, maps, loot, ambient, reactions, voice, and misc."""
import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
from typing import Optional

from utils.state_manager import (
    load_state, save_state, get_turn_order,
    get_current_turn_index, set_current_turn_index,
)
from utils.character_manager import (
    load_character, save_character, get_ability_modifier,
)
from utils.combat_manager import load_combat
from utils.handout_manager import (
    create_handout, get_handout, get_handouts_for_player,
    get_all_handouts, reveal_handout, share_handout_with,
    mark_as_read, delete_handout, add_player_secret,
    get_player_secrets, get_unread_secrets, mark_secret_read,
    HANDOUT_TYPES, get_handout_emoji, format_handout_display,
)
from utils.map_manager import (
    TacticalMap, Token, load_map, save_map, delete_map,
    create_from_template, TERRAIN_TYPES, TOKEN_SYMBOLS, MAP_TEMPLATES,
)
from utils.loot_manager import (
    generate_treasure_hoard, generate_enemy_loot, roll_magic_item,
    format_loot_display, format_currency, Rarity,
)
from utils.ambient_manager import (
    ambient_manager, AmbientMood, SoundEffect,
)
from utils.reaction_manager import (
    has_reaction_available, use_reaction, ReactionType,
    resolve_opportunity_attack, cast_shield, cast_counterspell,
    use_uncanny_dodge,
)
from utils.xp_manager import format_xp_bar
from utils.logger import get_log_file, log_message
from services.openai_service import summarize_history

from cogs.shared import play_tts, voice_manager

logger = logging.getLogger(__name__)

# ─── Choice constants ────────────────────────────────────────────────────────

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

HANDOUT_ACTION_CHOICES = [
    app_commands.Choice(name="📜 View - List your handouts", value="view"),
    app_commands.Choice(name="📖 Read - Read a specific handout", value="read"),
    app_commands.Choice(name="➕ Create - Create a new handout [DM]", value="create"),
    app_commands.Choice(name="👁️ Reveal - Reveal to all players [DM]", value="reveal"),
    app_commands.Choice(name="📤 Share - Share with a player [DM]", value="share"),
    app_commands.Choice(name="🗑️ Delete - Delete a handout [DM]", value="delete"),
    app_commands.Choice(name="📋 List All - View all handouts [DM]", value="list-all"),
]

MAP_TEMPLATE_CHOICES = [
    app_commands.Choice(name="🏰 Dungeon Room", value="dungeon"),
    app_commands.Choice(name="🌲 Forest Clearing", value="forest"),
    app_commands.Choice(name="🍺 Tavern", value="tavern"),
    app_commands.Choice(name="🕳️ Cave", value="cave"),
]

MAP_ACTION_CHOICES = [
    app_commands.Choice(name="🗺️ View - Display current map", value="view"),
    app_commands.Choice(name="➕ Create - Create a new map", value="create"),
    app_commands.Choice(name="🎯 Add Token - Place a token", value="add-token"),
    app_commands.Choice(name="🏃 Move - Move a token", value="move"),
    app_commands.Choice(name="🗑️ Remove - Remove a token", value="remove"),
    app_commands.Choice(name="📏 Distance - Measure between tokens", value="distance"),
    app_commands.Choice(name="🎯 Range - Find tokens in range", value="range"),
    app_commands.Choice(name="🏔️ Terrain - Set terrain type", value="terrain"),
    app_commands.Choice(name="❌ Clear - Delete the map", value="clear"),
]

TOKEN_TYPE_CHOICES = [
    app_commands.Choice(name="🔵 Player", value="player"),
    app_commands.Choice(name="🔴 Enemy", value="enemy"),
    app_commands.Choice(name="🟢 NPC", value="npc"),
    app_commands.Choice(name="🟣 Boss", value="boss"),
    app_commands.Choice(name="⬜ Object", value="object"),
]

MAP_TERRAIN_CHOICES = [
    app_commands.Choice(name=". Floor", value="floor"),
    app_commands.Choice(name="# Wall", value="wall"),
    app_commands.Choice(name="~ Water", value="water"),
    app_commands.Choice(name=": Difficult Terrain", value="difficult"),
    app_commands.Choice(name="+ Door", value="door"),
    app_commands.Choice(name="X Locked Door", value="door_locked"),
    app_commands.Choice(name="O Pillar", value="pillar"),
    app_commands.Choice(name="T Tree", value="tree"),
    app_commands.Choice(name="^ Rubble", value="rubble"),
]


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # /say
    # =================================================================
    @app_commands.command(name="say", description="Say something in character")
    @app_commands.describe(speech="What does your character say?")
    async def say_action(self, interaction: discord.Interaction, speech: str):
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

    # =================================================================
    # /done
    # =================================================================
    @app_commands.command(name="done", description="End your turn")
    async def end_turn(self, interaction: discord.Interaction):
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

        next_idx = (idx + 1) % len(turn_order)
        set_current_turn_index(state, next_idx)
        save_state(channel_id, state)

        next_player_id = turn_order[next_idx]
        next_char = load_character(next_player_id)
        char_name = next_char.get('name', 'adventurer') if next_char else 'adventurer'

        await interaction.response.send_message(f"➡️ <@{next_player_id}>, it's your turn! What does **{char_name}** do?")
        log_message(channel_id, "DM", f"Turn passed to {char_name}")

        await play_tts(interaction, f"Your turn, {char_name}. What do you do?", "Narrator")

    # =================================================================
    # /status
    # =================================================================
    @app_commands.command(name="status", description="Show current campaign status")
    async def status(self, interaction: discord.Interaction):
        """Display campaign and party status."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)

        if not state.get("campaign_title"):
            await interaction.response.send_message("No campaign running. Use `/campaign` to start one!")
            return

        turn_order = state.get("turn_order", [])
        current_idx = state.get("current_turn_index", 0)
        current_player = turn_order[current_idx] if turn_order else None

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

    # =================================================================
    # /recap
    # =================================================================
    @app_commands.command(name="recap", description="Get a summary of recent events")
    async def recap(self, interaction: discord.Interaction):
        """Summarize what happened recently."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)

        if not state.get("campaign_title"):
            await interaction.response.send_message("No campaign running.")
            return

        await interaction.response.defer()
        summary = summarize_history(state)
        await interaction.followup.send(f"📖 **Previously...**\n\n{summary}")

    # =================================================================
    # /handout
    # =================================================================
    @app_commands.command(name="handout", description="Manage handouts and player documents")
    @app_commands.describe(
        action="What to do with handouts",
        handout_id="Handout ID (for read, reveal, share, delete)",
        title="Title (for create)",
        content="Content text (for create)",
        handout_type="Type of handout (for create)",
        image_url="Image URL (for create)",
        player="Player to share with (for create, share)",
    )
    @app_commands.choices(
        action=HANDOUT_ACTION_CHOICES,
        handout_type=HANDOUT_TYPE_CHOICES,
    )
    async def handout_cmd(
        self,
        interaction: discord.Interaction,
        action: str = "view",
        handout_id: Optional[int] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        handout_type: str = "note",
        image_url: Optional[str] = None,
        player: Optional[discord.Member] = None,
    ):
        """Consolidated handout command."""
        channel_id = str(interaction.channel.id)
        player_id = str(interaction.user.id)

        # VIEW
        if action == "view":
            handouts = get_handouts_for_player(channel_id, player_id)
            if not handouts:
                await interaction.response.send_message(
                    "📜 No handouts available yet.\n"
                    "*The DM can create handouts with `/handout action:create`*",
                    ephemeral=True,
                )
                return

            for h in handouts:
                mark_as_read(channel_id, h["id"], player_id)

            output = "# 📜 Your Handouts\n\n"
            for handout in handouts:
                emoji = get_handout_emoji(handout["type"])
                output += f"{emoji} **{handout['title']}** (ID: {handout['id']})\n"
                preview = handout["content"][:100]
                if len(handout["content"]) > 100:
                    preview += "..."
                output += f"*{preview}*\n\n"

            output += "*Use `/handout action:read handout_id:<id>` to view full content*"
            await interaction.response.send_message(output, ephemeral=True)

        # READ
        elif action == "read":
            if handout_id is None:
                await interaction.response.send_message(
                    "❌ Required: `handout_id`\nExample: `/handout action:read handout_id:1`",
                    ephemeral=True,
                )
                return

            visible_handouts = get_handouts_for_player(channel_id, player_id)
            handout = None
            for h in visible_handouts:
                if h["id"] == handout_id:
                    handout = h
                    break

            if not handout:
                await interaction.response.send_message(
                    "❌ Handout not found or you don't have access to it.", ephemeral=True
                )
                return

            mark_as_read(channel_id, handout_id, player_id)
            output = format_handout_display(handout)
            if handout.get("image_url"):
                output += f"\n\n🖼️ {handout['image_url']}"
            await interaction.response.send_message(output, ephemeral=True)

        # CREATE
        elif action == "create":
            if not title or not content:
                await interaction.response.send_message(
                    "❌ Required: `title`, `content`\n"
                    "Example: `/handout action:create title:Ancient Map content:This map shows...`",
                    ephemeral=True,
                )
                return

            visible_to = [str(player.id)] if player else None

            handout = create_handout(
                channel_id=channel_id,
                title=title,
                content=content,
                handout_type=handout_type,
                image_url=image_url,
                visible_to=visible_to,
                created_by=str(interaction.user.id),
            )

            emoji = get_handout_emoji(handout_type)

            if player:
                await interaction.response.send_message(
                    f"{emoji} **Handout created for {player.display_name}:**\n"
                    f"*{title}*\n\n"
                    f"They can view it with `/handout action:view`",
                    ephemeral=True,
                )
                try:
                    await player.send(
                        f"{emoji} **New Handout: {title}**\n"
                        f"───────────────────────\n"
                        f"{content}\n"
                        + (f"\n🖼️ {image_url}" if image_url else "")
                    )
                except discord.Forbidden:
                    logger.warning(f"Cannot DM handout to player {player.display_name} — DMs disabled")
            else:
                output = (
                    f"{emoji} **{title}**\n"
                    f"───────────────────────\n"
                    f"{content}"
                )
                if image_url:
                    output += f"\n\n🖼️ {image_url}"
                await interaction.response.send_message(output)

        # REVEAL
        elif action == "reveal":
            if handout_id is None:
                await interaction.response.send_message(
                    "❌ Required: `handout_id`\nExample: `/handout action:reveal handout_id:1`",
                    ephemeral=True,
                )
                return

            handout = reveal_handout(channel_id, handout_id)
            if not handout:
                await interaction.response.send_message("❌ Handout not found.", ephemeral=True)
                return

            output = format_handout_display(handout)
            if handout.get("image_url"):
                output += f"\n\n🖼️ {handout['image_url']}"
            await interaction.response.send_message(f"📜 **The DM reveals a handout!**\n\n{output}")

        # SHARE
        elif action == "share":
            if handout_id is None or not player:
                await interaction.response.send_message(
                    "❌ Required: `handout_id`, `player`\n"
                    "Example: `/handout action:share handout_id:1 player:@Someone`",
                    ephemeral=True,
                )
                return

            handout = share_handout_with(channel_id, handout_id, [str(player.id)])
            if not handout:
                await interaction.response.send_message("❌ Handout not found.", ephemeral=True)
                return

            await interaction.response.send_message(
                f"📜 Shared **{handout['title']}** with {player.display_name}",
                ephemeral=True,
            )
            try:
                emoji = get_handout_emoji(handout["type"])
                await player.send(
                    f"{emoji} **New Handout: {handout['title']}**\n"
                    f"───────────────────────\n"
                    f"{handout['content']}\n"
                    + (f"\n🖼️ {handout['image_url']}" if handout.get('image_url') else "")
                )
            except discord.Forbidden:
                logger.warning(f"Cannot DM shared handout to player {player.display_name} — DMs disabled")

        # DELETE
        elif action == "delete":
            if handout_id is None:
                await interaction.response.send_message(
                    "❌ Required: `handout_id`\nExample: `/handout action:delete handout_id:1`",
                    ephemeral=True,
                )
                return

            if delete_handout(channel_id, handout_id):
                await interaction.response.send_message(f"🗑️ Handout #{handout_id} deleted.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Handout not found.", ephemeral=True)

        # LIST-ALL
        elif action == "list-all":
            handouts = get_all_handouts(channel_id)
            if not handouts:
                await interaction.response.send_message(
                    "📜 No handouts created yet.\n"
                    "Use `/handout action:create` to create one!",
                    ephemeral=True,
                )
                return

            output = "# 📜 All Campaign Handouts\n\n"
            for handout in handouts:
                emoji = get_handout_emoji(handout["type"])
                if handout["visible_to"] is None:
                    visibility = "👁️ Everyone"
                else:
                    count = len(handout["visible_to"])
                    visibility = f"🔒 {count} player(s)"
                read_count = len(handout.get("read_by", []))
                output += (
                    f"{emoji} **{handout['title']}** (ID: {handout['id']})\n"
                    f"   Type: {handout['type']} | {visibility} | Read by: {read_count}\n\n"
                )
            output += (
                "───────────────────────\n"
                "**Actions:** create, reveal, share, delete"
            )
            await interaction.response.send_message(output, ephemeral=True)

    # =================================================================
    # /secret
    # =================================================================
    @app_commands.command(name="secret", description="Send a secret message to a specific player")
    @app_commands.describe(
        player="The player to receive the secret",
        message="The secret message (only they will see it)",
        title="Optional title for the secret",
    )
    async def secret_cmd(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        message: str,
        title: Optional[str] = None,
    ):
        """Send a secret message only visible to one player."""
        channel_id = str(interaction.channel.id)
        player_id = str(player.id)

        secret = add_player_secret(channel_id, player_id, message, title)

        await interaction.response.send_message(
            f"🤫 Secret sent to **{player.display_name}**:\n"
            f"*\"{message[:50]}{'...' if len(message) > 50 else ''}\"*",
            ephemeral=True,
        )

        try:
            char = load_character(player_id)
            char_name = char.get('name', player.display_name) if char else player.display_name
            await player.send(
                f"🤫 **Secret for {char_name}:**\n"
                f"───────────────────────\n"
                f"{message}\n\n"
                f"*Only you can see this message.*"
            )
        except discord.Forbidden:
            logger.warning(f"Cannot DM secret to player {player.display_name} — DMs disabled")

    # =================================================================
    # /mysecrets
    # =================================================================
    @app_commands.command(name="mysecrets", description="View secrets shared with you")
    async def mysecrets_cmd(self, interaction: discord.Interaction):
        """View all secret messages sent to you."""
        channel_id = str(interaction.channel.id)
        player_id = str(interaction.user.id)

        secrets = get_player_secrets(channel_id, player_id)
        if not secrets:
            await interaction.response.send_message(
                "🤫 No secrets for you... yet.\n"
                "*The DM may share secrets with you during the game.*",
                ephemeral=True,
            )
            return

        for s in secrets:
            mark_secret_read(channel_id, player_id, s["id"])

        output = "# 🤫 Your Secrets\n\n"
        for secret in secrets:
            title_text = secret.get("title", "Secret")
            output += f"**{title_text}:**\n"
            output += f"*{secret['content']}*\n\n"
        output += "*Only you can see these messages.*"
        await interaction.response.send_message(output, ephemeral=True)

    # =================================================================
    # /map
    # =================================================================
    @app_commands.command(name="map", description="Manage tactical battle maps")
    @app_commands.describe(
        action="What to do with the map",
        name="Token/map name (for add-token, move, remove, distance, range, create)",
        x="X position (for add-token, move, terrain)",
        y="Y position (for add-token, move, terrain)",
        token_type="Type of token (for add-token)",
        template="Map template (for create)",
        width="Map width 5-30 (for create)",
        height="Map height 5-25 (for create)",
        target="Second token name (for distance)",
        range_feet="Range in feet (for range)",
        terrain="Terrain type (for terrain)",
    )
    @app_commands.choices(
        action=MAP_ACTION_CHOICES,
        token_type=TOKEN_TYPE_CHOICES,
        template=MAP_TEMPLATE_CHOICES,
        terrain=MAP_TERRAIN_CHOICES,
    )
    async def map_cmd(
        self,
        interaction: discord.Interaction,
        action: str = "view",
        name: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        token_type: str = "player",
        template: str = "dungeon",
        width: float = 20.0,
        height: float = 15.0,
        target: Optional[str] = None,
        range_feet: float = 30.0,
        terrain: str = "floor",
    ):
        """Consolidated tactical map command."""
        channel_id = str(interaction.channel.id)

        # VIEW
        if action == "view":
            map_obj = load_map(channel_id)
            if not map_obj:
                await interaction.response.send_message(
                    "🗺️ No map active.\nUse `/map action:create` to create one!",
                    ephemeral=True,
                )
                return
            await interaction.response.send_message(map_obj.render_discord())

        # CREATE
        elif action == "create":
            map_name = name or "Battle Map"
            width = max(5, min(30, width))
            height = max(5, min(25, height))
            map_obj = create_from_template(template, width=width, height=height, name=map_name)
            if not map_obj:
                map_obj = TacticalMap(width, height, map_name)
            save_map(channel_id, map_obj)
            await interaction.response.send_message(
                f"🗺️ **New map created!**\n\n{map_obj.render_discord()}"
            )

        # ADD-TOKEN
        elif action == "add-token":
            if not name or x is None or y is None:
                await interaction.response.send_message(
                    "❌ Required: `name`, `x`, `y`\n"
                    "Example: `/map action:add-token name:Goblin x:5 y:3`",
                    ephemeral=True,
                )
                return
            map_obj = load_map(channel_id)
            if not map_obj:
                await interaction.response.send_message(
                    "No map active. Use `/map action:create` first!", ephemeral=True
                )
                return
            token = map_obj.add_token(name, x, y, token_type)
            if not token:
                await interaction.response.send_message(
                    f"❌ Position ({x},{y}) is out of bounds!", ephemeral=True
                )
                return
            save_map(channel_id, map_obj)
            emoji = TOKEN_SYMBOLS.get(token_type, TOKEN_SYMBOLS["player"])["color"]
            await interaction.response.send_message(
                f"{emoji} **{name}** placed at ({x},{y})\n\n{map_obj.render_discord()}"
            )

        # MOVE
        elif action == "move":
            if not name or x is None or y is None:
                await interaction.response.send_message(
                    "❌ Required: `name`, `x`, `y`\n"
                    "Example: `/map action:move name:Goblin x:8 y:5`",
                    ephemeral=True,
                )
                return
            map_obj = load_map(channel_id)
            if not map_obj:
                await interaction.response.send_message("No map active.", ephemeral=True)
                return
            old_pos = map_obj.move_token(name, x, y)
            if old_pos is None:
                await interaction.response.send_message(
                    f"❌ Token '{name}' not found or position out of bounds!", ephemeral=True
                )
                return
            save_map(channel_id, map_obj)
            distance = max(abs(x - old_pos[0]), abs(y - old_pos[1])) * map_obj.scale
            await interaction.response.send_message(
                f"🏃 **{name}** moved from ({old_pos[0]},{old_pos[1]}) to ({x},{y}) [{distance}ft]\n\n"
                f"{map_obj.render_discord()}"
            )

        # REMOVE
        elif action == "remove":
            if not name:
                await interaction.response.send_message(
                    "❌ Required: `name`\nExample: `/map action:remove name:Goblin`",
                    ephemeral=True,
                )
                return
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
                    f"❌ Token '{name}' not found.", ephemeral=True
                )

        # DISTANCE
        elif action == "distance":
            if not name or not target:
                await interaction.response.send_message(
                    "❌ Required: `name`, `target`\n"
                    "Example: `/map action:distance name:Player target:Goblin`",
                    ephemeral=True,
                )
                return
            map_obj = load_map(channel_id)
            if not map_obj:
                await interaction.response.send_message("No map active.", ephemeral=True)
                return
            dist = map_obj.get_distance(name, target)
            if dist is None:
                await interaction.response.send_message(
                    "❌ One or both tokens not found.", ephemeral=True
                )
                return
            t1 = map_obj.get_token(name)
            t2 = map_obj.get_token(target)
            await interaction.response.send_message(
                f"📏 Distance from **{name}** ({t1.x},{t1.y}) to **{target}** ({t2.x},{t2.y}): **{dist} feet**"
            )

        # RANGE
        elif action == "range":
            if not name:
                await interaction.response.send_message(
                    "❌ Required: `name`\nExample: `/map action:range name:Player range_feet:30`",
                    ephemeral=True,
                )
                return
            map_obj = load_map(channel_id)
            if not map_obj:
                await interaction.response.send_message("No map active.", ephemeral=True)
                return
            center = map_obj.get_token(name)
            if not center:
                await interaction.response.send_message(
                    f"❌ Token '{name}' not found.", ephemeral=True
                )
                return
            in_range = map_obj.get_tokens_in_range(name, range_feet)
            if not in_range:
                await interaction.response.send_message(
                    f"📏 No tokens within {range_feet}ft of **{name}**"
                )
                return
            token_list = []
            for tkn in in_range:
                d = map_obj.get_distance(name, tkn.name)
                emoji = TOKEN_SYMBOLS.get(tkn.token_type, TOKEN_SYMBOLS["player"])["color"]
                token_list.append(f"{emoji} **{tkn.name}** - {d}ft")
            await interaction.response.send_message(
                f"📏 Tokens within {range_feet}ft of **{name}**:\n" + "\n".join(token_list)
            )

        # TERRAIN
        elif action == "terrain":
            if x is None or y is None:
                await interaction.response.send_message(
                    "❌ Required: `x`, `y`\nExample: `/map action:terrain x:5 y:3 terrain:wall`",
                    ephemeral=True,
                )
                return
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
                    f"❌ Position ({x},{y}) is out of bounds!", ephemeral=True
                )

        # CLEAR
        elif action == "clear":
            if delete_map(channel_id):
                await interaction.response.send_message("🗑️ Map deleted.")
            else:
                await interaction.response.send_message("No map to delete.", ephemeral=True)

    # =================================================================
    # /ambient
    # =================================================================
    @app_commands.command(name="ambient", description="Set ambient music mood")
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
    async def ambient_cmd(self, interaction: discord.Interaction, mood: str):
        """Set the ambient music mood."""
        if not interaction.guild:
            await interaction.response.send_message("Must be in a server.", ephemeral=True)
            return

        try:
            ambient_mood = AmbientMood(mood)
        except ValueError:
            await interaction.response.send_message("Invalid mood.", ephemeral=True)
            return

        voice_client = interaction.guild.voice_client
        if voice_client:
            await ambient_manager.set_mood(voice_client, ambient_mood)
            await interaction.response.send_message(f"🎵 Ambient mood set to **{mood.title()}**")
        else:
            state = ambient_manager.get_state(interaction.guild.id)
            state['current_mood'] = ambient_mood
            await interaction.response.send_message(
                f"🎵 Ambient mood queued: **{mood.title()}** (join voice to hear)"
            )

    # =================================================================
    # /sfx
    # =================================================================
    @app_commands.command(name="sfx", description="Play a sound effect")
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
    async def sfx_cmd(self, interaction: discord.Interaction, effect: str):
        """Play a sound effect."""
        if not interaction.guild:
            await interaction.response.send_message("Must be in a server.", ephemeral=True)
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                "Bot must be in a voice channel. Use `/joinvoice`", ephemeral=True
            )
            return

        try:
            sfx = SoundEffect(effect)
            await ambient_manager.play_sfx(voice_client, sfx)
            await interaction.response.send_message(f"🔊 Playing: {effect.replace('_', ' ').title()}")
        except Exception as e:
            await interaction.response.send_message(f"Could not play sound effect: {e}", ephemeral=True)

    # =================================================================
    # /reaction
    # =================================================================
    @app_commands.command(name="reaction", description="Use your reaction in combat")
    @app_commands.describe(
        reaction_type="Type of reaction to use",
        target="Target of the reaction (if applicable)",
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
        self,
        interaction: discord.Interaction,
        reaction_type: str,
        target: Optional[str] = None,
    ):
        """Use your reaction in combat."""
        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)

        char = load_character(user_id)
        if not char:
            await interaction.response.send_message("Create a character first!", ephemeral=True)
            return

        char_name = char.get('name', 'Character')

        combat = load_combat(channel_id)
        if not combat or not combat.get('active'):
            await interaction.response.send_message("No active combat!", ephemeral=True)
            return

        if not has_reaction_available(channel_id, char_name):
            await interaction.response.send_message(
                "You've already used your reaction this round!", ephemeral=True
            )
            return

        try:
            rtype = ReactionType(reaction_type)
        except ValueError:
            await interaction.response.send_message("Invalid reaction type.", ephemeral=True)
            return

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
                await interaction.response.send_message(
                    "Specify the spell level being countered!", ephemeral=True
                )
                return
            try:
                spell_level = int(target)
            except ValueError:
                spell_level = 3
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
                await interaction.response.send_message(
                    "Specify the damage amount to halve!", ephemeral=True
                )
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
                await interaction.response.send_message(
                    "Specify the target of your opportunity attack!", ephemeral=True
                )
                return
            attack_bonus = get_ability_modifier(char.get('STR', 10)) + char.get('proficiency', 2)
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
            result = use_reaction(channel_id, char_name, rtype)
            if result.get('error'):
                await interaction.response.send_message(result['error'], ephemeral=True)
                return
            await interaction.response.send_message(
                f"⚡ **{char_name}** uses **{reaction_type.replace('_', ' ').title()}**!"
            )

    # =================================================================
    # /loot
    # =================================================================
    @app_commands.command(name="loot", description="Generate random loot")
    @app_commands.describe(cr="Challenge Rating for loot scaling", loot_type="Type of loot to generate")
    @app_commands.choices(loot_type=[
        app_commands.Choice(name="Treasure Hoard", value="hoard"),
        app_commands.Choice(name="Enemy Drop", value="enemy"),
        app_commands.Choice(name="Magic Item", value="magic"),
    ])
    async def loot_cmd(
        self,
        interaction: discord.Interaction,
        cr: int = 1,
        loot_type: str = "enemy",
    ):
        """Generate random loot based on CR."""
        from utils.inventory_manager import create_loot_distribution

        channel_id = str(interaction.channel_id)

        if loot_type == "hoard":
            loot = generate_treasure_hoard(cr)
            msg = f"💰 **Treasure Hoard (CR {cr})**\n"
            msg += format_loot_display(loot)
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
                create_loot_distribution(channel_id, [item['name']], {})
                msg += "\n\n*Use `/claimloot <item>` to claim!*"
            else:
                msg = "No magic item generated."
        else:
            loot = generate_enemy_loot("Defeated Enemy", cr)
            msg = f"🗡️ **Enemy Loot (CR {cr})**\n"
            msg += format_loot_display(loot)
            items = loot.get('items', [])
            if items or loot.get('currency'):
                create_loot_distribution(channel_id, items, loot.get('currency', {}))
                msg += "\n\n*Use `/claimloot <item>` or `/claimgold` to claim!*"

        await interaction.response.send_message(msg)

    # =================================================================
    # /treasure
    # =================================================================
    @app_commands.command(name="treasure", description="Generate a treasure hoard")
    @app_commands.describe(cr="Challenge Rating of the encounter")
    async def treasure_cmd(self, interaction: discord.Interaction, cr: int = 5):
        """Generate a full treasure hoard."""
        loot = generate_treasure_hoard(cr, include_magic=True)

        lines = [f"💎 **Treasure Hoard** (CR {cr})"]
        lines.append("═══════════════════════")

        if loot.get('currency'):
            lines.append(f"🪙 **Coins:** {format_currency(loot['currency'])}")
        if loot.get('gems'):
            lines.append("💎 **Gems:**")
            for gem, value in loot['gems']:
                lines.append(f"  • {gem} ({value} gp)")
        if loot.get('art_objects'):
            lines.append("🖼️ **Art Objects:**")
            for obj, value in loot['art_objects']:
                lines.append(f"  • {obj} ({value} gp)")
        if loot.get('magic_items'):
            lines.append("✨ **Magic Items:**")
            for item in loot['magic_items']:
                lines.append(f"  {item['rarity_icon']} **{item['name']}**")
                lines.append(f"    *{item['effect']}*")
        if loot.get('mundane'):
            lines.append(f"📦 **Other Items:** {', '.join(loot['mundane'])}")

        await interaction.response.send_message("\n".join(lines))

    # =================================================================
    # /identify
    # =================================================================
    @app_commands.command(name="identify", description="Attempt to identify a magic item")
    @app_commands.describe(
        item="The unidentified item to identify",
        method="How to identify: arcana (DC 15 check), identify (spell), or rest (short rest)",
    )
    @app_commands.choices(method=[
        app_commands.Choice(name="Arcana Check (DC 15)", value="arcana"),
        app_commands.Choice(name="Identify Spell", value="identify"),
        app_commands.Choice(name="Short Rest with Item", value="short_rest"),
    ])
    async def identify_cmd(
        self,
        interaction: discord.Interaction,
        item: str,
        method: str = "arcana",
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

    # =================================================================
    # /lootpile
    # =================================================================
    @app_commands.command(name="lootpile", description="View unclaimed loot")
    async def lootpile_cmd(self, interaction: discord.Interaction):
        """View the current loot pile available to claim."""
        from utils.inventory_manager import format_pending_loot

        channel_id = str(interaction.channel_id)
        display = format_pending_loot(channel_id)
        await interaction.response.send_message(display)

    # =================================================================
    # /claimloot
    # =================================================================
    @app_commands.command(name="claimloot", description="Claim an item from the loot pile")
    @app_commands.describe(item="Name of the item to claim")
    async def claimloot_cmd(self, interaction: discord.Interaction, item: str):
        """Claim an item from pending loot."""
        from utils.inventory_manager import claim_loot_item

        channel_id = str(interaction.channel_id)
        user_id = str(interaction.user.id)
        success, message = claim_loot_item(channel_id, user_id, item)
        await interaction.response.send_message(message)

    # =================================================================
    # /claimgold
    # =================================================================
    @app_commands.command(name="claimgold", description="Claim gold from the loot pile")
    @app_commands.describe(amount="Amount of gold to claim (leave empty for all)")
    async def claimgold_cmd(self, interaction: discord.Interaction, amount: Optional[int] = None):
        """Claim gold from pending loot."""
        from utils.inventory_manager import claim_loot_gold

        channel_id = str(interaction.channel_id)
        user_id = str(interaction.user.id)
        success, message = claim_loot_gold(channel_id, user_id, amount)
        await interaction.response.send_message(message)

    # =================================================================
    # /splitgold
    # =================================================================
    @app_commands.command(name="splitgold", description="Split loot gold evenly among party")
    async def splitgold_cmd(self, interaction: discord.Interaction):
        """Split loot pile gold evenly among all registered characters."""
        from utils.inventory_manager import claim_loot_gold

        channel_id = str(interaction.channel_id)
        state = load_state(channel_id)
        players = state.get("players", [])

        if not players:
            await interaction.response.send_message("No players registered.", ephemeral=True)
            return

        success, message = claim_loot_gold(channel_id, str(interaction.user.id), amount=None, party_user_ids=players)
        await interaction.response.send_message(message)

    # =================================================================
    # /exportlog
    # =================================================================
    @app_commands.command(name="exportlog", description="Export session log")
    async def export_log(self, interaction: discord.Interaction):
        """Export the session log as a file."""
        session_id = str(interaction.channel.id)
        log_path = get_log_file(session_id)

        if not log_path or not os.path.exists(log_path):
            await interaction.response.send_message("No log found for this session.", ephemeral=True)
            return

        await interaction.response.send_message(file=discord.File(log_path))

    # =================================================================
    # /voice
    # =================================================================
    @app_commands.command(name="voice", description="Toggle voice narration on/off")
    @app_commands.describe(enabled="Enable or disable voice")
    async def voice_toggle(self, interaction: discord.Interaction, enabled: bool):
        """Toggle TTS for this channel."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        state["tts_enabled"] = enabled
        save_state(channel_id, state)

        status_text = "🔊 **enabled**" if enabled else "🔇 **disabled**"
        await interaction.response.send_message(f"Voice narration is now {status_text}")

    # =================================================================
    # /turns
    # =================================================================
    @app_commands.command(name="turns", description="Toggle turn order mode")
    @app_commands.describe(mode="Turn order mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Free-form (anyone can act)", value="free"),
        app_commands.Choice(name="Strict (follow turn order)", value="strict"),
    ])
    async def turns_mode(self, interaction: discord.Interaction, mode: str):
        """Toggle between free-form and strict turn order."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)
        state["free_form"] = (mode == "free")
        save_state(channel_id, state)

        if mode == "free":
            await interaction.response.send_message(
                "🎭 **Free-form mode** - Anyone can `/do` actions anytime!"
            )
        else:
            await interaction.response.send_message(
                "📋 **Strict turn order** - Must follow turn order. Use `/done` to pass turn."
            )

    # =================================================================
    # /leave
    # =================================================================
    @app_commands.command(name="leave", description="Disconnect bot from voice")
    async def leave_voice(self, interaction: discord.Interaction):
        """Disconnect from voice channel."""
        if interaction.guild:
            await voice_manager.disconnect(interaction.guild.id)
            await interaction.response.send_message("👋 Left voice channel.")
        else:
            await interaction.response.send_message("Not in a server.", ephemeral=True)

    # =================================================================
    # /joinvoice
    # =================================================================
    @app_commands.command(name="joinvoice", description="Join your voice channel for TTS narration")
    async def join_voice(self, interaction: discord.Interaction):
        """Connect bot to user's voice channel."""
        if not interaction.guild:
            await interaction.response.send_message("Not in a server.", ephemeral=True)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel first!", ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            channel = interaction.user.voice.channel
            await voice_manager.get_or_create(channel)

            channel_id = str(interaction.channel.id)
            state = load_state(channel_id)
            state["tts_enabled"] = True
            save_state(channel_id, state)

            await interaction.followup.send(
                f"🔊 Joined **{channel.name}**! Voice narration is now enabled."
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to join voice: {e}")

    # =================================================================
    # /reconnect
    # =================================================================
    @app_commands.command(name="reconnect", description="Fix voice connection issues")
    async def reconnect_voice(self, interaction: discord.Interaction):
        """Force reconnect to voice channel."""
        if not interaction.guild:
            await interaction.response.send_message("Not in a server.", ephemeral=True)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel first!", ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            await voice_manager.disconnect(interaction.guild.id)
            await asyncio.sleep(1)
            channel = interaction.user.voice.channel
            await voice_manager.get_or_create(channel)
            await interaction.followup.send(f"🔄 Reconnected to **{channel.name}**!")
        except Exception as e:
            await interaction.followup.send(f"❌ Reconnection failed: {e}")

    # =================================================================
    # /party
    # =================================================================
    @app_commands.command(name="party", description="View party status dashboard")
    async def party_dashboard(self, interaction: discord.Interaction):
        """Display a comprehensive party status dashboard."""
        channel_id = str(interaction.channel.id)
        state = load_state(channel_id)

        if not state.get('campaign_title'):
            await interaction.response.send_message(
                "No active campaign. Use `/campaign` to start!", ephemeral=True
            )
            return

        players = state.get('players', [])
        if not players:
            await interaction.response.send_message("No players in the party yet.", ephemeral=True)
            return

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

            hp_pct = hp / max_hp if max_hp > 0 else 0
            hp_bar_len = 10
            hp_filled = int(hp_bar_len * hp_pct)
            hp_bar = '█' * hp_filled + '░' * (hp_bar_len - hp_filled)

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

            spell_slots = char.get('spell_slots', {})
            spell_slots_used = char.get('spell_slots_used', {})
            slots_info = ""
            for lvl in ['1', '2', '3', '4', '5']:
                total = spell_slots.get(lvl, 0)
                used = spell_slots_used.get(lvl, 0)
                if total > 0:
                    remaining = total - used
                    slots_info += f"L{lvl}:{remaining}/{total} "

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

        party_hp_pct = total_hp / total_max_hp if total_max_hp > 0 else 0
        party_status = "💚 Healthy" if party_hp_pct > 0.5 else "💛 Injured" if party_hp_pct > 0.25 else "❤️ Critical"

        lines.append("───────────────────────")
        lines.append(f"**Party Status:** {party_status} ({total_hp}/{total_max_hp} total HP)")

        combat = load_combat(channel_id)
        if combat and combat.get('active'):
            current = combat['turn_order'][combat['current_turn']]
            lines.append(
                f"⚔️ **In Combat** - Round {combat.get('round', 1)} - {current['name']}'s turn"
            )

        await interaction.response.send_message("\n".join(lines))


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
