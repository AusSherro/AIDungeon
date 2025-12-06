"""
Combat Flow Auto-Advance System for D&D 5e Combat

Provides:
- Turn timer with configurable timeout
- Warning notifications at 30s remaining  
- Auto-pass on timeout (Dodge action)
- End-of-round effect processing
- Combat end detection
- Post-combat automation (XP, loot, rest offers)
"""

import asyncio
import random
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from utils.combat_manager import (
    load_combat, save_combat, next_turn, 
    get_combat_status, damage_combatant, heal_combatant
)
from utils.dice_roller import roll_dice


# =============================================================================
# CONFIGURATION
# =============================================================================

class CombatFlowConfig:
    """Configuration for combat flow automation."""
    
    # Turn timer settings
    TURN_TIMEOUT_SECONDS: int = 90  # Default timeout per turn
    WARNING_SECONDS: int = 30  # Seconds before timeout to send warning
    
    # Auto-advance settings
    AUTO_EXECUTE_ENEMY_TURNS: bool = True
    DELAY_BETWEEN_ENEMY_TURNS: float = 1.5  # Seconds between consecutive enemy turns
    
    # End-of-round processing
    PROCESS_ONGOING_DAMAGE: bool = True
    PROCESS_REGENERATION: bool = True
    PROCESS_CONDITION_DURATION: bool = True
    
    # Combat end automation
    AUTO_END_ON_VICTORY: bool = True
    AUTO_END_ON_TPK: bool = True
    AUTO_AWARD_XP: bool = True
    OFFER_SHORT_REST_AFTER_COMBAT: bool = True


# =============================================================================
# TURN TIMER
# =============================================================================

@dataclass
class TurnTimerState:
    """State for a player's turn timer."""
    channel_id: str
    combatant_name: str
    player_id: str
    started_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = CombatFlowConfig.TURN_TIMEOUT_SECONDS
    warning_sent: bool = False
    timer_task: Optional[asyncio.Task] = None
    
    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.started_at).total_seconds()
    
    @property
    def remaining_seconds(self) -> float:
        return max(0, self.timeout_seconds - self.elapsed_seconds)
    
    @property
    def should_warn(self) -> bool:
        return (not self.warning_sent and 
                self.remaining_seconds <= CombatFlowConfig.WARNING_SECONDS)


