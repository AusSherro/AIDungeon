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


# =============================================================================
# EQUIPMENT - Weapons, Armor, and Gear
# =============================================================================

WEAPONS = {
    # Simple Melee Weapons
    "Club": {"damage": "1d4", "damage_type": "bludgeoning", "weight": 2, "cost": "1 sp", "properties": ["light"], "category": "simple", "melee": True},
    "Dagger": {"damage": "1d4", "damage_type": "piercing", "weight": 1, "cost": "2 gp", "properties": ["finesse", "light", "thrown (20/60)"], "category": "simple", "melee": True},
    "Greatclub": {"damage": "1d8", "damage_type": "bludgeoning", "weight": 10, "cost": "2 sp", "properties": ["two-handed"], "category": "simple", "melee": True},
    "Handaxe": {"damage": "1d6", "damage_type": "slashing", "weight": 2, "cost": "5 gp", "properties": ["light", "thrown (20/60)"], "category": "simple", "melee": True},
    "Javelin": {"damage": "1d6", "damage_type": "piercing", "weight": 2, "cost": "5 sp", "properties": ["thrown (30/120)"], "category": "simple", "melee": True},
    "Light Hammer": {"damage": "1d4", "damage_type": "bludgeoning", "weight": 2, "cost": "2 gp", "properties": ["light", "thrown (20/60)"], "category": "simple", "melee": True},
    "Mace": {"damage": "1d6", "damage_type": "bludgeoning", "weight": 4, "cost": "5 gp", "properties": [], "category": "simple", "melee": True},
    "Quarterstaff": {"damage": "1d6", "damage_type": "bludgeoning", "weight": 4, "cost": "2 sp", "properties": ["versatile (1d8)"], "category": "simple", "melee": True},
    "Sickle": {"damage": "1d4", "damage_type": "slashing", "weight": 2, "cost": "1 gp", "properties": ["light"], "category": "simple", "melee": True},
    "Spear": {"damage": "1d6", "damage_type": "piercing", "weight": 3, "cost": "1 gp", "properties": ["thrown (20/60)", "versatile (1d8)"], "category": "simple", "melee": True},
    
    # Simple Ranged Weapons
    "Light Crossbow": {"damage": "1d8", "damage_type": "piercing", "weight": 5, "cost": "25 gp", "properties": ["ammunition (80/320)", "loading", "two-handed"], "category": "simple", "melee": False},
    "Dart": {"damage": "1d4", "damage_type": "piercing", "weight": 0.25, "cost": "5 cp", "properties": ["finesse", "thrown (20/60)"], "category": "simple", "melee": False},
    "Shortbow": {"damage": "1d6", "damage_type": "piercing", "weight": 2, "cost": "25 gp", "properties": ["ammunition (80/320)", "two-handed"], "category": "simple", "melee": False},
    "Sling": {"damage": "1d4", "damage_type": "bludgeoning", "weight": 0, "cost": "1 sp", "properties": ["ammunition (30/120)"], "category": "simple", "melee": False},
    
    # Martial Melee Weapons
    "Battleaxe": {"damage": "1d8", "damage_type": "slashing", "weight": 4, "cost": "10 gp", "properties": ["versatile (1d10)"], "category": "martial", "melee": True},
    "Flail": {"damage": "1d8", "damage_type": "bludgeoning", "weight": 2, "cost": "10 gp", "properties": [], "category": "martial", "melee": True},
    "Glaive": {"damage": "1d10", "damage_type": "slashing", "weight": 6, "cost": "20 gp", "properties": ["heavy", "reach", "two-handed"], "category": "martial", "melee": True},
    "Greataxe": {"damage": "1d12", "damage_type": "slashing", "weight": 7, "cost": "30 gp", "properties": ["heavy", "two-handed"], "category": "martial", "melee": True},
    "Greatsword": {"damage": "2d6", "damage_type": "slashing", "weight": 6, "cost": "50 gp", "properties": ["heavy", "two-handed"], "category": "martial", "melee": True},
    "Halberd": {"damage": "1d10", "damage_type": "slashing", "weight": 6, "cost": "20 gp", "properties": ["heavy", "reach", "two-handed"], "category": "martial", "melee": True},
    "Lance": {"damage": "1d12", "damage_type": "piercing", "weight": 6, "cost": "10 gp", "properties": ["reach", "special"], "category": "martial", "melee": True},
    "Longsword": {"damage": "1d8", "damage_type": "slashing", "weight": 3, "cost": "15 gp", "properties": ["versatile (1d10)"], "category": "martial", "melee": True},
    "Maul": {"damage": "2d6", "damage_type": "bludgeoning", "weight": 10, "cost": "10 gp", "properties": ["heavy", "two-handed"], "category": "martial", "melee": True},
    "Morningstar": {"damage": "1d8", "damage_type": "piercing", "weight": 4, "cost": "15 gp", "properties": [], "category": "martial", "melee": True},
    "Pike": {"damage": "1d10", "damage_type": "piercing", "weight": 18, "cost": "5 gp", "properties": ["heavy", "reach", "two-handed"], "category": "martial", "melee": True},
    "Rapier": {"damage": "1d8", "damage_type": "piercing", "weight": 2, "cost": "25 gp", "properties": ["finesse"], "category": "martial", "melee": True},
    "Scimitar": {"damage": "1d6", "damage_type": "slashing", "weight": 3, "cost": "25 gp", "properties": ["finesse", "light"], "category": "martial", "melee": True},
    "Shortsword": {"damage": "1d6", "damage_type": "piercing", "weight": 2, "cost": "10 gp", "properties": ["finesse", "light"], "category": "martial", "melee": True},
    "Trident": {"damage": "1d6", "damage_type": "piercing", "weight": 4, "cost": "5 gp", "properties": ["thrown (20/60)", "versatile (1d8)"], "category": "martial", "melee": True},
    "War Pick": {"damage": "1d8", "damage_type": "piercing", "weight": 2, "cost": "5 gp", "properties": [], "category": "martial", "melee": True},
    "Warhammer": {"damage": "1d8", "damage_type": "bludgeoning", "weight": 2, "cost": "15 gp", "properties": ["versatile (1d10)"], "category": "martial", "melee": True},
    "Whip": {"damage": "1d4", "damage_type": "slashing", "weight": 3, "cost": "2 gp", "properties": ["finesse", "reach"], "category": "martial", "melee": True},
    
    # Martial Ranged Weapons
    "Blowgun": {"damage": "1", "damage_type": "piercing", "weight": 1, "cost": "10 gp", "properties": ["ammunition (25/100)", "loading"], "category": "martial", "melee": False},
    "Hand Crossbow": {"damage": "1d6", "damage_type": "piercing", "weight": 3, "cost": "75 gp", "properties": ["ammunition (30/120)", "light", "loading"], "category": "martial", "melee": False},
    "Heavy Crossbow": {"damage": "1d10", "damage_type": "piercing", "weight": 18, "cost": "50 gp", "properties": ["ammunition (100/400)", "heavy", "loading", "two-handed"], "category": "martial", "melee": False},
    "Longbow": {"damage": "1d8", "damage_type": "piercing", "weight": 2, "cost": "50 gp", "properties": ["ammunition (150/600)", "heavy", "two-handed"], "category": "martial", "melee": False},
    "Net": {"damage": "0", "damage_type": "none", "weight": 3, "cost": "1 gp", "properties": ["special", "thrown (5/15)"], "category": "martial", "melee": False},
}

