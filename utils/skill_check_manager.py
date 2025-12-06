"""
Skill Check Resolution Manager for D&D 5e

Handles the complete skill check flow:
1. Parse AI requests for skill checks
2. Prompt players for rolls with buttons
3. Handle advantage/disadvantage from conditions
4. Re-inject results to AI for consequence narration
5. Group check handling with majority rule
6. Passive check automation
"""

import re
import random
import asyncio
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Skill-to-ability mapping
SKILLS = {
    'acrobatics': 'DEX',
    'animal_handling': 'WIS',
    'arcana': 'INT',
    'athletics': 'STR',
    'deception': 'CHA',
    'history': 'INT',
    'insight': 'WIS',
    'intimidation': 'CHA',
    'investigation': 'INT',
    'medicine': 'WIS',
    'nature': 'INT',
    'perception': 'WIS',
    'performance': 'CHA',
    'persuasion': 'CHA',
    'religion': 'INT',
    'sleight_of_hand': 'DEX',
    'stealth': 'DEX',
    'survival': 'WIS'
}

# Ability score abbreviations
ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha']
ABILITY_FULL_NAMES = {
    'str': 'Strength', 'strength': 'Strength',
    'dex': 'Dexterity', 'dexterity': 'Dexterity',
    'con': 'Constitution', 'constitution': 'Constitution',
    'int': 'Intelligence', 'intelligence': 'Intelligence',
    'wis': 'Wisdom', 'wisdom': 'Wisdom',
    'cha': 'Charisma', 'charisma': 'Charisma'
}


class CheckType(Enum):
    SKILL = "skill"
    ABILITY = "ability"
    SAVING_THROW = "saving_throw"


@dataclass
class SkillCheckRequest:
    """Represents a parsed skill check request from AI narration."""
    check_type: CheckType
    skill_or_ability: str
    dc: Optional[int] = None
    target_players: List[str] = field(default_factory=list)  # Empty = all players
    is_group_check: bool = False
    advantage: bool = False
    disadvantage: bool = False
    context: str = ""  # What action triggered this check
    raw_text: str = ""  # Original AI text that requested the check


@dataclass
class SkillCheckResult:
    """Result of a skill check roll."""
    player_id: str
    player_name: str
    skill_or_ability: str
    roll: int  # Natural roll (d20)
    modifier: int
    total: int
    dc: Optional[int]
    success: Optional[bool]
    natural_20: bool
    natural_1: bool
    advantage: bool
    disadvantage: bool
    rolls: List[int] = field(default_factory=list)  # All rolls made (for adv/dis)


@dataclass
class GroupCheckResult:
    """Result of a group skill check."""
    skill_or_ability: str
    dc: Optional[int]
    individual_results: List[SkillCheckResult]
    successes: int
    failures: int
    group_success: bool  # True if majority succeeded
    

@dataclass
class PendingCheck:
    """A skill check waiting for player response."""
    channel_id: str
    request: SkillCheckRequest
    players_needed: List[str]  # Player IDs who need to roll
    results: Dict[str, SkillCheckResult] = field(default_factory=dict)
    timeout_seconds: int = 60
    message_id: Optional[int] = None  # Discord message with buttons
    created_at: float = 0.0


# Global pending checks storage
_pending_checks: Dict[str, PendingCheck] = {}  # channel_id -> PendingCheck


# =============================================================================
# SKILL CHECK DETECTION PATTERNS
# =============================================================================

# Primary pattern: "Roll [Skill/Ability], DC X" or "Make a [Skill] check"
SKILL_CHECK_PATTERN = re.compile(
    r'(?:roll|make)\s+(?:a\s+)?'
    r'(?:(?P<ability>strength|dexterity|constitution|intelligence|wisdom|charisma|str|dex|con|int|wis|cha)\s*(?:\()?)?'
    r'(?P<skill>acrobatics|animal\s*handling|arcana|athletics|deception|history|insight|intimidation|'
    r'investigation|medicine|nature|perception|performance|persuasion|religion|sleight\s*of\s*hand|'
    r'stealth|survival)'
    r'(?:\s*\))?'
    r'(?:\s*(?:check|save|roll))?'
    r'(?:,?\s*dc\s*(?P<dc>\d+))?',
    re.IGNORECASE
)