class CombatTimerManager:
    """
    Manages turn timers for combat encounters.
    
    Handles:
    - Starting timers when a player's turn begins
    - Sending warnings when time is running low
    - Auto-passing turns when time expires
    - Canceling timers when turns end normally
    """
    
    def __init__(self):
        self._active_timers: Dict[str, TurnTimerState] = {}  # channel_id -> timer state
        self._callbacks: Dict[str, Dict] = {}  # channel_id -> callback functions
    
    def set_callbacks(
        self, 
        channel_id: str,
        on_warning: Callable[[str, str, int], Any],
        on_timeout: Callable[[str, str], Any]
    ):
        """
        Set callback functions for timer events.
        
        Args:
            channel_id: The channel ID
            on_warning: Called when warning should be sent (channel_id, player_id, seconds_remaining)
            on_timeout: Called when turn times out (channel_id, combatant_name)
        """
        self._callbacks[channel_id] = {
            'on_warning': on_warning,
            'on_timeout': on_timeout
        }
    
    async def start_turn_timer(
        self, 
        channel_id: str,
        combatant_name: str,
        player_id: str,
        timeout_seconds: Optional[int] = None
    ) -> TurnTimerState:
        """
        Start a timer for a player's turn.
        
        Args:
            channel_id: The channel ID
            combatant_name: Name of the combatant whose turn it is
            player_id: Discord user ID of the player
            timeout_seconds: Custom timeout (uses default if not specified)
        
        Returns:
            The TurnTimerState for this turn
        """
        # Cancel any existing timer for this channel
        await self.cancel_timer(channel_id)
        
        timeout = timeout_seconds or CombatFlowConfig.TURN_TIMEOUT_SECONDS
        
        timer_state = TurnTimerState(
            channel_id=channel_id,
            combatant_name=combatant_name,
            player_id=player_id,
            timeout_seconds=timeout
        )
        
        # Start the timer task
        timer_state.timer_task = asyncio.create_task(
            self._run_timer(timer_state)
        )
        
        self._active_timers[channel_id] = timer_state
        return timer_state
    
    async def cancel_timer(self, channel_id: str) -> bool:
        """
        Cancel the active timer for a channel.
        
        Returns:
            True if a timer was cancelled, False if no timer was active
        """
        if channel_id not in self._active_timers:
            return False
        
        timer_state = self._active_timers[channel_id]
        
        if timer_state.timer_task and not timer_state.timer_task.done():
            timer_state.timer_task.cancel()
            try:
                await timer_state.timer_task
            except asyncio.CancelledError:
                pass
        
        del self._active_timers[channel_id]
        return True
    
    def get_timer_state(self, channel_id: str) -> Optional[TurnTimerState]:
        """Get the current timer state for a channel."""
        return self._active_timers.get(channel_id)
    
    def get_remaining_time(self, channel_id: str) -> Optional[int]:
        """Get remaining seconds for the current turn, or None if no timer."""
        timer = self._active_timers.get(channel_id)
        return int(timer.remaining_seconds) if timer else None
    
    async def _run_timer(self, timer_state: TurnTimerState):
        """Internal timer loop that handles warnings and timeout."""
        try:
            # Wait until warning time
            warning_wait = timer_state.timeout_seconds - CombatFlowConfig.WARNING_SECONDS
            if warning_wait > 0:
                await asyncio.sleep(warning_wait)
            
            # Check if still active (turn might have ended)
            if timer_state.channel_id not in self._active_timers:
                return
            
            # Send warning
            timer_state.warning_sent = True
            callbacks = self._callbacks.get(timer_state.channel_id, {})
            if 'on_warning' in callbacks:
                await callbacks['on_warning'](
                    timer_state.channel_id,
                    timer_state.player_id,
                    int(timer_state.remaining_seconds)
                )
            
            # Wait for remaining time
            await asyncio.sleep(timer_state.remaining_seconds)
            
            # Check if still active
            if timer_state.channel_id not in self._active_timers:
                return
            
            # Timeout - trigger auto-pass
            if 'on_timeout' in callbacks:
                await callbacks['on_timeout'](
                    timer_state.channel_id,
                    timer_state.combatant_name
                )
            
            # Clean up
            if timer_state.channel_id in self._active_timers:
                del self._active_timers[timer_state.channel_id]
                
        except asyncio.CancelledError:
            pass  # Timer was cancelled (turn ended normally)


# Global timer manager instance
combat_timer = CombatTimerManager()


# =============================================================================
# END-OF-ROUND PROCESSING
# =============================================================================

class ConditionEffect(Enum):
    """Types of condition effects to process."""
    ONGOING_DAMAGE = "ongoing_damage"
    REGENERATION = "regeneration"
    DURATION_COUNTDOWN = "duration"
    SAVING_THROW = "saving_throw"
    CONCENTRATION = "concentration"


@dataclass
class EndOfRoundResult:
    """Result of end-of-round processing for a combatant."""
    combatant_name: str
    effects: List[Dict] = field(default_factory=list)
    hp_change: int = 0
    conditions_expired: List[str] = field(default_factory=list)
    conditions_saved: List[str] = field(default_factory=list)
    concentration_broken: bool = False
    narration: str = ""


