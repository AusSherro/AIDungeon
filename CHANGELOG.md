# Changelog

## [0.3.0] - 2024-12-03
### Added
- **Campaign Memory System**: Long-term memory with campaign summaries, key NPCs, quests, and events
- `/context` command to view what the AI remembers about the campaign
- `/summarize` command to save recent events to long-term memory
- `/remember` command to manually add notes, NPCs, or quests
- AI automatically extracts NPCs and quests when summarizing
- `get_prompt_context_for_ai()` combines campaign memory with recent history
- Web portal character creation page with dice roller and standard array buttons
- Full web portal character editor with stats, inventory, and proficiencies
- Styled web portal with dark theme, navigation, and flash messages
- Campaign view in web portal showing memory, NPCs, quests, and key events
- DM dashboard with campaign overview and quick links

### Changed
- State manager now includes `campaign_summary`, `key_npcs`, `key_events`, and `quests` fields
- OpenAI service now uses layered context (memory + recent history)
- Web portal templates now use base template with consistent styling
- README completely rewritten with command reference tables

### Fixed
- Character list now shows race, class, and level info

## [0.2.0] - 2024-12-02
### Added
- **Skill Check Flow**: AI asks for rolls, player uses `/roll`, outcome narrated
- Pending roll system that auto-resolves with DC checks
- `/turns` command to toggle free-form vs strict turn order
- `/fight` now triggers combat mode (strict turns)
- `/endcombat` restores free-form exploration
- Critical hit/fumble detection on natural 20s and 1s
- TTS cleanup to remove "What will you do?" suggestions from voice narration
- All 18 D&D 5e skills with proper ability modifiers

### Changed
- Roll command now auto-applies character modifiers for skill checks
- Combat system uses character sheet HP/AC instead of defaults
- Initiative uses DEX modifier
- System prompt enhanced with skill check requirements

## [0.1.0] - 2024-12-01
### Added
- Complete command rewrite with 24 streamlined slash commands
- `/campaign` to start adventures, `/do` for actions, `/say` for dialogue
- Full character creation with class/race selection (autocomplete)
- Combat system with `/fight`, `/attack`, `/combatinfo`, `/nextturn`, `/endcombat`
- HP management with `/hp`, `/deathsave`, `/rest`
- Inventory system with `/inventory`
- Voice narration with ElevenLabs and Edge TTS fallback

## [Unreleased]
### Added
- Per-channel campaign state tracking including title, realm, plot hook, location, players and prompt history.
- `/whereami` command to recall the current setting.
- `/campaignstate` debug command to dump channel state.
- Narration suggestions appended to AI responses.
- Skill-based `/roll` command and `/save` for saving throws.
- `/recap` command summarizing recent events.
- `/set-difficulty` to adjust challenge level.
- `/inventory view/add/remove` and automatic loot detection.
- `voice_profiles.json` for dynamic ElevenLabs voice selection.
- `/set_auto_advance` command to toggle automatic turn advancement.
- Inline dice parsing in `/act`.
- Web portal pages for character editing and campaign summaries.
- Automatic XP awards when enemies are defeated.

### Changed
- `/new_campaign` and `/start_adventure` store structured campaign details.
- `/act` builds a dynamic system prompt from channel state.
- Voice connections are now managed per guild to avoid memory leaks when the bot joins multiple servers.
- System prompts now include recent actions and party composition.