# Ability check pattern: "Roll a Strength check"
ABILITY_CHECK_PATTERN = re.compile(
    r'(?:roll|make)\s+(?:a\s+)?'
    r'(?P<ability>strength|dexterity|constitution|intelligence|wisdom|charisma|str|dex|con|int|wis|cha)'
    r'(?:\s+(?:check|save|roll|saving\s+throw))?'
    r'(?:,?\s*dc\s*(?P<dc>\d+))?',
    re.IGNORECASE
)

# Saving throw pattern: "Make a Dexterity saving throw"
SAVING_THROW_PATTERN = re.compile(
    r'(?:roll|make)\s+(?:a\s+)?'
    r'(?P<ability>strength|dexterity|constitution|intelligence|wisdom|charisma|str|dex|con|int|wis|cha)'
    r'\s+saving\s+throw'
    r'(?:,?\s*dc\s*(?P<dc>\d+))?',
    re.IGNORECASE
)

# Group check pattern: "Everyone roll", "The party must", "All of you"
GROUP_CHECK_PATTERN = re.compile(
    r'(?:everyone|all\s+of\s+you|the\s+party|each\s+of\s+you|all\s+players?)',
    re.IGNORECASE
)

# DC extraction backup pattern
DC_PATTERN = re.compile(r'dc\s*(\d+)', re.IGNORECASE)

# Target player pattern: "Player Name, roll..." or "Player Name must..."
PLAYER_TARGET_PATTERN = re.compile(
    r'(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s+(?:roll|make|must)',
    re.IGNORECASE
)


def parse_skill_check_request(text: str, player_names: List[str] = None) -> Optional[SkillCheckRequest]:
    """
    Parse AI narration to detect skill check requests.
    
    Args:
        text: The AI's narration text
        player_names: List of player character names for target detection
    
    Returns:
        SkillCheckRequest if a check is detected, None otherwise
    """
    if player_names is None:
        player_names = []
    
    # Check for saving throw first (more specific)
    save_match = SAVING_THROW_PATTERN.search(text)
    if save_match:
        ability = save_match.group('ability').lower()
        dc = int(save_match.group('dc')) if save_match.group('dc') else None
        
        return SkillCheckRequest(
            check_type=CheckType.SAVING_THROW,
            skill_or_ability=normalize_ability(ability),
            dc=dc,
            is_group_check=bool(GROUP_CHECK_PATTERN.search(text)),
            target_players=find_target_players(text, player_names),
            raw_text=text
        )
    
    # Check for skill check
    skill_match = SKILL_CHECK_PATTERN.search(text)
    if skill_match:
        skill = skill_match.group('skill').lower().replace(' ', '_')
        dc = int(skill_match.group('dc')) if skill_match.group('dc') else None
        
        # Try to get DC from elsewhere in the text if not in the match
        if dc is None:
            dc_match = DC_PATTERN.search(text)
            if dc_match:
                dc = int(dc_match.group(1))
        
        return SkillCheckRequest(
            check_type=CheckType.SKILL,
            skill_or_ability=skill,
            dc=dc,
            is_group_check=bool(GROUP_CHECK_PATTERN.search(text)),
            target_players=find_target_players(text, player_names),
            raw_text=text
        )
    
    # Check for ability check
    ability_match = ABILITY_CHECK_PATTERN.search(text)
    if ability_match:
        ability = ability_match.group('ability').lower()
        dc = int(ability_match.group('dc')) if ability_match.group('dc') else None
        
        if dc is None:
            dc_match = DC_PATTERN.search(text)
            if dc_match:
                dc = int(dc_match.group(1))
        
        return SkillCheckRequest(
            check_type=CheckType.ABILITY,
            skill_or_ability=normalize_ability(ability),
            dc=dc,
            is_group_check=bool(GROUP_CHECK_PATTERN.search(text)),
            target_players=find_target_players(text, player_names),
            raw_text=text
        )
    
    return None


def normalize_ability(ability: str) -> str:
    """Convert ability abbreviation to full name."""
    ability = ability.lower()
    return ABILITY_FULL_NAMES.get(ability, ability.title())


def normalize_skill(skill: str) -> str:
    """Normalize skill name to internal format."""
    return skill.lower().replace(' ', '_').replace('-', '_')


def find_target_players(text: str, player_names: List[str]) -> List[str]:
    """Find specific player names mentioned in the check request."""
    targets = []
    text_lower = text.lower()
    
    for name in player_names:
        if name.lower() in text_lower:
            targets.append(name)
    
    return targets