def process_end_of_turn_effects(channel_id: str, combatant: Dict) -> EndOfRoundResult:
    """
    Process end-of-turn effects for a specific combatant.
    
    This includes:
    - Ongoing damage (poison, fire, etc.)
    - Regeneration (trolls, vampires, etc.)
    - Condition duration countdowns
    - End-of-turn saving throws
    
    Args:
        channel_id: The channel ID
        combatant: The combatant whose turn just ended
    
    Returns:
        EndOfRoundResult with all effects processed
    """
    result = EndOfRoundResult(combatant_name=combatant['name'])
    narration_parts = []
    
    # Process ongoing damage
    ongoing_damage = combatant.get('ongoing_damage', [])
    for damage_effect in ongoing_damage:
        damage_type = damage_effect.get('type', 'damage')
        damage_amount = damage_effect.get('amount', 0)
        
        if damage_amount > 0:
            damage_combatant(channel_id, combatant['name'], damage_amount, damage_type)
            result.hp_change -= damage_amount
            result.effects.append({
                'type': 'ongoing_damage',
                'damage': damage_amount,
                'damage_type': damage_type
            })
            narration_parts.append(f"takes {damage_amount} {damage_type} damage")
    
    # Process regeneration
    regen_amount = combatant.get('regeneration', 0)
    if regen_amount > 0 and combatant.get('hp', 0) > 0:
        if not combatant.get('regeneration_blocked'):
            heal_combatant(channel_id, combatant['name'], regen_amount)
            result.hp_change += regen_amount
            result.effects.append({
                'type': 'regeneration',
                'amount': regen_amount
            })
            narration_parts.append(f"regenerates {regen_amount} HP")
    
    # Process condition durations
    status_durations = combatant.get('status_durations', {})
    for condition, duration in list(status_durations.items()):
        if duration <= 1:
            # Condition expires
            result.conditions_expired.append(condition)
            narration_parts.append(f"is no longer {condition}")
        else:
            # Decrement duration (actual update happens in combat_manager)
            pass
    
    # Process end-of-turn saving throws
    saving_throws = combatant.get('end_of_turn_saves', [])
    for save in saving_throws:
        save_dc = save.get('dc', 10)
        save_ability = save.get('ability', 'CON')
        condition = save.get('condition', 'affected')
        
        # Roll saving throw
        save_roll = random.randint(1, 20)
        ability_mod = (combatant.get('stats', {}).get(save_ability, 10) - 10) // 2
        total = save_roll + ability_mod
        
        if total >= save_dc:
            result.conditions_saved.append(condition)
            narration_parts.append(f"breaks free of {condition} (rolled {total} vs DC {save_dc})")
        else:
            narration_parts.append(f"fails to break free of {condition} (rolled {total} vs DC {save_dc})")
    
    # Build narration
    if narration_parts:
        result.narration = f"{combatant['name']} " + ", ".join(narration_parts) + "."
    
    return result


def process_start_of_turn_effects(channel_id: str, combatant: Dict) -> EndOfRoundResult:
    """
    Process start-of-turn effects for a combatant.
    
    This includes:
    - Start-of-turn damage (standing in fire, etc.)
    - Start-of-turn saving throws
    """
    result = EndOfRoundResult(combatant_name=combatant['name'])
    narration_parts = []
    
    # Process start-of-turn damage
    start_damage = combatant.get('start_of_turn_damage', [])
    for damage_effect in start_damage:
        damage_type = damage_effect.get('type', 'damage')
        damage_amount = damage_effect.get('amount', 0)
        
        if damage_amount > 0:
            damage_combatant(channel_id, combatant['name'], damage_amount, damage_type)
            result.hp_change -= damage_amount
            result.effects.append({
                'type': 'start_of_turn_damage',
                'damage': damage_amount,
                'damage_type': damage_type
            })
            narration_parts.append(f"takes {damage_amount} {damage_type} damage at the start of their turn")
    
    if narration_parts:
        result.narration = f"{combatant['name']} " + ", ".join(narration_parts) + "."
    
    return result