ARMOR = {
    # Light Armor
    "Padded": {"ac": 11, "max_dex": None, "stealth_disadvantage": True, "weight": 8, "cost": "5 gp", "category": "light", "strength_req": None},
    "Leather": {"ac": 11, "max_dex": None, "stealth_disadvantage": False, "weight": 10, "cost": "10 gp", "category": "light", "strength_req": None},
    "Studded Leather": {"ac": 12, "max_dex": None, "stealth_disadvantage": False, "weight": 13, "cost": "45 gp", "category": "light", "strength_req": None},
    
    # Medium Armor
    "Hide": {"ac": 12, "max_dex": 2, "stealth_disadvantage": False, "weight": 12, "cost": "10 gp", "category": "medium", "strength_req": None},
    "Chain Shirt": {"ac": 13, "max_dex": 2, "stealth_disadvantage": False, "weight": 20, "cost": "50 gp", "category": "medium", "strength_req": None},
    "Scale Mail": {"ac": 14, "max_dex": 2, "stealth_disadvantage": True, "weight": 45, "cost": "50 gp", "category": "medium", "strength_req": None},
    "Breastplate": {"ac": 14, "max_dex": 2, "stealth_disadvantage": False, "weight": 20, "cost": "400 gp", "category": "medium", "strength_req": None},
    "Half Plate": {"ac": 15, "max_dex": 2, "stealth_disadvantage": True, "weight": 40, "cost": "750 gp", "category": "medium", "strength_req": None},
    
    # Heavy Armor
    "Ring Mail": {"ac": 14, "max_dex": 0, "stealth_disadvantage": True, "weight": 40, "cost": "30 gp", "category": "heavy", "strength_req": None},
    "Chain Mail": {"ac": 16, "max_dex": 0, "stealth_disadvantage": True, "weight": 55, "cost": "75 gp", "category": "heavy", "strength_req": 13},
    "Splint": {"ac": 17, "max_dex": 0, "stealth_disadvantage": True, "weight": 60, "cost": "200 gp", "category": "heavy", "strength_req": 15},
    "Plate": {"ac": 18, "max_dex": 0, "stealth_disadvantage": True, "weight": 65, "cost": "1500 gp", "category": "heavy", "strength_req": 15},
    
    # Shields
    "Shield": {"ac": 2, "max_dex": None, "stealth_disadvantage": False, "weight": 6, "cost": "10 gp", "category": "shield", "strength_req": None},
}

AMMUNITION = {
    "Arrows (20)": {"cost": "1 gp", "weight": 1, "compatible": ["Shortbow", "Longbow"]},
    "Blowgun Needles (50)": {"cost": "1 gp", "weight": 1, "compatible": ["Blowgun"]},
    "Crossbow Bolts (20)": {"cost": "1 gp", "weight": 1.5, "compatible": ["Light Crossbow", "Hand Crossbow", "Heavy Crossbow"]},
    "Sling Bullets (20)": {"cost": "4 cp", "weight": 1.5, "compatible": ["Sling"]},
}

ADVENTURING_GEAR = {
    "Backpack": {"cost": "2 gp", "weight": 5},
    "Bedroll": {"cost": "1 gp", "weight": 7},
    "Rope (50 ft)": {"cost": "1 gp", "weight": 10},
    "Torch": {"cost": "1 cp", "weight": 1},
    "Rations (1 day)": {"cost": "5 sp", "weight": 2},
    "Waterskin": {"cost": "2 sp", "weight": 5},
    "Tinderbox": {"cost": "5 sp", "weight": 1},
    "Healer's Kit": {"cost": "5 gp", "weight": 3, "uses": 10},
    "Thieves' Tools": {"cost": "25 gp", "weight": 1},
    "Holy Symbol": {"cost": "5 gp", "weight": 1},
    "Arcane Focus (Crystal)": {"cost": "10 gp", "weight": 1},
    "Component Pouch": {"cost": "25 gp", "weight": 2},
    "Spellbook": {"cost": "50 gp", "weight": 3},
    "Lantern (Hooded)": {"cost": "5 gp", "weight": 2},
    "Oil Flask": {"cost": "1 sp", "weight": 1},
    "Grappling Hook": {"cost": "2 gp", "weight": 4},
    "Crowbar": {"cost": "2 gp", "weight": 5},
    "Hammer": {"cost": "1 gp", "weight": 3},
    "Pitons (10)": {"cost": "5 cp", "weight": 2.5},
    "Mirror (Steel)": {"cost": "5 gp", "weight": 0.5},
    "Manacles": {"cost": "2 gp", "weight": 6},
    "Potion of Healing": {"cost": "50 gp", "weight": 0.5, "effect": "Heals 2d4+2 HP"},
}


def get_weapon(name: str) -> dict:
    """Get weapon data by name."""
    return WEAPONS.get(name)


def get_armor(name: str) -> dict:
    """Get armor data by name."""
    return ARMOR.get(name)


def calculate_ac(armor_name: str, dex_modifier: int, has_shield: bool = False) -> int:
    """Calculate total AC based on armor, dex, and shield."""
    base_ac = 10  # Unarmored
    
    if armor_name and armor_name in ARMOR:
        armor = ARMOR[armor_name]
        if armor["category"] == "shield":
            # Shield only, use unarmored + shield
            base_ac = 10 + dex_modifier + 2
        else:
            base_ac = armor["ac"]
            if armor["max_dex"] is None:
                # Light armor - full DEX bonus
                base_ac += dex_modifier
            elif armor["max_dex"] > 0:
                # Medium armor - capped DEX bonus
                base_ac += min(dex_modifier, armor["max_dex"])
            # Heavy armor - no DEX bonus (max_dex = 0)
    else:
        # Unarmored
        base_ac = 10 + dex_modifier
    
    if has_shield:
        base_ac += 2
    
    return base_ac


