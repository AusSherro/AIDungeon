# AI Dungeon Master

A voice-enabled AI Dungeon Master for D&D 5e using GPT-4o and ElevenLabs TTS (with free Edge TTS fallback), designed for Discord with persistent campaign state, long-term memory, and comprehensive D&D 5e mechanics.

---

## 🚀 Quick Start

1. **Clone the repo:**
   ```bash
   git clone https://github.com/AusSherro/AIDungeon.git
   cd AIDungeon/ai-dm-voice
   ```
2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Copy and edit `.env`:**
   ```powershell
   copy .env.example .env
   # Edit .env and add your API keys
   ```
4. **Run the Flask API and web portal:**
   ```powershell
   python app.py
   ```
   Visit `http://localhost:5000/portal/` in your browser to view the character portal.
5. **Run the Discord bot:**
   ```powershell
   python discord_bot.py
   ```

---

## 🎮 Discord Commands

### Getting Started
| Command | Description |
|---------|-------------|
| `/character name:Gandalf char_class:Wizard race:Human` | Create your character |
| `/stats strength:14 dexterity:16 ...` | Set ability scores |
| `/campaign [theme]` | Start a new adventure (join voice first!) |

### During Play
| Command | Description |
|---------|-------------|
| `/do <action>` | Describe what your character does |
| `/say <speech>` | Speak in character |
| `/roll <dice or skill>` | Roll dice (1d20, 2d6+3) or skill checks (athletics, stealth) |
| `/done` | End your turn |

### Character Management
| Command | Description |
|---------|-------------|
| `/character` | View your character sheet |
| `/stats` | Set ability scores |
| `/hp damage:5` or `/hp heal:10` | Manage HP |
| `/inventory [add/remove]` | Manage inventory |
| `/rest short/long` | Take a rest |
| `/deathsave` | Roll death saving throw |
| `/levelup` | Level up your character |
| `/xp [amount]` | View or award XP |

### Party & XP
| Command | Description |
|---------|-------------|
| `/party` | View party dashboard (HP, AC, conditions, spell slots) |
| `/xp` | View your XP progress and level |
| `/awardparty xp:500` | Award XP to all party members |

### Spellcasting
| Command | Description |
|---------|-------------|
| `/spells` | View known spells and spell slots |
| `/cast <spell> [slot_level]` | Cast a spell (uses spell slot) |
| `/prepare <spell>` | Prepare a spell for casting |
| `/learn <spell>` | Learn a new spell |

### Equipment
| Command | Description |
|---------|-------------|
| `/equip <item>` | Equip a weapon, armor, or shield |
| `/unequip <slot>` | Unequip from weapon/armor/shield slot |
| `/gear` | View equipped items and AC |

### Combat
| Command | Description |
|---------|-------------|
| `/fight goblin*3 orc` | Start combat with monsters from database |
| `/fight goblin:15:13 orc:25:14` | Start combat (name:hp:ac for custom) |
| `/attack target:Goblin bonus:5 damage:1d8+3` | Attack a target |
| `/combatinfo` | View turn order and HP |
| `/nextturn` | Advance to next combatant |
| `/reaction` | Use your reaction (Shield, Counterspell, etc.) |
| `/endcombat` | End combat (auto-awards XP and generates loot!) |

### Loot & Treasure
| Command | Description |
|---------|-------------|
| `/loot [cr]` | Generate random loot by CR |
| `/treasure cr:5` | Generate a full treasure hoard |

### Campaign Memory
| Command | Description |
|---------|-------------|
| `/status` | View party and campaign info |
| `/recap` | AI summary of recent events |
| `/context` | See what the AI remembers |
| `/summarize` | Save events to long-term memory |
| `/remember note/npc/quest` | Manually add to memory |

### Ambient & Sound
| Command | Description |
|---------|-------------|
| `/ambient [mood]` | Set ambient music mood (combat, tavern, dungeon, etc.) |
| `/sfx [effect]` | Play sound effect (sword, spell, explosion, etc.) |

### Settings
| Command | Description |
|---------|-------------|
| `/voice true/false` | Toggle TTS on/off |
| `/turns free/strict` | Toggle free-form vs turn order |
| `/leave` | Disconnect from voice |
| `/help` | Show all commands |
| `/exportlog` | Export session log |