def process_round_transition(channel_id: str) -> Dict:
    """
    Process the transition between rounds.
    
    Called when the initiative order loops back to the top.
    
    Returns:
        Dict with round info and effects processed
    """
    combat = load_combat(channel_id)
    if not combat:
        return {'error': 'No active combat'}
    
    current_round = combat.get('round', 1)
    new_round = current_round + 1
    
    results = {
        'old_round': current_round,
        'new_round': new_round,
        'effects': [],
        'lair_action_reset': False
    }
    
    # Reset lair action availability
    if combat.get('lair_actions'):
        combat['lair_action_used_this_round'] = False
        results['lair_action_reset'] = True
    
    # Update round counter
    combat['round'] = new_round
    combat['current_turn'] = 0
    
    # Process any round-transition effects
    for combatant in combat.get('combatants', []):
        # Reset reaction availability
        combatant['reaction_used'] = False
        
        # Clear "damaged this round" tracking
        combatant['damaged_this_round'] = False
        
        # Decrement status durations
        status_durations = combatant.get('status_durations', {})
        expired = []
        for status, duration in list(status_durations.items()):
            new_duration = duration - 1
            if new_duration <= 0:
                expired.append(status)
                del status_durations[status]
            else:
                status_durations[status] = new_duration
        
        # Remove expired conditions
        for status in expired:
            if status in combatant.get('status', []):
                combatant['status'].remove(status)
                results['effects'].append({
                    'combatant': combatant['name'],
                    'effect': f"{status} expired"
                })
    
    save_combat(channel_id, combat)
    return results


# =============================================================================
# COMBAT END DETECTION
# =============================================================================

class CombatEndReason(Enum):
    """Reasons why combat ended."""
    VICTORY = "victory"           # All enemies defeated
    TPK = "tpk"                   # All players defeated (Total Party Kill)
    FLED = "fled"                 # Combat ended due to fleeing
    MANUAL = "manual"             # DM manually ended combat
    TRUCE = "truce"               # Combat ended via negotiation


@dataclass
class CombatEndResult:
    """Result of combat end detection."""
    should_end: bool = False
    reason: Optional[CombatEndReason] = None
    surviving_players: List[str] = field(default_factory=list)
    defeated_enemies: List[Dict] = field(default_factory=list)
    total_xp: int = 0
    loot_generated: Optional[Dict] = None
    summary: str = ""


def check_combat_end(channel_id: str) -> CombatEndResult:
    """
    Check if combat should end and determine the reason.
    
    Args:
        channel_id: The channel ID
    
    Returns:
        CombatEndResult with end status and details
    """
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        return CombatEndResult(should_end=False)
    
    combatants = combat.get('combatants', [])
    
    # Count alive players and enemies
    alive_players = [
        c for c in combatants 
        if c.get('type') == 'player' 
        and c.get('hp', 0) > 0 
        and 'dead' not in c.get('status', [])
    ]
    
    alive_enemies = [
        c for c in combatants 
        if c.get('type') == 'enemy' 
        and c.get('hp', 0) > 0 
        and 'dead' not in c.get('status', [])
    ]
    
    defeated_enemies = [
        c for c in combatants 
        if c.get('type') == 'enemy' 
        and (c.get('hp', 0) <= 0 or 'dead' in c.get('status', []))
    ]
    
    result = CombatEndResult()
    result.surviving_players = [p['name'] for p in alive_players]
    result.defeated_enemies = defeated_enemies
    
    # Check for victory (all enemies defeated)
    if not alive_enemies and alive_players:
        result.should_end = True
        result.reason = CombatEndReason.VICTORY
        
        # Calculate total XP
        for enemy in defeated_enemies:
            result.total_xp += enemy.get('xp', 0)
        
        result.summary = (
            f"🎉 **Victory!** All enemies have been defeated.\n"
            f"Surviving party members: {', '.join(result.surviving_players)}"
        )
    
    # Check for TPK (all players defeated)
    elif not alive_players and alive_enemies:
        result.should_end = True
        result.reason = CombatEndReason.TPK
        result.summary = (
            f"💀 **Total Party Kill!** All adventurers have fallen.\n"
            f"Remaining enemies: {', '.join([e['name'] for e in alive_enemies])}"
        )
    
    # Check for everyone dead (rare but possible with AoE)
    elif not alive_players and not alive_enemies:
        result.should_end = True
        result.reason = CombatEndReason.VICTORY  # Treat as pyrrhic victory
        result.summary = "💀 The battle ends with no survivors..."
    
    return result


