# Changelog

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

### Changed
- `/new_campaign` and `/start_adventure` store structured campaign details.
- `/act` builds a dynamic system prompt from channel state.

