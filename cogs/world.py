"""World Cog — All world, environment, travel, and encounter slash commands."""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from utils.environment_manager import (
    create_trap, create_trap_from_template, get_trap,
    detect_trap, disarm_trap, trigger_trap, remove_trap, list_traps,
    create_hazard, remove_hazard, list_hazards,
    set_weather, get_weather, clear_weather,
    set_lighting, get_lighting,
    add_terrain_zone, remove_terrain_zone, list_terrain_zones,
    get_cover_bonus, calculate_cover,
    format_environment_summary,
    format_trap_info, format_weather_info, format_lighting_info,
)
from utils.encounter_manager import (
    Encounter,
    generate_combat_encounter, generate_social_encounter, generate_discovery_encounter,
    generate_random_event, roll_for_encounter, determine_encounter_type,
    start_travel, calculate_travel_time, advance_travel, get_travel_status, clear_travel_state,
    format_encounter_summary, format_random_event,
    TERRAIN_MODIFIERS,
)
from utils.world_map import (
    load_world_state,
    add_location, get_location, get_current_location, set_current_location,
    connect_locations,
    can_fast_travel, get_fast_travel_options, fast_travel,
)
from utils.state_manager import load_state, save_state
from utils.character_manager import load_character

logger = logging.getLogger(__name__)

# Shared choice lists used by multiple commands in this cog
TERRAIN_CHOICES = [
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
]

LOCATION_TYPE_CHOICES = [
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
]


class WorldCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # =================================================================
    # /environment
    # =================================================================
    @app_commands.command(name="environment", description="View current environmental conditions")
    async def environment_cmd(self, interaction: discord.Interaction):
        """Display the current environment status."""
        channel_id = str(interaction.channel.id)

        summary = format_environment_summary(channel_id)

        embed = discord.Embed(
            title="🌍 Environment Status",
            description=summary,
            color=discord.Color.dark_teal()
        )

        await interaction.response.send_message(embed=embed)

    # =================================================================
    # /trap
    # =================================================================
    @app_commands.command(name="trap", description="Create, view, or manage traps")
    @app_commands.describe(
        action="Action to perform",
        name="Name of the trap",
        template="Use a pre-defined trap template",
        dc="Detection DC",
        save_dc="Save DC when triggered",
        damage="Damage dice (e.g., 2d6)",
        damage_type="Type of damage",
        x="X position on map",
        y="Y position on map",
        roll="Perception or disarm roll result"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📋 List - View all traps", value="list"),
        app_commands.Choice(name="➕ Create - Create a trap", value="create"),
        app_commands.Choice(name="👁️ View - View trap details", value="view"),
        app_commands.Choice(name="🗑️ Remove - Remove a trap", value="remove"),
        app_commands.Choice(name="💥 Trigger - Trigger a trap", value="trigger"),
        app_commands.Choice(name="🔍 Detect - Roll to detect trap", value="detect"),
        app_commands.Choice(name="🔧 Disarm - Roll to disarm trap", value="disarm"),
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
        self,
        interaction: discord.Interaction,
        action: str,
        name: str = "",
        template: str = "",
        dc: float = 15.0,
        save_dc: float = 13.0,
        damage: str = "2d6",
        damage_type: str = "piercing",
        x: float = -1.0,
        y: float = -1.0,
        roll: Optional[int] = None
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

        elif action == "detect":
            if not name or roll is None:
                await interaction.response.send_message(
                    "❌ Required: `name`, `roll`\n"
                    "Example: `/trap action:detect name:\"Pit Trap\" roll:18`",
                    ephemeral=True
                )
                return

            result = detect_trap(channel_id, name, roll)

            if "error" in result:
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            elif result.get("already_detected"):
                await interaction.response.send_message(
                    f"👁️ The trap **{name}** was already detected!",
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

        elif action == "disarm":
            if not name or roll is None:
                await interaction.response.send_message(
                    "❌ Required: `name`, `roll`\n"
                    "Example: `/trap action:disarm name:\"Pit Trap\" roll:15`",
                    ephemeral=True
                )
                return

            result = disarm_trap(channel_id, name, roll)

            if "error" in result:
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            elif result.get("already_disarmed"):
                await interaction.response.send_message(
                    f"✅ The trap **{name}** is already disarmed!",
                    ephemeral=True
                )
            elif result.get("triggered"):
                trap = result["trap"]
                trigger_trap(channel_id, name, [interaction.user.display_name])
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

    # =================================================================
    # /weather
    # =================================================================
    @app_commands.command(name="weather", description="Set weather conditions")
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
        self,
        interaction: discord.Interaction,
        weather_type: str = "",
        intensity: float = 1.0,
        duration: float = -1.0
    ):
        """Set or view current weather conditions."""
        channel_id = str(interaction.channel.id)

        if not weather_type:
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

    # =================================================================
    # /lighting
    # =================================================================
    @app_commands.command(name="lighting", description="Set lighting conditions")
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
        self,
        interaction: discord.Interaction,
        light_level: str = "",
        source: str = "",
        radius: float = 0.0
    ):
        """Set or view current lighting conditions."""
        channel_id = str(interaction.channel.id)

        if not light_level:
            lighting = get_lighting(channel_id)
            await interaction.response.send_message(format_lighting_info(lighting))
            return

        lighting = set_lighting(channel_id, light_level, source, radius)
        info = format_lighting_info(lighting)

        emoji = "🔦" if light_level == "dim" else ("🌑" if "dark" in light_level else "☀️")
        await interaction.response.send_message(f"{emoji} Lighting Changed!\n\n{info}")

    # =================================================================
    # /time
    # =================================================================
    @app_commands.command(name="time", description="View or set in-game time")
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
        self,
        interaction: discord.Interaction,
        action: str = "view",
        hours: float = 1.0,
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

    # =================================================================
    # /location
    # =================================================================
    @app_commands.command(name="location", description="Set or view current location with environment presets")
    @app_commands.describe(
        location="Location name (cave, dungeon, forest, tavern, etc.)"
    )
    async def location_cmd(
        self,
        interaction: discord.Interaction,
        location: str = ""
    ):
        """Set or view current location with automatic environment presets."""
        channel_id = str(interaction.channel.id)

        try:
            from utils.world_generator import (
                get_current_location, set_current_location as wg_set_current_location,
                apply_location_preset, get_location_memory,
                LOCATION_PRESETS
            )

            if not location:
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
                results = apply_location_preset(channel_id, location)

                if results:
                    await interaction.response.send_message("\n".join(results))
                else:
                    wg_set_current_location(channel_id, location)
                    await interaction.response.send_message(f"📍 Location set to: {location}")

        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ Error managing location: {str(e)}", ephemeral=True
            )

    # =================================================================
    # /hazard
    # =================================================================
    @app_commands.command(name="hazard", description="Create or manage environmental hazards")
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
        self,
        interaction: discord.Interaction,
        action: str,
        name: str = "",
        hazard_type: str = "fire",
        damage: str = "2d6",
        damage_type: str = "fire",
        save_dc: float = 15.0,
        duration: float = -1.0,
        x: float = -1.0,
        y: float = -1.0,
        width: float = 1.0,
        height: float = 1.0
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

    # =================================================================
    # /terrain
    # =================================================================
    @app_commands.command(name="terrain", description="Create or manage terrain zones")
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
        self,
        interaction: discord.Interaction,
        action: str,
        name: str = "",
        terrain_type: str = "difficult",
        x: float = 0.0,
        y: float = 0.0,
        width: float = 1.0,
        height: float = 1.0
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

    # =================================================================
    # /cover
    # =================================================================
    @app_commands.command(name="cover", description="Calculate cover between positions")
    @app_commands.describe(
        attacker_x="Attacker X position",
        attacker_y="Attacker Y position",
        target_x="Target X position",
        target_y="Target Y position"
    )
    async def cover_cmd(
        self,
        interaction: discord.Interaction,
        attacker_x: int,
        attacker_y: int,
        target_x: int,
        target_y: int
    ):
        """Calculate cover between two positions."""
        channel_id = str(interaction.channel.id)

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

    # =================================================================
    # /travel
    # =================================================================
    @app_commands.command(name="travel", description="Manage travel - start journeys, check status, advance time")
    @app_commands.describe(
        action="Action to perform",
        destination="Where you're traveling to (for start)",
        distance="Distance in miles (for start)",
        terrain="Terrain type",
        pace="Travel pace",
        hours="Hours to advance (for advance)",
        origin="Starting location (for start)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="start", value="start"),
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="advance", value="advance"),
        app_commands.Choice(name="cancel", value="cancel"),
    ])
    @app_commands.choices(terrain=TERRAIN_CHOICES)
    @app_commands.choices(pace=[
        app_commands.Choice(name="Slow (Stealth possible)", value="slow"),
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="Fast (-5 Passive Perception)", value="fast"),
    ])
    async def travel_cmd(
        self,
        interaction: discord.Interaction,
        action: str = "status",
        destination: str = "",
        distance: float = 0.0,
        terrain: str = "road",
        pace: str = "normal",
        hours: float = 1.0,
        origin: str = ""
    ):
        """Consolidated travel management command."""
        channel_id = str(interaction.channel.id)

        # === START ===
        if action == "start":
            if not destination:
                await interaction.response.send_message("❌ Specify a destination with `destination:`", ephemeral=True)
                return
            if distance <= 0:
                await interaction.response.send_message("❌ Specify a distance with `distance:`", ephemeral=True)
                return

            if not origin:
                state = load_state(channel_id)
                origin = state.get("location", "Current Location")

            travel_info = calculate_travel_time(distance, terrain, pace)
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

            embed.set_footer(text="Use /travel action:advance to move forward")
            await interaction.response.send_message(embed=embed)

        # === STATUS ===
        elif action == "status":
            status = get_travel_status(channel_id)
            if not status:
                await interaction.response.send_message(
                    "🏠 Not currently traveling. Use `/travel action:start destination:... distance:...` to begin a journey.",
                    ephemeral=True
                )
                return

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

        # === ADVANCE ===
        elif action == "advance":
            status = get_travel_status(channel_id)
            if not status:
                await interaction.response.send_message(
                    "🏠 Not currently traveling. Use `/travel action:start` to begin a journey.",
                    ephemeral=True
                )
                return

            hours = max(1, min(8, hours))
            result = advance_travel(channel_id, hours)

            if result.get('error'):
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
                return

            lines = [
                f"⏰ **{hours} hour(s) pass...**",
                f"Traveled: {result['miles_traveled']:.1f} miles",
            ]

            if result['arrived']:
                lines.append(f"\n🎉 **Arrived at {result['destination']}!**")
                state = load_state(channel_id)
                state["location"] = result['destination']
                save_state(channel_id, state)
            else:
                lines.append(f"Progress: {result['progress_percent']:.0f}% ({result['remaining']:.1f} miles remaining)")

            await interaction.response.send_message("\n".join(lines))

            if result.get('encounter'):
                enc = result['encounter']
                if enc.get('needs_generation'):
                    await interaction.followup.send(
                        "⚔️ **Random Encounter!** Use `/encounter action:combat` to generate the combat encounter."
                    )
                elif enc.get('event_type') == 'combat':
                    await interaction.followup.send(format_encounter_summary(Encounter.from_dict(enc)))
                else:
                    await interaction.followup.send(format_random_event(enc))

        # === CANCEL ===
        elif action == "cancel":
            status = get_travel_status(channel_id)
            if not status:
                await interaction.response.send_message("🏠 Not currently traveling.", ephemeral=True)
                return

            clear_travel_state(channel_id)
            await interaction.response.send_message(
                f"🛑 Journey to **{status['destination']}** cancelled.\n"
                f"Party remains in the wilderness ({status['traveled_miles']:.1f} miles from {status['origin']})."
            )

    # =================================================================
    # /encounter
    # =================================================================
    @app_commands.command(name="encounter", description="Generate or check for encounters")
    @app_commands.describe(
        action="Type of encounter action",
        difficulty="Encounter difficulty (for combat)",
        terrain="Terrain type",
        event_type="Type of non-combat event",
        hours="Hours to check for encounters",
        is_night="Is it nighttime?",
        stealthy="Is the party being stealthy?"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="combat", value="combat"),
        app_commands.Choice(name="social", value="social"),
        app_commands.Choice(name="discovery", value="discovery"),
        app_commands.Choice(name="random", value="random"),
        app_commands.Choice(name="check", value="check"),
    ])
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard", value="hard"),
        app_commands.Choice(name="Deadly", value="deadly"),
    ])
    @app_commands.choices(terrain=TERRAIN_CHOICES)
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Social (NPCs)", value="social"),
        app_commands.Choice(name="Discovery", value="discovery"),
        app_commands.Choice(name="Weather Change", value="weather"),
        app_commands.Choice(name="Rest Site", value="rest_site"),
        app_commands.Choice(name="Random", value="random"),
    ])
    async def encounter_cmd(
        self,
        interaction: discord.Interaction,
        action: str = "random",
        difficulty: str = "medium",
        terrain: str = "plains",
        event_type: str = "random",
        hours: float = 1.0,
        is_night: bool = False,
        stealthy: bool = False
    ):
        """Consolidated encounter command."""
        channel_id = str(interaction.channel.id)

        # Get terrain from travel state if available
        travel_status = get_travel_status(channel_id)
        if travel_status and terrain == "plains":
            terrain = travel_status.get('terrain', terrain)

        # === COMBAT ===
        if action == "combat":
            state = load_state(channel_id)
            party_levels = []

            for player_data in state.get("players", []):
                user_id = player_data.get("id")
                if user_id:
                    char = load_character(str(user_id))
                    if char:
                        party_levels.append(char.get("level", 1))

            if not party_levels:
                party_levels = [1, 1, 1, 1]

            encounter = generate_combat_encounter(party_levels, terrain, difficulty)

            embed = discord.Embed(
                title=f"⚔️ {encounter.name}",
                description=encounter.description,
                color=discord.Color.red()
            )

            diff_colors = {"trivial": "🟢", "easy": "🟡", "medium": "🟠", "hard": "🔴", "deadly": "💀"}
            embed.add_field(
                name="Difficulty",
                value=f"{diff_colors.get(encounter.difficulty, '⚪')} {encounter.difficulty.title()}",
                inline=True
            )
            embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            embed.add_field(name="XP Reward", value=str(encounter.xp_reward), inline=True)

            enemy_text = ""
            for monster in encounter.monsters:
                enemy_text += f"• **{monster['name']}** (HP: {monster['hp']}, AC: {monster['ac']})\n"

            if enemy_text:
                embed.add_field(name="Enemies", value=enemy_text, inline=False)

            embed.set_footer(text="Use /combat to start combat with these enemies")

            state["pending_encounter"] = encounter.to_dict()
            save_state(channel_id, state)

            await interaction.response.send_message(embed=embed)

        # === SOCIAL ===
        elif action == "social":
            encounter = generate_social_encounter(terrain)
            embed = discord.Embed(
                title=f"👥 {encounter.name}",
                description=encounter.description,
                color=discord.Color.blue()
            )
            embed.add_field(name="Type", value="Social Encounter", inline=True)
            embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            embed.set_footer(text="Roleplay this encounter or use /do to interact")
            await interaction.response.send_message(embed=embed)

        # === DISCOVERY ===
        elif action == "discovery":
            encounter = generate_discovery_encounter(terrain)
            embed = discord.Embed(
                title=f"🔍 {encounter.name}",
                description=encounter.description,
                color=discord.Color.gold()
            )
            embed.add_field(name="Type", value="Discovery", inline=True)
            embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            embed.set_footer(text="Investigate with /do or continue on your way")
            await interaction.response.send_message(embed=embed)

        # === RANDOM ===
        elif action == "random":
            rand_type = event_type
            if rand_type == "random":
                rand_type = determine_encounter_type()
                while rand_type == "combat":
                    rand_type = determine_encounter_type()

            if rand_type == "social":
                encounter = generate_social_encounter(terrain)
                embed = discord.Embed(
                    title=f"👥 {encounter.name}",
                    description=encounter.description,
                    color=discord.Color.blue()
                )
                embed.add_field(name="Type", value="Social Encounter", inline=True)
                embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            elif rand_type == "discovery":
                encounter = generate_discovery_encounter(terrain)
                embed = discord.Embed(
                    title=f"🔍 {encounter.name}",
                    description=encounter.description,
                    color=discord.Color.gold()
                )
                embed.add_field(name="Type", value="Discovery", inline=True)
                embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            else:
                event = generate_random_event(rand_type)
                emoji_map = {"weather": "🌦️", "discovery": "🔍", "rest_site": "🏕️", "social": "👥", "hazard": "⚠️"}
                embed = discord.Embed(
                    title=f"{emoji_map.get(rand_type, '❓')} {event['name']}",
                    description=event['description'],
                    color=discord.Color.green()
                )
                embed.add_field(name="Type", value=rand_type.replace("_", " ").title(), inline=True)
                if event.get('effect'):
                    embed.add_field(name="Effect", value=event['effect'], inline=False)

            await interaction.response.send_message(embed=embed)

        # === CHECK ===
        elif action == "check":
            base_chance = TERRAIN_MODIFIERS.get(terrain, {}).get("encounter_chance", 0.15)
            encounter_occurred = roll_for_encounter(terrain, hours, is_night, stealthy)

            if encounter_occurred:
                evt_type = determine_encounter_type()
                await interaction.response.send_message(
                    f"🎲 **Encounter Check:** Something happens!\n"
                    f"Event Type: **{evt_type.title()}**\n"
                    f"Use `/encounter action:combat` for combat or `/encounter action:random` for non-combat."
                )
            else:
                await interaction.response.send_message(
                    f"🎲 **Encounter Check:** The journey continues uneventfully.\n"
                    f"(Base chance: {base_chance*100:.0f}%, checked for {hours} hour(s))"
                )

    # =================================================================
    # /worldmap
    # =================================================================
    @app_commands.command(name="worldmap", description="Manage world map - view locations, fast travel, add/set locations")
    @app_commands.describe(
        action="Action to perform",
        location="Location name (for view, fasttravel, set, add)",
        terrain="Terrain type (for add)",
        location_type="Type of location (for add)",
        description="Brief description (for add)",
        distance="Distance from current location in miles (for add)",
        is_poi="Is this a point of interest? (for add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="fasttravel", value="fasttravel"),
        app_commands.Choice(name="set", value="set"),
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="info", value="info"),
    ])
    @app_commands.choices(terrain=TERRAIN_CHOICES)
    @app_commands.choices(location_type=LOCATION_TYPE_CHOICES)
    async def worldmap_cmd(
        self,
        interaction: discord.Interaction,
        action: str = "list",
        location: str = "",
        terrain: str = "wilderness",
        location_type: str = "unknown",
        description: str = "",
        distance: float = 0.0,
        is_poi: bool = False
    ):
        """Consolidated world map command."""
        channel_id = str(interaction.channel.id)

        # === LIST (default view) ===
        if action == "list" or action == "view":
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

            embed.set_footer(text="Use /worldmap action:fasttravel location:... to travel")
            await interaction.response.send_message(embed=embed)

        # === FASTTRAVEL ===
        elif action == "fasttravel":
            if not location:
                options = get_fast_travel_options(channel_id)
                if options:
                    opt_text = "\n".join([f"• {opt['name']}" for opt in options[:15]])
                    await interaction.response.send_message(
                        f"**Available Fast Travel Destinations:**\n{opt_text}\n\n"
                        f"Use `/worldmap action:fasttravel location:...` to travel.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ No fast travel destinations available.\nExplore the world to discover and visit new locations!",
                        ephemeral=True
                    )
                return

            if not can_fast_travel(channel_id, location):
                options = get_fast_travel_options(channel_id)
                if options:
                    opt_text = "\n".join([f"• {opt['name']}" for opt in options[:10]])
                    await interaction.response.send_message(
                        f"❌ Cannot fast travel to **{location}**.\n"
                        f"You can only fast travel to visited locations.\n\n"
                        f"**Available Destinations:**\n{opt_text}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ No fast travel destinations available.",
                        ephemeral=True
                    )
                return

            result = fast_travel(channel_id, location)

            if result.get("error"):
                await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
                return

            state = load_state(channel_id)
            state["location"] = location
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

        # === SET (current location) ===
        elif action == "set":
            if not location:
                await interaction.response.send_message("❌ Specify a location with `location:`", ephemeral=True)
                return

            set_current_location(channel_id, location)

            state = load_state(channel_id)
            state["location"] = location
            save_state(channel_id, state)

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

        # === ADD (new location) ===
        elif action == "add":
            if not location:
                await interaction.response.send_message("❌ Specify a location name with `location:`", ephemeral=True)
                return

            new_loc = add_location(
                channel_id=channel_id,
                name=location,
                terrain=terrain,
                location_type=location_type,
                description=description,
                is_poi=is_poi,
                status="known"
            )

            if distance > 0:
                current = get_current_location(channel_id)
                if current:
                    connect_locations(channel_id, current, location, distance)

            embed = discord.Embed(
                title="📍 Location Added",
                description=f"**{location}** has been added to the world map",
                color=discord.Color.green()
            )
            embed.add_field(name="Type", value=location_type.title(), inline=True)
            embed.add_field(name="Terrain", value=terrain.title(), inline=True)
            if is_poi:
                embed.add_field(name="Point of Interest", value="⭐ Yes", inline=True)
            if description:
                embed.add_field(name="Description", value=description, inline=False)
            if distance > 0:
                embed.add_field(
                    name="Distance",
                    value=f"{distance:.0f} miles from current location",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        # === INFO (detailed location view) ===
        elif action == "info":
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


async def setup(bot: commands.Bot):
    await bot.add_cog(WorldCog(bot))