# =============================================================================
# SKILL CHECK EXECUTION
# =============================================================================

def calculate_skill_modifier(char_data: dict, skill_or_ability: str, check_type: CheckType) -> int:
    """
    Calculate the total modifier for a skill check.
    
    Args:
        char_data: Character data dictionary
        skill_or_ability: The skill or ability being checked
        check_type: Type of check (skill, ability, or saving throw)
    
    Returns:
        Total modifier to add to the d20 roll
    """
    from utils.character_manager import get_ability_modifier, calculate_skill_bonus
    
    if check_type == CheckType.SKILL:
        return calculate_skill_bonus(char_data, skill_or_ability)
    elif check_type == CheckType.ABILITY:
        ability = skill_or_ability.upper()[:3]
        score = char_data.get(ability, 10)
        return get_ability_modifier(score)
    elif check_type == CheckType.SAVING_THROW:
        ability = skill_or_ability.upper()[:3]
        score = char_data.get(ability, 10)
        base_mod = get_ability_modifier(score)
        
        # Check for saving throw proficiency
        save_profs = char_data.get('saving_throw_proficiencies', [])
        if ability.lower() in [s.lower() for s in save_profs]:
            base_mod += char_data.get('proficiency', 2)
        
        return base_mod
    
    return 0


def check_advantage_disadvantage(char_data: dict, skill_or_ability: str) -> Tuple[bool, bool]:
    """
    Check if the character has advantage or disadvantage based on conditions.
    
    Returns:
        (has_advantage, has_disadvantage)
    """
    conditions = char_data.get('conditions', [])
    
    has_advantage = False
    has_disadvantage = False
    
    # Conditions that grant disadvantage
    disadvantage_conditions = ['frightened', 'poisoned', 'exhaustion']
    for condition in conditions:
        if isinstance(condition, str):
            cond_name = condition.lower()
        elif isinstance(condition, dict):
            cond_name = condition.get('name', '').lower()
        else:
            continue
        
        if cond_name in disadvantage_conditions:
            has_disadvantage = True
        
        # Special cases
        if cond_name == 'invisible':
            # Advantage on attack rolls (handled elsewhere)
            pass
        if cond_name == 'restrained':
            has_disadvantage = True  # DEX saves
        if cond_name == 'prone':
            # Disadvantage on attacks (not skill checks usually)
            pass
    
    # Check for buffs that grant advantage
    buffs = char_data.get('buffs', [])
    for buff in buffs:
        if isinstance(buff, str):
            buff_name = buff.lower()
        elif isinstance(buff, dict):
            buff_name = buff.get('name', '').lower()
        else:
            continue
        
        if 'enhance ability' in buff_name:
            has_advantage = True
        if 'guidance' in buff_name:
            # Guidance adds 1d4, not advantage - handled separately
            pass
    
    return has_advantage, has_disadvantage


def roll_skill_check(
    player_id: str,
    player_name: str,
    char_data: dict,
    request: SkillCheckRequest,
    force_advantage: bool = False,
    force_disadvantage: bool = False
) -> SkillCheckResult:
    """
    Execute a skill check roll for a player.
    
    Args:
        player_id: Discord user ID
        player_name: Character name
        char_data: Character data dictionary
        request: The skill check request
        force_advantage: Override to force advantage
        force_disadvantage: Override to force disadvantage
    
    Returns:
        SkillCheckResult with roll details
    """
    # Calculate modifier
    modifier = calculate_skill_modifier(char_data, request.skill_or_ability, request.check_type)
    
    # Check for advantage/disadvantage from conditions
    cond_adv, cond_dis = check_advantage_disadvantage(char_data, request.skill_or_ability)
    
    has_advantage = force_advantage or request.advantage or cond_adv
    has_disadvantage = force_disadvantage or request.disadvantage or cond_dis
    
    # Advantage and disadvantage cancel out
    if has_advantage and has_disadvantage:
        has_advantage = False
        has_disadvantage = False
    
    # Roll the dice
    roll1 = random.randint(1, 20)
    roll2 = random.randint(1, 20) if (has_advantage or has_disadvantage) else roll1
    
    if has_advantage:
        final_roll = max(roll1, roll2)
        rolls = [roll1, roll2]
    elif has_disadvantage:
        final_roll = min(roll1, roll2)
        rolls = [roll1, roll2]
    else:
        final_roll = roll1
        rolls = [roll1]
    
    total = final_roll + modifier
    
    # Determine success/failure
    success = None
    if request.dc is not None:
        if final_roll == 20:
            success = True  # Natural 20 always succeeds on ability checks (house rule, optional)
        elif final_roll == 1:
            success = False  # Natural 1 always fails (house rule, optional)
        else:
            success = total >= request.dc
    
    return SkillCheckResult(
        player_id=player_id,
        player_name=player_name,
        skill_or_ability=request.skill_or_ability,
        roll=final_roll,
        modifier=modifier,
        total=total,
        dc=request.dc,
        success=success,
        natural_20=(final_roll == 20),
        natural_1=(final_roll == 1),
        advantage=has_advantage,
        disadvantage=has_disadvantage,
        rolls=rolls
    )


