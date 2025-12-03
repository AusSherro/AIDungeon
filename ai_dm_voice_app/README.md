# ai_dm_voice_app

A modular, voice-enabled AI Dungeon Master using GPT-4o and ElevenLabs, with Discord support and persistent campaign state.

---

## 🚀 Quick Start

1. **Clone the repo and enter the folder:**
   ```powershell
   git clone <repo-url>
   cd ai-dm-voice/ai_dm_voice_app
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

## 🧪 Example Usage

### Flask API

**Sample curl:**
```bash
curl -X POST http://localhost:5000/dm -H "Content-Type: application/json" -d '{"input": "The party enters the tavern."}' --output response.mp3
```

#### `/api/generate`

Use this endpoint when you only need the raw text from the AI without TTS.
The body accepts a JSON payload with:

* `prompt` - the player's input or narration seed
* `action_type` - how to treat the prompt (`do`, `say`, `story`, `continue`)
    * `do` - describe a player action
    * `say` - lines of in-character speech
    * `story` - force narrative exposition
    * `continue` - keep narrating from the last response
* `genre` *(optional)* - e.g. `sci-fi`, `horror`, `fantasy`
* `context` *(optional)* - array of prior messages for additional history

**Sample curl:**
```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
        "prompt": "Open the ancient door",
        "action_type": "do",
        "genre": "fantasy",
        "context": ["The hallway is dark and cold."]
      }'
```
The response contains JSON with a `text` field describing the next part of the story.

### Discord
- Invite your bot to your server.
- Use `/new_campaign [prompt]` in a voice channel to start a campaign and set turn order.
- The bot will announce the first player and prompt them to act.
- The current player uses `/act <action>` to take their turn (AI narrates and speaks as before).
- Narration now ends with 2-3 suggested actions to keep the story moving.
- When finished, the player uses `/end_turn` to pass to the next player (announced in text and voice).
- If you try to act out of turn, the bot will remind you to wait.
- Check your current location: `/whereami`
- Debug the channel state: `/campaignstate` (ephemeral)
- Recap recent events: `/recap`
- Adjust difficulty: `/set-difficulty <easy|normal|hard>` (admin only)
- The bot manages voice connections per server, so multiple guilds can play simultaneously without issues.

---

## 📝 Character Sheets (Player Stats & Inventory)

- Register your character: `/register <character_name>`
- View your stats: `/mystats`
- Set a stat: `/setstat <stat> <value>` (e.g. `/setstat STR 15`)
- Add to inventory: `/inventory add "Item Name"`
- Remove from inventory: `/inventory remove "Item"`
- View inventory: `/inventory view`
- Character data is stored per Discord user in `/characters/` as JSON files.

### 🧙‍♂️ D&D 5e Spellcasting System

The bot now includes a comprehensive D&D 5e spellcasting system with 100+ spells:

- **View your spells:** `/spells` - Shows cantrips, spell slots, known and prepared spells
- **Cast a spell:** `/cast <spell_name>` - Cast a spell, consuming the appropriate slot
- **Prepare a spell:** `/prepare <spell_name>` - Prepare a spell for casting (toggle on/off)
- **Learn a spell:** `/learn <spell_name>` - Learn a new spell or cantrip for your class
- **Level up:** `/levelup` - Gain a level, roll HP, and unlock new features/spell slots

The system tracks:
- Spell slots by level (auto-calculated based on class and level)
- Cantrips known
- Spells known (for Bards, Sorcerers, Warlocks, Rangers)
- Prepared spells (for Clerics, Druids, Paladins, Wizards)
- Class features at each level

### 🌐 Web Portal

When `python app.py` is running, open `http://localhost:5000/portal/` to browse all
registered characters, edit them and view campaign summaries. The portal includes:

- **Character list** with create/edit/delete functionality
- **Character detail page** showing:
  - Ability scores with modifiers
  - Combat stats (AC, Initiative, Proficiency)
  - Spell slots with visual indicators
  - Known cantrips and spells
  - Class & racial features
  - Inventory
- **🔄 Sync button** - Synchronizes spell slots and features with class/level
- **📖 Manage Spells** - Full spell management interface to learn/forget/prepare spells
- **DM Dashboard** for campaign and NPC management
- **Campaign summaries** with combat history

---

## 📜 Session Logging & Export

- All narration and player messages are logged per session/channel in `/logs/` as Markdown files.
- Log format: `[timestamp] **Speaker:** message`
- Export your session log: `/exportlog` (zips and sends the Markdown log file)

---

## 🎲 Dice Rolling

- Roll dice: `/roll <dice>` (e.g. `/roll 2d6+1`, `/roll 1d20`)
- Skill check: `/roll athletics` (uses your STR mod, supports --adv/--disadv)
- Saving throw: `/save WIS vs 14`
- The bot will also auto-roll if the AI says e.g. "Roll a 1d20" in its response.
- Dice results are shown in chat and logged.
- Dice rolls can use character stats and proficiency.
- Supports advantage/disadvantage.
- Rolls feed into AI for narrative outcomes.

