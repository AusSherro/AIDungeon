import re
import random

def parse_dice(dice_str):
    """
    Parses dice notation like '2d6+1' and returns (num, sides, modifier).
    Supports: NdM+K, NdM-K, dM, M, etc.
    """
    dice_str = dice_str.replace(' ', '')
    match = re.fullmatch(r'(\d*)d(\d+)([+-]\d+)?', dice_str, re.IGNORECASE)
    if match:
        num = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        return num, sides, modifier
    # Try just a number (e.g. '6')
    if dice_str.isdigit():
        return 1, int(dice_str), 0
    raise ValueError(f"Invalid dice format: {dice_str}")

def roll_dice(dice_str):
    num, sides, modifier = parse_dice(dice_str)
    rolls = [random.randint(1, sides) for _ in range(num)]
    total = sum(rolls) + modifier
    return total, rolls, modifier

def roll_check(dice_str, user_id=None, stat=None, advantage=False, disadvantage=False, proficiency=False):
    from utils.character_manager import load_character
    num, sides, modifier = parse_dice(dice_str)
    rolls = []
    if advantage or disadvantage:
        roll1 = [random.randint(1, sides) for _ in range(num)]
        roll2 = [random.randint(1, sides) for _ in range(num)]
        if advantage:
            rolls = [max(a, b) for a, b in zip(roll1, roll2)]
        else:
            rolls = [min(a, b) for a, b in zip(roll1, roll2)]
    else:
        rolls = [random.randint(1, sides) for _ in range(num)]
    total = sum(rolls) + modifier
    if user_id and stat:
        char = load_character(user_id)
        if char and stat.upper() in char:
            stat_mod = (char[stat.upper()] - 10) // 2
            total += stat_mod
            modifier += stat_mod
        if proficiency and char and 'proficiency' in char:
            total += char['proficiency']
            modifier += char['proficiency']
    return total, rolls, modifier

def get_modifier_string(stat_value):
    mod = (stat_value - 10) // 2
    return f"+{mod}" if mod >= 0 else str(mod)


INLINE_ROLL_RE = re.compile(r'\[(\d*d\d+(?:[+-]\d+)?)\]')


def extract_inline_rolls(text: str):
    """Return a dict of inline dice notation to results."""
    rolls = {}
    for notation in INLINE_ROLL_RE.findall(text):
        try:
            total, _rolls, _ = roll_dice(notation)
            rolls[notation] = total
        except Exception:
            continue
    return rolls
