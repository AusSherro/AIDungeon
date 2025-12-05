"""
Experience Points & Auto-Leveling System
Handles XP awards, level-up detection, and progression tracking.
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from utils.character_manager import load_character, save_character, level_up as do_level_up

# Import XP thresholds from D&D data
try:
    from utils.dnd5e_data import XP_THRESHOLDS, get_level_for_xp
except ImportError:
    # Fallback XP thresholds
    XP_THRESHOLDS = {
        1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
        6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
        11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
        16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
    }
    
    def get_level_for_xp(xp: int) -> int:
        for level in range(20, 0, -1):
            if xp >= XP_THRESHOLDS[level]:
                return level
        return 1

# =============================================================================
# MONSTER XP VALUES BY CR
# =============================================================================

CR_XP_VALUES = {
    '0': 10,
    '1/8': 25,
    '1/4': 50,
    '1/2': 100,
    '1': 200,
    '2': 450,
    '3': 700,
    '4': 1100,
    '5': 1800,
    '6': 2300,
    '7': 2900,
    '8': 3900,
    '9': 5000,
    '10': 5900,
    '11': 7200,
    '12': 8400,
    '13': 10000,
    '14': 11500,
    '15': 13000,
    '16': 15000,
    '17': 18000,
    '18': 20000,
    '19': 22000,
    '20': 25000,
    '21': 33000,
    '22': 41000,
    '23': 50000,
    '24': 62000,
    '25': 75000,
    '26': 90000,
    '27': 105000,
    '28': 120000,
    '29': 135000,
    '30': 155000,
}

# =============================================================================
# XP FUNCTIONS
# =============================================================================

def get_xp_for_cr(cr: str) -> int:
    """Get XP value for a given Challenge Rating."""
    return CR_XP_VALUES.get(str(cr), 0)


def get_xp_to_next_level(current_xp: int, current_level: int) -> int:
    """Calculate XP needed to reach next level."""
    if current_level >= 20:
        return 0
    next_level = current_level + 1
    return max(0, XP_THRESHOLDS[next_level] - current_xp)


def get_level_progress(xp: int, level: int) -> Tuple[int, int, float]:
    """
    Get level progress information.
    
    Returns:
        Tuple of (xp_in_current_level, xp_needed_for_level, percentage)
    """
    if level >= 20:
        return (xp, XP_THRESHOLDS[20], 1.0)
    
    current_threshold = XP_THRESHOLDS[level]
    next_threshold = XP_THRESHOLDS[level + 1]
    
    xp_in_level = xp - current_threshold
    xp_for_level = next_threshold - current_threshold
    
    percentage = min(1.0, xp_in_level / xp_for_level) if xp_for_level > 0 else 1.0
    
    return (xp_in_level, xp_for_level, percentage)


def award_xp(user_id: str, xp_amount: int) -> Dict:
    """
    Award XP to a character and check for level up.
    
    Args:
        user_id: The player's user ID
        xp_amount: Amount of XP to award
        
    Returns:
        Dict with award details and level up info
    """
    char = load_character(user_id)
    if not char:
        return {'error': 'No character found'}
    
    old_xp = char.get('xp', 0)
    old_level = char.get('level', 1)
    
    new_xp = old_xp + xp_amount
    char['xp'] = new_xp
    
    # Check for level up
    new_level = get_level_for_xp(new_xp)
    levels_gained = new_level - old_level
    
    result = {
        'character': char.get('name', 'Character'),
        'xp_gained': xp_amount,
        'old_xp': old_xp,
        'new_xp': new_xp,
        'old_level': old_level,
        'new_level': new_level,
        'levels_gained': levels_gained,
        'level_up': levels_gained > 0,
        'xp_to_next': get_xp_to_next_level(new_xp, new_level),
    }
    
    # Update level if changed (but don't auto-apply features - use /levelup for that)
    if levels_gained > 0:
        char['level'] = new_level
        # Update proficiency bonus
        char['proficiency'] = 2 + (new_level - 1) // 4
        result['ready_for_levelup'] = True
    
    save_character(user_id, char)
    
    return result


def award_party_xp(player_ids: List[str], total_xp: int, equal_split: bool = True) -> List[Dict]:
    """
    Award XP to multiple players (typically after combat).
    
    Args:
        player_ids: List of player user IDs
        total_xp: Total XP to distribute
        equal_split: If True, divide evenly; if False, each player gets full amount
        
    Returns:
        List of award results for each player
    """
    if not player_ids:
        return []
    
    xp_per_player = total_xp // len(player_ids) if equal_split else total_xp
    
    results = []
    for pid in player_ids:
        result = award_xp(pid, xp_per_player)
        results.append(result)
    
    return results


def calculate_combat_xp(enemies: List[Dict]) -> int:
    """
    Calculate total XP from defeated enemies.
    
    Args:
        enemies: List of enemy dicts with 'xp' or 'cr' fields
        
    Returns:
        Total XP value
    """
    total = 0
    for enemy in enemies:
        if 'xp' in enemy:
            total += enemy['xp']
        elif 'cr' in enemy:
            total += get_xp_for_cr(enemy['cr'])
        else:
            # Default XP for unknown enemies
            total += 50
    return total


def format_xp_bar(xp: int, level: int, width: int = 20) -> str:
    """
    Create an ASCII progress bar for XP.
    
    Args:
        xp: Current XP
        level: Current level
        width: Width of the bar in characters
        
    Returns:
        Formatted progress bar string
    """
    if level >= 20:
        return f"[{'█' * width}] MAX LEVEL"
    
    _, xp_for_level, percentage = get_level_progress(xp, level)
    
    filled = int(width * percentage)
    empty = width - filled
    
    bar = '█' * filled + '░' * empty
    return f"[{bar}] {int(percentage * 100)}%"


def get_xp_summary(user_id: str) -> Dict:
    """
    Get a complete XP summary for a character.
    
    Returns:
        Dict with all XP-related information
    """
    char = load_character(user_id)
    if not char:
        return {'error': 'No character found'}
    
    xp = char.get('xp', 0)
    level = char.get('level', 1)
    
    xp_in_level, xp_for_level, percentage = get_level_progress(xp, level)
    
    return {
        'name': char.get('name', 'Character'),
        'level': level,
        'xp': xp,
        'xp_in_level': xp_in_level,
        'xp_for_level': xp_for_level,
        'xp_to_next': get_xp_to_next_level(xp, level),
        'progress_percentage': percentage,
        'progress_bar': format_xp_bar(xp, level),
        'at_max_level': level >= 20,
    }


# =============================================================================
# MILESTONE LEVELING (Alternative to XP)
# =============================================================================

def milestone_level_up(user_id: str, target_level: int = None) -> Dict:
    """
    Level up a character using milestone leveling.
    
    Args:
        user_id: The player's user ID
        target_level: Target level (default: current + 1)
        
    Returns:
        Dict with level up details
    """
    char = load_character(user_id)
    if not char:
        return {'error': 'No character found'}
    
    current_level = char.get('level', 1)
    
    if target_level is None:
        target_level = current_level + 1
    
    if target_level > 20:
        return {'error': 'Maximum level is 20'}
    
    if target_level <= current_level:
        return {'error': f'Target level must be higher than current level ({current_level})'}
    
    # Set XP to match target level
    char['xp'] = XP_THRESHOLDS[target_level]
    char['level'] = target_level
    char['proficiency'] = 2 + (target_level - 1) // 4
    
    save_character(user_id, char)
    
    return {
        'character': char.get('name', 'Character'),
        'old_level': current_level,
        'new_level': target_level,
        'levels_gained': target_level - current_level,
        'new_xp': char['xp'],
        'milestone': True,
    }
