"""
Reaction System for D&D 5e Combat
Handles opportunity attacks, Shield, Counterspell, and other reaction mechanics.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum
from utils.combat_manager import load_combat, save_combat
from utils.dice_roller import roll_dice

# =============================================================================
# REACTION TYPES
# =============================================================================

class ReactionType(Enum):
    OPPORTUNITY_ATTACK = "opportunity_attack"
    SHIELD = "shield"
    COUNTERSPELL = "counterspell"
    ABSORB_ELEMENTS = "absorb_elements"
    HELLISH_REBUKE = "hellish_rebuke"
    CUTTING_WORDS = "cutting_words"
    UNCANNY_DODGE = "uncanny_dodge"
    DEFLECT_MISSILES = "deflect_missiles"
    PARRY = "parry"
    RIPOSTE = "riposte"
    PROTECTION = "protection"
    SENTINEL = "sentinel"
    MAGE_SLAYER = "mage_slayer"
    WAR_CASTER_OA = "war_caster_oa"

# =============================================================================
# REACTION TRIGGERS
# =============================================================================

REACTION_TRIGGERS = {
    ReactionType.OPPORTUNITY_ATTACK: {
        'trigger': 'enemy_leaves_reach',
        'description': 'When an enemy leaves your reach without Disengaging',
        'requires': ['melee_weapon'],
    },
    ReactionType.SHIELD: {
        'trigger': 'hit_by_attack',
        'description': 'When you are hit by an attack or targeted by Magic Missile',
        'requires': ['spell_known:Shield', 'spell_slot:1'],
        'effect': '+5 AC until start of next turn',
    },
    ReactionType.COUNTERSPELL: {
        'trigger': 'enemy_casts_spell',
        'description': 'When a creature within 60 feet casts a spell',
        'requires': ['spell_known:Counterspell', 'spell_slot:3'],
        'effect': 'Attempt to interrupt the spell',
    },
    ReactionType.ABSORB_ELEMENTS: {
        'trigger': 'take_elemental_damage',
        'description': 'When you take acid, cold, fire, lightning, or thunder damage',
        'requires': ['spell_known:Absorb Elements', 'spell_slot:1'],
        'effect': 'Resistance to damage, extra damage on next attack',
    },
    ReactionType.HELLISH_REBUKE: {
        'trigger': 'take_damage_from_creature',
        'description': 'When you take damage from a creature within 60 feet',
        'requires': ['spell_known:Hellish Rebuke', 'spell_slot:1'],
        'effect': 'Target takes 2d10 fire damage (DEX save for half)',
    },
    ReactionType.CUTTING_WORDS: {
        'trigger': 'enemy_makes_check',
        'description': 'When a creature you can see makes an attack, check, or damage roll',
        'requires': ['class:Bard', 'feature:Cutting Words'],
        'effect': 'Subtract Bardic Inspiration die from the roll',
    },
    ReactionType.UNCANNY_DODGE: {
        'trigger': 'hit_by_attack_you_can_see',
        'description': 'When an attacker you can see hits you with an attack',
        'requires': ['class:Rogue', 'level:5'],
        'effect': 'Halve the attack damage',
    },
    ReactionType.DEFLECT_MISSILES: {
        'trigger': 'hit_by_ranged_attack',
        'description': 'When you are hit by a ranged weapon attack',
        'requires': ['class:Monk', 'feature:Deflect Missiles'],
        'effect': 'Reduce damage by 1d10 + DEX + level',
    },
    ReactionType.PARRY: {
        'trigger': 'hit_by_melee_attack',
        'description': 'When a creature hits you with a melee attack',
        'requires': ['class:Fighter', 'subclass:Battle Master', 'superiority_die'],
        'effect': 'Add superiority die to AC against that attack',
    },
    ReactionType.RIPOSTE: {
        'trigger': 'enemy_misses_melee',
        'description': 'When a creature misses you with a melee attack',
        'requires': ['class:Fighter', 'subclass:Battle Master', 'superiority_die'],
        'effect': 'Make a melee attack, add superiority die to damage',
    },
    ReactionType.PROTECTION: {
        'trigger': 'ally_attacked',
        'description': 'When an ally within 5 feet is attacked',
        'requires': ['fighting_style:Protection', 'shield'],
        'effect': 'Impose disadvantage on the attack roll',
    },
    ReactionType.SENTINEL: {
        'trigger': 'enemy_attacks_ally',
        'description': 'When a creature within 5 feet attacks someone other than you',
        'requires': ['feat:Sentinel'],
        'effect': 'Make a melee weapon attack against that creature',
    },
    ReactionType.MAGE_SLAYER: {
        'trigger': 'adjacent_enemy_casts_spell',
        'description': 'When a creature within 5 feet casts a spell',
        'requires': ['feat:Mage Slayer'],
        'effect': 'Make a melee weapon attack against that creature',
    },
}


# =============================================================================
# REACTION TRACKING
# =============================================================================

def has_reaction_available(channel_id: str, combatant_name: str) -> bool:
    """Check if a combatant has their reaction available this round."""
    combat = load_combat(channel_id)
    if not combat:
        return False
    
    combatant = next((c for c in combat['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant:
        return False
    
    return not combatant.get('reaction_used', False)


def use_reaction(channel_id: str, combatant_name: str, reaction_type: ReactionType) -> Dict:
    """
    Use a combatant's reaction.
    
    Args:
        channel_id: The channel ID
        combatant_name: Name of the combatant using reaction
        reaction_type: Type of reaction being used
        
    Returns:
        Dict with reaction result
    """
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        return {'error': 'No active combat'}
    
    combatant = next((c for c in combat['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant:
        return {'error': f'{combatant_name} not found in combat'}
    
    if combatant.get('reaction_used'):
        return {'error': f'{combatant_name} has already used their reaction this round'}
    
    # Mark reaction as used
    combatant['reaction_used'] = True
    combatant.setdefault('reactions_taken', []).append({
        'type': reaction_type.value,
        'round': combat.get('round', 1),
    })
    
    save_combat(channel_id, combat)
    
    return {
        'success': True,
        'combatant': combatant_name,
        'reaction': reaction_type.value,
        'trigger_info': REACTION_TRIGGERS.get(reaction_type, {}),
    }


def reset_reactions(channel_id: str, combatant_name: str = None):
    """
    Reset reactions at the start of a combatant's turn.
    
    Args:
        channel_id: The channel ID
        combatant_name: Specific combatant or None for all
    """
    combat = load_combat(channel_id)
    if not combat:
        return
    
    for combatant in combat['combatants']:
        if combatant_name is None or combatant['name'].lower() == combatant_name.lower():
            combatant['reaction_used'] = False
    
    save_combat(channel_id, combat)


def reset_all_reactions_new_round(channel_id: str):
    """Reset all reactions at the start of a new round."""
    reset_reactions(channel_id, None)


# =============================================================================
# OPPORTUNITY ATTACK
# =============================================================================

def check_opportunity_attack(
    channel_id: str, 
    moving_combatant: str, 
    from_pos: Tuple[int, int], 
    to_pos: Tuple[int, int]
) -> List[Dict]:
    """
    Check if any combatants can make an opportunity attack.
    
    Args:
        channel_id: The channel ID
        moving_combatant: Name of the combatant moving
        from_pos: Starting position (x, y)
        to_pos: Ending position (x, y)
        
    Returns:
        List of combatants who can make opportunity attacks
    """
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        return []
    
    mover = next((c for c in combat['combatants'] if c['name'].lower() == moving_combatant.lower()), None)
    if not mover:
        return []
    
    # Get mover's team
    mover_type = mover.get('type', 'player')
    
    can_attack = []
    for combatant in combat['combatants']:
        # Skip self
        if combatant['name'].lower() == moving_combatant.lower():
            continue
        
        # Skip allies (same type)
        if combatant.get('type') == mover_type:
            continue
        
        # Skip if reaction already used
        if combatant.get('reaction_used'):
            continue
        
        # Skip if unconscious/dead
        if combatant.get('hp', 1) <= 0 or 'unconscious' in combatant.get('status', []):
            continue
        
        # Check if combatant was in melee range (5 feet) of starting position
        combatant_pos = combatant.get('position', (0, 0))
        distance_from_start = abs(combatant_pos[0] - from_pos[0]) + abs(combatant_pos[1] - from_pos[1])
        distance_from_end = abs(combatant_pos[0] - to_pos[0]) + abs(combatant_pos[1] - to_pos[1])
        
        # If was within 1 square (5 ft) and is now further away
        if distance_from_start <= 1 and distance_from_end > 1:
            can_attack.append({
                'combatant': combatant['name'],
                'reaction_type': ReactionType.OPPORTUNITY_ATTACK,
                'target': moving_combatant,
            })
    
    return can_attack


def resolve_opportunity_attack(
    channel_id: str,
    attacker_name: str,
    target_name: str,
    attack_bonus: int,
    damage_dice: str
) -> Dict:
    """
    Resolve an opportunity attack.
    
    Args:
        channel_id: The channel ID
        attacker_name: Name of the attacker
        target_name: Name of the target
        attack_bonus: Attack bonus modifier
        damage_dice: Damage dice string (e.g., "1d8+3")
        
    Returns:
        Dict with attack result
    """
    # Use reaction
    reaction_result = use_reaction(channel_id, attacker_name, ReactionType.OPPORTUNITY_ATTACK)
    if reaction_result.get('error'):
        return reaction_result
    
    combat = load_combat(channel_id)
    target = next((c for c in combat['combatants'] if c['name'].lower() == target_name.lower()), None)
    
    if not target:
        return {'error': f'{target_name} not found'}
    
    # Roll attack
    attack_roll = roll_dice('1d20')[0]
    is_crit = attack_roll == 20
    is_fumble = attack_roll == 1
    total_attack = attack_roll + attack_bonus
    hit = (total_attack >= target.get('ac', 10) or is_crit) and not is_fumble
    
    damage = 0
    if hit:
        damage = roll_dice(damage_dice)[0]
        if is_crit:
            damage *= 2
        target['hp'] = max(0, target.get('hp', 0) - damage)
        if target['hp'] == 0 and 'unconscious' not in target.get('status', []):
            target['status'].append('unconscious')
    
    save_combat(channel_id, combat)
    
    return {
        'type': 'opportunity_attack',
        'attacker': attacker_name,
        'target': target_name,
        'attack_roll': attack_roll,
        'total': total_attack,
        'hit': hit,
        'crit': is_crit,
        'fumble': is_fumble,
        'damage': damage if hit else 0,
        'target_hp': target['hp'],
        'target_ac': target.get('ac', 10),
    }


# =============================================================================
# SHIELD SPELL
# =============================================================================

def cast_shield(channel_id: str, caster_name: str) -> Dict:
    """
    Cast Shield as a reaction.
    
    Args:
        channel_id: The channel ID
        caster_name: Name of the caster
        
    Returns:
        Dict with result
    """
    reaction_result = use_reaction(channel_id, caster_name, ReactionType.SHIELD)
    if reaction_result.get('error'):
        return reaction_result
    
    combat = load_combat(channel_id)
    caster = next((c for c in combat['combatants'] if c['name'].lower() == caster_name.lower()), None)
    
    if not caster:
        return {'error': f'{caster_name} not found'}
    
    # Add Shield status effect
    caster.setdefault('temp_ac_bonus', 0)
    caster['temp_ac_bonus'] += 5
    caster.setdefault('status', []).append('shield_active')
    
    # Track when it expires (start of caster's next turn)
    caster['shield_expires_round'] = combat.get('round', 1) + 1
    
    save_combat(channel_id, combat)
    
    return {
        'type': 'shield',
        'caster': caster_name,
        'ac_bonus': 5,
        'new_ac': caster.get('ac', 10) + caster.get('temp_ac_bonus', 0),
        'expires': 'start of your next turn',
    }


# =============================================================================
# COUNTERSPELL
# =============================================================================

def cast_counterspell(
    channel_id: str, 
    caster_name: str, 
    target_spell_level: int,
    slot_level: int = 3
) -> Dict:
    """
    Cast Counterspell as a reaction.
    
    Args:
        channel_id: The channel ID
        caster_name: Name of the caster
        target_spell_level: Level of the spell being countered
        slot_level: Level of spell slot used (default 3)
        
    Returns:
        Dict with result
    """
    reaction_result = use_reaction(channel_id, caster_name, ReactionType.COUNTERSPELL)
    if reaction_result.get('error'):
        return reaction_result
    
    # Determine if counterspell succeeds
    if slot_level >= target_spell_level:
        # Automatic success
        success = True
        check_roll = None
    else:
        # Need to make ability check (DC = 10 + spell level)
        dc = 10 + target_spell_level
        check_roll = roll_dice('1d20')[0]
        # Assume +4 spellcasting modifier for simplicity
        total = check_roll + 4
        success = total >= dc
    
    return {
        'type': 'counterspell',
        'caster': caster_name,
        'slot_level': slot_level,
        'target_spell_level': target_spell_level,
        'success': success,
        'check_roll': check_roll,
        'message': f"The spell is countered!" if success else "The counterspell fails!",
    }


# =============================================================================
# UNCANNY DODGE
# =============================================================================

def use_uncanny_dodge(channel_id: str, user_name: str, damage: int) -> Dict:
    """
    Use Uncanny Dodge to halve attack damage.
    
    Args:
        channel_id: The channel ID
        user_name: Name of the Rogue using this ability
        damage: The damage being taken
        
    Returns:
        Dict with result
    """
    reaction_result = use_reaction(channel_id, user_name, ReactionType.UNCANNY_DODGE)
    if reaction_result.get('error'):
        return reaction_result
    
    reduced_damage = damage // 2
    
    return {
        'type': 'uncanny_dodge',
        'user': user_name,
        'original_damage': damage,
        'reduced_damage': reduced_damage,
        'damage_prevented': damage - reduced_damage,
    }


# =============================================================================
# SENTINEL FEAT
# =============================================================================

def check_sentinel_trigger(
    channel_id: str,
    attacker_name: str,
    target_name: str
) -> List[Dict]:
    """
    Check if any combatants with Sentinel can react.
    
    Args:
        channel_id: The channel ID
        attacker_name: Name of the attacker
        target_name: Name of the attack target
        
    Returns:
        List of combatants who can use Sentinel
    """
    combat = load_combat(channel_id)
    if not combat or not combat.get('active'):
        return []
    
    attacker = next((c for c in combat['combatants'] if c['name'].lower() == attacker_name.lower()), None)
    target = next((c for c in combat['combatants'] if c['name'].lower() == target_name.lower()), None)
    
    if not attacker or not target:
        return []
    
    attacker_pos = attacker.get('position', (0, 0))
    
    can_react = []
    for combatant in combat['combatants']:
        # Skip attacker and target
        if combatant['name'].lower() in [attacker_name.lower(), target_name.lower()]:
            continue
        
        # Must have Sentinel feat
        if 'Sentinel' not in combatant.get('feats', []):
            continue
        
        # Must have reaction available
        if combatant.get('reaction_used'):
            continue
        
        # Must be adjacent to attacker (within 5 ft)
        combatant_pos = combatant.get('position', (0, 0))
        distance = abs(combatant_pos[0] - attacker_pos[0]) + abs(combatant_pos[1] - attacker_pos[1])
        
        if distance <= 1:
            can_react.append({
                'combatant': combatant['name'],
                'reaction_type': ReactionType.SENTINEL,
                'trigger': f"{attacker_name} attacked {target_name}",
            })
    
    return can_react


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_available_reactions(channel_id: str, combatant_name: str) -> List[ReactionType]:
    """
    Get list of reactions available to a combatant based on their abilities.
    
    Args:
        channel_id: The channel ID
        combatant_name: Name of the combatant
        
    Returns:
        List of available reaction types
    """
    combat = load_combat(channel_id)
    if not combat:
        return []
    
    combatant = next((c for c in combat['combatants'] if c['name'].lower() == combatant_name.lower()), None)
    if not combatant:
        return []
    
    # Everyone can make opportunity attacks (if they have a melee weapon)
    available = [ReactionType.OPPORTUNITY_ATTACK]
    
    # Check for spell reactions
    spells_known = combatant.get('spells_known', [])
    if 'Shield' in spells_known:
        available.append(ReactionType.SHIELD)
    if 'Counterspell' in spells_known:
        available.append(ReactionType.COUNTERSPELL)
    if 'Absorb Elements' in spells_known:
        available.append(ReactionType.ABSORB_ELEMENTS)
    if 'Hellish Rebuke' in spells_known:
        available.append(ReactionType.HELLISH_REBUKE)
    
    # Check for class features
    char_class = combatant.get('class', '').lower()
    level = combatant.get('level', 1)
    
    if char_class == 'rogue' and level >= 5:
        available.append(ReactionType.UNCANNY_DODGE)
    if char_class == 'monk':
        available.append(ReactionType.DEFLECT_MISSILES)
    if char_class == 'bard':
        available.append(ReactionType.CUTTING_WORDS)
    
    # Check for feats
    feats = combatant.get('feats', [])
    if 'Sentinel' in feats:
        available.append(ReactionType.SENTINEL)
    if 'Mage Slayer' in feats:
        available.append(ReactionType.MAGE_SLAYER)
    
    return available


def format_reaction_prompt(reactions: List[Dict]) -> str:
    """Format reaction opportunities for Discord display."""
    if not reactions:
        return ""
    
    lines = ["⚡ **Reaction Opportunity!**"]
    for r in reactions:
        combatant = r['combatant']
        reaction_type = r['reaction_type']
        trigger_info = REACTION_TRIGGERS.get(reaction_type, {})
        
        lines.append(f"  • **{combatant}** can use **{reaction_type.value.replace('_', ' ').title()}**")
        if trigger_info.get('effect'):
            lines.append(f"    → {trigger_info['effect']}")
    
    lines.append("Use `/reaction` to respond!")
    return "\n".join(lines)