def get_combat_status_summary(channel_id: str) -> Dict:
    """
    Get a comprehensive status summary for display at turn start.
    
    Returns dict with:
        - round: Current round number
        - current_combatant: Who's turn it is
        - player_status: List of player HP/conditions
        - enemy_status: List of enemy HP (if visible)
        - environment: Any active environmental effects
    """
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        return {'error': 'No active combat'}
    
    current_turn = combat.get('current_turn', 0)
    turn_order = combat.get('turn_order', [])
    current_combatant = turn_order[current_turn] if turn_order else None
    
    # Build player status
    player_status = []
    for c in combat.get('combatants', []):
        if c.get('type') != 'player':
            continue
        
        hp = c.get('hp', 0)
        max_hp = c.get('max_hp', 1)
        hp_pct = hp / max_hp
        
        # Health status emoji
        if hp <= 0:
            health_emoji = "💀"
        elif hp_pct <= 0.25:
            health_emoji = "❤️"  # Critical
        elif hp_pct <= 0.5:
            health_emoji = "💛"  # Wounded
        else:
            health_emoji = "💚"  # Healthy
        
        conditions = c.get('status', [])
        condition_str = f" [{', '.join(conditions)}]" if conditions else ""
        
        player_status.append({
            'name': c['name'],
            'hp': hp,
            'max_hp': max_hp,
            'health_emoji': health_emoji,
            'conditions': conditions,
            'display': f"{health_emoji} **{c['name']}**: {hp}/{max_hp}{condition_str}"
        })
    
    # Build enemy status (bloodied indicators only)
    enemy_status = []
    for c in combat.get('combatants', []):
        if c.get('type') != 'enemy':
            continue
        
        hp = c.get('hp', 0)
        max_hp = c.get('max_hp', 1)
        
        if hp <= 0:
            status = "💀 Dead"
        elif hp <= max_hp * 0.5:
            status = "🩸 Bloodied"
        else:
            status = "🟢 Healthy"
        
        enemy_status.append({
            'name': c['name'],
            'status': status,
            'display': f"{c['name']}: {status}"
        })
    
    return {
        'round': combat.get('round', 1),
        'current_combatant': current_combatant,
        'player_status': player_status,
        'enemy_status': enemy_status,
        'lair_actions_available': (
            combat.get('lair_actions') and 
            not combat.get('lair_action_used_this_round')
        )
    }


# =============================================================================
# TURN ANNOUNCEMENT BUILDER
# =============================================================================

