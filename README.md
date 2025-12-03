# AI Dungeon Master

A voice-enabled AI Dungeon Master for D&D 5e using GPT-4o and ElevenLabs TTS (with free Edge TTS fallback), designed for Discord with persistent campaign state and long-term memory.

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

### Combat
| Command | Description |
|---------|-------------|
| `/fight goblin:15:13 orc:25:14` | Start combat (name:hp:ac) |
| `/attack target:Goblin bonus:5 damage:1d8+3` | Attack a target |
| `/combatinfo` | View turn order and HP |
| `/nextturn` | Advance to next combatant |
| `/endcombat` | End combat encounter |

### Campaign Memory
| Command | Description |
|---------|-------------|
| `/status` | View party and campaign info |
| `/recap` | AI summary of recent events |
| `/context` | See what the AI remembers |
| `/summarize` | Save events to long-term memory |
| `/remember note/npc/quest` | Manually add to memory |

### Settings
| Command | Description |
|---------|-------------|
| `/voice true/false` | Toggle TTS on/off |
| `/turns free/strict` | Toggle free-form vs turn order |
| `/leave` | Disconnect from voice |
| `/help` | Show all commands |
| `/exportlog` | Export session log |

---

## � Voice Options (TTS)

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

## 🎲 Skill Checks & Roll Flow

The AI follows D&D 5e rules for skill checks:

1. You describe an action with `/do I try to pick the lock`
2. AI asks for a roll: *"Make a Dexterity (Sleight of Hand) check, DC 15"*
3. Use `/roll sleight_of_hand` - the bot auto-applies your modifiers
4. AI narrates the outcome based on success/failure

**Supported Skills:** All 18 D&D 5e skills with proper ability score modifiers
**Difficulty Classes:** Very Easy (5) to Nearly Impossible (30)
**Special:** Natural 20s and 1s are highlighted with critical effects

---

## ⚔️ Combat System

Start combat with `/fight goblin:15:13 orc:25:14` (name:hp:ac format)

- **Initiative** is rolled automatically using DEX modifiers
- **Turn order** shows current combatant with HP/AC
- **Attacks** use `/attack target:Goblin bonus:5 damage:1d8+3`
- **Critical hits** (nat 20) deal double damage dice
- **Combat mode** enforces strict turn order until `/endcombat`

---

## 🌐 Web Portal

Access `http://localhost:5000/portal/` when the Flask app is running:

- **Character List** - View all characters with class/race/level
- **Character Creation** - Full form with dice roller and standard array buttons
- **Character Editor** - Edit stats, inventory, and proficiencies
- **Campaign View** - See memory, NPCs, quests, and key events
- **DM Dashboard** - Overview of all active campaigns

---

## 🗃️ State Persistence

- Game state is saved per Discord channel in `state/` as JSON
- Character data is saved per Discord user ID in `characters/`
- Combat encounters are saved in `combat/`
- Session logs are saved in `logs/` as Markdown

---

## 📁 Project Structure
```
ai-dm-voice/
├── app.py                 # Flask REST API & web portal
├── discord_bot.py         # Main Discord bot (24 commands)
├── config.py              # Configuration management
├── services/
│   ├── openai_service.py  # GPT-4o + skill check detection + memory
│   └── elevenlabs_service.py  # TTS with Edge fallback
├── utils/
│   ├── character_manager.py   # D&D 5e character sheets
│   ├── combat_manager.py      # Initiative, attacks, HP tracking
│   ├── dice_roller.py         # Dice notation parser
│   ├── state_manager.py       # Campaign state + memory system
│   ├── voice_map.py           # Voice ID mapping
│   ├── voice_parser.py        # Voice tag extraction + TTS cleanup
│   └── prompt_builder.py      # Dynamic system prompts
├── webportal/
│   ├── routes.py              # Flask routes
│   └── templates/             # HTML templates
├── state/                 # Game state (per channel)
├── characters/            # Player character data
├── combat/                # Combat encounter data
├── logs/                  # Session transcripts
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