### Tactical Maps
| Command | Description |
|---------|-------------|
| `/newmap` | Create a new battle map (dungeon, forest, tavern, cave) |
| `/map` | View the current tactical map |
| `/addtoken` | Add a character/enemy token to the map |
| `/movetoken` | Move a token to a new position |
| `/removetoken` | Remove a token from the map |
| `/distance` | Measure distance between two tokens |
| `/inrange` | Find all tokens within range |
| `/setterrain` | Set terrain at a position |
| `/clearmap` | Delete the current map |

### Handouts & Secrets
| Command | Description |
|---------|-------------|
| `/handout` | Create a handout (note, letter, map, etc.) |
| `/secret` | Send a secret message to one player |
| `/viewhandouts` | View handouts shared with you |
| `/readhandout` | Read a specific handout |
| `/mysecrets` | View secret messages for you |
| `/dmhandouts` | [DM] View all campaign handouts |
| `/revealhandout` | [DM] Reveal handout to all |
| `/sharehandout` | [DM] Share with specific player |

---

## ⚔️ Reaction System

Combat reactions are tracked and can be used strategically:

| Reaction | Trigger | Effect |
|----------|---------|--------|
| **Opportunity Attack** | Enemy leaves your reach | Free melee attack |
| **Shield** | When hit by attack | +5 AC until next turn |
| **Counterspell** | Enemy casts a spell | Attempt to counter |
| **Uncanny Dodge** | When hit by attack | Half damage (Rogue 5+) |
| **Sentinel** | Enemy attacks ally | Free attack on attacker |

Reactions reset at the start of your turn. Use `/reaction` to trigger manually.

---

## 💰 Loot & Treasure System

Automatic loot generation when combat ends:

### Loot by CR
- **CR 0-4**: Mundane items, coins, minor gems
- **CR 5-10**: Uncommon magic items, art objects, more gold
- **CR 11-16**: Rare magic items, jewelry, significant treasure
- **CR 17+**: Very rare/legendary items, hoards

### Treasure Hoards
Use `/treasure cr:X` to generate full hoards with:
- Gold, silver, copper, platinum coins
- Gems (10gp to 5000gp value)
- Art objects (25gp to 7500gp value)
- Magic items by rarity

### Magic Item Rarities
| Rarity | Typical CR | Examples |
|--------|------------|----------|
| Common | 1-4 | Potion of Healing, +1 Ammunition |
| Uncommon | 5-10 | Bag of Holding, Cloak of Protection |
| Rare | 11-16 | +2 Weapons, Flame Tongue |
| Very Rare | 17+ | +3 Weapons, Staff of Power |
| Legendary | 20+ | Vorpal Sword, Holy Avenger |

---

## 📊 Experience & Leveling

Automatic XP tracking with level-up notifications:

### XP Awards
- **Combat**: Auto-calculated from defeated enemies when combat ends
- **Party Distribution**: XP split evenly among all players
- **Milestone**: Use `/awardparty` for story milestone rewards

### Level Thresholds (D&D 5e)
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

The `/xp` command shows a visual progress bar toward your next level!

---

## 🎲 D&D 5e Data System

The bot includes comprehensive D&D 5e SRD data for authentic gameplay:

### Classes (12)
All PHB classes with full progression tables:
- Barbarian, Bard, Cleric, Druid, Fighter, Monk
- Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard

Each class includes: hit dice, saving throws, proficiencies, spell slots, and features by level.

### Races (9)
- Dwarf (Hill/Mountain), Elf (High/Wood/Dark), Halfling (Lightfoot/Stout)
- Human, Dragonborn, Gnome (Forest/Rock), Half-Elf, Half-Orc, Tiefling

Each race includes: ability bonuses, traits, speed, languages, and proficiencies.

### Spells (100+)
Full spell database organized by class and level:
- Cantrips through 9th level
- School, casting time, range, components, duration
- Ritual and concentration tags

### Equipment
**37 Weapons** with full stats:
- Simple/Martial, Melee/Ranged
- Damage dice, damage types, properties (finesse, heavy, two-handed, etc.)

**13 Armor Types:**
- Light (Leather, Studded), Medium (Chain Shirt, Breastplate), Heavy (Chain Mail, Plate)
- AC calculations, DEX caps, stealth disadvantage, strength requirements

### Feats (40)
Popular feats with full effects:
- Great Weapon Master, Sharpshooter, Sentinel, Polearm Master
- Lucky, Alert, Mobile, War Caster, and more
- Prerequisite checking included

### Conditions (16)
All conditions with mechanical effects:
- Blinded, Charmed, Frightened, Grappled, Incapacitated
- Invisible, Paralyzed, Petrified, Poisoned, Prone
- Restrained, Stunned, Unconscious, Exhaustion (6 levels)