def build_turn_announcement(channel_id: str, combatant: Dict) -> Dict:
    """
    Build a rich turn announcement for a player.
    
    Returns dict with:
        - message: The formatted Discord message
        - tts_text: Text for TTS narration
        - available_actions: List of suggested actions
    """
    combat = load_combat(channel_id)
    if not combat:
        return {'error': 'No active combat'}
    
    name = combatant['name']
    player_id = combatant.get('id')
    hp = combatant.get('hp', 0)
    max_hp = combatant.get('max_hp', 1)
    conditions = combatant.get('status', [])
    
    # Health status
    hp_pct = hp / max_hp
    if hp_pct <= 0.25:
        health_warning = "⚠️ **CRITICAL HP!** "
    elif hp_pct <= 0.5:
        health_warning = "⚡ You're wounded. "
    else:
        health_warning = ""
    
    # Build conditions string
    condition_str = ""
    if conditions:
        condition_effects = []
        for cond in conditions:
            cond_lower = cond.lower()
            if 'poisoned' in cond_lower:
                condition_effects.append("🤢 Poisoned (disadvantage on attacks/checks)")
            elif 'frightened' in cond_lower:
                condition_effects.append("😨 Frightened (can't move closer to source)")
            elif 'restrained' in cond_lower:
                condition_effects.append("⛓️ Restrained (disadvantage on DEX saves, attacks have advantage)")
            elif 'blinded' in cond_lower:
                condition_effects.append("👁️ Blinded (attacks have disadvantage)")
            elif 'stunned' in cond_lower:
                condition_effects.append("😵 Stunned (can't act, auto-fail STR/DEX saves)")
            elif 'prone' in cond_lower:
                condition_effects.append("⬇️ Prone (stand up costs half movement)")
            elif 'grappled' in cond_lower:
                condition_effects.append("🤼 Grappled (speed is 0)")
            else:
                condition_effects.append(f"⚡ {cond.title()}")
        condition_str = "\n" + "\n".join(condition_effects)
    
    # Reaction availability
    reaction_available = not combatant.get('reaction_used', False)
    reaction_str = "✅ Reaction available" if reaction_available else "❌ Reaction used"
    
    # Available actions based on state
    available_actions = []
    if hp > 0:
        available_actions.append("⚔️ `/attack` - Make an attack")
        available_actions.append("✨ `/cast` - Cast a spell")
        available_actions.append("🎭 `/do` - Take another action")
        available_actions.append("🏃 `/nextturn` - End your turn")
        if conditions:
            available_actions.append("🎲 `/roll` - Make a saving throw")
    else:
        available_actions.append("💀 You're unconscious!")
        available_actions.append("🎲 `/deathsave` - Roll a death saving throw")
    
    # Build message
    message = (
        f"➡️ <@{player_id}> (**{name}**), it's your turn!\n"
        f"───────────────────────\n"
        f"❤️ HP: **{hp}/{max_hp}** | 🛡️ AC: {combatant.get('ac', 10)} | {reaction_str}\n"
        f"{health_warning}{condition_str}\n"
        f"\n**Actions:**\n" + "\n".join(available_actions)
    )
    
    # TTS text (simplified)
    tts_text = f"{name}, it's your turn! "
    if hp_pct <= 0.25:
        tts_text += "Your health is critical! "
    if conditions:
        tts_text += f"You are currently {' and '.join(conditions)}. "
    tts_text += "What do you do?"
    
    return {
        'message': message,
        'tts_text': tts_text,
        'available_actions': available_actions,
        'player_id': player_id,
        'is_critical': hp_pct <= 0.25,
        'has_conditions': bool(conditions)
    }


# =============================================================================
# AUTO-PASS TURN
# =============================================================================

def execute_auto_pass(channel_id: str, combatant_name: str) -> Dict:
    """
    Execute an automatic turn pass (Dodge action) for a timed-out player.
    
    The character takes the Dodge action, giving attackers disadvantage
    until their next turn.
    
    Returns:
        Dict with action taken and result
    """
    combat = load_combat(channel_id)
    if not combat:
        return {'error': 'No active combat'}
    
    # Find the combatant
    combatant = None
    for c in combat.get('combatants', []):
        if c['name'].lower() == combatant_name.lower():
            combatant = c
            break
    
    if not combatant:
        return {'error': 'Combatant not found'}
    
    # Apply Dodge condition until next turn
    if 'dodging' not in combatant.get('status', []):
        combatant.setdefault('status', []).append('dodging')
        combatant['status_durations'] = combatant.get('status_durations', {})
        combatant['status_durations']['dodging'] = 1  # Lasts until their next turn
    
    save_combat(channel_id, combat)
    
    return {
        'action': 'dodge',
        'combatant': combatant_name,
        'message': (
            f"⏰ **{combatant_name}'s turn has timed out!**\n"
            f"🛡️ {combatant_name} takes the **Dodge** action.\n"
            f"*Attacks against {combatant_name} have disadvantage until their next turn.*"
        ),
        'tts_text': f"{combatant_name}'s turn has timed out. They take the dodge action."
    }


# =============================================================================
# POST-COMBAT AUTOMATION
# =============================================================================

@dataclass
class PostCombatResult:
    """Result of post-combat processing."""
    xp_awarded: int = 0
    xp_per_player: int = 0
    level_ups: List[str] = field(default_factory=list)
    loot: Optional[Dict] = None
    can_short_rest: bool = True
    summary_lines: List[str] = field(default_factory=list)


