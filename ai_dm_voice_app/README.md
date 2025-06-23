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
4. **Run the Flask API:**
   ```powershell
   python app.py
   ```
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

---

## 📝 Character Sheets (Player Stats & Inventory)

- Register your character: `/register <character_name>`
- View your stats: `/mystats`
- Set a stat: `/setstat <stat> <value>` (e.g. `/setstat STR 15`)
- Add to inventory: `/inventory add "Item Name"`
- Remove from inventory: `/inventory remove "Item"`
- View inventory: `/inventory view`
- Character data is stored per Discord user in `/characters/` as JSON files.

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

Edit `utils/voice_map.py`:
```python
VOICE_MAP = {
    'Grumpy Dwarf': 'elevenlabs-voice-id-1',
    'Elven Queen': 'elevenlabs-voice-id-2',
    'Narrator': 'dUercWozs0yhe4xBCgZ0',
    # Add more mappings here
}
```
Find your ElevenLabs voice IDs at https://elevenlabs.io/ and add them here.

---

## 🏰 Starting a New Adventure (Slash Command)

- Use `/start_adventure [prompt]` to generate a new campaign setup (title, setting, plot hook) using GPT-4o.
    - You can provide a prompt for inspiration, e.g. `/start_adventure pirates in a flying whale fortress`.
    - If no prompt is given, a default adventure is generated.
- The campaign is saved in the per-channel state and shown in chat.
- If you are in a voice channel, the campaign intro will be read aloud using ElevenLabs TTS (Narrator voice).

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
├── app.py
├── discord_bot.py
├── utils/
│   ├── voice_parser.py
│   ├── voice_map.py
│   └── state_manager.py
├── services/
│   ├── openai_service.py
│   └── elevenlabs_service.py
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