def get_weapons_by_category(category: str) -> list:
    """Get all weapons of a specific category (simple/martial)."""
    return [name for name, data in WEAPONS.items() if data["category"] == category]


def get_melee_weapons() -> list:
    """Get all melee weapons."""
    return [name for name, data in WEAPONS.items() if data["melee"]]


def get_ranged_weapons() -> list:
    """Get all ranged weapons."""
    return [name for name, data in WEAPONS.items() if not data["melee"]]


# =============================================================================
# CONDITIONS - Status effects with mechanical impacts
# =============================================================================

CONDITIONS = {
    "Blinded": {
        "description": "A blinded creature can't see and automatically fails any ability check that requires sight.",
        "effects": {
            "attack_rolls": "disadvantage",
            "attacks_against": "advantage",
            "auto_fail_sight_checks": True,
        }
    },
    "Charmed": {
        "description": "A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects.",
        "effects": {
            "cant_attack_charmer": True,
            "social_checks_from_charmer": "advantage",
        }
    },
    "Deafened": {
        "description": "A deafened creature can't hear and automatically fails any ability check that requires hearing.",
        "effects": {
            "auto_fail_hearing_checks": True,
        }
    },
    "Frightened": {
        "description": "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight.",
        "effects": {
            "attack_rolls": "disadvantage",
            "ability_checks": "disadvantage",
            "cant_move_closer_to_source": True,
        }
    },
    "Grappled": {
        "description": "A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed.",
        "effects": {
            "speed": 0,
        }
    },
    "Incapacitated": {
        "description": "An incapacitated creature can't take actions or reactions.",
        "effects": {
            "cant_take_actions": True,
            "cant_take_reactions": True,
        }
    },
    "Invisible": {
        "description": "An invisible creature is impossible to see without the aid of magic or a special sense.",
        "effects": {
            "attack_rolls": "advantage",
            "attacks_against": "disadvantage",
            "heavily_obscured": True,
        }
    },
    "Paralyzed": {
        "description": "A paralyzed creature is incapacitated and can't move or speak.",
        "effects": {
            "incapacitated": True,
            "speed": 0,
            "cant_speak": True,
            "auto_fail_str_dex_saves": True,
            "attacks_against": "advantage",
            "melee_hits_are_crits": True,
        }
    },
    "Petrified": {
        "description": "A petrified creature is transformed into a solid inanimate substance and is incapacitated.",
        "effects": {
            "incapacitated": True,
            "speed": 0,
            "auto_fail_str_dex_saves": True,
            "attacks_against": "advantage",
            "damage_resistance": "all",
            "immune_to_poison_disease": True,
            "weight_multiplied": 10,
        }
    },
    "Poisoned": {
        "description": "A poisoned creature has disadvantage on attack rolls and ability checks.",
        "effects": {
            "attack_rolls": "disadvantage",
            "ability_checks": "disadvantage",
        }
    },
    "Prone": {
        "description": "A prone creature's only movement option is to crawl. The creature has disadvantage on attack rolls.",
        "effects": {
            "attack_rolls": "disadvantage",
            "melee_attacks_against": "advantage",
            "ranged_attacks_against": "disadvantage",
            "movement": "crawl",
            "stand_up_cost": "half_movement",
        }
    },
    "Restrained": {
        "description": "A restrained creature's speed becomes 0, and it can't benefit from any bonus to its speed.",
        "effects": {
            "speed": 0,
            "attack_rolls": "disadvantage",
            "attacks_against": "advantage",
            "dex_saves": "disadvantage",
        }
    },
    "Stunned": {
        "description": "A stunned creature is incapacitated, can't move, and can speak only falteringly.",
        "effects": {
            "incapacitated": True,
            "speed": 0,
            "auto_fail_str_dex_saves": True,
            "attacks_against": "advantage",
        }
    },
    "Unconscious": {
        "description": "An unconscious creature is incapacitated, can't move or speak, and is unaware of its surroundings.",
        "effects": {
            "incapacitated": True,
            "speed": 0,
            "cant_speak": True,
            "unaware": True,
            "drops_held_items": True,
            "falls_prone": True,
            "auto_fail_str_dex_saves": True,
            "attacks_against": "advantage",
            "melee_hits_are_crits": True,
        }
    },
    "Exhaustion": {
        "description": "Exhaustion is measured in six levels. Effects are cumulative.",
        "levels": {
            1: {"effect": "Disadvantage on ability checks"},
            2: {"effect": "Speed halved"},
            3: {"effect": "Disadvantage on attack rolls and saving throws"},
            4: {"effect": "Hit point maximum halved"},
            5: {"effect": "Speed reduced to 0"},
            6: {"effect": "Death"},
        }
    },
    "Concentration": {
        "description": "Some spells require concentration to maintain. Taking damage requires a Constitution save (DC 10 or half damage, whichever is higher).",
        "effects": {
            "con_save_on_damage": True,
            "ends_on_incapacitated": True,
            "ends_on_another_concentration": True,
        }
    },
}


def get_condition(name: str) -> dict:
    """Get condition data by name."""
    return CONDITIONS.get(name)


def get_condition_effects(name: str) -> dict:
    """Get the mechanical effects of a condition."""
    condition = CONDITIONS.get(name)
    if condition:
        return condition.get("effects", {})
    return {}


def apply_exhaustion_effects(level: int) -> list:
    """Get cumulative exhaustion effects up to the given level."""
    if level < 1 or level > 6:
        return []
    
    effects = []
    exhaustion = CONDITIONS.get("Exhaustion", {}).get("levels", {})
    for i in range(1, level + 1):
        if i in exhaustion:
            effects.append(exhaustion[i]["effect"])
    return effects


def check_attack_modifiers(conditions: list) -> dict:
    """Check how conditions affect attack rolls."""
    result = {"advantage": False, "disadvantage": False}
    
    for condition_name in conditions:
        effects = get_condition_effects(condition_name)
        if effects.get("attack_rolls") == "advantage":
            result["advantage"] = True
        elif effects.get("attack_rolls") == "disadvantage":
            result["disadvantage"] = True
    
    return result