def process_post_combat(
    channel_id: str, 
    player_ids: List[str],
    end_result: CombatEndResult
) -> PostCombatResult:
    """
    Process post-combat rewards and cleanup.
    
    Args:
        channel_id: The channel ID
        player_ids: List of player Discord IDs
        end_result: The combat end result
    
    Returns:
        PostCombatResult with XP, loot, and level-up info
    """
    from utils.xp_manager import award_party_xp, XP_THRESHOLDS
    from utils.loot_manager import generate_enemy_loot
    from utils.character_manager import load_character
    
    result = PostCombatResult()
    
    if end_result.reason == CombatEndReason.TPK:
        result.summary_lines.append("💀 **The party has fallen...**")
        result.can_short_rest = False
        return result
    
    # Award XP
    if end_result.total_xp > 0 and player_ids:
        xp_results = award_party_xp(player_ids, end_result.total_xp, equal_split=True)
        result.xp_awarded = end_result.total_xp
        result.xp_per_player = end_result.total_xp // len(player_ids)
        
        for xp_result in xp_results:
            if xp_result.get('level_up'):
                result.level_ups.append(xp_result['character'])
        
        result.summary_lines.append(
            f"✨ **XP Earned:** {result.xp_awarded} "
            f"({result.xp_per_player} each)"
        )
        
        if result.level_ups:
            result.summary_lines.append(
                f"🎉 **Level Up!** {', '.join(result.level_ups)}"
            )
    
    # ==== PHASE 11: Enhanced Loot Generation ====
    # Generate loot from ALL defeated enemies using the new system
    if end_result.defeated_enemies:
        try:
            from utils.combat_trigger import generate_loot_for_enemies, format_post_combat_loot
            from utils.inventory_manager import create_loot_distribution, add_unidentified_item
            
            # Generate loot based on all defeated enemies
            loot = generate_loot_for_enemies(
                end_result.defeated_enemies,
                party_size=len(player_ids) if player_ids else 1
            )
            
            # Create a claimable loot pile
            loot_items = loot.get('items', [])
            magic_items = loot.get('magic_items', [])
            gold = loot.get('gold', 0)
            
            # Add unidentified magic items
            unidentified_items = []
            for magic_item in magic_items:
                if not magic_item.get('identified', True):
                    # Add as unidentified
                    unidentified_items.append({
                        'display_name': f"Mysterious {magic_item.get('rarity', 'magic')} item",
                        'true_name': magic_item['name'],
                        'rarity': magic_item.get('rarity', 'common')
                    })
                else:
                    loot_items.append(magic_item['name'])
            
            # Create the loot distribution for claiming
            if loot_items or gold > 0 or unidentified_items:
                create_loot_distribution(
                    channel_id,
                    items=loot_items,
                    gold=gold,
                    source=f"Defeated {len(end_result.defeated_enemies)} enemies"
                )
                
                result.loot = {
                    'gold': gold,
                    'items': loot_items,
                    'magic_items': unidentified_items
                }
                
                # Build loot summary
                result.summary_lines.append("\n💰 **LOOT FOUND!**")
                if gold > 0:
                    result.summary_lines.append(f"  • **Gold:** {gold} gp")
                if loot_items:
                    result.summary_lines.append(f"  • **Items:** {', '.join(loot_items)}")
                if unidentified_items:
                    result.summary_lines.append(f"  • **Magic Items:** {len(unidentified_items)} unidentified ✨")
                    result.summary_lines.append("    *Use `/identify <item>` to identify magic items*")
                
                result.summary_lines.append("*Use `/claimloot <item>` to claim, `/splitgold` to divide gold.*")
        except Exception as e:
            # Fallback to old loot system
            print(f"Phase 11 loot generation error: {e}")
            toughest = max(
                end_result.defeated_enemies,
                key=lambda e: e.get('xp', 0)
            )
            cr = int(str(toughest.get('cr', '1')).split('/')[0]) if toughest.get('cr') else 1
            result.loot = generate_enemy_loot(toughest['name'], cr)
            
            if result.loot:
                result.summary_lines.append("💰 **Loot Found!**")
    
    # Short rest option
    if result.can_short_rest:
        result.summary_lines.append(
            "───────────────────────\n"
            "☀️ *You may take a short rest to recover.*\n"
            "Use `/rest short` to spend hit dice and recover HP."
        )
    
    return result
