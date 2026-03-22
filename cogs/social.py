"""Social commands — NPC, faction, shop, quest, and rumor management."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from utils.state_manager import load_state, save_state, add_or_update_npc
from utils.character_manager import (
    load_character, save_character, add_inventory, remove_inventory
)
from utils.xp_manager import award_xp
from utils.npc_manager import (
    get_npc, create_npc, update_npc_disposition, get_standing_title,
    list_all_npcs, list_all_factions, get_faction, create_faction,
    modify_faction_standing, create_merchant_shop, buy_from_shop, sell_to_shop
)
from utils.quest_manager import (
    format_quest_log, get_active_quests, get_available_quests,
    get_completed_quests, get_quest_by_name, get_quest, create_quest,
    complete_quest, abandon_quest, accept_quest, add_objective,
    update_objective_progress, add_note_to_quest, create_quest_from_template,
    load_rumors, get_uninvestigated_rumors, convert_rumor_to_quest, link_quests
)

logger = logging.getLogger(__name__)

NPC_ROLES = [
    "generic", "quest_giver", "merchant", "innkeeper", "guard",
    "noble", "villain", "ally", "informant",
]
SHOP_TYPES = ["general", "weapons", "armor", "potions", "magic"]
QUEST_TYPES = [
    "main", "side", "faction", "personal", "bounty",
    "fetch", "escort", "explore", "mystery",
]
QUEST_DIFFICULTIES = ["trivial", "easy", "medium", "hard", "deadly", "legendary"]


class SocialCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # /npc — view NPCs or specific NPC (also create if description given)
    # =================================================================
    @app_commands.command(name="npc", description="View NPCs or create a new one")
    @app_commands.describe(
        name="NPC name (omit to list all)",
        description="Description — providing this creates the NPC",
        role="NPC's role in the world",
        location="Where the NPC is located",
    )
    @app_commands.choices(
        role=[app_commands.Choice(name=r.replace('_', ' ').title(), value=r) for r in NPC_ROLES]
    )
    async def npc_cmd(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None,
        description: Optional[str] = None,
        role: str = "generic",
        location: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        # CREATE — name + description provided
        if name and description:
            state = load_state(channel_id)
            current_location = location or state.get("location", "")

            npc = create_npc(
                channel_id,
                name=name,
                description=description,
                role=role,
                location=current_location,
            )

            add_or_update_npc(state, name, description)
            save_state(channel_id, state)

            await interaction.response.send_message(
                f"👤 **{npc.name}** registered!\n"
                f"Role: {npc.role.replace('_', ' ').title()} | Race: {npc.race.title()}\n"
                f"Voice: {npc.voice_archetype or 'Default'}"
            )
            return

        # VIEW — name provided (no description)
        if name:
            npc = get_npc(channel_id, name)
            if not npc:
                await interaction.response.send_message(f"❌ NPC **{name}** not found.", ephemeral=True)
                return

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
            return

        # LIST — no name given
        npcs = list_all_npcs(channel_id)
        if not npcs:
            await interaction.response.send_message(
                "📋 No NPCs registered yet.\n"
                "NPCs are auto-detected from AI narration, or use `/npc name:\"NPC Name\" description:\"...\"`",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📋 Known NPCs",
            description=f"**{len(npcs)}** NPCs in this campaign",
            color=discord.Color.blue(),
        )

        for npc in npcs[:25]:
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
                inline=True,
            )

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /npcdisposition
    # =================================================================
    @app_commands.command(name="npcdisposition", description="Adjust NPC disposition")
    @app_commands.describe(
        name="NPC name",
        change="Disposition change amount",
    )
    async def npcdisposition_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        change: int,
    ):
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

    # =================================================================
    # /faction — list, view, or create factions
    # =================================================================
    @app_commands.command(name="faction", description="View or create factions")
    @app_commands.describe(
        name="Faction name (omit to list all)",
        description="Description — providing this creates the faction",
        leader="Faction leader name",
        headquarters="Faction headquarters",
    )
    async def faction_cmd(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None,
        description: Optional[str] = None,
        leader: Optional[str] = None,
        headquarters: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        # CREATE — name + description provided
        if name and description:
            faction = create_faction(
                channel_id,
                name=name,
                description=description,
                leader=leader or "",
                headquarters=headquarters or "",
            )
            await interaction.response.send_message(
                f"⚔️ **{faction.name}** faction created!\n"
                f"Starting standing: {faction.standing_title}"
            )
            return

        # VIEW — name provided (no description)
        if name:
            faction = get_faction(channel_id, name)
            if not faction:
                await interaction.response.send_message(f"❌ Faction **{name}** not found.", ephemeral=True)
                return

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
            return

        # LIST — no name given
        factions = list_all_factions(channel_id)
        if not factions:
            await interaction.response.send_message(
                "⚔️ No factions registered yet.\n"
                "Use `/faction name:\"Faction Name\" description:\"...\"`",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="⚔️ Factions",
            description=f"**{len(factions)}** factions in this campaign",
            color=discord.Color.purple(),
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
                inline=True,
            )

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /reputation
    # =================================================================
    @app_commands.command(name="reputation", description="Adjust faction standing")
    @app_commands.describe(
        name="Faction name",
        change="Reputation change amount",
        reason="Reason for reputation change",
    )
    async def reputation_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        change: int,
        reason: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        result = modify_faction_standing(channel_id, name, change, reason or "")
        if not result:
            await interaction.response.send_message(f"❌ Faction **{name}** not found.", ephemeral=True)
            return

        updated_faction, message = result

        color = discord.Color.green() if change > 0 else discord.Color.red()
        embed = discord.Embed(
            title=f"📊 Reputation Change: {updated_faction.name}",
            description=message,
            color=color,
        )
        embed.add_field(name="Current Standing", value=f"{updated_faction.standing_title} ({updated_faction.party_standing:+d})")

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /shop — view or create merchant shop
    # =================================================================
    @app_commands.command(name="shop", description="View or create a merchant shop")
    @app_commands.describe(
        merchant="Merchant NPC name",
        shop_name="Name for the shop (creates if provided)",
        shop_type="Type of shop inventory",
    )
    @app_commands.choices(
        shop_type=[app_commands.Choice(name=t.title(), value=t) for t in SHOP_TYPES]
    )
    async def shop_cmd(
        self,
        interaction: discord.Interaction,
        merchant: str,
        shop_name: Optional[str] = None,
        shop_type: str = "general",
    ):
        channel_id = str(interaction.channel.id)

        # CREATE — shop_name provided
        if shop_name:
            npc = create_merchant_shop(
                channel_id,
                merchant,
                shop_name=shop_name,
                shop_type=shop_type,
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
            return

        # VIEW — no shop_name
        npc = get_npc(channel_id, merchant)
        if not npc or not npc.shop:
            await interaction.response.send_message(
                f"❌ **{merchant}** doesn't have a shop.\n"
                f"Use `/shop merchant:{merchant} shop_name:\"Shop Name\"` to create one.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"🏪 {npc.shop.shop_name}",
            description=f"Proprietor: **{npc.name}**",
            color=discord.Color.gold(),
        )

        items_text = []
        for shop_item in npc.shop.items:
            if shop_item['quantity'] > 0:
                items_text.append(f"• **{shop_item['name']}** - {shop_item['price']} gp (x{shop_item['quantity']})")

        if items_text:
            embed.add_field(name="📦 Inventory", value="\n".join(items_text[:15]), inline=False)
            if len(items_text) > 15:
                embed.add_field(name="", value="\n".join(items_text[15:30]), inline=False)
        else:
            embed.add_field(name="📦 Inventory", value="*Shop is currently out of stock*", inline=False)

        embed.add_field(name="💰 Shop Gold", value=f"{npc.shop.gold_reserve} gp", inline=True)
        embed.add_field(name="📊 Buy Rate", value=f"{int(npc.shop.buy_rate * 100)}%", inline=True)

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /buy
    # =================================================================
    @app_commands.command(name="buy", description="Purchase an item from a merchant")
    @app_commands.describe(
        merchant="Merchant NPC name",
        item="Item to buy",
        quantity="Quantity to buy",
    )
    async def buy_cmd(
        self,
        interaction: discord.Interaction,
        merchant: str,
        item: str,
        quantity: float = 1.0,
    ):
        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)

        result = buy_from_shop(channel_id, merchant, item, quantity)
        if not result:
            await interaction.response.send_message(
                f"❌ Could not purchase **{item}**. Check that:\n"
                f"• The merchant **{merchant}** exists and has a shop\n"
                f"• The item is in stock\n"
                f"• You requested a valid quantity",
                ephemeral=True,
            )
            return

        item_data, total_cost = result

        char = load_character(user_id)
        if char:
            for _ in range(quantity):
                add_inventory(user_id, item_data['name'])
            save_character(user_id, char)

        await interaction.response.send_message(
            f"💰 Purchased **{quantity}x {item_data['name']}** for **{total_cost} gp**!\n"
            f"*{item_data.get('description', '')}*"
        )

    # =================================================================
    # /sell
    # =================================================================
    @app_commands.command(name="sell", description="Sell an item to a merchant")
    @app_commands.describe(
        merchant="Merchant NPC name",
        item="Item to sell",
        price="Base price for selling",
        quantity="Quantity to sell",
    )
    async def sell_cmd(
        self,
        interaction: discord.Interaction,
        merchant: str,
        item: str,
        price: int,
        quantity: float = 1.0,
    ):
        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)

        char = load_character(user_id)
        if char:
            inventory = char.get("inventory", [])
            item_count = sum(1 for i in inventory if i.lower() == item.lower())
            if item_count < quantity:
                await interaction.response.send_message(
                    f"❌ You only have **{item_count}x {item}** in your inventory.",
                    ephemeral=True,
                )
                return

        gold_received = sell_to_shop(channel_id, merchant, item, price, quantity)
        if gold_received is None:
            await interaction.response.send_message(
                f"❌ Could not sell to **{merchant}**. The shop may not have enough gold.",
                ephemeral=True,
            )
            return

        if char:
            for _ in range(quantity):
                remove_inventory(user_id, item)

        await interaction.response.send_message(
            f"💰 Sold **{quantity}x {item}** for **{gold_received} gp**!"
        )

    # =================================================================
    # /quest — view or create a quest
    # =================================================================
    @app_commands.command(name="quest", description="View or create a quest")
    @app_commands.describe(
        name="Quest name",
        description="Quest description (creates if provided)",
        quest_type="Type of quest",
        difficulty="Quest difficulty",
        giver="NPC who gave the quest",
    )
    @app_commands.choices(
        quest_type=[app_commands.Choice(name=t.replace('_', ' ').title(), value=t) for t in QUEST_TYPES],
        difficulty=[app_commands.Choice(name=d.title(), value=d) for d in QUEST_DIFFICULTIES],
    )
    async def quest_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        description: Optional[str] = None,
        quest_type: str = "side",
        difficulty: str = "medium",
        giver: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        # CREATE — description provided
        if description:
            new_quest = create_quest(
                channel_id=channel_id,
                name=name,
                description=description,
                quest_type=quest_type,
                difficulty=difficulty,
                giver_npc=giver,
            )

            embed = discord.Embed(
                title="📜 New Quest Created!",
                description=f"**{new_quest.name}**\n{new_quest.description}",
                color=discord.Color.green(),
            )
            embed.add_field(name="Type", value=new_quest.quest_type.title(), inline=True)
            embed.add_field(name="Difficulty", value=new_quest.difficulty.title(), inline=True)
            rewards = new_quest.get_rewards()
            embed.add_field(name="Base Rewards", value=f"⭐ {rewards.xp} XP, 💰 {rewards.gold} gp", inline=True)

            await interaction.response.send_message(embed=embed)
            return

        # VIEW — no description
        existing = get_quest_by_name(channel_id, name)
        if not existing:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📜 {existing.name}",
            description=existing.description,
            color=discord.Color.gold() if existing.status == "active" else discord.Color.green(),
        )

        status_emoji = {"active": "⚔️", "completed": "✅", "failed": "❌", "available": "📋", "abandoned": "🚫"}
        embed.add_field(name="Status", value=f"{status_emoji.get(existing.status, '📜')} {existing.status.title()}", inline=True)
        embed.add_field(name="Type", value=existing.quest_type.title(), inline=True)
        embed.add_field(name="Difficulty", value=existing.difficulty.title(), inline=True)

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

        if existing.giver_npc:
            embed.set_footer(text=f"Quest Giver: {existing.giver_npc}")

        if existing.notes:
            embed.add_field(name="Notes", value="\n".join(existing.notes[-3:]), inline=False)

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /quests — view full quest log
    # =================================================================
    @app_commands.command(name="quests", description="View the full quest log")
    @app_commands.describe(show_completed="Include completed quests")
    async def quests_cmd(
        self,
        interaction: discord.Interaction,
        show_completed: bool = False,
    ):
        channel_id = str(interaction.channel.id)

        quest_log = format_quest_log(channel_id, include_completed=show_completed)

        if len(quest_log) > 1900:
            embed = discord.Embed(title="📜 Quest Log", color=discord.Color.gold())

            active = get_active_quests(channel_id)
            available = get_available_quests(channel_id)

            if active:
                active_text = ""
                for q in active[:10]:
                    prog = f"({q.get_progress()[0]}/{q.get_progress()[1]})"
                    active_text += f"• **{q.name}** {prog}\n"
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
                embed.description = "*No active quests. Use `/quest` to add one!*"

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(quest_log)

    # =================================================================
    # /questtemplate
    # =================================================================
    @app_commands.command(name="questtemplate", description="Create a quest from a template")
    @app_commands.describe(
        name="Quest name",
        template="Quest template",
        description="Optional quest description",
        giver="NPC who gave the quest",
    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Bounty - Hunt a target", value="bounty"),
        app_commands.Choice(name="Fetch - Retrieve an item", value="fetch"),
        app_commands.Choice(name="Rescue - Save someone", value="rescue"),
        app_commands.Choice(name="Investigate - Solve a mystery", value="investigate"),
        app_commands.Choice(name="Clear Dungeon - Clear all threats", value="clear_dungeon"),
        app_commands.Choice(name="Escort - Protect during journey", value="escort"),
    ])
    async def questtemplate_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        template: str,
        description: Optional[str] = None,
        giver: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        if not description:
            description = f"A {template.replace('_', ' ')} quest"

        quest = create_quest_from_template(
            channel_id=channel_id,
            template_name=template,
            quest_name=name,
            description=description,
            giver_npc=giver,
        )

        if quest:
            embed = discord.Embed(title=f"📜 Quest Created: {quest.name}", description=quest.description, color=discord.Color.gold())
            objectives = quest.get_objectives()
            if objectives:
                obj_text = "\n".join([f"☐ {obj.description}" for obj in objectives])
                embed.add_field(name="Objectives", value=obj_text, inline=False)
            rewards = quest.get_rewards()
            embed.add_field(name="Rewards", value=f"⭐ {rewards.xp} XP, 💰 {rewards.gold} gp", inline=True)
            embed.add_field(name="Type", value=quest.quest_type.title(), inline=True)
            if giver:
                embed.set_footer(text=f"Quest Giver: {giver}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ Template **{template}** not found.", ephemeral=True)

    # =================================================================
    # /questobjective
    # =================================================================
    @app_commands.command(name="questobjective", description="Add an objective to a quest")
    @app_commands.describe(
        name="Quest name",
        objective="Objective description",
        required="Number required to complete (default 1)",
    )
    async def questobjective_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        objective: str,
        required: float = 1.0,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        new_obj = add_objective(channel_id=channel_id, quest_id=quest.id, description=objective, required=required)

        if new_obj:
            req = f" (0/{required})" if required > 1 else ""
            await interaction.response.send_message(f"✅ Added objective to **{quest.name}**:\n☐ {objective}{req}")
        else:
            await interaction.response.send_message("❌ Failed to add objective.", ephemeral=True)

    # =================================================================
    # /questprogress
    # =================================================================
    @app_commands.command(name="questprogress", description="Update quest objective progress")
    @app_commands.describe(
        name="Quest name",
        objective_number="Objective number",
        progress="Progress amount",
    )
    async def questprogress_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        objective_number: float = 1.0,
        progress: float = 1.0,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        obj_id = f"obj_{objective_number}"
        completed, message = update_objective_progress(channel_id, quest.id, obj_id, progress)

        if message:
            if completed:
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
                        await interaction.response.send_message(f"📊 Progress updated: {obj.description} ({obj.progress}/{obj.required})")
                        return
                await interaction.response.send_message("Progress updated.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Objective {objective_number} not found in quest **{quest.name}**.", ephemeral=True)

    # =================================================================
    # /questnote
    # =================================================================
    @app_commands.command(name="questnote", description="Add a note to a quest")
    @app_commands.describe(
        name="Quest name",
        note="Note text",
    )
    async def questnote_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        note: str,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        if add_note_to_quest(channel_id, quest.id, note):
            await interaction.response.send_message(f"📝 Note added to **{quest.name}**:\n*{note}*")
        else:
            await interaction.response.send_message("❌ Failed to add note.", ephemeral=True)

    # =================================================================
    # /questcomplete
    # =================================================================
    @app_commands.command(name="questcomplete", description="Complete a quest")
    @app_commands.describe(name="Quest name")
    async def questcomplete_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        if quest.status == "completed":
            await interaction.response.send_message(f"Quest **{quest.name}** is already completed!", ephemeral=True)
            return

        success, rewards, message = complete_quest(channel_id, quest.id)

        if success:
            embed = discord.Embed(title="🎉 Quest Complete!", description=f"**{quest.name}**", color=discord.Color.green())

            # Distribute rewards to party members
            state = load_state(channel_id)
            players = state.get('players', [])
            distribution_lines = []

            if rewards and players:
                party_size = len(players)

                # Distribute XP
                if rewards.xp > 0:
                    xp_each = rewards.xp // party_size
                    xp_remainder = rewards.xp % party_size
                    for i, user_id in enumerate(players):
                        share = xp_each + (1 if i < xp_remainder else 0)
                        result = award_xp(str(user_id), share)
                        if result and result.get('level_up'):
                            char_name = result.get('character', 'Unknown')
                            distribution_lines.append(
                                f"🎆 **{char_name}** leveled up to **{result['new_level']}**!"
                            )
                    embed.add_field(
                        name="⭐ XP Awarded",
                        value=f"{rewards.xp} XP split among {party_size} party member{'s' if party_size > 1 else ''} ({xp_each} each)",
                        inline=False,
                    )

                # Distribute gold
                if rewards.gold > 0:
                    gold_each = rewards.gold // party_size
                    gold_remainder = rewards.gold % party_size
                    for i, user_id in enumerate(players):
                        share = gold_each + (1 if i < gold_remainder else 0)
                        char_data = load_character(str(user_id))
                        if char_data:
                            char_data['gold'] = char_data.get('gold', 0) + share
                            save_character(str(user_id), char_data)
                    embed.add_field(
                        name="💰 Gold Awarded",
                        value=f"{rewards.gold} gp split among party ({gold_each} gp each)",
                        inline=False,
                    )

                # List items (added to first player's inventory as claimable)
                if rewards.items:
                    for item_name in rewards.items:
                        # Give items to the player who completed the quest
                        add_inventory(str(interaction.user.id), item_name)
                    embed.add_field(
                        name="🎁 Items",
                        value="\n".join(f"• {item}" for item in rewards.items)
                            + f"\n*(Added to <@{interaction.user.id}>'s inventory)*",
                        inline=False,
                    )

                # Apply reputation changes
                if rewards.reputation:
                    rep_lines = []
                    for faction_name, change in rewards.reputation.items():
                        result = modify_faction_standing(channel_id, faction_name, change, reason=f"Completed quest: {quest.name}")
                        if result:
                            _, notif = result
                            rep_lines.append(notif)
                        else:
                            sign = "+" if change > 0 else ""
                            rep_lines.append(f"🏛️ **{faction_name}:** {sign}{change}")
                    if rep_lines:
                        embed.add_field(name="🏛️ Reputation", value="\n".join(rep_lines), inline=False)

            elif rewards:
                # No players registered — just display rewards without distributing
                reward_text = []
                if rewards.xp > 0:
                    reward_text.append(f"⭐ **{rewards.xp}** Experience Points")
                if rewards.gold > 0:
                    reward_text.append(f"💰 **{rewards.gold}** Gold Pieces")
                if rewards.items:
                    reward_text.append(f"🎁 **Items:** {', '.join(rewards.items)}")
                if reward_text:
                    embed.add_field(name="Rewards (not distributed — no players registered)", value="\n".join(reward_text), inline=False)

            if distribution_lines:
                embed.add_field(name="🎆 Level Ups!", value="\n".join(distribution_lines), inline=False)

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)

    # =================================================================
    # /questabandon
    # =================================================================
    @app_commands.command(name="questabandon", description="Abandon a quest")
    @app_commands.describe(name="Quest name")
    async def questabandon_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        if quest.status != "active":
            await interaction.response.send_message(f"Quest **{quest.name}** is not active (status: {quest.status}).", ephemeral=True)
            return

        if abandon_quest(channel_id, quest.id):
            await interaction.response.send_message(f"🚫 **Quest Abandoned:** {quest.name}\n*You can always pick it up again later if available.*")
        else:
            await interaction.response.send_message("❌ Failed to abandon quest.", ephemeral=True)

    # =================================================================
    # /rumors
    # =================================================================
    @app_commands.command(name="rumors", description="View rumors the party has heard")
    async def rumors_cmd(self, interaction: discord.Interaction):
        channel_id = str(interaction.channel.id)

        all_rumors = load_rumors(channel_id)

        if not all_rumors:
            await interaction.response.send_message("👂 *No rumors heard yet. Talk to NPCs to learn about potential adventures!*", ephemeral=True)
            return

        embed = discord.Embed(title="👂 Rumors & Gossip", description="*Whispers heard on your adventures...*", color=discord.Color.purple())

        uninvestigated = [r for r in all_rumors if not r.get("investigated", False)]
        investigated = [r for r in all_rumors if r.get("investigated", False)]

        if uninvestigated:
            rumor_text = ""
            for i, r in enumerate(uninvestigated[-10:], 1):
                source = f" *(from {r['source']})*" if r.get("source") else ""
                rumor_text += f"{i}. \"{r['text']}\"{source}\n"
            embed.add_field(name="🔍 Uninvestigated", value=rumor_text, inline=False)

        if investigated:
            invest_text = ""
            for r in investigated[-5:]:
                quest_note = f" → Led to quest" if r.get("led_to_quest") else ""
                invest_text += f"• ~~{r['text']}~~{quest_note}\n"
            embed.add_field(name="✅ Investigated", value=invest_text, inline=False)

        embed.set_footer(text="Use /investigaterumor to follow up on a rumor")
        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /investigaterumor
    # =================================================================
    @app_commands.command(name="investigaterumor", description="Convert a rumor into a quest")
    @app_commands.describe(
        rumor_number="Rumor number to investigate",
        name="Quest name for the new quest",
        description="Optional quest description",
    )
    async def investigaterumor_cmd(
        self,
        interaction: discord.Interaction,
        rumor_number: float,
        name: str,
        description: Optional[str] = None,
    ):
        channel_id = str(interaction.channel.id)

        if rumor_number < 1:
            await interaction.response.send_message("❌ Specify a valid rumor number.", ephemeral=True)
            return

        rumors = get_uninvestigated_rumors(channel_id)

        if not rumors:
            await interaction.response.send_message("❌ No uninvestigated rumors available.", ephemeral=True)
            return

        if rumor_number > len(rumors):
            await interaction.response.send_message(f"❌ Invalid rumor number. You have {len(rumors)} uninvestigated rumors.", ephemeral=True)
            return

        rumor = rumors[rumor_number - 1]
        desc = description if description else f"Investigate: {rumor['text']}"

        quest = convert_rumor_to_quest(channel_id=channel_id, rumor_id=rumor["id"], quest_name=name, description=desc)

        if quest:
            embed = discord.Embed(title="🔍 Rumor Investigated!", description=f"**{quest.name}**\n{quest.description}", color=discord.Color.green())
            embed.add_field(name="Original Rumor", value=f"*\"{rumor['text']}\"*", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to create quest from rumor.", ephemeral=True)

    # =================================================================
    # /questchain
    # =================================================================
    @app_commands.command(name="questchain", description="Link two quests in sequence")
    @app_commands.describe(
        name="Parent quest name",
        child_quest="Child quest name (unlocks when parent completes)",
    )
    async def questchain_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
        child_quest: str,
    ):
        channel_id = str(interaction.channel.id)

        parent = get_quest_by_name(channel_id, name)
        child = get_quest_by_name(channel_id, child_quest)

        if not parent:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return
        if not child:
            await interaction.response.send_message(f"❌ Quest **{child_quest}** not found.", ephemeral=True)
            return

        if link_quests(channel_id, parent.id, child.id):
            await interaction.response.send_message(f"🔗 **Quest Chain Created!**\nWhen **{parent.name}** completes, **{child.name}** will unlock automatically.")
        else:
            await interaction.response.send_message("❌ Failed to link quests.", ephemeral=True)

    # =================================================================
    # /acceptquest
    # =================================================================
    @app_commands.command(name="acceptquest", description="Accept an available quest")
    @app_commands.describe(name="Quest name")
    async def acceptquest_cmd(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        channel_id = str(interaction.channel.id)

        quest = get_quest_by_name(channel_id, name)
        if not quest:
            await interaction.response.send_message(f"❌ Quest **{name}** not found.", ephemeral=True)
            return

        if quest.status != "available":
            await interaction.response.send_message(f"Quest **{quest.name}** is not available (status: {quest.status}).", ephemeral=True)
            return

        if accept_quest(channel_id, quest.id):
            embed = discord.Embed(title="⚔️ Quest Accepted!", description=f"**{quest.name}**\n{quest.description}", color=discord.Color.green())
            objectives = quest.get_objectives()
            if objectives:
                obj_text = "\n".join([f"☐ {obj.description}" for obj in objectives if not obj.is_hidden])
                if obj_text:
                    embed.add_field(name="Objectives", value=obj_text, inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to accept quest.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SocialCog(bot))