def check_attacks_against_modifiers(conditions: list) -> dict:
    """Check how a target's conditions affect attacks against them."""
    result = {"advantage": False, "disadvantage": False}
    
    for condition_name in conditions:
        effects = get_condition_effects(condition_name)
        if effects.get("attacks_against") == "advantage":
            result["advantage"] = True
        elif effects.get("attacks_against") == "disadvantage":
            result["disadvantage"] = True
    
    return result


# =============================================================================
# FEATS
# =============================================================================

FEATS = {
    "Alert": {
        "description": "Always on the lookout for danger, you gain benefits that help you avoid ambushes.",
        "effects": {
            "initiative_bonus": 5,
            "cant_be_surprised": True,
            "no_advantage_from_hidden": True,
        },
        "prerequisites": None,
    },
    "Athlete": {
        "description": "You have undergone extensive physical training.",
        "effects": {
            "ability_increase": {"choice": ["STR", "DEX"], "amount": 1},
            "stand_up_cost": "5 feet",
            "climbing_no_extra_cost": True,
            "running_jump_bonus": True,
        },
        "prerequisites": None,
    },
    "Charger": {
        "description": "When you use your action to Dash, you can use a bonus action to make one melee attack or shove.",
        "effects": {
            "dash_bonus_attack": True,
            "charge_damage_bonus": 5,
        },
        "prerequisites": None,
    },
    "Crossbow Expert": {
        "description": "Thanks to extensive practice with the crossbow, you gain benefits.",
        "effects": {
            "ignore_loading": True,
            "no_disadvantage_close_range": True,
            "bonus_action_hand_crossbow": True,
        },
        "prerequisites": None,
    },
    "Defensive Duelist": {
        "description": "When wielding a finesse weapon, you can add your proficiency bonus to AC as a reaction.",
        "effects": {
            "reaction_ac_bonus": "proficiency",
            "requires_finesse_weapon": True,
        },
        "prerequisites": {"DEX": 13},
    },
    "Dual Wielder": {
        "description": "You master fighting with two weapons.",
        "effects": {
            "ac_bonus_dual_wield": 1,
            "dual_wield_non_light": True,
            "draw_two_weapons": True,
        },
        "prerequisites": None,
    },
    "Durable": {
        "description": "Hardy and resilient, you gain increased durability.",
        "effects": {
            "ability_increase": {"stat": "CON", "amount": 1},
            "minimum_hit_dice_heal": "double_con_mod",
        },
        "prerequisites": None,
    },
    "Elemental Adept": {
        "description": "You gain resistance to a damage type and can ignore resistance.",
        "effects": {
            "ignore_resistance": True,
            "minimum_damage_dice": 2,
            "damage_type_choice": ["acid", "cold", "fire", "lightning", "thunder"],
        },
        "prerequisites": {"spellcasting": True},
    },
    "Grappler": {
        "description": "You've developed the skills necessary to hold your own in close-quarters grappling.",
        "effects": {
            "advantage_vs_grappled": True,
            "pin_creature": True,
        },
        "prerequisites": {"STR": 13},
    },
    "Great Weapon Master": {
        "description": "You've learned to put the weight of a weapon to your advantage.",
        "effects": {
            "bonus_action_attack_on_crit": True,
            "bonus_action_attack_on_kill": True,
            "power_attack": {"attack_penalty": -5, "damage_bonus": 10},
        },
        "prerequisites": None,
    },
    "Healer": {
        "description": "You are an able physician, allowing you to mend wounds quickly.",
        "effects": {
            "stabilize_to_1hp": True,
            "healer_kit_heal": "1d6 + 4 + creature_hit_dice",
        },
        "prerequisites": None,
    },
    "Heavily Armored": {
        "description": "You have trained to master the use of heavy armor.",
        "effects": {
            "ability_increase": {"stat": "STR", "amount": 1},
            "heavy_armor_proficiency": True,
        },
        "prerequisites": {"armor_proficiency": "medium"},
    },
    "Heavy Armor Master": {
        "description": "You can use your armor to deflect strikes that would kill others.",
        "effects": {
            "ability_increase": {"stat": "STR", "amount": 1},
            "nonmagical_damage_reduction": 3,
        },
        "prerequisites": {"armor_proficiency": "heavy"},
    },
    "Inspiring Leader": {
        "description": "You can spend 10 minutes inspiring your companions, granting temporary HP.",
        "effects": {
            "temp_hp_grant": "level + CHA",
            "affects_up_to": 6,
        },
        "prerequisites": {"CHA": 13},
    },
    "Keen Mind": {
        "description": "You have a mind that can track time, direction, and detail with uncanny precision.",
        "effects": {
            "ability_increase": {"stat": "INT", "amount": 1},
            "always_know_north": True,
            "always_know_time": True,
            "perfect_recall_1_month": True,
        },
        "prerequisites": None,
    },
    "Lightly Armored": {
        "description": "You have trained to master the use of light armor.",
        "effects": {
            "ability_increase": {"choice": ["STR", "DEX"], "amount": 1},
            "light_armor_proficiency": True,
        },
        "prerequisites": None,
    },
    "Linguist": {
        "description": "You have studied languages and codes.",
        "effects": {
            "ability_increase": {"stat": "INT", "amount": 1},
            "extra_languages": 3,
            "create_ciphers": True,
        },
        "prerequisites": None,
    },
    "Lucky": {
        "description": "You have inexplicable luck that seems to kick in at just the right moment.",
        "effects": {
            "luck_points": 3,
            "reroll_attack_ability_save": True,
            "force_enemy_reroll": True,
        },
        "prerequisites": None,
    },
    "Mage Slayer": {
        "description": "You have practiced techniques useful in melee combat against spellcasters.",
        "effects": {
            "reaction_attack_on_spell": True,
            "advantage_concentration_save": True,
            "advantage_save_vs_adjacent_spell": True,
        },
        "prerequisites": None,
    },
    "Magic Initiate": {
        "description": "Choose a class: you learn two cantrips and one 1st-level spell from that class's list.",
        "effects": {
            "learn_cantrips": 2,
            "learn_1st_level_spell": 1,
            "cast_once_per_long_rest": True,
        },
        "prerequisites": None,
    },
    "Martial Adept": {
        "description": "You have martial training that allows you to perform special combat maneuvers.",
        "effects": {
            "learn_maneuvers": 2,
            "superiority_dice": "1d6",
        },
        "prerequisites": None,
    },
    "Medium Armor Master": {
        "description": "You have practiced moving in medium armor.",
        "effects": {
            "no_stealth_disadvantage_medium": True,
            "max_dex_bonus_medium": 3,
        },
        "prerequisites": {"armor_proficiency": "medium"},
    },
    "Mobile": {
        "description": "You are exceptionally speedy and agile.",
        "effects": {
            "speed_bonus": 10,
            "no_difficult_terrain_dash": True,
            "no_opportunity_attack_after_melee": True,
        },
        "prerequisites": None,
    },
    "Moderately Armored": {
        "description": "You have trained to master the use of medium armor and shields.",
        "effects": {
            "ability_increase": {"choice": ["STR", "DEX"], "amount": 1},
            "medium_armor_proficiency": True,
            "shield_proficiency": True,
        },
        "prerequisites": {"armor_proficiency": "light"},
    },
    "Mounted Combatant": {
        "description": "You are a dangerous foe to face while mounted.",
        "effects": {
            "advantage_vs_smaller_unmounted": True,
            "redirect_attack_to_self": True,
            "mount_evasion": True,
        },
        "prerequisites": None,
    },
    "Observant": {
        "description": "Quick to notice details, you gain benefits to perception.",
        "effects": {
            "ability_increase": {"choice": ["INT", "WIS"], "amount": 1},
            "read_lips": True,
            "passive_perception_bonus": 5,
            "passive_investigation_bonus": 5,
        },
        "prerequisites": None,
    },
    "Polearm Master": {
        "description": "You keep your enemies at bay with reach weapons.",
        "effects": {
            "bonus_action_butt_attack": "1d4",
            "opportunity_attack_on_enter_reach": True,
            "works_with": ["glaive", "halberd", "pike", "quarterstaff", "spear"],
        },
        "prerequisites": None,
    },
    "Resilient": {
        "description": "Choose one ability score. You gain proficiency in saving throws using that ability.",
        "effects": {
            "ability_increase": {"choice": "any", "amount": 1},
            "saving_throw_proficiency": "chosen_ability",
        },
        "prerequisites": None,
    },
    "Ritual Caster": {
        "description": "You have learned a number of spells that you can cast as rituals.",
        "effects": {
            "ritual_book": True,
            "learn_ritual_spells": True,
        },
        "prerequisites": {"INT": 13, "or": {"WIS": 13}},
    },
    "Savage Attacker": {
        "description": "Once per turn when you roll damage for a melee attack, you can reroll and use either total.",
        "effects": {
            "reroll_melee_damage": True,
            "once_per_turn": True,
        },
        "prerequisites": None,
    },
    "Sentinel": {
        "description": "You have mastered techniques to take advantage of every drop in any enemy's guard.",
        "effects": {
            "opportunity_attack_stops_movement": True,
            "opportunity_attack_on_disengage": True,
            "reaction_attack_on_ally_attack": True,
        },
        "prerequisites": None,
    },
    "Sharpshooter": {
        "description": "You have mastered ranged weapons and can make shots that others find impossible.",
        "effects": {
            "ignore_cover_except_total": True,
            "no_disadvantage_long_range": True,
            "power_attack": {"attack_penalty": -5, "damage_bonus": 10},
        },
        "prerequisites": None,
    },
    "Shield Master": {
        "description": "You use shields for both offense and defense.",
        "effects": {
            "bonus_action_shove": True,
            "add_shield_ac_to_dex_save": True,
            "no_damage_on_dex_save_success": True,
        },
        "prerequisites": None,
    },
    "Skilled": {
        "description": "You gain proficiency in any combination of three skills or tools of your choice.",
        "effects": {
            "skill_or_tool_proficiencies": 3,
        },
        "prerequisites": None,
    },
    "Skulker": {
        "description": "You are expert at slinking through shadows.",
        "effects": {
            "hide_when_lightly_obscured": True,
            "no_position_reveal_on_miss": True,
            "no_disadvantage_dim_light_perception": True,
        },
        "prerequisites": {"DEX": 13},
    },
    "Spell Sniper": {
        "description": "You have learned techniques to enhance your attacks with certain kinds of spells.",
        "effects": {
            "double_spell_attack_range": True,
            "ignore_cover": True,
            "learn_attack_cantrip": 1,
        },
        "prerequisites": {"spellcasting": True},
    },
    "Tavern Brawler": {
        "description": "Accustomed to rough-and-tumble fighting using whatever is at hand.",
        "effects": {
            "ability_increase": {"choice": ["STR", "CON"], "amount": 1},
            "unarmed_damage": "1d4",
            "improvised_weapon_proficiency": True,
            "bonus_action_grapple_on_hit": True,
        },
        "prerequisites": None,
    },
    "Tough": {
        "description": "Your hit point maximum increases.",
        "effects": {
            "hp_bonus_per_level": 2,
        },
        "prerequisites": None,
    },
    "War Caster": {
        "description": "You have practiced casting spells in the midst of combat.",
        "effects": {
            "advantage_concentration": True,
            "somatic_with_full_hands": True,
            "opportunity_attack_spell": True,
        },
        "prerequisites": {"spellcasting": True},
    },
    "Weapon Master": {
        "description": "You have practiced extensively with a variety of weapons.",
        "effects": {
            "ability_increase": {"choice": ["STR", "DEX"], "amount": 1},
            "weapon_proficiencies": 4,
        },
        "prerequisites": None,
    },
}