def resolve_group_check(results: List[SkillCheckResult], dc: Optional[int]) -> GroupCheckResult:
    """
    Resolve a group skill check using majority rule.
    
    Args:
        results: List of individual skill check results
        dc: The DC for the check
    
    Returns:
        GroupCheckResult with overall success/failure
    """
    if not results:
        return GroupCheckResult(
            skill_or_ability="",
            dc=dc,
            individual_results=[],
            successes=0,
            failures=0,
            group_success=False
        )
    
    successes = sum(1 for r in results if r.success)
    failures = len(results) - successes
    
    # Majority rule: more than half must succeed
    group_success = successes > failures
    
    return GroupCheckResult(
        skill_or_ability=results[0].skill_or_ability,
        dc=dc,
        individual_results=results,
        successes=successes,
        failures=failures,
        group_success=group_success
    )


# =============================================================================
# PASSIVE CHECKS
# =============================================================================

def calculate_passive_score(char_data: dict, skill: str) -> int:
    """
    Calculate passive skill score (10 + modifiers).
    
    Args:
        char_data: Character data dictionary
        skill: The skill to calculate passive for
    
    Returns:
        Passive skill score
    """
    from utils.character_manager import calculate_skill_bonus
    
    modifier = calculate_skill_bonus(char_data, skill)
    
    # Check for advantage/disadvantage on passive (from conditions, observant feat, etc.)
    has_adv, has_dis = check_advantage_disadvantage(char_data, skill)
    
    passive = 10 + modifier
    
    if has_adv:
        passive += 5
    if has_dis:
        passive -= 5
    
    # Check for Observant feat (bonus to passive Perception and Investigation)
    features = char_data.get('features', [])
    if 'Observant' in features and skill in ['perception', 'investigation']:
        passive += 5
    
    return passive


def check_passive_perception(
    players: List[dict], 
    hidden_dc: int, 
    hidden_thing: str = "something hidden"
) -> List[Tuple[str, str, bool]]:
    """
    Check all players' passive Perception against a hidden DC.
    
    Args:
        players: List of player data dicts (must include 'id', 'name', and character data)
        hidden_dc: DC to notice the hidden thing
        hidden_thing: Description of what's hidden (for narration)
    
    Returns:
        List of (player_name, player_id, noticed) tuples for those who noticed
    """
    results = []
    
    for player in players:
        char_data = player.get('char_data', player)
        passive = calculate_passive_score(char_data, 'perception')
        
        if passive >= hidden_dc:
            results.append((
                player.get('name', 'Unknown'),
                player.get('id', ''),
                True
            ))
    
    return results


def check_passive_insight(
    players: List[dict],
    deception_total: int,
    deceiver: str = "the NPC"
) -> List[Tuple[str, str, bool]]:
    """
    Check all players' passive Insight against a deception.
    
    Args:
        players: List of player data dicts
        deception_total: The deceiver's Deception check total
        deceiver: Name of who's being deceptive
    
    Returns:
        List of (player_name, player_id, noticed) tuples for those who see through it
    """
    results = []
    
    for player in players:
        char_data = player.get('char_data', player)
        passive = calculate_passive_score(char_data, 'insight')
        
        if passive >= deception_total:
            results.append((
                player.get('name', 'Unknown'),
                player.get('id', ''),
                True
            ))
    
    return results


# =============================================================================
# PENDING CHECK MANAGEMENT
# =============================================================================