### Monsters (15+)
Pre-built statblocks for quick encounters:
- **CR 1/8-1/4:** Kobold, Goblin, Skeleton, Zombie
- **CR 1/2:** Orc, Hobgoblin
- **CR 1:** Bugbear, Dire Wolf, Ghoul, Goblin Boss
- **CR 2-5:** Ogre, Werewolf, Troll, Orc War Chief
- **CR 8:** Young Green Dragon

Each includes: AC, HP, stats, actions, traits, legendary actions (where applicable).

---

## �️ Tactical Maps

Grid-based battle maps for tactical combat positioning:

### Map Templates
- **Dungeon Room** - Walled room with door
- **Forest Clearing** - Trees and bushes around edges
- **Tavern** - Bar counter, tables, stairs
- **Cave** - Irregular walls with rubble and pits

### Terrain Types
| Symbol | Terrain | Effect |
|--------|---------|--------|
| `.` | Floor | Normal movement |
| `#` | Wall | Impassable |
| `~` | Water | Difficult terrain |
| `:` | Difficult | Half movement |
| `+` | Door | Passable |
| `X` | Locked Door | Impassable until unlocked |
| `O` | Pillar | Impassable, half cover |
| `T` | Tree | Impassable, half cover |
| `^` | Rubble | Difficult, half cover |

### Token Types
- 🔵 **Player** - Player characters
- 🔴 **Enemy** - Hostile creatures
- 🟢 **NPC** - Non-player characters
- 🟣 **Boss** - Boss monsters
- ⬜ **Object** - Items and objects

---

## 📜 Handouts & Secrets

Share information with players during the game:

### Handout Types
- 📝 Note, ✉️ Letter, 🗺️ Map, 🖼️ Image
- 📦 Item Description, 📚 Lore, 🔍 Clue, 📖 Journal Entry

### Features
- **Public Handouts** - Visible to all players
- **Private Handouts** - Shared with specific players only
- **Secrets** - DM can send hidden messages to individual players
- **Image Support** - Attach image URLs to handouts

---

## �🔊 Voice Options (TTS)

The bot supports multiple TTS providers to fit your needs:

| Provider | Cost | Quality | Setup |
|----------|------|---------|-------|
| **ElevenLabs** | Paid (10k chars/mo free) | ⭐⭐⭐⭐⭐ Excellent | Set `ELEVENLABS_API_KEY` in `.env` |
| **Edge TTS** | Free | ⭐⭐⭐⭐ Good | Auto-fallback, no setup needed |
| **Disabled** | N/A | N/A | Set `TTS_PROVIDER=disabled` |

**Configuration in `.env`:**
```bash
TTS_PROVIDER=elevenlabs  # Options: elevenlabs, edge, disabled
```

**Per-channel toggle:** Use `/voice false` to disable voice for a channel (saves credits!)
### NPC Voice Variety

The AI automatically assigns unique voices to different NPCs based on their characteristics:

| Archetype | Voice Style | Examples |
|-----------|-------------|----------|
| **Elderly Wizard** | Wise, gravelly | Gandalf, Mordenkainen |
| **Gruff Dwarf** | Deep, Scottish accent | Tavern keepers, smiths |
| **Mysterious Elf** | Ethereal, melodic | Elven lords, seers |
| **Menacing Villain** | Dark, sinister | Liches, dark lords |
| **Cheerful Halfling** | Friendly, warm | Merchants, innkeepers |
| **Noble Knight** | Commanding, regal | Kings, paladins |

Voices are selected based on race, role, and personality tags in the AI response.

### Ambient Music & SFX

Set the mood with ambient soundscapes:

| Mood | Description |
|------|-------------|
| `combat` | Tense battle music |
| `exploration` | Adventurous wandering |
| `tavern` | Cozy inn atmosphere |
| `dungeon` | Dark, foreboding |
| `mystery` | Suspenseful intrigue |
| `victory` | Triumphant celebration |
| `danger` | Ominous warning |
| `peaceful` | Calm rest scenes |

Sound effects: `sword`, `spell`, `explosion`, `door`, `coins`, `monster`, `heal`, `critical`
---

## 🧠 Campaign Memory System

The AI remembers your adventure through a layered memory system:

1. **Recent History** - Last 10 conversation exchanges (rolling window)
2. **Campaign Summary** - AI-generated summary of major events (long-term)
3. **Key NPCs** - Important characters with descriptions and status
4. **Quests** - Active and completed objectives
5. **Key Events** - Major plot points and discoveries

