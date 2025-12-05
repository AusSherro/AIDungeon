# AI Dungeon Master - Playthrough Guide

> A complete guide to running D&D 5e sessions with the AI Dungeon Master bot.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Setting Up a Campaign](#setting-up-a-campaign)
3. [Creating Characters](#creating-characters)
4. [Gameplay Commands](#gameplay-commands)
5. [Combat System](#combat-system)
6. [Combat Reactions](#combat-reactions)
7. [XP & Leveling](#xp--leveling)
8. [Loot & Treasure](#loot--treasure)
9. [Spellcasting](#spellcasting)
10. [Rest & Recovery](#rest--recovery)
11. [DM Tools](#dm-tools)
12. [Tactical Maps](#tactical-maps)
13. [Player Handouts](#player-handouts)
14. [Voice & Ambient](#voice--ambient)
15. [Example Session](#example-session)

---

## Quick Start

1. **Invite the bot** to your Discord server
2. **Join a voice channel** (optional, for TTS narration)
3. Run `/campaign` to start a new adventure
4. Create your character with `/character`
5. Use `/do` to take actions!

---

## Setting Up a Campaign

### Starting a New Campaign
```
/campaign
```
The AI generates a unique campaign intro with setting, hook, and starting location.

### Viewing Campaign Context
```
/context
```
Shows the current campaign summary, active NPCs, and quests.

### Getting a Recap
```
/recap
```
Summarizes recent events - great for starting a new session.

### Remembering Important Info
```
/remember <info>
```
Example: `/remember The innkeeper mentioned a secret passage behind the fireplace`

---

## Creating Characters

### Register a New Character
```
/character <name> <race> <class>
```
Example: `/character Thorin Dwarf Fighter`

**Available Races:** Human, Elf, Dwarf, Halfling, Gnome, Half-Elf, Half-Orc, Tiefling, Dragonborn

**Available Classes:** Fighter, Wizard, Rogue, Cleric, Ranger, Barbarian, Bard, Druid, Monk, Paladin, Sorcerer, Warlock

### View Character Sheet
```
/stats
```
Shows full character sheet with abilities, skills, HP, and equipment.

### Set Ability Scores
```
/stats set <ability> <value>
```
Example: `/stats set strength 16`

### Level Up
```
/levelup
```
Increases your level and adjusts HP and proficiency bonus.

---

## Gameplay Commands

### Take an Action
```
/do <action>
```
Example: `/do I search the room for hidden doors`

The AI DM narrates the result and may ask for skill checks.

### Say Something (In Character)
```
/say <dialogue>
```
Example: `/say "Greetings, traveler. What news from the north?"`

### Roll Dice
```
/roll <dice>
```
Examples:
- `/roll d20` - Standard d20 roll
- `/roll 2d6+3` - Two d6 plus 3
- `/roll d20+5 advantage` - Roll with advantage
- `/roll 4d6kh3` - Roll 4d6, keep highest 3

### Check Turn Order
```
/turns
```
Shows whose turn it is in the current scene.

### End Your Turn
```
/done
```
Passes to the next player in turn order.

---

## Combat System

### Start Combat
```
/fight <enemies>
```
Example: `/fight 3 goblins and an orc warchief`

This rolls initiative for everyone and starts turn tracking.

### View Combat Status
```
/combatinfo
```
Shows all combatants with HP, AC, conditions, and initiative order.

### Attack an Enemy
```
/attack <target>
```
Example: `/attack goblin1`

Rolls to hit and damage automatically based on your equipped weapon.

### Advance to Next Turn
```
/nextturn
```
Moves to the next combatant in initiative order.

### End Combat
```
/endcombat
```
Ends the encounter, automatically awards XP to the party, and generates loot from defeated enemies.

---

## Combat Reactions

Reactions are special actions you can take on other creatures' turns. You get one reaction per round, which resets at the start of your turn.

### Using Reactions
```
/reaction <type> [target]
```

### Available Reactions

| Reaction | Trigger | Effect |
|----------|---------|--------|
| `opportunity_attack` | Enemy leaves your reach | Free melee attack |
| `shield` | When hit by attack | +5 AC until next turn (uses spell slot) |
| `counterspell` | Enemy casts spell within 60ft | Interrupt the spell (uses spell slot) |
| `uncanny_dodge` | When hit by attack you can see | Halve the damage (Rogue 5+) |
| `absorb_elements` | Take elemental damage | Resistance + bonus damage on next hit |
| `hellish_rebuke` | Take damage from creature | 2d10 fire damage to attacker |
| `cutting_words` | Enemy makes roll | Subtract Bardic Inspiration (Bard) |
| `deflect_missiles` | Hit by ranged attack | Reduce damage (Monk) |

### Examples
```
/reaction shield                    # Cast Shield when hit
/reaction counterspell 5            # Counter a 5th-level spell
/reaction uncanny_dodge 24          # Halve 24 damage to 12
/reaction opportunity_attack Goblin # Attack fleeing enemy
```

---

## XP & Leveling

Experience points are tracked automatically and award level-ups when thresholds are reached.

### View Your XP
```
/xp
```
Shows your current XP, level, and a progress bar to next level.

### Award XP to Party (DM)
```
/awardparty <amount>
```
Example: `/awardparty 500` - Awards 500 XP split among all party members.

### Automatic XP Awards
When combat ends with `/endcombat`, XP is automatically calculated from defeated enemies and distributed to the party.

### XP Thresholds

| Level | XP Required | Level | XP Required |
|-------|-------------|-------|-------------|
| 1 | 0 | 11 | 85,000 |
| 2 | 300 | 12 | 100,000 |
| 3 | 900 | 13 | 120,000 |
| 4 | 2,700 | 14 | 140,000 |
| 5 | 6,500 | 15 | 165,000 |
| 6 | 14,000 | 16 | 195,000 |
| 7 | 23,000 | 17 | 225,000 |
| 8 | 34,000 | 18 | 265,000 |
| 9 | 48,000 | 19 | 305,000 |
| 10 | 64,000 | 20 | 355,000 |

### Leveling Up
```
/levelup
```
When you have enough XP, use this command to increase your level and gain new features.

---

## Loot & Treasure

Generate treasure hoards and magic items based on Challenge Rating.

### Generate Random Loot
```
/loot [cr]
```
Example: `/loot 5` - Generate loot appropriate for CR 5 encounter.

### Generate Treasure Hoard
```
/treasure cr:<cr>
```
Example: `/treasure cr:10` - Generate a full treasure hoard.

### Loot Tiers

| CR Range | Typical Loot |
|----------|--------------|
| 0-4 | Coins, minor gems, mundane items |
| 5-10 | Uncommon magic items, art objects |
| 11-16 | Rare magic items, jewelry |
| 17+ | Very rare/legendary items |

### Automatic Loot
When combat ends, loot is automatically generated from the most powerful defeated enemy.

---

## Spellcasting

### Learn a Spell
```
/learn <spell_name>
```
Example: `/learn fireball`

### Learn a Cantrip
```
/learn cantrip <cantrip_name>
```
Example: `/learn cantrip fire bolt`

### Prepare Spells (for prepared casters)
```
/prepare <spell_name>
```
Example: `/prepare cure wounds`

### Cast a Spell
```
/cast <spell_name> [target]
```
Examples:
- `/cast magic missile goblin1`
- `/cast fireball` (area spell)
- `/cast cure wounds Thorin`

### View Your Spells
```
/spells
```
Shows known spells, prepared spells, and remaining spell slots.

### Check Spell Slots
```
/status
```
Shows current HP, conditions, and spell slot usage.

---

## Rest & Recovery

### Short Rest (1 hour)
```
/rest short
```
- Spend Hit Dice to heal
- Warlocks recover spell slots
- Fighters recover some abilities

### Long Rest (8 hours)
```
/rest long
```
- Recover all HP
- Recover all spell slots
- Recover half your Hit Dice
- Remove exhaustion levels

---

## DM Tools

### Manage HP
```
/hp damage <amount> [target]
/hp heal <amount> [target]
/hp set <amount> [target]
```
Examples:
- `/hp damage 15` - Take 15 damage
- `/hp heal 10 Thorin` - Heal Thorin for 10
- `/hp set 50` - Set your HP to 50

### Death Saves
```
/deathsave
```
When at 0 HP, roll a death saving throw. Three successes = stabilize, three failures = death.

### Inventory Management
```
/inventory add <item>
/inventory remove <item>
/inventory list
```
Examples:
- `/inventory add rope 50ft`
- `/inventory remove torch`

---

## Tactical Maps

### Create a New Map
```
/newmap <name> <width> <height> [template]
```
Examples:
- `/newmap tavern_brawl 10 10`
- `/newmap forest_ambush 15 12 forest`
- `/newmap dungeon_room 8 8 dungeon`

**Templates:** `dungeon`, `forest`, `tavern`, `cave`

### View the Map
```
/map
```
Displays the ASCII tactical map with all tokens.

### Add Tokens
```
/addtoken <name> <x> <y> [symbol] [color]
```
Examples:
- `/addtoken Thorin 3 5 T blue` - Player token
- `/addtoken Goblin1 7 5 G red` - Enemy token
- `/addtoken Chest 5 8 $ yellow` - Object

### Move Tokens
```
/movetoken <name> <x> <y>
```
Example: `/movetoken Thorin 5 6`

### Remove Tokens
```
/removetoken <name>
```

### Set Terrain
```
/setterrain <x> <y> <terrain_type>
```
**Terrain Types:** `floor`, `wall`, `water`, `difficult`, `pit`, `door`, `stairs`, `altar`, `tree`, `bush`, `rock`, `fire`, `ice`, `lava`, `magic`

### Check Distance
```
/distance <token1> <token2>
```
Example: `/distance Thorin Goblin1`
Returns distance in feet (5ft per square).

### Check Range
```
/inrange <token> <range_feet>
```
Example: `/inrange Thorin 30`
Shows all tokens within 30 feet.

### Clear the Map
```
/clearmap
```
Deletes the current tactical map.

---

## Player Handouts

### Create a Handout (DM)
```
/handout <title> <content> [type] [visible_to]
```
Examples:
- `/handout "Mysterious Letter" "Meet me at midnight..." letter`
- `/handout "Dungeon Map" "Shows a winding passage..." map @Player1`

**Handout Types:** `note`, `letter`, `map`, `image`, `item`, `lore`, `clue`, `journal`, `wanted`, `secret`

### Create a Secret (DM)
```
/secret <player> <title> <content>
```
Example: `/secret @Rogue "Hidden Knowledge" "You notice the merchant is lying..."`

Only that player can see their secrets.

### View Your Handouts
```
/viewhandouts
```
Shows all handouts shared with you.

### Read a Handout
```
/readhandout <handout_id>
```

### Check Your Secrets
```
/mysecrets
```
Shows secrets only you can see.

### DM: View All Handouts
```
/dmhandouts
```

### DM: Reveal a Handout
```
/revealhandout <handout_id>
```
Makes a hidden handout visible to everyone.

### DM: Share with Player
```
/sharehandout <handout_id> <player>
```

---

## Voice & Ambient

### Join Voice Channel
```
/voice
```
Bot joins your current voice channel for TTS narration.

### Leave Voice Channel
```
/leave
```
Bot disconnects from voice.

### Set Ambient Mood
```
/ambient <mood>
```
**Available Moods:**
- `calm` - Peaceful, relaxing atmosphere
- `tense` - Building suspense
- `combat` - Battle music
- `mystery` - Intrigue and investigation
- `celebration` - Victory and revelry
- `horror` - Dark and foreboding
- `travel` - Journey and exploration
- `dungeon` - Underground adventure

Example: `/ambient combat` - Set battle music when combat starts.

### Play Sound Effects
```
/sfx <effect>
```
**Available Effects:**
- `sword` - Sword clash
- `spell` - Magic casting
- `explosion` - Boom!
- `door` - Door opening/closing
- `coins` - Jingling coins
- `monster` - Creature roar
- `heal` - Healing magic
- `critical` - Critical hit flourish

### NPC Voice Variety
The AI automatically assigns unique voices to different NPCs:
- Elderly wizards get wise, gravelly voices
- Dwarves get deep, gruff voices
- Elves get ethereal, melodic voices
- Villains get dark, sinister voices

### Export Session Log
```
/exportlog
```
Downloads a markdown file of the entire session.

---

## Example Session

Here's a complete example of starting and playing a session:

### 1. Start the Campaign
```
DM: /campaign
Bot: 🎭 Welcome to "The Shattered Crown"...
     You find yourselves in the bustling port city of Saltmarsh...
```

### 2. Create Characters
```
Player1: /character Thorin Dwarf Fighter
Bot: ✅ Thorin the Dwarf Fighter has joined the adventure!

Player2: /character Elara Elf Wizard  
Bot: ✅ Elara the Elf Wizard has joined the adventure!
```

### 3. Set Up Stats
```
Player1: /stats set strength 16
Player1: /stats set constitution 14

Player2: /stats set intelligence 17
Player2: /learn magic missile
Player2: /learn cantrip fire bolt
```

### 4. Roleplay
```
Player1: /do I approach the barkeep and order an ale
Bot: 🎲 The grizzled barkeep slides a foaming mug across the counter...
     "Three copper, stranger. You're not from around here, are ye?"

Player1: /say "Just passing through. Heard there's work for adventurers."
Bot: The barkeep leans in conspiratorially...
     "Aye, there's been trouble at the old lighthouse..."
```

### 5. Combat Encounter
```
DM: /fight 2 bandits
Bot: ⚔️ COMBAT BEGINS!
     Initiative Order:
     1. Elara (18)
     2. Bandit 1 (15)
     3. Thorin (12)
     4. Bandit 2 (8)

Player2: /cast fire bolt bandit1
Bot: 🔥 Elara hurls a bolt of fire! (Attack: 17 vs AC 12 - HIT!)
     Damage: 8 fire damage! Bandit 1 staggers back, singed.

Bot: Bandit 1's turn... (AI narrates enemy action)

Player1: /attack bandit1
Bot: ⚔️ Thorin swings his battleaxe! (Attack: 21 vs AC 12 - HIT!)
     Damage: 11 slashing! Bandit 1 falls!
```

### 6. Using Maps
```
DM: /newmap lighthouse_fight 10 8 dungeon
DM: /addtoken Thorin 2 4 T blue
DM: /addtoken Elara 2 5 E green
DM: /addtoken Bandit1 7 3 B red
DM: /addtoken Bandit2 7 5 B red

Player1: /map
Bot: 
    0 1 2 3 4 5 6 7 8 9
  ┌─────────────────────┐
0 │ # # # # # # # # # # │
1 │ # . . . . . . . . # │
2 │ # . . . . . . . . # │
3 │ # . . . . . . B . # │
4 │ # . T . . . . . . # │
5 │ # . E . . . . B . # │
6 │ # . . . . . . . . # │
7 │ # # # # # # # # # # │
  └─────────────────────┘

Player1: /distance Thorin Bandit1
Bot: 📏 Distance: 25 feet (5 squares)
```

### 7. Rest and Recovery
```
Player1: /rest short
Bot: ⏰ Thorin takes a short rest (1 hour)
     Spent 1 Hit Die: Recovered 9 HP
     Current HP: 28/30

Player2: /rest long
Bot: 🌙 Elara takes a long rest (8 hours)
     HP fully restored: 18/18
     Spell slots restored: 1st: 2/2
```

### 8. Handouts
```
DM: /handout "Torn Page" "...the artifact lies beneath the old well..." clue @Player1
Bot: 📜 Handout created! Shared with Thorin.

Player1: /viewhandouts
Bot: 📚 Your Handouts:
     1. 📎 "Torn Page" (clue) - UNREAD
     
Player1: /readhandout 1
Bot: 📜 TORN PAGE (Clue)
     "...the artifact lies beneath the old well..."
```

---

## Tips for Great Sessions

1. **Be descriptive** - The AI responds better to detailed actions
2. **Stay in character** - Use `/say` for dialogue, `/do` for actions  
3. **Use the map** - Tactical positioning makes combat more strategic
4. **Take rests** - Manage resources like spell slots and HP
5. **Check context** - Use `/recap` if you forget what's happening
6. **Export logs** - Save memorable sessions with `/exportlog`

---

## Command Quick Reference

| Command | Description |
|---------|-------------|
| `/campaign` | Start new campaign |
| `/character` | Create character |
| `/do` | Take an action |
| `/say` | Speak in character |
| `/roll` | Roll dice |
| `/fight` | Start combat |
| `/attack` | Attack target |
| `/reaction` | Use reaction (Shield, Counterspell, etc.) |
| `/cast` | Cast a spell |
| `/rest` | Short/long rest |
| `/xp` | View XP progress |
| `/party` | View party dashboard |
| `/loot` | Generate loot |
| `/treasure` | Generate treasure hoard |
| `/map` | View tactical map |
| `/handout` | Create handout |
| `/ambient` | Set ambient mood |
| `/sfx` | Play sound effect |
| `/help` | Show all commands |

---

*Happy adventuring! May your rolls be high and your stories legendary.* 🎲⚔️🐉