def create_pending_check(
    channel_id: str,
    request: SkillCheckRequest,
    player_ids: List[str],
    timeout: int = 60
) -> PendingCheck:
    """Create a pending check awaiting player rolls."""
    import time
    
    pending = PendingCheck(
        channel_id=channel_id,
        request=request,
        players_needed=list(player_ids),
        timeout_seconds=timeout,
        created_at=time.time()
    )
    
    _pending_checks[channel_id] = pending
    return pending


def get_pending_check(channel_id: str) -> Optional[PendingCheck]:
    """Get the pending check for a channel, if any."""
    return _pending_checks.get(channel_id)


def add_check_result(channel_id: str, player_id: str, result: SkillCheckResult) -> bool:
    """
    Add a player's roll result to the pending check.
    
    Returns:
        True if all players have rolled, False if still waiting
    """
    pending = _pending_checks.get(channel_id)
    if not pending:
        return False
    
    pending.results[player_id] = result
    
    # Check if all players have rolled
    return len(pending.results) >= len(pending.players_needed)


def complete_pending_check(channel_id: str) -> Optional[PendingCheck]:
    """
    Complete and remove the pending check for a channel.
    
    Returns:
        The completed PendingCheck, or None if not found
    """
    return _pending_checks.pop(channel_id, None)


def clear_pending_check(channel_id: str):
    """Clear any pending check for a channel."""
    _pending_checks.pop(channel_id, None)


def is_check_pending(channel_id: str) -> bool:
    """Check if there's a pending skill check for this channel."""
    return channel_id in _pending_checks


def get_missing_players(channel_id: str) -> List[str]:
    """Get list of player IDs who haven't rolled yet."""
    pending = _pending_checks.get(channel_id)
    if not pending:
        return []
    
    return [pid for pid in pending.players_needed if pid not in pending.results]


# =============================================================================
# RESULT FORMATTING
# =============================================================================

def format_check_result(result: SkillCheckResult) -> str:
    """Format a skill check result for Discord display."""
    skill_name = result.skill_or_ability.replace('_', ' ').title()
    
    # Roll info
    if result.advantage:
        roll_info = f"({result.rolls[0]}, {result.rolls[1]} → **{result.roll}**)"
        adv_text = " with advantage"
    elif result.disadvantage:
        roll_info = f"({result.rolls[0]}, {result.rolls[1]} → **{result.roll}**)"
        adv_text = " with disadvantage"
    else:
        roll_info = f"({result.roll})"
        adv_text = ""
    
    # Modifier
    mod_str = f"+{result.modifier}" if result.modifier >= 0 else str(result.modifier)
    
    # Critical
    if result.natural_20:
        crit = " 🌟 **Natural 20!**"
    elif result.natural_1:
        crit = " 💀 **Natural 1!**"
    else:
        crit = ""
    
    # Build message
    msg = f"🎲 **{result.player_name}** rolls {skill_name}{adv_text}: **{result.total}** {roll_info} {mod_str}{crit}"
    
    # Success/failure if DC known
    if result.dc is not None:
        if result.success:
            msg += f" ✅ **SUCCESS!** (DC {result.dc})"
        else:
            msg += f" ❌ **FAILURE!** (DC {result.dc})"
    
    return msg


def format_group_check_result(result: GroupCheckResult) -> str:
    """Format a group check result for Discord display."""
    skill_name = result.skill_or_ability.replace('_', ' ').title()
    
    lines = [f"📋 **Group {skill_name} Check** (DC {result.dc or '?'})"]
    lines.append("───────────────────────")
    
    for individual in result.individual_results:
        status = "✅" if individual.success else "❌"
        lines.append(f"{status} {individual.player_name}: **{individual.total}** ({individual.roll})")
    
    lines.append("───────────────────────")
    lines.append(f"**Result:** {result.successes} successes, {result.failures} failures")
    
    if result.group_success:
        lines.append("🎉 **The party succeeds!**")
    else:
        lines.append("💔 **The party fails!**")
    
    return "\n".join(lines)


def format_passive_notice(player_name: str, what_noticed: str) -> str:
    """Format a passive perception/insight notice."""
    return f"👁️ **{player_name}** notices {what_noticed}."


