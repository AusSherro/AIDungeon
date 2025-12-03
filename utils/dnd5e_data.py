"""
D&D 5e SRD Data
Comprehensive class features, spells, and racial traits for the AI Dungeon Master.
Based on the 5e SRD (Systems Reference Document).
"""

# =============================================================================
# XP THRESHOLDS FOR LEVELING
# =============================================================================
XP_THRESHOLDS = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
}

def get_level_for_xp(xp: int) -> int:
    """Return the level a character should be at given their XP."""
    for level in range(20, 0, -1):
        if xp >= XP_THRESHOLDS[level]:
            return level
    return 1

def get_proficiency_bonus(level: int) -> int:
    """Return proficiency bonus for a given level."""
    return 2 + (level - 1) // 4

# =============================================================================
# CLASS DATA
# =============================================================================
CLASSES = {
    "Barbarian": {
        "hit_die": 12,
        "primary_ability": "STR",
        "saving_throws": ["STR", "CON"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
        "num_skills": 2,
        "spellcasting": None,
        "features": {
            1: ["Rage (2/day)", "Unarmored Defense (10 + DEX + CON)"],
            2: ["Reckless Attack", "Danger Sense"],
            3: ["Primal Path"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack", "Fast Movement (+10 ft)"],
            6: ["Path Feature"],
            7: ["Feral Instinct"],
            8: ["Ability Score Improvement"],
            9: ["Brutal Critical (1 die)"],
            10: ["Path Feature"],
            11: ["Relentless Rage"],
            12: ["Ability Score Improvement"],
            13: ["Brutal Critical (2 dice)"],
            14: ["Path Feature"],
            15: ["Persistent Rage"],
            16: ["Ability Score Improvement"],
            17: ["Brutal Critical (3 dice)"],
            18: ["Indomitable Might"],
            19: ["Ability Score Improvement"],
            20: ["Primal Champion (+4 STR, +4 CON)"],
        },
        "rage_damage": {1: 2, 9: 3, 16: 4},
        "rages_per_day": {1: 2, 3: 3, 6: 4, 12: 5, 17: 6, 20: "unlimited"},
    },
    
    "Bard": {
        "hit_die": 8,
        "primary_ability": "CHA",
        "saving_throws": ["DEX", "CHA"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple", "hand crossbows", "longswords", "rapiers", "shortswords"],
        "skill_choices": "any",
        "num_skills": 3,
        "spellcasting": {
            "ability": "CHA",
            "type": "known",
            "cantrips": {1: 2, 4: 3, 10: 4},
            "spells_known": {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12, 10: 14, 11: 15, 13: 16, 14: 18, 15: 19, 17: 20, 18: 22},
            "slots": {
                1: {1: 2},
                2: {1: 3},
                3: {1: 4, 2: 2},
                4: {1: 4, 2: 3},
                5: {1: 4, 2: 3, 3: 2},
                6: {1: 4, 2: 3, 3: 3},
                7: {1: 4, 2: 3, 3: 3, 4: 1},
                8: {1: 4, 2: 3, 3: 3, 4: 2},
                9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
                10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
                11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
                13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
                15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
                18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
                19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
                20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
            }
        },
        "features": {
            1: ["Spellcasting", "Bardic Inspiration (d6)"],
            2: ["Jack of All Trades", "Song of Rest (d6)"],
            3: ["Bard College", "Expertise (2 skills)"],
            4: ["Ability Score Improvement"],
            5: ["Bardic Inspiration (d8)", "Font of Inspiration"],
            6: ["Countercharm", "College Feature"],
            8: ["Ability Score Improvement"],
            9: ["Song of Rest (d8)"],
            10: ["Bardic Inspiration (d10)", "Expertise (2 more)", "Magical Secrets"],
            12: ["Ability Score Improvement"],
            13: ["Song of Rest (d10)"],
            14: ["Magical Secrets", "College Feature"],
            15: ["Bardic Inspiration (d12)"],
            16: ["Ability Score Improvement"],
            17: ["Song of Rest (d12)"],
            18: ["Magical Secrets"],
            19: ["Ability Score Improvement"],
            20: ["Superior Inspiration"],
        },
    },
    
    "Cleric": {
        "hit_die": 8,
        "primary_ability": "WIS",
        "saving_throws": ["WIS", "CHA"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple"],
        "skill_choices": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "WIS",
            "type": "prepared",
            "cantrips": {1: 3, 4: 4, 10: 5},
            "prepare_formula": "WIS + level",
            "slots": {
                1: {1: 2},
                2: {1: 3},
                3: {1: 4, 2: 2},
                4: {1: 4, 2: 3},
                5: {1: 4, 2: 3, 3: 2},
                6: {1: 4, 2: 3, 3: 3},
                7: {1: 4, 2: 3, 3: 3, 4: 1},
                8: {1: 4, 2: 3, 3: 3, 4: 2},
                9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
                10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
                11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
                13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
                15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
                18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
                19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
                20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
            }
        },
        "features": {
            1: ["Spellcasting", "Divine Domain"],
            2: ["Channel Divinity (1/rest)", "Domain Feature"],
            4: ["Ability Score Improvement"],
            5: ["Destroy Undead (CR 1/2)"],
            6: ["Channel Divinity (2/rest)", "Domain Feature"],
            8: ["Ability Score Improvement", "Destroy Undead (CR 1)", "Domain Feature"],
            10: ["Divine Intervention"],
            11: ["Destroy Undead (CR 2)"],
            12: ["Ability Score Improvement"],
            14: ["Destroy Undead (CR 3)"],
            16: ["Ability Score Improvement"],
            17: ["Destroy Undead (CR 4)", "Domain Feature"],
            18: ["Channel Divinity (3/rest)"],
            19: ["Ability Score Improvement"],
            20: ["Divine Intervention Improvement"],
        },
    },
    
    "Druid": {
        "hit_die": 8,
        "primary_ability": "WIS",
        "saving_throws": ["INT", "WIS"],
        "armor_proficiencies": ["light", "medium", "shields (non-metal)"],
        "weapon_proficiencies": ["clubs", "daggers", "darts", "javelins", "maces", "quarterstaffs", "scimitars", "sickles", "slings", "spears"],
        "skill_choices": ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "WIS",
            "type": "prepared",
            "cantrips": {1: 2, 4: 3, 10: 4},
            "prepare_formula": "WIS + level",
            "slots": {
                1: {1: 2}, 2: {1: 3}, 3: {1: 4, 2: 2}, 4: {1: 4, 2: 3},
                5: {1: 4, 2: 3, 3: 2}, 6: {1: 4, 2: 3, 3: 3},
                7: {1: 4, 2: 3, 3: 3, 4: 1}, 8: {1: 4, 2: 3, 3: 3, 4: 2},
                9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}, 10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
                11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
                13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
                15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
                20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
            }
        },
        "features": {
            1: ["Druidic", "Spellcasting"],
            2: ["Wild Shape (2/rest)", "Druid Circle"],
            4: ["Wild Shape Improvement", "Ability Score Improvement"],
            6: ["Circle Feature"],
            8: ["Ability Score Improvement"],
            10: ["Circle Feature"],
            12: ["Ability Score Improvement"],
            14: ["Circle Feature"],
            16: ["Ability Score Improvement"],
            18: ["Timeless Body", "Beast Spells"],
            19: ["Ability Score Improvement"],
            20: ["Archdruid"],
        },
        "wild_shape": {
            2: {"max_cr": 0.25, "limitations": "No flying/swimming"},
            4: {"max_cr": 0.5, "limitations": "No flying"},
            8: {"max_cr": 1, "limitations": "None"},
        },
    },
    
    "Fighter": {
        "hit_die": 10,
        "primary_ability": "STR or DEX",
        "saving_throws": ["STR", "CON"],
        "armor_proficiencies": ["light", "medium", "heavy", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
        "num_skills": 2,
        "spellcasting": None,  # Eldritch Knight gets spells at level 3
        "features": {
            1: ["Fighting Style", "Second Wind (1d10 + level)"],
            2: ["Action Surge (1 use)"],
            3: ["Martial Archetype"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack (2 attacks)"],
            6: ["Ability Score Improvement"],
            7: ["Archetype Feature"],
            8: ["Ability Score Improvement"],
            9: ["Indomitable (1 use)"],
            10: ["Archetype Feature"],
            11: ["Extra Attack (3 attacks)"],
            12: ["Ability Score Improvement"],
            13: ["Indomitable (2 uses)"],
            14: ["Ability Score Improvement"],
            15: ["Archetype Feature"],
            16: ["Ability Score Improvement"],
            17: ["Action Surge (2 uses)", "Indomitable (3 uses)"],
            18: ["Archetype Feature"],
            19: ["Ability Score Improvement"],
            20: ["Extra Attack (4 attacks)"],
        },
    },
    
    "Monk": {
        "hit_die": 8,
        "primary_ability": "DEX & WIS",
        "saving_throws": ["STR", "DEX"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["simple", "shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
        "num_skills": 2,
        "spellcasting": None,
        "features": {
            1: ["Unarmored Defense (10 + DEX + WIS)", "Martial Arts (1d4)"],
            2: ["Ki", "Unarmored Movement (+10 ft)"],
            3: ["Monastic Tradition", "Deflect Missiles"],
            4: ["Ability Score Improvement", "Slow Fall"],
            5: ["Extra Attack", "Stunning Strike", "Martial Arts (1d6)"],
            6: ["Ki-Empowered Strikes", "Tradition Feature", "Unarmored Movement (+15 ft)"],
            7: ["Evasion", "Stillness of Mind"],
            8: ["Ability Score Improvement"],
            9: ["Unarmored Movement Improvement"],
            10: ["Purity of Body", "Unarmored Movement (+20 ft)"],
            11: ["Tradition Feature", "Martial Arts (1d8)"],
            12: ["Ability Score Improvement"],
            13: ["Tongue of the Sun and Moon"],
            14: ["Diamond Soul", "Unarmored Movement (+25 ft)"],
            15: ["Timeless Body"],
            16: ["Ability Score Improvement"],
            17: ["Tradition Feature", "Martial Arts (1d10)"],
            18: ["Empty Body", "Unarmored Movement (+30 ft)"],
            19: ["Ability Score Improvement"],
            20: ["Perfect Self"],
        },
        "ki_points": lambda level: level if level >= 2 else 0,
        "martial_arts_die": {1: "1d4", 5: "1d6", 11: "1d8", 17: "1d10"},
        "unarmored_movement": {2: 10, 6: 15, 10: 20, 14: 25, 18: 30},
    },
    
    "Paladin": {
        "hit_die": 10,
        "primary_ability": "STR & CHA",
        "saving_throws": ["WIS", "CHA"],
        "armor_proficiencies": ["light", "medium", "heavy", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "CHA",
            "type": "prepared",
            "prepare_formula": "CHA + level/2",
            "slots": {
                2: {1: 2}, 3: {1: 3}, 5: {1: 4, 2: 2}, 7: {1: 4, 2: 3},
                9: {1: 4, 2: 3, 3: 2}, 11: {1: 4, 2: 3, 3: 3},
                13: {1: 4, 2: 3, 3: 3, 4: 1}, 15: {1: 4, 2: 3, 3: 3, 4: 2},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}, 19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
            }
        },
        "features": {
            1: ["Divine Sense", "Lay on Hands (5 × level HP)"],
            2: ["Fighting Style", "Spellcasting", "Divine Smite"],
            3: ["Divine Health", "Sacred Oath"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack"],
            6: ["Aura of Protection (+CHA to saves, 10 ft)"],
            7: ["Oath Feature"],
            8: ["Ability Score Improvement"],
            9: ["--"],
            10: ["Aura of Courage"],
            11: ["Improved Divine Smite (+1d8 radiant)"],
            12: ["Ability Score Improvement"],
            14: ["Cleansing Touch"],
            15: ["Oath Feature"],
            16: ["Ability Score Improvement"],
            18: ["Aura Improvements (30 ft)"],
            19: ["Ability Score Improvement"],
            20: ["Oath Feature"],
        },
    },
    
    "Ranger": {
        "hit_die": 10,
        "primary_ability": "DEX & WIS",
        "saving_throws": ["STR", "DEX"],
        "armor_proficiencies": ["light", "medium", "shields"],
        "weapon_proficiencies": ["simple", "martial"],
        "skill_choices": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
        "num_skills": 3,
        "spellcasting": {
            "ability": "WIS",
            "type": "known",
            "spells_known": {2: 2, 3: 3, 5: 4, 7: 5, 9: 6, 11: 7, 13: 8, 15: 9, 17: 10, 19: 11},
            "slots": {
                2: {1: 2}, 3: {1: 3}, 5: {1: 4, 2: 2}, 7: {1: 4, 2: 3},
                9: {1: 4, 2: 3, 3: 2}, 11: {1: 4, 2: 3, 3: 3},
                13: {1: 4, 2: 3, 3: 3, 4: 1}, 15: {1: 4, 2: 3, 3: 3, 4: 2},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}, 19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
            }
        },
        "features": {
            1: ["Favored Enemy", "Natural Explorer"],
            2: ["Fighting Style", "Spellcasting"],
            3: ["Ranger Archetype", "Primeval Awareness"],
            4: ["Ability Score Improvement"],
            5: ["Extra Attack"],
            6: ["Favored Enemy Improvement", "Natural Explorer Improvement"],
            7: ["Archetype Feature"],
            8: ["Ability Score Improvement", "Land's Stride"],
            10: ["Natural Explorer Improvement", "Hide in Plain Sight"],
            11: ["Archetype Feature"],
            12: ["Ability Score Improvement"],
            14: ["Favored Enemy Improvement", "Vanish"],
            15: ["Archetype Feature"],
            16: ["Ability Score Improvement"],
            18: ["Feral Senses"],
            19: ["Ability Score Improvement"],
            20: ["Foe Slayer"],
        },
    },
    
    "Rogue": {
        "hit_die": 8,
        "primary_ability": "DEX",
        "saving_throws": ["DEX", "INT"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple", "hand crossbows", "longswords", "rapiers", "shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
        "num_skills": 4,
        "spellcasting": None,  # Arcane Trickster gets spells at level 3
        "features": {
            1: ["Expertise (2 skills)", "Sneak Attack (1d6)", "Thieves' Cant"],
            2: ["Cunning Action"],
            3: ["Roguish Archetype", "Sneak Attack (2d6)"],
            4: ["Ability Score Improvement"],
            5: ["Uncanny Dodge", "Sneak Attack (3d6)"],
            6: ["Expertise (2 more)"],
            7: ["Evasion", "Sneak Attack (4d6)"],
            8: ["Ability Score Improvement"],
            9: ["Archetype Feature", "Sneak Attack (5d6)"],
            10: ["Ability Score Improvement"],
            11: ["Reliable Talent", "Sneak Attack (6d6)"],
            12: ["Ability Score Improvement"],
            13: ["Archetype Feature", "Sneak Attack (7d6)"],
            14: ["Blindsense"],
            15: ["Slippery Mind", "Sneak Attack (8d6)"],
            16: ["Ability Score Improvement"],
            17: ["Archetype Feature", "Sneak Attack (9d6)"],
            18: ["Elusive"],
            19: ["Ability Score Improvement", "Sneak Attack (10d6)"],
            20: ["Stroke of Luck"],
        },
        "sneak_attack": lambda level: f"{(level + 1) // 2}d6",
    },
    
    "Sorcerer": {
        "hit_die": 6,
        "primary_ability": "CHA",
        "saving_throws": ["CON", "CHA"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["daggers", "darts", "slings", "quarterstaffs", "light crossbows"],
        "skill_choices": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "CHA",
            "type": "known",
            "cantrips": {1: 4, 4: 5, 10: 6},
            "spells_known": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 10: 11, 11: 12, 13: 13, 15: 14, 17: 15},
            "slots": {
                1: {1: 2}, 2: {1: 3}, 3: {1: 4, 2: 2}, 4: {1: 4, 2: 3},
                5: {1: 4, 2: 3, 3: 2}, 6: {1: 4, 2: 3, 3: 3},
                7: {1: 4, 2: 3, 3: 3, 4: 1}, 8: {1: 4, 2: 3, 3: 3, 4: 2},
                9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}, 10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
                11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
                13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
                15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
                20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
            }
        },
        "features": {
            1: ["Spellcasting", "Sorcerous Origin"],
            2: ["Font of Magic (Sorcery Points = level)"],
            3: ["Metamagic (2 options)"],
            4: ["Ability Score Improvement"],
            6: ["Origin Feature"],
            8: ["Ability Score Improvement"],
            10: ["Metamagic (1 more)"],
            12: ["Ability Score Improvement"],
            14: ["Origin Feature"],
            16: ["Ability Score Improvement"],
            17: ["Metamagic (1 more)"],
            18: ["Origin Feature"],
            19: ["Ability Score Improvement"],
            20: ["Sorcerous Restoration"],
        },
        "sorcery_points": lambda level: level if level >= 2 else 0,
    },
    
    "Warlock": {
        "hit_die": 8,
        "primary_ability": "CHA",
        "saving_throws": ["WIS", "CHA"],
        "armor_proficiencies": ["light"],
        "weapon_proficiencies": ["simple"],
        "skill_choices": ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "CHA",
            "type": "known",
            "cantrips": {1: 2, 4: 3, 10: 4},
            "spells_known": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 11: 11, 13: 12, 15: 13, 17: 14, 19: 15},
            "pact_magic": True,
            "slot_level": {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 5, 10: 5, 11: 5, 12: 5, 13: 5, 14: 5, 15: 5, 16: 5, 17: 5, 18: 5, 19: 5, 20: 5},
            "num_slots": {1: 1, 2: 2, 11: 3, 17: 4},
        },
        "features": {
            1: ["Otherworldly Patron", "Pact Magic"],
            2: ["Eldritch Invocations (2)"],
            3: ["Pact Boon"],
            4: ["Ability Score Improvement"],
            5: ["Invocations (3)"],
            6: ["Patron Feature"],
            7: ["Invocations (4)"],
            8: ["Ability Score Improvement"],
            9: ["Invocations (5)"],
            10: ["Patron Feature"],
            11: ["Mystic Arcanum (6th level)"],
            12: ["Ability Score Improvement", "Invocations (6)"],
            13: ["Mystic Arcanum (7th level)"],
            14: ["Patron Feature"],
            15: ["Mystic Arcanum (8th level)", "Invocations (7)"],
            16: ["Ability Score Improvement"],
            17: ["Mystic Arcanum (9th level)"],
            18: ["Invocations (8)"],
            19: ["Ability Score Improvement"],
            20: ["Eldritch Master"],
        },
    },
    
    "Wizard": {
        "hit_die": 6,
        "primary_ability": "INT",
        "saving_throws": ["INT", "WIS"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["daggers", "darts", "slings", "quarterstaffs", "light crossbows"],
        "skill_choices": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
        "num_skills": 2,
        "spellcasting": {
            "ability": "INT",
            "type": "prepared",
            "cantrips": {1: 3, 4: 4, 10: 5},
            "prepare_formula": "INT + level",
            "spellbook": True,
            "spellbook_start": 6,  # Start with 6 1st level spells
            "spellbook_gain": 2,   # Gain 2 spells per level
            "slots": {
                1: {1: 2}, 2: {1: 3}, 3: {1: 4, 2: 2}, 4: {1: 4, 2: 3},
                5: {1: 4, 2: 3, 3: 2}, 6: {1: 4, 2: 3, 3: 3},
                7: {1: 4, 2: 3, 3: 3, 4: 1}, 8: {1: 4, 2: 3, 3: 3, 4: 2},
                9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1}, 10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
                11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
                13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
                15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
                17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
                20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
            }
        },
        "features": {
            1: ["Spellcasting", "Arcane Recovery"],
            2: ["Arcane Tradition"],
            4: ["Ability Score Improvement"],
            6: ["Tradition Feature"],
            8: ["Ability Score Improvement"],
            10: ["Tradition Feature"],
            12: ["Ability Score Improvement"],
            14: ["Tradition Feature"],
            16: ["Ability Score Improvement"],
            18: ["Spell Mastery"],
            19: ["Ability Score Improvement"],
            20: ["Signature Spells"],
        },
    },
}


def get_class_data(class_name: str) -> dict:
    """Get class data for a given class name."""
    return CLASSES.get(class_name, CLASSES.get("Fighter"))


def get_spell_slots(class_name: str, level: int) -> dict:
    """Get spell slots for a class at a given level."""
    class_data = get_class_data(class_name)
    if not class_data.get("spellcasting"):
        return {}
    
    slots = class_data["spellcasting"].get("slots", {})
    # Find the highest level entry that's <= current level
    result = {}
    for lvl in sorted(slots.keys()):
        if lvl <= level:
            result = slots[lvl]
    return result


def get_features_at_level(class_name: str, level: int) -> list:
    """Get all features gained at a specific level."""
    class_data = get_class_data(class_name)
    return class_data.get("features", {}).get(level, [])


def get_all_features_up_to_level(class_name: str, level: int) -> list:
    """Get all features up to and including a level."""
    class_data = get_class_data(class_name)
    features = []
    for lvl in range(1, level + 1):
        lvl_features = class_data.get("features", {}).get(lvl, [])
        for f in lvl_features:
            if f not in features and f != "--":
                features.append(f)
    return features


# =============================================================================
# SPELLS - Organized by class spell lists with level and school
# =============================================================================
SPELLS = {
    # Format: "Spell Name": {"level": 0-9, "school": "school", "classes": [...], "ritual": bool, "concentration": bool}
    
    # === CANTRIPS (Level 0) ===
    "Acid Splash": {"level": 0, "school": "Conjuration", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Hurl acid bubble dealing 1d6 acid damage"},
    "Blade Ward": {"level": 0, "school": "Abjuration", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Resistance to bludgeoning, piercing, slashing"},
    "Chill Touch": {"level": 0, "school": "Necromancy", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "1d8 necrotic, target can't regain HP"},
    "Dancing Lights": {"level": 0, "school": "Evocation", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Create up to 4 floating lights"},
    "Druidcraft": {"level": 0, "school": "Transmutation", "classes": ["Druid"], "ritual": False, "concentration": False, "description": "Create nature effects, predict weather"},
    "Eldritch Blast": {"level": 0, "school": "Evocation", "classes": ["Warlock"], "ritual": False, "concentration": False, "description": "1d10 force damage beam"},
    "Fire Bolt": {"level": 0, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "1d10 fire damage ranged attack"},
    "Friends": {"level": 0, "school": "Enchantment", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Advantage on CHA checks vs one creature"},
    "Guidance": {"level": 0, "school": "Divination", "classes": ["Cleric", "Druid"], "ritual": False, "concentration": True, "description": "Add 1d4 to one ability check"},
    "Light": {"level": 0, "school": "Evocation", "classes": ["Bard", "Cleric", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Object sheds bright light 20 ft"},
    "Mage Hand": {"level": 0, "school": "Conjuration", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Spectral hand manipulates objects"},
    "Mending": {"level": 0, "school": "Transmutation", "classes": ["Bard", "Cleric", "Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Repair single break in object"},
    "Message": {"level": 0, "school": "Transmutation", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Whisper message to creature 120 ft"},
    "Minor Illusion": {"level": 0, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Create sound or image"},
    "Poison Spray": {"level": 0, "school": "Conjuration", "classes": ["Druid", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "1d12 poison damage (CON save)"},
    "Prestidigitation": {"level": 0, "school": "Transmutation", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Minor magical tricks"},
    "Produce Flame": {"level": 0, "school": "Conjuration", "classes": ["Druid"], "ritual": False, "concentration": False, "description": "Light source or 1d8 fire attack"},
    "Ray of Frost": {"level": 0, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "1d8 cold, reduce speed by 10 ft"},
    "Resistance": {"level": 0, "school": "Abjuration", "classes": ["Cleric", "Druid"], "ritual": False, "concentration": True, "description": "Add 1d4 to one saving throw"},
    "Sacred Flame": {"level": 0, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "1d8 radiant damage (DEX save)"},
    "Shillelagh": {"level": 0, "school": "Transmutation", "classes": ["Druid"], "ritual": False, "concentration": False, "description": "Club/staff uses WIS, deals 1d8"},
    "Shocking Grasp": {"level": 0, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "1d8 lightning, no reactions"},
    "Spare the Dying": {"level": 0, "school": "Necromancy", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Stabilize dying creature"},
    "Thaumaturgy": {"level": 0, "school": "Transmutation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Minor divine manifestations"},
    "Thorn Whip": {"level": 0, "school": "Transmutation", "classes": ["Druid"], "ritual": False, "concentration": False, "description": "1d6 piercing, pull 10 ft"},
    "True Strike": {"level": 0, "school": "Divination", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Advantage on next attack"},
    "Vicious Mockery": {"level": 0, "school": "Enchantment", "classes": ["Bard"], "ritual": False, "concentration": False, "description": "1d4 psychic, disadvantage on attack"},
    
    # === 1ST LEVEL SPELLS ===
    "Alarm": {"level": 1, "school": "Abjuration", "classes": ["Ranger", "Wizard"], "ritual": True, "concentration": False, "description": "Set ward that alerts you"},
    "Animal Friendship": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Druid", "Ranger"], "ritual": False, "concentration": False, "description": "Charm beast for 24 hours"},
    "Armor of Agathys": {"level": 1, "school": "Abjuration", "classes": ["Warlock"], "ritual": False, "concentration": False, "description": "5 temp HP, cold damage to attackers"},
    "Arms of Hadar": {"level": 1, "school": "Conjuration", "classes": ["Warlock"], "ritual": False, "concentration": False, "description": "2d6 necrotic, no reactions"},
    "Bane": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Cleric"], "ritual": False, "concentration": True, "description": "Subtract 1d4 from attacks/saves"},
    "Bless": {"level": 1, "school": "Enchantment", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": True, "description": "Add 1d4 to attacks and saves"},
    "Burning Hands": {"level": 1, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "3d6 fire in 15-ft cone"},
    "Charm Person": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Druid", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Charm humanoid for 1 hour"},
    "Color Spray": {"level": 1, "school": "Illusion", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Blind creatures (6d10 HP affected)"},
    "Command": {"level": 1, "school": "Enchantment", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "One-word command"},
    "Comprehend Languages": {"level": 1, "school": "Divination", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": True, "concentration": False, "description": "Understand all languages"},
    "Create or Destroy Water": {"level": 1, "school": "Transmutation", "classes": ["Cleric", "Druid"], "ritual": False, "concentration": False, "description": "Create/destroy 10 gallons"},
    "Cure Wounds": {"level": 1, "school": "Evocation", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger"], "ritual": False, "concentration": False, "description": "Heal 1d8 + spellcasting mod"},
    "Detect Evil and Good": {"level": 1, "school": "Divination", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": True, "description": "Sense aberrations, celestials, etc."},
    "Detect Magic": {"level": 1, "school": "Divination", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger", "Sorcerer", "Wizard"], "ritual": True, "concentration": True, "description": "Sense magic within 30 ft"},
    "Detect Poison and Disease": {"level": 1, "school": "Divination", "classes": ["Cleric", "Druid", "Paladin", "Ranger"], "ritual": True, "concentration": True, "description": "Sense poison and disease"},
    "Disguise Self": {"level": 1, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Change appearance for 1 hour"},
    "Dissonant Whispers": {"level": 1, "school": "Enchantment", "classes": ["Bard"], "ritual": False, "concentration": False, "description": "3d6 psychic, must flee"},
    "Divine Favor": {"level": 1, "school": "Evocation", "classes": ["Paladin"], "ritual": False, "concentration": True, "description": "+1d4 radiant on weapon attacks"},
    "Entangle": {"level": 1, "school": "Conjuration", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "Restrain creatures in area"},
    "Expeditious Retreat": {"level": 1, "school": "Transmutation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Dash as bonus action"},
    "Faerie Fire": {"level": 1, "school": "Evocation", "classes": ["Bard", "Druid"], "ritual": False, "concentration": True, "description": "Outline creatures, attacks have advantage"},
    "False Life": {"level": 1, "school": "Necromancy", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Gain 1d4+4 temp HP"},
    "Feather Fall": {"level": 1, "school": "Transmutation", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Slow falling rate"},
    "Find Familiar": {"level": 1, "school": "Conjuration", "classes": ["Wizard"], "ritual": True, "concentration": False, "description": "Summon familiar spirit"},
    "Fog Cloud": {"level": 1, "school": "Conjuration", "classes": ["Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "20-ft sphere of fog"},
    "Goodberry": {"level": 1, "school": "Transmutation", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": False, "description": "Create 10 berries (1 HP each)"},
    "Grease": {"level": 1, "school": "Conjuration", "classes": ["Wizard"], "ritual": False, "concentration": False, "description": "Slippery ground, DEX or fall"},
    "Guiding Bolt": {"level": 1, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "4d6 radiant, next attack has advantage"},
    "Healing Word": {"level": 1, "school": "Evocation", "classes": ["Bard", "Cleric", "Druid"], "ritual": False, "concentration": False, "description": "Bonus action heal 1d4 + mod"},
    "Hellish Rebuke": {"level": 1, "school": "Evocation", "classes": ["Warlock"], "ritual": False, "concentration": False, "description": "Reaction: 2d10 fire damage"},
    "Heroism": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Paladin"], "ritual": False, "concentration": True, "description": "Immunity to fear, temp HP each turn"},
    "Hex": {"level": 1, "school": "Enchantment", "classes": ["Warlock"], "ritual": False, "concentration": True, "description": "+1d6 necrotic on hits, disadvantage on ability"},
    "Hunter's Mark": {"level": 1, "school": "Divination", "classes": ["Ranger"], "ritual": False, "concentration": True, "description": "+1d6 damage on hits"},
    "Identify": {"level": 1, "school": "Divination", "classes": ["Bard", "Wizard"], "ritual": True, "concentration": False, "description": "Learn properties of item"},
    "Inflict Wounds": {"level": 1, "school": "Necromancy", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Melee: 3d10 necrotic"},
    "Jump": {"level": 1, "school": "Transmutation", "classes": ["Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Triple jump distance"},
    "Longstrider": {"level": 1, "school": "Transmutation", "classes": ["Bard", "Druid", "Ranger", "Wizard"], "ritual": False, "concentration": False, "description": "+10 ft speed for 1 hour"},
    "Mage Armor": {"level": 1, "school": "Abjuration", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "AC 13 + DEX for 8 hours"},
    "Magic Missile": {"level": 1, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "3 darts, 1d4+1 force each"},
    "Protection from Evil and Good": {"level": 1, "school": "Abjuration", "classes": ["Cleric", "Paladin", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Protection from creature types"},
    "Purify Food and Drink": {"level": 1, "school": "Transmutation", "classes": ["Cleric", "Druid", "Paladin"], "ritual": True, "concentration": False, "description": "Remove poison/disease from food"},
    "Sanctuary": {"level": 1, "school": "Abjuration", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Enemies must save to attack target"},
    "Shield": {"level": 1, "school": "Abjuration", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Reaction: +5 AC"},
    "Shield of Faith": {"level": 1, "school": "Abjuration", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": True, "description": "+2 AC for 10 minutes"},
    "Silent Image": {"level": 1, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Create 15-ft cube illusion"},
    "Sleep": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Put 5d8 HP of creatures to sleep"},
    "Speak with Animals": {"level": 1, "school": "Divination", "classes": ["Bard", "Druid", "Ranger"], "ritual": True, "concentration": False, "description": "Communicate with beasts"},
    "Tasha's Hideous Laughter": {"level": 1, "school": "Enchantment", "classes": ["Bard", "Wizard"], "ritual": False, "concentration": True, "description": "Target falls prone laughing"},
    "Thunderwave": {"level": 1, "school": "Evocation", "classes": ["Bard", "Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "2d8 thunder, push 10 ft"},
    "Unseen Servant": {"level": 1, "school": "Conjuration", "classes": ["Bard", "Warlock", "Wizard"], "ritual": True, "concentration": False, "description": "Invisible servant performs tasks"},
    "Witch Bolt": {"level": 1, "school": "Evocation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "1d12 lightning, 1d12 each turn"},
    
    # === 2ND LEVEL SPELLS ===
    "Aid": {"level": 2, "school": "Abjuration", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "+5 max HP to 3 creatures"},
    "Alter Self": {"level": 2, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Change form for 1 hour"},
    "Animal Messenger": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Druid", "Ranger"], "ritual": True, "concentration": False, "description": "Animal delivers message"},
    "Barkskin": {"level": 2, "school": "Transmutation", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "AC can't be less than 16"},
    "Blindness/Deafness": {"level": 2, "school": "Necromancy", "classes": ["Bard", "Cleric", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Blind or deafen target"},
    "Blur": {"level": 2, "school": "Illusion", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Attacks have disadvantage"},
    "Calm Emotions": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Cleric"], "ritual": False, "concentration": True, "description": "Suppress charm/fear or hostility"},
    "Continual Flame": {"level": 2, "school": "Evocation", "classes": ["Cleric", "Wizard"], "ritual": False, "concentration": False, "description": "Permanent heatless flame"},
    "Darkness": {"level": 2, "school": "Evocation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "15-ft sphere of darkness"},
    "Darkvision": {"level": 2, "school": "Transmutation", "classes": ["Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Grant 60 ft darkvision"},
    "Detect Thoughts": {"level": 2, "school": "Divination", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Read surface thoughts"},
    "Enhance Ability": {"level": 2, "school": "Transmutation", "classes": ["Bard", "Cleric", "Druid", "Sorcerer"], "ritual": False, "concentration": True, "description": "Advantage on ability checks"},
    "Enlarge/Reduce": {"level": 2, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Double or halve size"},
    "Enthrall": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Warlock"], "ritual": False, "concentration": False, "description": "Captivate creatures"},
    "Find Steed": {"level": 2, "school": "Conjuration", "classes": ["Paladin"], "ritual": False, "concentration": False, "description": "Summon loyal mount"},
    "Find Traps": {"level": 2, "school": "Divination", "classes": ["Cleric", "Druid", "Ranger"], "ritual": False, "concentration": False, "description": "Sense presence of traps"},
    "Flame Blade": {"level": 2, "school": "Evocation", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "Fiery blade, 3d6 fire"},
    "Flaming Sphere": {"level": 2, "school": "Conjuration", "classes": ["Druid", "Wizard"], "ritual": False, "concentration": True, "description": "Rolling fire sphere, 2d6"},
    "Gentle Repose": {"level": 2, "school": "Necromancy", "classes": ["Cleric", "Wizard"], "ritual": True, "concentration": False, "description": "Preserve corpse"},
    "Gust of Wind": {"level": 2, "school": "Evocation", "classes": ["Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Strong wind pushes creatures"},
    "Heat Metal": {"level": 2, "school": "Transmutation", "classes": ["Bard", "Druid"], "ritual": False, "concentration": True, "description": "Heat metal object, 2d8 fire"},
    "Hold Person": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Paralyze humanoid"},
    "Invisibility": {"level": 2, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Target invisible for 1 hour"},
    "Knock": {"level": 2, "school": "Transmutation", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Open locked object"},
    "Lesser Restoration": {"level": 2, "school": "Abjuration", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger"], "ritual": False, "concentration": False, "description": "End disease/condition"},
    "Levitate": {"level": 2, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Rise vertically"},
    "Locate Object": {"level": 2, "school": "Divination", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger", "Wizard"], "ritual": False, "concentration": True, "description": "Sense direction to object"},
    "Magic Weapon": {"level": 2, "school": "Transmutation", "classes": ["Paladin", "Wizard"], "ritual": False, "concentration": True, "description": "+1 magic weapon"},
    "Mirror Image": {"level": 2, "school": "Illusion", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "3 illusory duplicates"},
    "Misty Step": {"level": 2, "school": "Conjuration", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Bonus action teleport 30 ft"},
    "Moonbeam": {"level": 2, "school": "Evocation", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "2d10 radiant in beam"},
    "Pass without Trace": {"level": 2, "school": "Abjuration", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "+10 to Stealth checks"},
    "Prayer of Healing": {"level": 2, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Heal 6 creatures 2d8+mod"},
    "Protection from Poison": {"level": 2, "school": "Abjuration", "classes": ["Cleric", "Druid", "Paladin", "Ranger"], "ritual": False, "concentration": False, "description": "Neutralize poison"},
    "Ray of Enfeeblement": {"level": 2, "school": "Necromancy", "classes": ["Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Half STR damage"},
    "Scorching Ray": {"level": 2, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "3 rays, 2d6 fire each"},
    "See Invisibility": {"level": 2, "school": "Divination", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "See invisible creatures"},
    "Shatter": {"level": 2, "school": "Evocation", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "3d8 thunder in 10-ft sphere"},
    "Silence": {"level": 2, "school": "Illusion", "classes": ["Bard", "Cleric", "Ranger"], "ritual": True, "concentration": True, "description": "No sound in 20-ft sphere"},
    "Spider Climb": {"level": 2, "school": "Transmutation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Walk on walls/ceilings"},
    "Spike Growth": {"level": 2, "school": "Transmutation", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "2d4 piercing per 5 ft moved"},
    "Spiritual Weapon": {"level": 2, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Floating weapon, 1d8+mod"},
    "Suggestion": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Suggest course of action"},
    "Warding Bond": {"level": 2, "school": "Abjuration", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "+1 AC/saves, share damage"},
    "Web": {"level": 2, "school": "Conjuration", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Restrain creatures in webs"},
    "Zone of Truth": {"level": 2, "school": "Enchantment", "classes": ["Bard", "Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "Can't lie in area"},
    
    # === 3RD LEVEL SPELLS ===
    "Animate Dead": {"level": 3, "school": "Necromancy", "classes": ["Cleric", "Wizard"], "ritual": False, "concentration": False, "description": "Create undead servant"},
    "Beacon of Hope": {"level": 3, "school": "Abjuration", "classes": ["Cleric"], "ritual": False, "concentration": True, "description": "Advantage on WIS/death saves, max healing"},
    "Bestow Curse": {"level": 3, "school": "Necromancy", "classes": ["Bard", "Cleric", "Wizard"], "ritual": False, "concentration": True, "description": "Curse target"},
    "Blink": {"level": 3, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "50% chance to vanish to Ethereal"},
    "Call Lightning": {"level": 3, "school": "Conjuration", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "3d10 lightning bolts"},
    "Clairvoyance": {"level": 3, "school": "Divination", "classes": ["Bard", "Cleric", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Remote sensing"},
    "Conjure Animals": {"level": 3, "school": "Conjuration", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "Summon beasts"},
    "Counterspell": {"level": 3, "school": "Abjuration", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Interrupt spellcasting"},
    "Create Food and Water": {"level": 3, "school": "Conjuration", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "Create food for 15 creatures"},
    "Daylight": {"level": 3, "school": "Evocation", "classes": ["Cleric", "Druid", "Paladin", "Ranger", "Sorcerer"], "ritual": False, "concentration": False, "description": "60-ft bright light sphere"},
    "Dispel Magic": {"level": 3, "school": "Abjuration", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "End spells on target"},
    "Fear": {"level": 3, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Frighten creatures in cone"},
    "Fireball": {"level": 3, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "8d6 fire in 20-ft sphere"},
    "Fly": {"level": 3, "school": "Transmutation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "60 ft flying speed"},
    "Gaseous Form": {"level": 3, "school": "Transmutation", "classes": ["Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Transform to mist"},
    "Glyph of Warding": {"level": 3, "school": "Abjuration", "classes": ["Bard", "Cleric", "Wizard"], "ritual": False, "concentration": False, "description": "Create magical trap"},
    "Haste": {"level": 3, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Double speed, +2 AC, extra action"},
    "Hunger of Hadar": {"level": 3, "school": "Conjuration", "classes": ["Warlock"], "ritual": False, "concentration": True, "description": "2d6 cold + 2d6 acid in darkness"},
    "Hypnotic Pattern": {"level": 3, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Charm creatures in cube"},
    "Lightning Bolt": {"level": 3, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "8d6 lightning in line"},
    "Magic Circle": {"level": 3, "school": "Abjuration", "classes": ["Cleric", "Paladin", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Ward against creature types"},
    "Major Image": {"level": 3, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "20-ft illusion with sound"},
    "Mass Healing Word": {"level": 3, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Heal 6 creatures 1d4+mod"},
    "Meld into Stone": {"level": 3, "school": "Transmutation", "classes": ["Cleric", "Druid"], "ritual": True, "concentration": False, "description": "Step into stone"},
    "Nondetection": {"level": 3, "school": "Abjuration", "classes": ["Bard", "Ranger", "Wizard"], "ritual": False, "concentration": False, "description": "Hide from divination"},
    "Plant Growth": {"level": 3, "school": "Transmutation", "classes": ["Bard", "Druid", "Ranger"], "ritual": False, "concentration": False, "description": "Enhance or overgrow plants"},
    "Protection from Energy": {"level": 3, "school": "Abjuration", "classes": ["Cleric", "Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Resistance to damage type"},
    "Remove Curse": {"level": 3, "school": "Abjuration", "classes": ["Cleric", "Paladin", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "End curses"},
    "Revivify": {"level": 3, "school": "Necromancy", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "Return creature dead < 1 min to life"},
    "Sending": {"level": 3, "school": "Evocation", "classes": ["Bard", "Cleric", "Wizard"], "ritual": False, "concentration": False, "description": "25-word message anywhere"},
    "Sleet Storm": {"level": 3, "school": "Conjuration", "classes": ["Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Freezing rain, difficult terrain"},
    "Slow": {"level": 3, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Halve speed, -2 AC, no reactions"},
    "Speak with Dead": {"level": 3, "school": "Necromancy", "classes": ["Bard", "Cleric"], "ritual": False, "concentration": False, "description": "Ask corpse 5 questions"},
    "Speak with Plants": {"level": 3, "school": "Transmutation", "classes": ["Bard", "Druid", "Ranger"], "ritual": False, "concentration": False, "description": "Communicate with plants"},
    "Spirit Guardians": {"level": 3, "school": "Conjuration", "classes": ["Cleric"], "ritual": False, "concentration": True, "description": "3d8 damage in 15-ft radius"},
    "Stinking Cloud": {"level": 3, "school": "Conjuration", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Nauseating cloud"},
    "Tongues": {"level": 3, "school": "Divination", "classes": ["Bard", "Cleric", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Understand all languages"},
    "Vampiric Touch": {"level": 3, "school": "Necromancy", "classes": ["Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "3d6 necrotic, heal half"},
    "Water Breathing": {"level": 3, "school": "Transmutation", "classes": ["Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": True, "concentration": False, "description": "Breathe underwater 24h"},
    "Water Walk": {"level": 3, "school": "Transmutation", "classes": ["Cleric", "Druid", "Ranger", "Sorcerer"], "ritual": True, "concentration": False, "description": "Walk on water"},
    "Wind Wall": {"level": 3, "school": "Evocation", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "Wall of wind, 3d8 bludgeoning"},
    
    # === 4TH LEVEL SPELLS ===
    "Arcane Eye": {"level": 4, "school": "Divination", "classes": ["Wizard"], "ritual": False, "concentration": True, "description": "Invisible floating eye"},
    "Banishment": {"level": 4, "school": "Abjuration", "classes": ["Cleric", "Paladin", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Send to another plane"},
    "Blight": {"level": 4, "school": "Necromancy", "classes": ["Druid", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "8d8 necrotic damage"},
    "Compulsion": {"level": 4, "school": "Enchantment", "classes": ["Bard"], "ritual": False, "concentration": True, "description": "Force movement direction"},
    "Confusion": {"level": 4, "school": "Enchantment", "classes": ["Bard", "Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Random actions"},
    "Conjure Minor Elementals": {"level": 4, "school": "Conjuration", "classes": ["Druid", "Wizard"], "ritual": False, "concentration": True, "description": "Summon elementals CR 2 or less"},
    "Conjure Woodland Beings": {"level": 4, "school": "Conjuration", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "Summon fey creatures"},
    "Control Water": {"level": 4, "school": "Transmutation", "classes": ["Cleric", "Druid", "Wizard"], "ritual": False, "concentration": True, "description": "Manipulate water"},
    "Death Ward": {"level": 4, "school": "Abjuration", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "Drop to 1 HP instead of 0"},
    "Dimension Door": {"level": 4, "school": "Conjuration", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Teleport 500 ft"},
    "Divination": {"level": 4, "school": "Divination", "classes": ["Cleric"], "ritual": True, "concentration": False, "description": "Ask deity question"},
    "Dominate Beast": {"level": 4, "school": "Enchantment", "classes": ["Druid", "Sorcerer"], "ritual": False, "concentration": True, "description": "Control beast"},
    "Evard's Black Tentacles": {"level": 4, "school": "Conjuration", "classes": ["Wizard"], "ritual": False, "concentration": True, "description": "3d6 bludgeoning, restrain"},
    "Fabricate": {"level": 4, "school": "Transmutation", "classes": ["Wizard"], "ritual": False, "concentration": False, "description": "Create objects from materials"},
    "Fire Shield": {"level": 4, "school": "Evocation", "classes": ["Wizard"], "ritual": False, "concentration": False, "description": "2d8 damage to melee attackers"},
    "Freedom of Movement": {"level": 4, "school": "Abjuration", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger"], "ritual": False, "concentration": False, "description": "Immune to restraint/paralysis"},
    "Giant Insect": {"level": 4, "school": "Transmutation", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "Enlarge insects"},
    "Greater Invisibility": {"level": 4, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Invisible even when attacking"},
    "Hallucinatory Terrain": {"level": 4, "school": "Illusion", "classes": ["Bard", "Druid", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Illusory terrain"},
    "Ice Storm": {"level": 4, "school": "Evocation", "classes": ["Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "2d8 bludgeoning + 4d6 cold"},
    "Locate Creature": {"level": 4, "school": "Divination", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Ranger", "Wizard"], "ritual": False, "concentration": True, "description": "Sense direction to creature"},
    "Phantasmal Killer": {"level": 4, "school": "Illusion", "classes": ["Wizard"], "ritual": False, "concentration": True, "description": "4d10 psychic from fear"},
    "Polymorph": {"level": 4, "school": "Transmutation", "classes": ["Bard", "Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Transform into beast"},
    "Stone Shape": {"level": 4, "school": "Transmutation", "classes": ["Cleric", "Druid", "Wizard"], "ritual": False, "concentration": False, "description": "Reshape stone"},
    "Stoneskin": {"level": 4, "school": "Abjuration", "classes": ["Druid", "Ranger", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Resist nonmagical damage"},
    "Wall of Fire": {"level": 4, "school": "Evocation", "classes": ["Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "5d8 fire damage wall"},
    
    # === 5TH LEVEL SPELLS ===
    "Animate Objects": {"level": 5, "school": "Transmutation", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Animate 10 small objects"},
    "Antilife Shell": {"level": 5, "school": "Abjuration", "classes": ["Druid"], "ritual": False, "concentration": True, "description": "Barrier against living creatures"},
    "Awaken": {"level": 5, "school": "Transmutation", "classes": ["Bard", "Druid"], "ritual": False, "concentration": False, "description": "Give beast/plant intelligence"},
    "Cloudkill": {"level": 5, "school": "Conjuration", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "5d8 poison fog"},
    "Commune": {"level": 5, "school": "Divination", "classes": ["Cleric"], "ritual": True, "concentration": False, "description": "3 yes/no questions to deity"},
    "Commune with Nature": {"level": 5, "school": "Divination", "classes": ["Druid", "Ranger"], "ritual": True, "concentration": False, "description": "Learn about terrain"},
    "Cone of Cold": {"level": 5, "school": "Evocation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "8d8 cold in 60-ft cone"},
    "Conjure Elemental": {"level": 5, "school": "Conjuration", "classes": ["Druid", "Wizard"], "ritual": False, "concentration": True, "description": "Summon CR 5 elemental"},
    "Contact Other Plane": {"level": 5, "school": "Divination", "classes": ["Warlock", "Wizard"], "ritual": True, "concentration": False, "description": "5 questions to extraplanar entity"},
    "Contagion": {"level": 5, "school": "Necromancy", "classes": ["Cleric", "Druid"], "ritual": False, "concentration": False, "description": "Inflict disease"},
    "Creation": {"level": 5, "school": "Illusion", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Create nonliving matter"},
    "Destructive Wave": {"level": 5, "school": "Evocation", "classes": ["Paladin"], "ritual": False, "concentration": False, "description": "5d6 thunder + 5d6 radiant/necrotic"},
    "Dispel Evil and Good": {"level": 5, "school": "Abjuration", "classes": ["Cleric", "Paladin"], "ritual": False, "concentration": True, "description": "End possession/charm"},
    "Dominate Person": {"level": 5, "school": "Enchantment", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Control humanoid"},
    "Dream": {"level": 5, "school": "Illusion", "classes": ["Bard", "Warlock", "Wizard"], "ritual": False, "concentration": False, "description": "Send message in dream"},
    "Flame Strike": {"level": 5, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "4d6 fire + 4d6 radiant"},
    "Geas": {"level": 5, "school": "Enchantment", "classes": ["Bard", "Cleric", "Druid", "Paladin", "Wizard"], "ritual": False, "concentration": False, "description": "Command creature 30 days"},
    "Greater Restoration": {"level": 5, "school": "Abjuration", "classes": ["Bard", "Cleric", "Druid"], "ritual": False, "concentration": False, "description": "End major conditions"},
    "Hallow": {"level": 5, "school": "Evocation", "classes": ["Cleric"], "ritual": False, "concentration": False, "description": "Holy/unholy area"},
    "Hold Monster": {"level": 5, "school": "Enchantment", "classes": ["Bard", "Sorcerer", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "Paralyze any creature"},
    "Insect Plague": {"level": 5, "school": "Conjuration", "classes": ["Cleric", "Druid", "Sorcerer"], "ritual": False, "concentration": True, "description": "4d10 piercing locusts"},
    "Legend Lore": {"level": 5, "school": "Divination", "classes": ["Bard", "Cleric", "Wizard"], "ritual": False, "concentration": False, "description": "Learn about person/place/object"},
    "Mass Cure Wounds": {"level": 5, "school": "Evocation", "classes": ["Bard", "Cleric", "Druid"], "ritual": False, "concentration": False, "description": "Heal 6 creatures 3d8+mod"},
    "Mislead": {"level": 5, "school": "Illusion", "classes": ["Bard", "Wizard"], "ritual": False, "concentration": True, "description": "Invisible + illusory double"},
    "Modify Memory": {"level": 5, "school": "Enchantment", "classes": ["Bard", "Wizard"], "ritual": False, "concentration": True, "description": "Change creature's memory"},
    "Passwall": {"level": 5, "school": "Transmutation", "classes": ["Wizard"], "ritual": False, "concentration": False, "description": "Passage through wall"},
    "Planar Binding": {"level": 5, "school": "Abjuration", "classes": ["Bard", "Cleric", "Druid", "Wizard"], "ritual": False, "concentration": False, "description": "Bind extraplanar creature"},
    "Raise Dead": {"level": 5, "school": "Necromancy", "classes": ["Bard", "Cleric", "Paladin"], "ritual": False, "concentration": False, "description": "Return dead creature to life"},
    "Reincarnate": {"level": 5, "school": "Transmutation", "classes": ["Druid"], "ritual": False, "concentration": False, "description": "Return dead to new body"},
    "Scrying": {"level": 5, "school": "Divination", "classes": ["Bard", "Cleric", "Druid", "Warlock", "Wizard"], "ritual": False, "concentration": True, "description": "See distant creature"},
    "Seeming": {"level": 5, "school": "Illusion", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Disguise multiple creatures"},
    "Telekinesis": {"level": 5, "school": "Transmutation", "classes": ["Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Move objects with mind"},
    "Teleportation Circle": {"level": 5, "school": "Conjuration", "classes": ["Bard", "Sorcerer", "Wizard"], "ritual": False, "concentration": False, "description": "Portal to known circle"},
    "Tree Stride": {"level": 5, "school": "Conjuration", "classes": ["Druid", "Ranger"], "ritual": False, "concentration": True, "description": "Teleport between trees"},
    "Wall of Force": {"level": 5, "school": "Evocation", "classes": ["Wizard"], "ritual": False, "concentration": True, "description": "Invisible wall"},
    "Wall of Stone": {"level": 5, "school": "Evocation", "classes": ["Druid", "Sorcerer", "Wizard"], "ritual": False, "concentration": True, "description": "Create stone wall"},
}


def get_spells_for_class(class_name: str, max_level: int = 9) -> dict:
    """Get all spells available to a class, organized by level."""
    result = {level: [] for level in range(0, max_level + 1)}
    for spell_name, spell_data in SPELLS.items():
        if class_name in spell_data["classes"] and spell_data["level"] <= max_level:
            result[spell_data["level"]].append({
                "name": spell_name,
                **spell_data
            })
    return result


def get_spell(spell_name: str) -> dict:
    """Get data for a specific spell."""
    return SPELLS.get(spell_name, None)


def get_cantrips_for_class(class_name: str) -> list:
    """Get all cantrips available to a class."""
    return [name for name, data in SPELLS.items() 
            if data["level"] == 0 and class_name in data["classes"]]


def get_ritual_spells(class_name: str = None) -> list:
    """Get all ritual spells, optionally filtered by class."""
    return [name for name, data in SPELLS.items() 
            if data["ritual"] and (class_name is None or class_name in data["classes"])]


# =============================================================================
# RACES - PHB races with traits and bonuses
# =============================================================================
RACES = {
    "Dwarf": {
        "ability_bonuses": {"CON": 2},
        "size": "Medium",
        "speed": 25,
        "traits": [
            "Darkvision (60 ft)",
            "Dwarven Resilience (advantage vs poison, resistance to poison damage)",
            "Stonecunning (History checks on stonework)",
        ],
        "languages": ["Common", "Dwarvish"],
        "weapon_proficiencies": ["battleaxe", "handaxe", "light hammer", "warhammer"],
        "tool_proficiencies": ["smith's tools", "brewer's supplies", "mason's tools"],  # choose one
        "subraces": {
            "Hill Dwarf": {
                "ability_bonuses": {"WIS": 1},
                "traits": ["Dwarven Toughness (+1 HP per level)"],
            },
            "Mountain Dwarf": {
                "ability_bonuses": {"STR": 2},
                "armor_proficiencies": ["light", "medium"],
            },
        },
    },
    
    "Elf": {
        "ability_bonuses": {"DEX": 2},
        "size": "Medium",
        "speed": 30,
        "traits": [
            "Darkvision (60 ft)",
            "Keen Senses (proficiency in Perception)",
            "Fey Ancestry (advantage vs charm, immune to magical sleep)",
            "Trance (4 hours rest instead of 8)",
        ],
        "languages": ["Common", "Elvish"],
        "skill_proficiencies": ["Perception"],
        "subraces": {
            "High Elf": {
                "ability_bonuses": {"INT": 1},
                "weapon_proficiencies": ["longsword", "shortsword", "shortbow", "longbow"],
                "traits": ["Cantrip (one wizard cantrip)", "Extra Language"],
            },
            "Wood Elf": {
                "ability_bonuses": {"WIS": 1},
                "speed": 35,
                "weapon_proficiencies": ["longsword", "shortsword", "shortbow", "longbow"],
                "traits": ["Mask of the Wild (hide in light obscurement)"],
            },
            "Drow": {
                "ability_bonuses": {"CHA": 1},
                "traits": [
                    "Superior Darkvision (120 ft)",
                    "Sunlight Sensitivity",
                    "Drow Magic (Dancing Lights, Faerie Fire at 3rd, Darkness at 5th)",
                ],
                "weapon_proficiencies": ["rapiers", "shortswords", "hand crossbows"],
            },
        },
    },
    
    "Halfling": {
        "ability_bonuses": {"DEX": 2},
        "size": "Small",
        "speed": 25,
        "traits": [
            "Lucky (reroll 1s on d20)",
            "Brave (advantage vs frightened)",
            "Halfling Nimbleness (move through larger creatures)",
        ],
        "languages": ["Common", "Halfling"],
        "subraces": {
            "Lightfoot": {
                "ability_bonuses": {"CHA": 1},
                "traits": ["Naturally Stealthy (hide behind larger creatures)"],
            },
            "Stout": {
                "ability_bonuses": {"CON": 1},
                "traits": ["Stout Resilience (advantage vs poison, resistance to poison)"],
            },
        },
    },
    
    "Human": {
        "ability_bonuses": {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
        "size": "Medium",
        "speed": 30,
        "traits": ["Extra Language"],
        "languages": ["Common"],
        "extra_languages": 1,
        "subraces": {
            "Variant Human": {
                "ability_bonuses": {},  # +1 to two different abilities instead
                "variant_ability_choices": 2,
                "traits": ["Skill proficiency (choose one)", "Feat (choose one)"],
            },
        },
    },
    
    "Dragonborn": {
        "ability_bonuses": {"STR": 2, "CHA": 1},
        "size": "Medium",
        "speed": 30,
        "traits": [
            "Breath Weapon (2d6 at 1st, 3d6 at 6th, 4d6 at 11th, 5d6 at 16th)",
            "Damage Resistance (based on ancestry)",
        ],
        "languages": ["Common", "Draconic"],
        "ancestry_options": {
            "Black": {"damage": "Acid", "breath": "5x30 ft line (DEX save)"},
            "Blue": {"damage": "Lightning", "breath": "5x30 ft line (DEX save)"},
            "Brass": {"damage": "Fire", "breath": "5x30 ft line (DEX save)"},
            "Bronze": {"damage": "Lightning", "breath": "5x30 ft line (DEX save)"},
            "Copper": {"damage": "Acid", "breath": "5x30 ft line (DEX save)"},
            "Gold": {"damage": "Fire", "breath": "15 ft cone (DEX save)"},
            "Green": {"damage": "Poison", "breath": "15 ft cone (CON save)"},
            "Red": {"damage": "Fire", "breath": "15 ft cone (DEX save)"},
            "Silver": {"damage": "Cold", "breath": "15 ft cone (CON save)"},
            "White": {"damage": "Cold", "breath": "15 ft cone (CON save)"},
        },
    },
    
    "Gnome": {
        "ability_bonuses": {"INT": 2},
        "size": "Small",
        "speed": 25,
        "traits": [
            "Darkvision (60 ft)",
            "Gnome Cunning (advantage on INT/WIS/CHA saves vs magic)",
        ],
        "languages": ["Common", "Gnomish"],
        "subraces": {
            "Forest Gnome": {
                "ability_bonuses": {"DEX": 1},
                "traits": [
                    "Natural Illusionist (Minor Illusion cantrip)",
                    "Speak with Small Beasts",
                ],
            },
            "Rock Gnome": {
                "ability_bonuses": {"CON": 1},
                "traits": [
                    "Artificer's Lore (2x proficiency on magic item History)",
                    "Tinker (create clockwork devices)",
                ],
                "tool_proficiencies": ["tinker's tools"],
            },
        },
    },
    
    "Half-Elf": {
        "ability_bonuses": {"CHA": 2},
        "ability_choices": 2,  # +1 to two other abilities
        "size": "Medium",
        "speed": 30,
        "traits": [
            "Darkvision (60 ft)",
            "Fey Ancestry (advantage vs charm, immune to magical sleep)",
            "Skill Versatility (proficiency in 2 skills)",
        ],
        "languages": ["Common", "Elvish"],
        "extra_languages": 1,
        "skill_choices": 2,  # any 2 skills
    },
    
    "Half-Orc": {
        "ability_bonuses": {"STR": 2, "CON": 1},
        "size": "Medium",
        "speed": 30,
        "traits": [
            "Darkvision (60 ft)",
            "Menacing (proficiency in Intimidation)",
            "Relentless Endurance (drop to 1 HP instead of 0, 1/long rest)",
            "Savage Attacks (+1 die on crit)",
        ],
        "languages": ["Common", "Orc"],
        "skill_proficiencies": ["Intimidation"],
    },
    
    "Tiefling": {
        "ability_bonuses": {"CHA": 2, "INT": 1},
        "size": "Medium",
        "speed": 30,
        "traits": [
            "Darkvision (60 ft)",
            "Hellish Resistance (resistance to fire damage)",
            "Infernal Legacy (Thaumaturgy cantrip, Hellish Rebuke at 3rd, Darkness at 5th)",
        ],
        "languages": ["Common", "Infernal"],
    },
}


def get_race_data(race_name: str, subrace: str = None) -> dict:
    """Get race data, optionally merged with subrace data."""
    race = RACES.get(race_name)
    if not race:
        return None
    
    result = {
        "name": race_name,
        "ability_bonuses": dict(race.get("ability_bonuses", {})),
        "size": race.get("size", "Medium"),
        "speed": race.get("speed", 30),
        "traits": list(race.get("traits", [])),
        "languages": list(race.get("languages", [])),
    }
    
    # Copy optional fields
    for field in ["weapon_proficiencies", "armor_proficiencies", "tool_proficiencies", 
                  "skill_proficiencies", "extra_languages", "skill_choices"]:
        if field in race:
            result[field] = race[field]
    
    # Merge subrace if provided
    if subrace and "subraces" in race and subrace in race["subraces"]:
        sub = race["subraces"][subrace]
        result["subrace"] = subrace
        
        # Merge ability bonuses
        for stat, bonus in sub.get("ability_bonuses", {}).items():
            result["ability_bonuses"][stat] = result["ability_bonuses"].get(stat, 0) + bonus
        
        # Merge traits
        result["traits"].extend(sub.get("traits", []))
        
        # Merge proficiencies
        for field in ["weapon_proficiencies", "armor_proficiencies", "tool_proficiencies"]:
            if field in sub:
                result[field] = result.get(field, []) + sub[field]
        
        # Override speed if subrace has different speed
        if "speed" in sub:
            result["speed"] = sub["speed"]
    
    return result


def get_all_races() -> list:
    """Get list of all race names."""
    return list(RACES.keys())


def get_subraces(race_name: str) -> list:
    """Get list of subraces for a race."""
    race = RACES.get(race_name)
    if not race or "subraces" not in race:
        return []
    return list(race["subraces"].keys())


def calculate_ability_scores(base_scores: dict, race_name: str, subrace: str = None) -> dict:
    """Apply racial bonuses to base ability scores."""
    race_data = get_race_data(race_name, subrace)
    if not race_data:
        return base_scores
    
    result = dict(base_scores)
    for stat, bonus in race_data.get("ability_bonuses", {}).items():
        result[stat] = result.get(stat, 10) + bonus
    return result
