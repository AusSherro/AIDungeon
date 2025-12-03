# AI Dungeon Master

A voice-enabled AI Dungeon Master for D&D 5e using GPT-4o and ElevenLabs TTS, designed for Discord with persistent campaign state.

---

## 🚀 Quick Start

1. **Clone the repo:**
   ```bash
   git clone https://github.com/AusSherro/AIDungeon.git
   cd AIDungeon
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

### 🌐 Web Portal

When `python app.py` is running, open `http://localhost:5000/portal/` to browse all
registered characters, edit them and view campaign summaries. The portal now shows
combat history and includes a simple DM dashboard for NPC management.

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
AIDungeon/
├── app.py                 # Flask REST API & web portal
├── discord_bot.py         # Main Discord bot
├── config.py              # Configuration management
├── services/
│   ├── openai_service.py  # GPT-4o integration
│   └── elevenlabs_service.py  # TTS integration
├── utils/
│   ├── character_manager.py   # D&D character sheets
│   ├── combat_manager.py      # Combat tracking
│   ├── dice_roller.py         # Dice mechanics
│   ├── state_manager.py       # State persistence
│   ├── voice_map.py           # Voice ID mapping
│   └── voice_parser.py        # Voice tag extraction
├── webportal/             # Web UI templates
├── state/                 # Game state (per channel)
├── characters/            # Player character data
├── combat/                # Combat encounter data
├── logs/                  # Session transcripts
├── .env.example           # Environment template
└── requirements.txt       # Dependencies
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

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
