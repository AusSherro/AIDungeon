# Changelog

## [0.6.0] - 2025-12-03
### Added
- **Player Handouts System**: DM tools for sharing information with players
  - `/handout` command to create notes, letters, maps, items, lore, clues, journal entries
  - `/secret` command for DM-to-player private messages
  - `/viewhandouts`, `/readhandout`, `/mysecrets` for players
  - `/dmhandouts`, `/revealhandout`, `/sharehandout`, `/deletehandout` for DM
  - Image URL support for visual handouts
- **Tactical Maps**: Grid-based battle maps for combat positioning
  - `/newmap` with templates (dungeon, forest, tavern, cave)
  - `/map` to view current battle map with ASCII rendering
  - `/addtoken`, `/movetoken`, `/removetoken` for token management
  - `/distance` and `/inrange` for tactical positioning
  - `/setterrain` for modifying map terrain
  - Terrain types: floor, wall, water, difficult, door, pillar, tree, rubble
  - Token types: player, enemy, NPC, boss, object
- **SQLite Database Layer**: Optional database backend for better performance
  - Full schema for characters, campaigns, NPCs, quests, events
  - Handouts, secrets, maps, and session logs tables
  - Migration utility from JSON files
  - Thread-safe operations with locks

## [0.5.0] - 2025-12-03
### Added
- **Equipment System**: Full weapon and armor management
  - 37 weapons with damage dice, types, and properties (finesse, heavy, two-handed, etc.)
  - 13 armor types with AC calculations, DEX caps, stealth disadvantage
  - `/equip`, `/unequip`, `/gear` commands
  - Automatic AC recalculation based on equipped armor and DEX
- **Condition Effects**: All 16 D&D 5e conditions with mechanical effects
  - Blinded, charmed, frightened, grappled, incapacitated, invisible
  - Paralyzed, petrified, poisoned, prone, restrained, stunned, unconscious
  - Exhaustion with 6 levels of increasing severity
- **Enhanced Rest Mechanics**: Class-specific resource recovery
  - Short rest: Hit Dice spending, Warlock pact slots, Fighter Second Wind, Monk Ki, Channel Divinity
  - Long rest: Full HP, all spell slots, half hit dice regained, exhaustion reduced
- **Feats Database**: 40 popular feats with prerequisites and effects
  - Great Weapon Master, Sharpshooter, Sentinel, Polearm Master, Lucky, Alert, Mobile, War Caster
- **Monster Statblocks**: 15+ pre-built monsters for quick encounters
  - CR 1/8-1/4: Kobold, Goblin, Skeleton, Zombie
  - CR 1/2: Orc, Hobgoblin
  - CR 1: Bugbear, Dire Wolf, Ghoul, Goblin Boss
  - CR 2-5: Ogre, Werewolf, Troll, Orc War Chief
  - CR 8: Young Green Dragon with legendary actions
- **Initiative Tracker Improvements**: Advanced combat features
  - Legendary actions for boss monsters (resets each round)
  - Legendary resistance to auto-succeed saves
  - Lair actions at initiative count 20
  - Damage types with resistance/immunity/vulnerability tracking
  - Regeneration mechanics (blocked by fire/acid)
  - Readied actions with trigger conditions
  - Delayed turns for tactical positioning

## [0.4.0] - 2025-12-02
### Added
- **Full Spellcasting System**: Complete spell management
  - `/spells` command to view known spells and spell slots
  - `/cast <spell>` with slot level upcasting support
  - `/prepare` and `/learn` commands for spell management
  - 100+ spells organized by class and level
  - Concentration tracking
- **Level Up System**: Character progression
  - `/levelup` command with HP rolling or average
  - Class features unlocked by level
  - Proficiency bonus scaling
  - New spell slots on level up
- **Web Portal Spell Management**: Browser-based spell UI
  - View known and prepared spells
  - Learn new spells by class
  - Prepare/unprepare spells
  - Sync character with class data

### Changed
- Character sheets now track spell slots by level
- Classes include full spell slot progression tables
- 40+ Discord slash commands

## [0.3.0] - 2025-12-01
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

## [0.2.0] - 2025-11-30
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

## [0.1.0] - 2025-11-29
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