def get_feat(name: str) -> dict:
    """Get feat data by name."""
    return FEATS.get(name)


def get_all_feats() -> list:
    """Get list of all feat names."""
    return list(FEATS.keys())


def check_feat_prerequisites(feat_name: str, character_data: dict) -> tuple:
    """Check if a character meets feat prerequisites.
    
    Returns:
        tuple of (meets_prereqs: bool, reason: str)
    """
    feat = get_feat(feat_name)
    if not feat:
        return False, f"Feat '{feat_name}' not found"
    
    prereqs = feat.get("prerequisites")
    if not prereqs:
        return True, "No prerequisites"
    
    # Check ability score requirements
    for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        if stat in prereqs:
            if character_data.get(stat, 10) < prereqs[stat]:
                return False, f"Requires {stat} {prereqs[stat]} (you have {character_data.get(stat, 10)})"
    
    # Check spellcasting requirement
    if prereqs.get("spellcasting"):
        if not character_data.get("spellcasting"):
            return False, "Requires the ability to cast at least one spell"
    
    # Check armor proficiency requirements
    if "armor_proficiency" in prereqs:
        required = prereqs["armor_proficiency"]
        proficiencies = character_data.get("armor_proficiencies", [])
        if required not in proficiencies:
            return False, f"Requires proficiency with {required} armor"
    
    return True, "Prerequisites met"