def build_roll_prompt(request: SkillCheckRequest, players: List[str]) -> str:
    """
    Build a prompt message asking players to roll.
    
    Args:
        request: The skill check request
        players: List of player mentions (e.g., ["<@123>", "<@456>"])
    
    Returns:
        Formatted prompt string
    """
    skill_name = request.skill_or_ability.replace('_', ' ').title()
    dc_text = f" (DC {request.dc})" if request.dc else ""
    
    if request.check_type == CheckType.SAVING_THROW:
        check_text = f"{skill_name} Saving Throw"
    elif request.check_type == CheckType.ABILITY:
        check_text = f"{skill_name} Check"
    else:
        check_text = skill_name
    
    if request.is_group_check:
        player_text = "Everyone"
    elif players:
        player_text = ", ".join(players)
    else:
        player_text = "Someone"
    
    return (
        f"🎲 **{player_text}, roll {check_text}{dc_text}!**\n"
        f"Use `/roll {request.skill_or_ability.lower()}` or click the button below."
    )


# =============================================================================
# AI RESULT INJECTION
# =============================================================================

def build_result_context(result: SkillCheckResult, original_action: str = "") -> str:
    """
    Build context string to inject back into AI for narration.
    
    Args:
        result: The skill check result
        original_action: What the player was trying to do
    
    Returns:
        Context string for AI prompt
    """
    skill_name = result.skill_or_ability.replace('_', ' ').title()
    
    # Build description of the roll
    if result.natural_20:
        roll_desc = f"rolled a natural 20 (total {result.total})"
    elif result.natural_1:
        roll_desc = f"rolled a natural 1 (total {result.total})"
    else:
        roll_desc = f"rolled {result.total}"
    
    # Success/failure
    if result.dc:
        if result.success:
            outcome = f"SUCCESS against DC {result.dc}"
        else:
            outcome = f"FAILURE against DC {result.dc}"
    else:
        outcome = "result pending"
    
    context = f"{result.player_name} {roll_desc} on a {skill_name} check. {outcome}"
    
    if original_action:
        context = f"Attempting to {original_action}: {context}"
    
    return context


def build_group_result_context(result: GroupCheckResult) -> str:
    """
    Build context string for group check results.
    
    Args:
        result: The group check result
    
    Returns:
        Context string for AI prompt
    """
    skill_name = result.skill_or_ability.replace('_', ' ').title()
    
    individual_results = []
    for r in result.individual_results:
        status = "succeeded" if r.success else "failed"
        individual_results.append(f"{r.player_name} {status} ({r.total})")
    
    outcome = "succeeded" if result.group_success else "failed"
    
    context = (
        f"Group {skill_name} check (DC {result.dc}): "
        f"{result.successes} successes, {result.failures} failures. "
        f"The party {outcome}. "
        f"Individual results: {'; '.join(individual_results)}"
    )
    
    return context


async def get_ai_outcome_narration(
    result: SkillCheckResult,
    original_action: str,
    state: dict
) -> str:
    """
    Get AI narration of the skill check outcome.
    
    Args:
        result: The skill check result
        original_action: What the player was attempting
        state: Campaign state for context
    
    Returns:
        AI-generated narration of the outcome
    """
    from services.openai_service import get_dm_response
    from utils.prompt_builder import build_system_prompt
    
    context = build_result_context(result, original_action)
    system_prompt = build_system_prompt(state)
    
    # Add instruction to narrate the outcome
    prompt = (
        f"{context}\n\n"
        f"Narrate the {'successful' if result.success else 'unsuccessful'} outcome of this action "
        f"in 2-3 dramatic sentences. Do not ask for any more rolls."
    )
    
    response, _ = get_dm_response(prompt, state, result.player_id, system_prompt=system_prompt)
    return response


async def get_group_ai_outcome_narration(
    result: GroupCheckResult,
    original_context: str,
    state: dict
) -> str:
    """
    Get AI narration of the group check outcome.
    
    Args:
        result: The group check result
        original_context: Context of what triggered the group check
        state: Campaign state
    
    Returns:
        AI-generated narration
    """
    from services.openai_service import get_dm_response
    from utils.prompt_builder import build_system_prompt
    
    context = build_group_result_context(result)
    system_prompt = build_system_prompt(state)
    
    prompt = (
        f"Context: {original_context}\n"
        f"{context}\n\n"
        f"Narrate the {'successful' if result.group_success else 'unsuccessful'} outcome "
        f"for the party in 2-3 dramatic sentences. Mention how individual performances contributed."
    )
    
    response, _ = get_dm_response(prompt, state, None, system_prompt=system_prompt)
    return response