---

## 🗣️ Adding New Voices

Create a `voice_profiles.json` file in the project root based on
`voice_profiles.json.example`:

```json
{
  "Narrator": "your-elevenlabs-voice-id",
  "Grumpy Dwarf": "..."
}
```

Use `/setvoice` (coming soon) or edit this file to map character tags to voice
IDs. The bot loads this file at runtime so you can swap voices without touching
the code.

---

## 🏰 Starting a New Adventure (Slash Command)

- Use `/start_adventure [prompt]` to generate a new campaign setup (title, setting, plot hook) using GPT-4o.
    - You can provide a prompt for inspiration, e.g. `/start_adventure pirates in a flying whale fortress`.
    - If no prompt is given, a default adventure is generated.
- The campaign is saved in the per-channel state and shown in chat.
- If you are in a voice channel, the campaign intro will be read aloud using ElevenLabs TTS (Narrator voice).

---

## 🕹️ Gameplay Loop

1. Start a campaign with `/new_campaign` or `/start_adventure`.
2. The bot announces the turn order and prompts the first player.
3. On your turn, describe your action with `/act <action>`.
4. Inline dice like `[1d20+2]` are rolled automatically when you `/act`.
5. If a roll is required by the DM, use `/roll` or `/save`.
6. Finish your turn with `/end_turn` (or enable `/set_auto_advance true`).
7. Acting out of turn triggers a reminder to wait.
8. Admins can reset a session with `/reset-campaign` or force the turn with `/force-turn <user>`.

---

## 🗃️ State Persistence
- Game state is saved per session (API) or per Discord channel (bot) in the `state/` folder as JSON.
- Each channel stores its campaign title, realm, plot hook, current location, player list and recent prompt history.
- You can delete these files to reset a session.

---

## 🔒 Security
- Never commit your real `.env` file or API keys.

---

## 🛠️ Extending
- Add Whisper for STT, dice mechanics, or a web frontend by creating new modules in `services/` or `utils/`.

---

## 📁 Structure
```
ai_dm_voice_app/
├── app.py                 # Flask API and web portal server
├── discord_bot.py         # Discord bot with slash commands
├── config.py              # Configuration management
├── utils/
│   ├── character_manager.py  # Character CRUD and spell management
│   ├── combat_manager.py     # Combat and initiative tracking
│   ├── dice_roller.py        # Dice rolling with modifiers
│   ├── dnd5e_data.py         # D&D 5e SRD data (classes, spells, races)
│   ├── logger.py             # Session logging
│   ├── state_manager.py      # Game state persistence
│   ├── voice_map.py          # Voice ID mapping
│   └── voice_parser.py       # Voice tag extraction
├── services/
│   ├── openai_service.py     # GPT-4o integration
│   └── elevenlabs_service.py # TTS integration
├── webportal/
│   ├── routes.py             # Web portal routes
│   └── templates/            # HTML templates
├── characters/            # Character JSON files
├── state/                 # Campaign state files
├── logs/                  # Session logs
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🛡️ Combat System
- Initiative, HP, and attack resolution are now handled automatically.
- Combatants are tracked and incapacitated are skipped in turn order.
- Reactions and D&D turn structure are supported.

## 🎲 Dice Rolling
- Dice rolls can use character stats and proficiency.
- Supports advantage/disadvantage.
- DM prompts reference the full D&D 5e difficulty classes (DC 5–30) and call out the relevant ability or saving throw, including proficiency bonuses and advantage/disadvantage. They also remind players about initiative order, Armor Class, and hit point tracking.
- Rolls feed into AI for narrative outcomes.

## 🧙 Character Sheets
- Now include proficiency, skills, HP, class/race, spell slots, XP, and level.
- Stat-based rolls and skill checks are supported.
- Full D&D 5e class data for all 12 PHB classes.
- Racial traits for all 9 PHB races with subraces.

## 📚 D&D 5e Data (`utils/dnd5e_data.py`)
The bot includes comprehensive D&D 5e SRD data:
- **12 Classes:** Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard
- **9 Races:** Human, Elf, Dwarf, Halfling, Gnome, Half-Elf, Half-Orc, Dragonborn, Tiefling (with subraces)
- **100+ Spells:** Cantrips through 5th level spells organized by class
- **Class Features:** All features from level 1-20 per class
- **Spell Slots:** Automatic calculation by class and level
- **XP Thresholds:** Automatic level detection from XP

## 🤖 AI Context
- AI receives character and combat state for more immersive, rules-aware narration.

## 🔄 Turn Management
- Auto-skips incapacitated combatants.
- Supports reactions and D&D turn structure.

## 🛠️ Quality of Life
- `/recap` for session summaries
- `/npc <name>` for NPC info
- `/location` for area description
- Auto-save and undo/rewind supported

---

##  License
This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