# =============================================================================
# MONSTERS - Pre-built statblocks for combat
# =============================================================================

MONSTERS = {
    # CR 1/8
    "Kobold": {
        "name": "Kobold",
        "size": "Small",
        "type": "humanoid",
        "alignment": "lawful evil",
        "ac": 12,
        "hp": 5,
        "hit_dice": "2d6-2",
        "speed": 30,
        "stats": {"STR": 7, "DEX": 15, "CON": 9, "INT": 8, "WIS": 7, "CHA": 8},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Draconic"],
        "cr": "1/8",
        "xp": 25,
        "traits": [
            {"name": "Sunlight Sensitivity", "description": "Disadvantage on attack rolls and Perception checks in sunlight."},
            {"name": "Pack Tactics", "description": "Advantage on attack rolls if ally is within 5 ft of target."},
        ],
        "actions": [
            {"name": "Dagger", "type": "melee", "attack_bonus": 4, "damage": "1d4+2", "damage_type": "piercing"},
            {"name": "Sling", "type": "ranged", "attack_bonus": 4, "damage": "1d4+2", "damage_type": "bludgeoning", "range": "30/120"},
        ],
    },
    
    # CR 1/4
    "Goblin": {
        "name": "Goblin",
        "size": "Small",
        "type": "humanoid",
        "alignment": "neutral evil",
        "ac": 15,
        "hp": 7,
        "hit_dice": "2d6",
        "speed": 30,
        "stats": {"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
        "skills": {"Stealth": 6},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Goblin"],
        "cr": "1/4",
        "xp": 50,
        "traits": [
            {"name": "Nimble Escape", "description": "Can take Disengage or Hide as a bonus action."},
        ],
        "actions": [
            {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "slashing"},
            {"name": "Shortbow", "type": "ranged", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "piercing", "range": "80/320"},
        ],
    },
    
    "Skeleton": {
        "name": "Skeleton",
        "size": "Medium",
        "type": "undead",
        "alignment": "lawful evil",
        "ac": 13,
        "hp": 13,
        "hit_dice": "2d8+4",
        "speed": 30,
        "stats": {"STR": 10, "DEX": 14, "CON": 15, "INT": 6, "WIS": 8, "CHA": 5},
        "vulnerabilities": ["bludgeoning"],
        "immunities": ["poison"],
        "condition_immunities": ["exhaustion", "poisoned"],
        "senses": {"darkvision": 60},
        "languages": ["understands languages it knew in life"],
        "cr": "1/4",
        "xp": 50,
        "actions": [
            {"name": "Shortsword", "type": "melee", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "piercing"},
            {"name": "Shortbow", "type": "ranged", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "piercing", "range": "80/320"},
        ],
    },
    
    "Zombie": {
        "name": "Zombie",
        "size": "Medium",
        "type": "undead",
        "alignment": "neutral evil",
        "ac": 8,
        "hp": 22,
        "hit_dice": "3d8+9",
        "speed": 20,
        "stats": {"STR": 13, "DEX": 6, "CON": 16, "INT": 3, "WIS": 6, "CHA": 5},
        "saving_throws": {"WIS": 0},
        "immunities": ["poison"],
        "condition_immunities": ["poisoned"],
        "senses": {"darkvision": 60},
        "cr": "1/4",
        "xp": 50,
        "traits": [
            {"name": "Undead Fortitude", "description": "If reduced to 0 HP, make CON save DC 5 + damage. On success, drop to 1 HP instead. Radiant/crit bypasses."},
        ],
        "actions": [
            {"name": "Slam", "type": "melee", "attack_bonus": 3, "damage": "1d6+1", "damage_type": "bludgeoning"},
        ],
    },
    
    # CR 1/2
    "Orc": {
        "name": "Orc",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "chaotic evil",
        "ac": 13,
        "hp": 15,
        "hit_dice": "2d8+6",
        "speed": 30,
        "stats": {"STR": 16, "DEX": 12, "CON": 16, "INT": 7, "WIS": 11, "CHA": 10},
        "skills": {"Intimidation": 2},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Orc"],
        "cr": "1/2",
        "xp": 100,
        "traits": [
            {"name": "Aggressive", "description": "As a bonus action, can move up to speed toward hostile creature it can see."},
        ],
        "actions": [
            {"name": "Greataxe", "type": "melee", "attack_bonus": 5, "damage": "1d12+3", "damage_type": "slashing"},
            {"name": "Javelin", "type": "melee_or_ranged", "attack_bonus": 5, "damage": "1d6+3", "damage_type": "piercing", "range": "30/120"},
        ],
    },
    
    "Hobgoblin": {
        "name": "Hobgoblin",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "lawful evil",
        "ac": 18,
        "hp": 11,
        "hit_dice": "2d8+2",
        "speed": 30,
        "stats": {"STR": 13, "DEX": 12, "CON": 12, "INT": 10, "WIS": 10, "CHA": 9},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Goblin"],
        "cr": "1/2",
        "xp": 100,
        "traits": [
            {"name": "Martial Advantage", "description": "Once per turn, deal extra 2d6 damage if ally within 5 ft of target."},
        ],
        "actions": [
            {"name": "Longsword", "type": "melee", "attack_bonus": 3, "damage": "1d8+1", "damage_type": "slashing"},
            {"name": "Longbow", "type": "ranged", "attack_bonus": 3, "damage": "1d8+1", "damage_type": "piercing", "range": "150/600"},
        ],
    },
    
    # CR 1
    "Bugbear": {
        "name": "Bugbear",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "chaotic evil",
        "ac": 16,
        "hp": 27,
        "hit_dice": "5d8+5",
        "speed": 30,
        "stats": {"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 11, "CHA": 9},
        "skills": {"Stealth": 6, "Survival": 2},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Goblin"],
        "cr": "1",
        "xp": 200,
        "traits": [
            {"name": "Brute", "description": "Melee weapon deals one extra die of damage (included)."},
            {"name": "Surprise Attack", "description": "If surprises a creature, deals extra 2d6 damage on first hit."},
        ],
        "actions": [
            {"name": "Morningstar", "type": "melee", "attack_bonus": 4, "damage": "2d8+2", "damage_type": "piercing"},
            {"name": "Javelin", "type": "melee_or_ranged", "attack_bonus": 4, "damage": "2d6+2", "damage_type": "piercing", "range": "30/120"},
        ],
    },
    
    "Dire Wolf": {
        "name": "Dire Wolf",
        "size": "Large",
        "type": "beast",
        "alignment": "unaligned",
        "ac": 14,
        "hp": 37,
        "hit_dice": "5d10+10",
        "speed": 50,
        "stats": {"STR": 17, "DEX": 15, "CON": 15, "INT": 3, "WIS": 12, "CHA": 7},
        "skills": {"Perception": 3, "Stealth": 4},
        "senses": {},
        "cr": "1",
        "xp": 200,
        "traits": [
            {"name": "Keen Hearing and Smell", "description": "Advantage on Perception checks that rely on hearing or smell."},
            {"name": "Pack Tactics", "description": "Advantage on attack rolls if ally is within 5 ft of target."},
        ],
        "actions": [
            {"name": "Bite", "type": "melee", "attack_bonus": 5, "damage": "2d6+3", "damage_type": "piercing", 
             "special": "DC 13 STR save or knocked prone"},
        ],
    },
    
    "Ghoul": {
        "name": "Ghoul",
        "size": "Medium",
        "type": "undead",
        "alignment": "chaotic evil",
        "ac": 12,
        "hp": 22,
        "hit_dice": "5d8",
        "speed": 30,
        "stats": {"STR": 13, "DEX": 15, "CON": 10, "INT": 7, "WIS": 10, "CHA": 6},
        "immunities": ["poison"],
        "condition_immunities": ["charmed", "exhaustion", "poisoned"],
        "senses": {"darkvision": 60},
        "languages": ["Common"],
        "cr": "1",
        "xp": 200,
        "actions": [
            {"name": "Bite", "type": "melee", "attack_bonus": 2, "damage": "2d6+2", "damage_type": "piercing"},
            {"name": "Claws", "type": "melee", "attack_bonus": 4, "damage": "2d4+2", "damage_type": "slashing",
             "special": "DC 10 CON save or paralyzed for 1 minute (repeat save at end of turn). Elves immune."},
        ],
    },
    
    # CR 2
    "Ogre": {
        "name": "Ogre",
        "size": "Large",
        "type": "giant",
        "alignment": "chaotic evil",
        "ac": 11,
        "hp": 59,
        "hit_dice": "7d10+21",
        "speed": 40,
        "stats": {"STR": 19, "DEX": 8, "CON": 16, "INT": 5, "WIS": 7, "CHA": 7},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Giant"],
        "cr": "2",
        "xp": 450,
        "actions": [
            {"name": "Greatclub", "type": "melee", "attack_bonus": 6, "damage": "2d8+4", "damage_type": "bludgeoning"},
            {"name": "Javelin", "type": "melee_or_ranged", "attack_bonus": 6, "damage": "2d6+4", "damage_type": "piercing", "range": "30/120"},
        ],
    },
    
    "Werewolf": {
        "name": "Werewolf",
        "size": "Medium",
        "type": "humanoid (shapechanger)",
        "alignment": "chaotic evil",
        "ac": 11,
        "hp": 58,
        "hit_dice": "9d8+18",
        "speed": 30,
        "stats": {"STR": 15, "DEX": 13, "CON": 14, "INT": 10, "WIS": 11, "CHA": 10},
        "skills": {"Perception": 4, "Stealth": 3},
        "immunities": ["bludgeoning, piercing, slashing from nonmagical/nonsilvered weapons"],
        "senses": {},
        "languages": ["Common (can't speak in wolf form)"],
        "cr": "3",
        "xp": 700,
        "traits": [
            {"name": "Shapechanger", "description": "Can polymorph into wolf-humanoid hybrid, wolf, or back to human."},
            {"name": "Keen Hearing and Smell", "description": "Advantage on Perception checks that rely on hearing or smell."},
        ],
        "actions": [
            {"name": "Multiattack (hybrid only)", "type": "special", "description": "Two attacks: one bite and one claws"},
            {"name": "Bite", "type": "melee", "attack_bonus": 4, "damage": "1d8+2", "damage_type": "piercing",
             "special": "DC 12 CON save or cursed with lycanthropy"},
            {"name": "Claws (hybrid only)", "type": "melee", "attack_bonus": 4, "damage": "2d4+2", "damage_type": "slashing"},
        ],
    },
    
    # CR 5
    "Troll": {
        "name": "Troll",
        "size": "Large",
        "type": "giant",
        "alignment": "chaotic evil",
        "ac": 15,
        "hp": 84,
        "hit_dice": "8d10+40",
        "speed": 30,
        "stats": {"STR": 18, "DEX": 13, "CON": 20, "INT": 7, "WIS": 9, "CHA": 7},
        "skills": {"Perception": 2},
        "senses": {"darkvision": 60},
        "languages": ["Giant"],
        "cr": "5",
        "xp": 1800,
        "traits": [
            {"name": "Keen Smell", "description": "Advantage on Perception checks that rely on smell."},
            {"name": "Regeneration", "description": "Regains 10 HP at start of turn. Stops if takes acid or fire damage. Dies only if at 0 HP and doesn't regenerate."},
        ],
        "actions": [
            {"name": "Multiattack", "type": "special", "description": "Three attacks: one bite and two claws"},
            {"name": "Bite", "type": "melee", "attack_bonus": 7, "damage": "1d6+4", "damage_type": "piercing"},
            {"name": "Claw", "type": "melee", "attack_bonus": 7, "damage": "2d6+4", "damage_type": "slashing"},
        ],
    },
    
    # CR 8
    "Young Green Dragon": {
        "name": "Young Green Dragon",
        "size": "Large",
        "type": "dragon",
        "alignment": "lawful evil",
        "ac": 18,
        "hp": 136,
        "hit_dice": "16d10+48",
        "speed": 40,
        "fly_speed": 80,
        "swim_speed": 40,
        "stats": {"STR": 19, "DEX": 12, "CON": 17, "INT": 16, "WIS": 13, "CHA": 15},
        "saving_throws": {"DEX": 4, "CON": 6, "WIS": 4, "CHA": 5},
        "skills": {"Deception": 5, "Perception": 7, "Stealth": 4},
        "immunities": ["poison"],
        "condition_immunities": ["poisoned"],
        "senses": {"blindsight": 30, "darkvision": 120},
        "languages": ["Common", "Draconic"],
        "cr": "8",
        "xp": 3900,
        "traits": [
            {"name": "Amphibious", "description": "Can breathe air and water."},
        ],
        "actions": [
            {"name": "Multiattack", "type": "special", "description": "Three attacks: one bite and two claws"},
            {"name": "Bite", "type": "melee", "attack_bonus": 7, "damage": "2d10+4", "damage_type": "piercing", "extra_damage": "1d6 poison"},
            {"name": "Claw", "type": "melee", "attack_bonus": 7, "damage": "2d6+4", "damage_type": "slashing"},
            {"name": "Poison Breath (Recharge 5-6)", "type": "special", "damage": "12d6", "damage_type": "poison",
             "description": "30 ft cone, DC 14 CON save for half damage"},
        ],
    },
    
    # Bosses
    "Goblin Boss": {
        "name": "Goblin Boss",
        "size": "Small",
        "type": "humanoid",
        "alignment": "neutral evil",
        "ac": 17,
        "hp": 21,
        "hit_dice": "6d6",
        "speed": 30,
        "stats": {"STR": 10, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 10},
        "skills": {"Stealth": 6},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Goblin"],
        "cr": "1",
        "xp": 200,
        "traits": [
            {"name": "Nimble Escape", "description": "Can take Disengage or Hide as a bonus action."},
        ],
        "actions": [
            {"name": "Multiattack", "type": "special", "description": "Two attacks with scimitar"},
            {"name": "Scimitar", "type": "melee", "attack_bonus": 4, "damage": "1d6+2", "damage_type": "slashing"},
            {"name": "Javelin", "type": "melee_or_ranged", "attack_bonus": 2, "damage": "1d6", "damage_type": "piercing", "range": "30/120"},
        ],
        "reactions": [
            {"name": "Redirect Attack", "description": "When missed by attack, can swap places with adjacent goblin who becomes target."},
        ],
    },
    
    "Orc War Chief": {
        "name": "Orc War Chief",
        "size": "Medium",
        "type": "humanoid",
        "alignment": "chaotic evil",
        "ac": 16,
        "hp": 93,
        "hit_dice": "11d8+44",
        "speed": 30,
        "stats": {"STR": 18, "DEX": 12, "CON": 18, "INT": 11, "WIS": 11, "CHA": 16},
        "saving_throws": {"STR": 6, "CON": 6, "WIS": 2},
        "skills": {"Intimidation": 5},
        "senses": {"darkvision": 60},
        "languages": ["Common", "Orc"],
        "cr": "4",
        "xp": 1100,
        "traits": [
            {"name": "Aggressive", "description": "As a bonus action, can move up to speed toward hostile creature it can see."},
            {"name": "Gruumsh's Fury", "description": "Deals extra 1d8 damage on hit (included)."},
        ],
        "actions": [
            {"name": "Multiattack", "type": "special", "description": "Two attacks with greataxe or javelins"},
            {"name": "Greataxe", "type": "melee", "attack_bonus": 6, "damage": "1d12+4", "damage_type": "slashing", "extra_damage": "1d8"},
            {"name": "Javelin", "type": "melee_or_ranged", "attack_bonus": 6, "damage": "1d6+4", "damage_type": "piercing", "extra_damage": "1d8", "range": "30/120"},
        ],
        "special": {
            "legendary_actions": None,
            "lair_actions": None,
        },
    },
}


def get_monster(name: str) -> dict:
    """Get monster statblock by name."""
    return MONSTERS.get(name)


def get_monsters_by_cr(cr: str) -> list:
    """Get all monsters of a specific challenge rating."""
    return [name for name, data in MONSTERS.items() if data.get("cr") == cr]


def get_all_monsters() -> list:
    """Get list of all monster names."""
    return list(MONSTERS.keys())


def get_monster_xp(name: str) -> int:
    """Get XP value for a monster."""
    monster = get_monster(name)
    if monster:
        return monster.get("xp", 0)
    return 0


def calculate_encounter_difficulty(monster_names: list, party_level: int, party_size: int = 4) -> dict:
    """Calculate encounter difficulty based on monsters and party.
    
    Returns dict with:
        - total_xp: Raw XP total
        - adjusted_xp: XP after multiplier for number of monsters
        - difficulty: "Trivial", "Easy", "Medium", "Hard", or "Deadly"
    """
    # XP thresholds per character level
    thresholds = {
        1: {"easy": 25, "medium": 50, "hard": 75, "deadly": 100},
        2: {"easy": 50, "medium": 100, "hard": 150, "deadly": 200},
        3: {"easy": 75, "medium": 150, "hard": 225, "deadly": 400},
        4: {"easy": 125, "medium": 250, "hard": 375, "deadly": 500},
        5: {"easy": 250, "medium": 500, "hard": 750, "deadly": 1100},
        6: {"easy": 300, "medium": 600, "hard": 900, "deadly": 1400},
        7: {"easy": 350, "medium": 750, "hard": 1100, "deadly": 1700},
        8: {"easy": 450, "medium": 900, "hard": 1400, "deadly": 2100},
        9: {"easy": 550, "medium": 1100, "hard": 1600, "deadly": 2400},
        10: {"easy": 600, "medium": 1200, "hard": 1900, "deadly": 2800},
        # ... continues to 20
    }
    
    # Calculate party thresholds
    level_thresh = thresholds.get(party_level, thresholds[10])
    party_thresholds = {k: v * party_size for k, v in level_thresh.items()}
    
    # Calculate monster XP
    total_xp = sum(get_monster_xp(name) for name in monster_names)
    
    # Encounter multiplier based on number of monsters
    num_monsters = len(monster_names)
    if num_monsters == 1:
        multiplier = 1
    elif num_monsters == 2:
        multiplier = 1.5
    elif num_monsters <= 6:
        multiplier = 2
    elif num_monsters <= 10:
        multiplier = 2.5
    elif num_monsters <= 14:
        multiplier = 3
    else:
        multiplier = 4
    
    adjusted_xp = int(total_xp * multiplier)
    
    # Determine difficulty
    if adjusted_xp >= party_thresholds["deadly"]:
        difficulty = "Deadly"
    elif adjusted_xp >= party_thresholds["hard"]:
        difficulty = "Hard"
    elif adjusted_xp >= party_thresholds["medium"]:
        difficulty = "Medium"
    elif adjusted_xp >= party_thresholds["easy"]:
        difficulty = "Easy"
    else:
        difficulty = "Trivial"
    
    return {
        "total_xp": total_xp,
        "adjusted_xp": adjusted_xp,
        "difficulty": difficulty,
        "party_thresholds": party_thresholds,
    }