### Managing Memory
- Use `/context` to see what the AI currently remembers
- Use `/summarize` to save recent events to long-term memory (do this periodically!)
- Use `/remember` to manually add notes, NPCs, or quests
- The AI automatically extracts NPCs and quests when you summarize

---

## ⚔️ Combat System

### Starting Combat
```
/fight goblin*3 orc      # 3 goblins + 1 orc from monster database
/fight custom:20:15      # Custom enemy with 20 HP, 15 AC
```

### Combat Features
- **Auto-Initiative** using DEX modifiers
- **Monster Statblocks** with full actions and traits
- **Legendary Actions** for boss monsters (resets each round)
- **Legendary Resistance** to auto-succeed saves
- **Lair Actions** at initiative count 20
- **Damage Types** with resistance/immunity/vulnerability
- **Regeneration** (blocked by fire/acid)
- **Readied Actions** with trigger conditions
- **Delayed Turns** for tactical positioning

### Combat Commands
```
/attack target:Goblin bonus:5 damage:1d8+3
/cast fireball slot:3           # AoE spell
/combatinfo                      # View turn order
/nextturn                        # Next combatant
```

---

## 🛏️ Rest Mechanics

### Short Rest
- Spend Hit Dice to heal (roll + CON modifier)
- **Warlock:** Pact Magic slots restored
- **Fighter:** Second Wind restored
- **Monk:** All Ki points restored
- **Cleric/Paladin:** Channel Divinity restored

### Long Rest
- Full HP restored
- All spell slots restored
- Half hit dice regained (minimum 1)
- Exhaustion reduced by 1 level
- Class resources restored (Rage, Ki, Bardic Inspiration, etc.)

---

## 🌐 Web Portal

Access `http://localhost:5000/portal/` when the Flask app is running:

- **Character List** - View all characters with class/race/level
- **Character Sheet** - Full sheet with stats, equipment, spells
- **Spell Management** - Learn, prepare, and manage spells
- **Sync Button** - Update character with class/level data
- **Campaign View** - See memory, NPCs, quests, and key events
- **DM Dashboard** - Overview of all active campaigns

---

## 🗃️ State Persistence

Data can be stored in two formats:

### JSON Files (Default)
- Game state saved per Discord channel in `state/`
- Character data saved per user ID in `characters/`
- Combat encounters in `combat/`
- Handouts in `handouts/`
- Maps in `maps/`
- Session logs in `logs/`

### SQLite Database (Optional)
- All data in `data/aidm.db`
- Better querying and relationships
- Run migration: `python -c "from utils.database import migrate_json_to_db; migrate_json_to_db()"`

---

## 📁 Project Structure
```
ai-dm-voice/
├── app.py                 # Flask REST API & web portal
├── discord_bot.py         # Main Discord bot (40+ commands)
├── config.py              # Configuration management
├── services/
│   ├── openai_service.py  # GPT-4o + skill check detection + memory
│   └── elevenlabs_service.py  # TTS with Edge fallback
├── utils/
│   ├── character_manager.py   # D&D 5e character sheets + equipment
│   ├── combat_manager.py      # Initiative, attacks, legendary actions
│   ├── dice_roller.py         # Dice notation parser
│   ├── state_manager.py       # Campaign state + memory system
│   ├── dnd5e_data.py          # Full D&D 5e SRD data
│   ├── handout_manager.py     # Handouts and secrets
│   ├── map_manager.py         # Tactical battle maps
│   ├── database.py            # SQLite storage layer
│   ├── voice_map.py           # Voice ID mapping + NPC voice archetypes
│   ├── voice_parser.py        # Voice tag extraction + TTS cleanup
│   ├── xp_manager.py          # XP tracking + auto-leveling
│   ├── loot_manager.py        # Treasure tables + loot generation
│   ├── reaction_manager.py    # Combat reactions (Shield, AoO, etc.)
│   └── ambient_manager.py     # Ambient music + sound effects
├── webportal/
│   ├── routes.py              # Flask routes
│   └── templates/             # HTML templates
├── state/                 # Campaign state (JSON)
├── characters/            # Player characters (JSON)
├── combat/                # Combat encounters
├── handouts/              # Handouts and secrets
├── maps/                  # Tactical maps
├── logs/                  # Session transcripts
├── data/                  # SQLite database
├── .env.example           # Environment template
└── requirements.txt       # Dependencies
```

---

## 🔒 Security
- Never commit your real `.env` file or API keys.
- The web portal is for local use - don't expose to the internet without auth!

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
