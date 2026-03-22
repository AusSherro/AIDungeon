# Changelog

## [6.0.0] - 2026-03-22
### Phase 6: Polish (Stabilization Plan)

#### Cluster 6.1 — TTS as Optional Feature
- **Added `is_available()` to elevenlabs_service.py**: Returns whether TTS is configured (checks provider and API key)
- **Wired `Config.TTS_ENABLED` into `play_tts()`**: Now checks both the config flag and `TTS_PROVIDER` before attempting any TTS; previously `Config.TTS_ENABLED` was defined but unused
- **TTS already well-gated**: All 13 callers properly `await` play_tts; errors caught with `logger.warning` (non-blocking); verified no bare elevenlabs imports

| File | Change |
|------|--------|
| `services/elevenlabs_service.py` | Added `is_available()` function |
| `cogs/shared.py` | `play_tts()` now checks `Config.TTS_ENABLED` in addition to `TTS_PROVIDER` |

#### Cluster 6.2 — Web Portal Update
- **Removed dnd5e_data silent fallback**: `webportal/routes.py` now imports dnd5e_data directly (fails loudly); removed `DND_DATA_AVAILABLE` flag and 2 conditional guards
- **Added auth warning**: Docstring now includes `WARNING: No authentication. For local use only.` and `TODO: Add basic auth`
- **All imports verified**: No Discord module dependencies, all utility imports resolve correctly

| File | Change |
|------|--------|
| `webportal/routes.py` | Direct dnd5e_data import, removed DND_DATA_AVAILABLE guards, added auth warning |

#### Cluster 6.3 — Basic Test Suite
- **Created 4 test files** with 20 tests covering dice rolling, state persistence, tag parsing, and character CRUD
- **All 20 tests pass** (`pytest tests/ -v` — 0.14s)
- **Added pytest to requirements.txt**

| File | Change |
|------|--------|
| `tests/__init__.py` | Created (empty) |
| `tests/test_dice_roller.py` | 6 tests: basic roll, multiple dice, modifiers, d100, parse_dice |
| `tests/test_state_manager.py` | 3 tests: missing state defaults, save/load roundtrip, corrupted file recovery |
| `tests/test_tag_parser.py` | 7 tests: combat tags (with/without space, lowercase), quest tags, strip_tags, multiple tags, no tags |
| `tests/test_character_manager.py` | 4 tests: register/load, damage/heal, damage floor, heal cap |
| `requirements.txt` | Added `pytest>=7.0.0` |

## [5.0.0] - 2026-03-22
### Phase 5: World Systems (Stabilization Plan)

#### Cluster 5.1 — NPC Manager Fixes
- **Fixed gender detection scope**: `detect_gender()` now accepts `npc_name` parameter and only counts pronouns in sentences that mention the NPC, preventing "he walked to where she stood" from giving random results
- **Applied buy_rate to buy_from_shop()**: Shop buy_rate multiplier now consistently applied to both buying and selling transactions
- **Verified shop save persistence**: Both `buy_from_shop()` and `sell_to_shop()` confirmed to call `save_npcs()` — no fix needed
- **NPC memory cap uses config**: `record_npc_interaction()` now uses `MAX_NPC_MEMORY_FACTS` (50) from config instead of hardcoded 20
- **Voice assignment crash protection**: `assign_voice_to_npc()` wrapped in try/except; returns `(None, 'narrator')` on any failure

| File | Change |
|------|--------|
| `utils/npc_manager.py` | `detect_gender()` scoped to NPC sentences, buy_rate applied in `buy_from_shop()`, config-based memory cap, voice assignment error handling |

#### Cluster 5.2 — Environment & World Generator Fixes
- **Flexible time parsing**: `parse_time_string()` now handles ranges ("4 to 5 hours" → 4), vague durations ("a few hours" → 3, "several hours" → 5, "couple hours" → 2), and minutes ("30 minutes" → 1 hour minimum)
- **Fixed indoor lighting override**: `update_lighting_for_time()` now checks `LOCATION_PRESETS` `is_outdoor` flag and location memory instead of relying on light source string whitelist; caves and dungeons no longer get time-of-day lighting
- **Added override parameter to apply_location_preset()**: When `override=False`, custom lighting set manually is preserved instead of being stomped by the preset
- **Verified TimeState rollover**: `advance()` already uses `while` loops for correct multi-day cascading — no fix needed

| File | Change |
|------|--------|
| `utils/world_generator.py` | Flexible time parsing, preset-based outdoor detection in `update_lighting_for_time()`, `override` param on `apply_location_preset()` |

#### Cluster 5.3 — Travel & World Map Fixes
- **Narrowed travel detection**: `detect_natural_language_travel()` now accepts `known_locations` list; checks known locations first (high confidence 0.9), then falls back to capitalized proper nouns only; expanded blocklist of generic words ("madness", "battle", "death", etc.)
- **Verified fast travel terrain fallback**: Already uses `.get(terrain, {}).get("speed_mult", 1.0)` — no fix needed
- **Normalized location keys to lowercase**: `add_location()` now stores keys as `name.lower()`; `get_location()` does direct lowercase lookup with fallback iteration for legacy data; `fast_travel()` and `get_world_context_for_ai()` use lowercase lookups
- **Fixed encounter night detection**: `advance_travel()` now uses `world_generator.get_time_state()` to determine actual in-game night (hour >= 20 or < 6) instead of `hours_traveled_today > 12`
- **Removed orphan ENCOUNTER_MULTIPLIERS dict**: Unused dict constant removed; `get_encounter_multiplier()` function already uses correct hardcoded if/elif chain per DMG pg. 82

| File | Change |
|------|--------|
| `utils/world_map.py` | Known-locations-first travel detection, lowercase location keys, fallback-safe dict lookups |
| `utils/encounter_manager.py` | Game-time night detection in `advance_travel()`, removed unused ENCOUNTER_MULTIPLIERS dict |

## [4.0.0] - 2026-03-22
### Phase 4: Character & Progression (Stabilization Plan)

#### Cluster 4.1 — Character Manager Fixes
- **Fixed HP floor on CON decrease**: `set_stat()` now enforces `max_hp = max(1, ...)` so HP never drops below 1 when CON is reduced
- **Death save stabilization clears conditions**: After 3 successful death saves, `dead`, `unconscious`, and `dying` conditions are automatically stripped from the character
- **Clarified Lay on Hands pool**: Added comment confirming `level * 5` is correct per D&D 5e Paladin rules
- **Clarified warlock pact slot recovery**: Added comment explaining why warlock slots use `pact_slots_used` (separate from `spell_slots`) per D&D 5e Pact Magic rules; recovery on short rest was already implemented correctly
- **Removed dnd5e_data silent fallback**: `dnd5e_data` import now fails loudly on startup instead of silently degrading; removed `DND_DATA_AVAILABLE` flag and all 11 conditional guards throughout the file; eliminated dead fallback code branches

| File | Change |
|------|--------|
| `utils/character_manager.py` | HP floor on CON decrease, death save condition clearing, lay_on_hands comment, warlock comment, removed try/except import + DND_DATA_AVAILABLE flag and all conditional branches |

#### Cluster 4.2 — Quest → XP → Rewards Pipeline
- **Wired up quest reward distribution**: `/questcomplete` now actually distributes rewards to party members — XP split evenly (with remainder to first players), gold split evenly (with remainder), items added to completing player's inventory, reputation changes applied via `modify_faction_standing()`
- **Fixed apostrophe handling in quest tag parser**: `parse_quest_tag_attributes()` now uses separate double-quote and single-quote patterns instead of a combined `[^"']+` class that rejected apostrophes inside double-quoted values
- **Added duplicate check to rumor→quest conversion**: `convert_rumor_to_quest()` now checks `get_quest_by_name()` before creating, preventing duplicate quests from the same rumor
- **Level-up notifications**: Quest completion embed now shows level-up announcements when XP gain triggers a level increase

| File | Change |
|------|--------|
| `utils/quest_manager.py` | Fixed `parse_quest_tag_attributes()` regex for apostrophes, added dedup check in `convert_rumor_to_quest()` |
| `cogs/social.py` | `/questcomplete` now distributes XP, gold, items, and reputation to party; imported `award_xp` from `xp_manager` |

## [3.4.0] - 2026-03-22
### Phase 3: Combat (Stabilization Plan)

#### Cluster 3.3 — Combat → Loot → Inventory Pipeline
- **Persisted pending loot to disk**: `_pending_loot` now saved to `state/loot/{channel}_loot.json` with atomic writes (tempfile + os.replace); `_load_pending_loot()` loads on demand from disk into memory cache; all loot functions (`claim_loot_item`, `claim_loot_gold`, `get_pending_loot`, `format_pending_loot`, `clear_pending_loot`) now use persistent storage
- **Fixed gold splitting remainder**: `claim_loot_gold(amount=None, party_user_ids=[...])` now splits evenly with `//` and gives remainder (1 gp) to first player instead of losing it
- **Fixed `claim_loot_gold(amount=None)`**: now splits evenly among party when `party_user_ids` provided, instead of giving all gold to the first claimant
- **Unified loot pipeline**: created `generate_and_register_loot()` in `combat_trigger.py` as the single entry point — generates loot AND registers claimable pile in `inventory_manager`; `process_post_combat()` now calls this single function instead of manually orchestrating two modules
- **Removed duplicate loot path**: `process_post_combat()` no longer imports from `loot_manager.py`; `loot_manager.py` kept for its `format_loot_display`, `generate_treasure_hoard`, and manual `/loot` command in utility cog
- **Fixed `/splitgold` command**: now uses `claim_loot_gold` with `party_user_ids` for consistent splitting logic and persistence

| File | Change |
|------|--------|
| `utils/inventory_manager.py` | Persistent loot storage (LOOT_DIR, _save/_load), gold split with remainder, party-aware claim_loot_gold |
| `utils/combat_trigger.py` | Added `generate_and_register_loot()` — unified loot pipeline entry point |
| `utils/combat_flow.py` | Simplified `process_post_combat()` to use single `generate_and_register_loot()` call |
| `cogs/utility.py` | `/splitgold` now uses `claim_loot_gold` with party_user_ids |

#### Cluster 3.2 — Combat Flow + Enemy AI Fixes
- **Refactored turn timer to use `asyncio.Event`** for race-free cancellation: `TurnTimerState` now has a `cancelled` Event; `_run_timer()` uses `asyncio.wait_for()` on the Event instead of `asyncio.sleep()` + stale-check pattern; callback exceptions caught and suppressed (no timer leaks)
- **Added `cleanup_channel()` method** to `CombatTimerManager`: cleans up both `_active_timers` and `_callbacks` dicts on combat end; `_run_timer` always cleans up via `finally` block
- **Improved enemy narration fallback** in `cogs/combat.py`: builds per-action mechanical descriptions (hit/miss/damage) instead of joining raw description strings
- **Removed competing loot fallback** from `process_post_combat()`: removed `generate_enemy_loot` import from loot_manager; error path now logs and shows user message instead of falling back to broken system

| File | Change |
|------|--------|
| `utils/combat_flow.py` | asyncio.Event timer, cleanup_channel(), removed loot_manager fallback, logger-based error reporting |
| `cogs/combat.py` | Enhanced narration fallback with per-action mechanical descriptions |

#### Cluster 3.1 — Combat Manager Bug Fixes
- **Fixed critical hit damage** in `utils/combat_manager.py`: crits now roll damage dice twice and add modifier once (D&D 5e RAW), instead of doubling the total result
- **Added Dex tiebreaker to initiative sorting**: tied initiatives now break on `init_bonus` (all 3 sort sites updated)
- **Added condition duration tracking**: `apply_status()` now accepts optional `duration` parameter; conditions stored as `{name, duration}` dicts in a new `conditions` list; durations auto-decrement at start of turn in `next_turn()`; expired conditions auto-removed from both `conditions` and legacy `status` lists
- **Normalized combatant IDs to strings**: players use `str(user_id)`, enemies get unique `"enemy_{name}_{index}"` IDs — no more `None` or mixed types
- **Guarded against missing initiative key**: all sorting lambdas use `.get('initiative', 0)` and `.get('init_bonus', 0)`

| File | Change |
|------|--------|
| `utils/combat_manager.py` | Crit damage fix (parse_dice + extra dice roll), Dex tiebreaker in 3 sort sites, condition duration tracking in next_turn/apply_status, string ID normalization in start_combat/_expand_enemy/add_combatant_mid_combat, safe .get() in all sort keys |

## [3.3.0] - 2026-03-22
### Phase 2: Core Game Loop (Stabilization Plan)

#### Cluster 2.4 — OpenAI Service Hardening
- **Hardened `services/openai_service.py`** for reliability:
  - Added `import openai` and centralized `_handle_openai_error()` helper with themed user-facing messages per exception type
  - All 10 API call sites now catch `openai.APIConnectionError`, `openai.RateLimitError`, `openai.APIStatusError` separately before generic `Exception` fallback
  - History trimming now preserves first 2 messages (campaign setup context) + last N, instead of just slicing from the end
  - Added missing `timeout=30` to `extract_npcs_and_quests()` API call
  - All error paths verified to return a string (never None or re-raised exception)

| File | Change |
|------|--------|
| `services/openai_service.py` | Specific OpenAI exceptions, smart history trim, _handle_openai_error helper, timeout on all calls |

#### Cluster 2.3 — Prompt Builder Overhaul
- **Rewrote `utils/prompt_builder.py`** for token-budgeted, prioritized context:
  - Moved all 9 context source imports to top-level (no more `try: from ... except: pass` inside the function)
  - Added token budget system (`MAX_CONTEXT_CHARS = 6000`, ~1500 tokens) — context sections added in priority order and stop when budget reached
  - Priority order: combat > campaign_summary > quests > NPCs > environment > world > travel > pacing > map > inventory
  - `campaign_summary` from state now included as high-priority context (was missing before)
  - Tag instructions condensed to single-line format per tag type (removed verbose multi-paragraph examples)
  - Tag sections are conditional: combat tags hidden during active combat, travel tags hidden during active travel
  - Action suggestions only shown when not in combat and not asking for a roll

| File | Change |
|------|--------|
| `utils/prompt_builder.py` | Rewritten — top-level imports, token budget, prioritized context, condensed conditional tag instructions |

#### Cluster 2.2 — AI Tag Detection Overhaul
- **Created `utils/tag_parser.py`** — unified parser for all structured tags in AI narration:
  - Single forgiving regex `[TAG_NAME: content]` (case-insensitive, flexible whitespace)
  - `parse_all_tags(text) -> ParsedTags` dataclass with fields for all 20+ tag types
  - `parse_attributes(attr_string)` handles `key="value"`, `key='value'`, `key=value`, and apostrophes in values
  - `strip_tags(text)` removes all `[TAG: ...]` blocks from display text
- **Updated `utils/combat_trigger.py`** — `detect_structured_combat()` and `detect_combat_trigger()` now accept optional `parsed: ParsedTags` to avoid re-parsing; surprise tags now extracted from parsed tags
- **Updated `utils/quest_manager.py`** — `detect_structured_quest_tags()` now uses `ParsedTags` instead of 7 separate regex patterns; imports `parse_attributes` from tag_parser
- **Updated `utils/world_generator.py`** — `detect_structured_tags()` now uses `ParsedTags` lists instead of individual regex matches
- **Updated `utils/world_map.py`** — `detect_structured_travel_tag()`, `detect_arrival_tag()`, `detect_location_discovered_tag()`, `detect_distance_revealed_tag()` all accept optional pre-parsed tags; `process_narration_for_travel()` pre-parses once and passes through

| File | Change |
|------|--------|
| `utils/tag_parser.py` | Created — unified tag parser with ParsedTags dataclass, parse_attributes, strip_tags |
| `utils/combat_trigger.py` | Updated detection functions to accept optional ParsedTags |
| `utils/quest_manager.py` | Updated detect_structured_quest_tags to use ParsedTags |
| `utils/world_generator.py` | Updated detect_structured_tags to use ParsedTags |
| `utils/world_map.py` | Updated all detection functions and process_narration_for_travel to use ParsedTags |

#### Cluster 2.1 — /do Action Loop Reliability
- **Refactored `/do` command** in `cogs/campaign.py` for resilient subsystem handling:
  - Replaced 6 separate notification string variables (`trap_notification`, `npc_notification`, `quest_notification`, `env_notification`, `travel_notification`, `combat_notification`) with a single `notifications: list[str]` pattern
  - Wrapped every subsystem call (resource consumption, trap detection, attack intent, NPC detection, quest processing, environment detection, travel detection, loot processing, skill checks, combat triggers) in isolated `try/except` blocks with `logger.error(..., exc_info=True)` for full tracebacks
  - Moved `save_state()` into a `finally` block so state is always persisted, even on partial failure
  - OpenAI failure now returns a clear user-facing error message instead of continuing with no narration
  - Removed all bare `except: pass` patterns — every error is now logged

| File | Change |
|------|--------|
| `cogs/campaign.py` | Refactored `/do` command: notifications list, isolated error handling, finally-block state save |

### Phase 1: The Cog Split (Stabilization Plan)

Splitting the monolithic `discord_bot.py` into focused discord.py Cog modules for maintainability.

### Cluster 1.1 — Cog Infrastructure + Campaign Core
- **Created `cogs/` package** with `__init__.py` listing all 6 planned cogs
- **Created `cogs/shared.py`** — shared state and helpers used across cogs:
  - `voice_manager` (VoiceClientManager singleton)
  - `_active_channels` dict (channel references for timer callbacks)
  - `play_tts()` function (TTS playback helper)
  - `SkillCheckConfig`, `SkillCheckRollButton`, `prompt_skill_check()`, `process_completed_skill_check()`, `check_and_prompt_passive_perception()` (skill check system)
- **Created `cogs/campaign.py`** — `CampaignCog` with 6 extracted commands:
  - `/campaign` — start a new D&D campaign
  - `/do` — core game loop (player action → AI response → subsystem processing)
  - `/context` — show AI campaign memory
  - `/summarize` — save events to long-term memory
  - `/remember` — manually add notes/NPCs/quests
  - `/help` — display available commands
- **Modified `discord_bot.py`**:
  - Imports shared state from `cogs.shared` instead of defining locally
  - `on_ready()` now loads cogs via `bot.load_extension()` before syncing commands
  - Removed ~1,011 lines of extracted code (6 commands + shared helpers)
  - Remaining commands stay in `discord_bot.py` for extraction in clusters 1.2–1.6

### Files Changed
| File | Change |
|------|--------|
| `cogs/__init__.py` | Created — COGS list for all 6 planned cog modules |
| `cogs/shared.py` | Created — shared state, play_tts, skill check system |
| `cogs/campaign.py` | Created — CampaignCog with /campaign, /do, /context, /summarize, /remember, /help |
| `discord_bot.py` | Removed extracted code, added cog loading in on_ready(), imports from cogs.shared |

### Cluster 1.2 — Combat Cog
- **Created `cogs/combat.py`** — `CombatCog` with 9 extracted commands:
  - `/fight` — start combat with enemies (simple/custom/multiplier formats)
  - `/attack` — player attack roll against target
  - `/nextturn` — advance to next combatant (auto-executes enemy turns)
  - `/endcombat` — end combat, award XP and loot
  - `/hp` — manage HP (damage/heal/set)
  - `/deathsave` — roll death saving throws
  - `/combatinfo` — show combat status and turn order
  - `/turntimer` — configure combat turn timer
  - `/timeleft` — check remaining turn time
- **Moved combat timer callbacks** to `cogs/combat.py`:
  - `on_turn_warning()`, `on_turn_timeout()`, `setup_timer_callbacks()`
- **Moved combat helper functions** to `cogs/combat.py`:
  - `execute_and_narrate_enemy_turn()`, `check_legendary_actions()`, `execute_legendary_action()`, `process_and_send_lair_action()`
- **Modified `discord_bot.py`**: Removed ~585 lines of combat code

| File | Change |
|------|--------|
| `cogs/combat.py` | Created — CombatCog with 9 combat commands + timer callbacks + helpers |
| `discord_bot.py` | Removed combat commands, timer callbacks, and combat helper functions |

### Cluster 1.3 — Character Cog
- **Created `cogs/character.py`** (998 lines) — `CharacterCog` with 20 extracted commands:
  - `/character`, `/stats` — view/create character, set stats
  - `/roll` — dice rolling with inline roll support
  - `/groupcheck`, `/savingthrow`, `/passivecheck` — skill check commands
  - `/rest` — short/long rest recovery
  - `/inventory` — view/add/remove items
  - `/attune`, `/unattune`, `/attunement` — magic item attunement
  - `/encumbrance` — carry weight check
  - `/spells`, `/cast`, `/prepare`, `/learn` — spellcasting system
  - `/resources` — class resource management
  - `/levelup` — level up character
  - `/xp`, `/awardparty` — XP tracking
- **Moved constants** `DND_CLASSES`, `DND_RACES`, `SKILL_CHOICES`, `ABILITY_CHOICES` into cog
- **Modified `discord_bot.py`**: Removed ~959 lines of character code (5422 → 4463 lines)

| File | Change |
|------|--------|
| `cogs/character.py` | Created — CharacterCog with 20 character management commands |
| `discord_bot.py` | Removed character commands and related section headers |

### Cluster 1.4 — World & Environment Cog
- **Created `cogs/world.py`** (1431 lines) — `WorldCog` with all world/environment commands:
  - `/environment` — view environmental conditions
  - `/trap` — create/list/detect/disarm/trigger traps (consolidated)
  - `/weather` — set/view weather conditions
  - `/lighting` — set/view lighting
  - `/time` — view/advance/set in-game time
  - `/location` — set location with auto-preset
  - `/hazard` — create/list hazards
  - `/terrain` — create/list terrain zones
  - `/cover` — calculate cover between positions
  - `/travel` — start/status/advance/cancel journeys (consolidated)
  - `/encounter` — generate/check encounters (consolidated)
  - `/worldmap` — view/fasttravel/add/set locations (consolidated)
- **Modified `discord_bot.py`**: Removed ~1,371 lines (4463 → 3092 lines)

| File | Change |
|------|--------|
| `cogs/world.py` | Created — WorldCog with 12 commands covering all 23 original world commands |
| `discord_bot.py` | Removed world/environment/travel/encounter commands |

### Cluster 1.5 — Social Cog (NPCs + Quests)
- **Created `cogs/social.py`** (1018 lines) — `SocialCog` with 19 separate slash commands:
  - `/npc`, `/npcdisposition` — NPC viewing and relationship management
  - `/faction`, `/reputation` — faction system
  - `/shop`, `/buy`, `/sell` — merchant system
  - `/quest`, `/quests`, `/questtemplate`, `/questobjective`, `/questprogress`, `/questnote`, `/questcomplete`, `/questabandon` — quest management
  - `/rumors`, `/investigaterumor` — rumor system
  - `/questchain`, `/acceptquest` — quest chains
- **Modified `discord_bot.py`**: Removed ~994 lines (3092 → 2098 lines)

| File | Change |
|------|--------|
| `cogs/social.py` | Created — SocialCog with 19 NPC/quest/faction/shop commands |
| `discord_bot.py` | Removed NPC and quest commands |

### Cluster 1.6 — Utility Cog + Session Cog + Final Cleanup
- **Created `cogs/utility.py`** (1406 lines) — `UtilityCog` with 25 remaining commands:
  - `/say`, `/done`, `/status`, `/recap` — campaign flow
  - `/handout`, `/secret`, `/mysecrets` — handout/secrets system
  - `/map` — tactical battle maps
  - `/ambient`, `/sfx` — audio/mood
  - `/reaction` — combat reactions
  - `/loot`, `/treasure`, `/identify`, `/lootpile`, `/claimloot`, `/claimgold`, `/splitgold` — loot system
  - `/exportlog` — session logging
  - `/voice`, `/turns`, `/leave`, `/joinvoice`, `/reconnect` — voice/settings
  - `/party` — party status dashboard
- **Created `cogs/session.py`** (395 lines) — `SessionCog` with:
  - `/session` — manage session (view/end/pause/recap/history/recover)
  - `on_voice_state_update` listener for auto-resume
- **Updated `cogs/__init__.py`**: Added `"cogs.session"` to COGS list (7 cogs total)
- **Trimmed `discord_bot.py`** from 2,098 → **39 lines** (clean bot shell)
  - Only contains: imports, bot setup, on_ready cog loader, and bot.run()
  - Zero utility/service imports — everything lives in cogs
  - Zero circular imports

| File | Change |
|------|--------|
| `cogs/utility.py` | Created — UtilityCog with 25 utility/loot/voice/settings commands |
| `cogs/session.py` | Created — SessionCog with /session + voice state listener |
| `cogs/__init__.py` | Updated — added cogs.session (7 cogs total) |
| `discord_bot.py` | Trimmed to 39-line bot shell (was 7,000+ lines before Phase 1) |

---

## [3.2.0] - 2026-03-22
### Phase 0: Foundation (Stabilization Plan)

Foundation hardening to make the codebase reliable before further development. No feature changes — just fixes to persistence, error handling, and configuration.

### Cluster 0.1 — State Manager Hardening
- **Atomic file writes**: `save_state()` now writes to a temp file then uses `os.replace()` — crash mid-write no longer corrupts JSON
- **Meta-lock for thread safety**: Lock creation protected by `_meta_lock` to prevent race conditions between threads
- **Load locking**: `load_state()` now acquires session lock (prevents read-then-stale-write races)
- **Corrupted file recovery**: Bad JSON files renamed to `.corrupted` instead of silently returning defaults
- **DEFAULT_STATE updated**: Added missing `session_active` and `session_started_at` keys
- **Removed bare except**: Backup cleanup `except: pass` replaced with proper handling
- Removed `shutil` dependency (no longer needed)

### Cluster 0.2 — Error Handling + Logging
- **Structured logging**: `utils/logger.py` now provides `setup_logging()` with `RotatingFileHandler` (5MB, 3 backups) writing to `logs/bot.log`
- **Console**: Only warnings and errors shown on console
- **Zero bare excepts**: All 9 bare `except:` blocks in `discord_bot.py` replaced with specific handlers:
  - `discord.HTTPException` for message edit failures
  - `discord.Forbidden` for DM send failures
  - `(ValueError, IndexError)` for dice/count parsing
  - `Exception` with logging for narration fallbacks
- **All `print()` replaced**: 13 `print()` calls in `discord_bot.py` and 11 in `services/openai_service.py` replaced with `logger.info/warning/error`
- `setup_logging()` called at bot startup before any other code runs

### Cluster 0.3 — Config Consolidation
- **New config values in `config.py`**:
  - `MAX_PROMPT_HISTORY = 20` (was hardcoded as 10)
  - `COMBAT_TURN_TIMEOUT = 90`, `COMBAT_TURN_WARNING = 30`
  - `AUTO_SAVE_INTERVAL = 300`, `INACTIVITY_TIMEOUT = 1800`
  - `SKILL_CHECK_TIMEOUT = 60`
  - `AI_MODEL = "gpt-4o"`, `AI_MAX_TOKENS = 500`, `AI_TEMPERATURE = 0.9`
  - `TTS_ENABLED` (from env var)
  - `MAX_NPC_MEMORY_FACTS = 50`
  - `DEFAULT_DIFFICULTY = "normal"`
- **`services/openai_service.py`**: All 10 `model="gpt-4o"` references now use `Config.AI_MODEL`; history window uses `Config.MAX_PROMPT_HISTORY` (20); `timeout=30` added to all API calls
- **`utils/session_manager.py`**: `AUTO_SAVE_INTERVAL` and `INACTIVITY_TIMEOUT` sourced from Config
- **`utils/combat_flow.py`**: `CombatFlowConfig.TURN_TIMEOUT_SECONDS` and `WARNING_SECONDS` sourced from Config
- **`discord_bot.py`**: `SkillCheckConfig.ROLL_TIMEOUT_SECONDS` sourced from Config

### Files Changed
| File | Changes |
|------|---------|
| `utils/state_manager.py` | Atomic writes, meta-lock, load locking, corruption recovery |
| `utils/logger.py` | Added `setup_logging()` with rotating file handler |
| `discord_bot.py` | Logging setup, 9 bare excepts fixed, 13 prints replaced, config imports |
| `config.py` | 12 new configuration constants added |
| `services/openai_service.py` | Config imports, logger, timeout on all API calls |
| `utils/session_manager.py` | Config imports for intervals |
| `utils/combat_flow.py` | Config imports for timer values |

---

## [3.1.0] - 2024-12-07
### Phase 16: Command Consolidation

Reduced total slash commands from ~120 to 76 to stay well under Discord's 100 command limit.

### Changed - Command Consolidations

**Quest Commands (12 → 1)**
- `/quest` now handles all quest operations via `action` parameter
- Actions: `list`, `view`, `create`, `complete`, `abandon`, `objective`, `progress`, `note`, `template`, `rumors`, `investigate-rumor`, `chain`, `accept`
- Removed: `/quests`, `/questcomplete`, `/questabandon`, `/questobjective`, `/questprogress`, `/questnote`, `/questtemplate`, `/rumors`, `/investigaterumor`, `/questchain`, `/acceptquest`

**Travel & Encounter Commands (7 → 2)**
- `/travel` now handles all travel operations via `action` parameter
- Actions: `start`, `status`, `advance`, `cancel`
- `/encounter` now handles all encounter operations
- Actions: `random-combat`, `social`, `check`
- Removed: `/travelstatus`, `/traveladvance`, `/travelcancel`, `/randomencounter`, `/encountercheck`

**World Map Commands (5 → 1)**
- `/worldmap` now handles all world map operations via `action` parameter
- Actions: `view`, `fast-travel`, `add-location`, `set-location`, `location-info`
- Removed: `/fasttravel`, `/addlocation`, `/setlocation`, `/locationinfo`

**Session Commands (4 → 1)**
- `/session` now handles all session operations via `action` parameter
- Actions: `view`, `end`, `pause`, `recap`, `history`, `recover`
- Removed: `/sessionrecap`, `/sessionhistory`, `/recover`

**Map Commands (9 → 1)**
- `/map` now handles all tactical map operations via `action` parameter
- Actions: `view`, `create`, `add-token`, `move`, `remove`, `distance`, `range`, `terrain`, `clear`
- Removed: `/newmap`, `/addtoken`, `/movetoken`, `/removetoken`, `/distance`, `/inrange`, `/setterrain`, `/clearmap`

**Handout Commands (9 → 3)**
- `/handout` now handles most handout operations via `action` parameter
- Actions: `view`, `read`, `create`, `reveal`, `share`, `delete`, `list-all`
- `/secret` kept separate for DM-to-player secrets
- `/mysecrets` kept separate for player convenience
- Removed: `/viewhandouts`, `/readhandout`, `/dmhandouts`, `/revealhandout`, `/sharehandout`, `/deletehandout`

**NPC & Shop Commands (7 → 2)**
- `/npc` now handles all NPC and faction operations via `action` parameter
- Actions: `list`, `view`, `create`, `disposition`, `factions`, `faction-view`, `faction-create`, `reputation`
- `/shop` now handles all shop operations via `action` parameter
- Actions: `view`, `create`, `buy`, `sell`
- Removed: `/npcdisposition`, `/faction`, `/reputation`, `/buy`, `/sell`

**Trap Commands (3 → 1)**
- `/trap` now includes detect and disarm actions
- Actions: `list`, `create`, `view`, `remove`, `trigger`, `detect`, `disarm`
- Removed: `/detecttrap`, `/disarmtrap`

### Technical
- Total commands reduced from ~120 to 76 (44 commands removed)
- All consolidated commands use `@app_commands.choices(action=[...])` pattern
- Underlying utility functions unchanged - automation systems unaffected
- All consolidations verified with `get_errors` - no issues found

---

## [3.0.0] - 2024-12-07
### 🎉 v3.0 - Full Autonomy Milestone COMPLETE

This release marks the completion of the **Full Autonomy** milestone. The bot can now run an entire D&D session with minimal DM intervention. Players just show up and play!

### What's New in v3.0
- **Combat starts automatically** from AI narration or player attack intent
- **Quests auto-create** from NPC dialogue and complete when objectives are met
- **Travel happens naturally** from narrative ("we head to town")
- **Environment adapts** to location and time automatically
- **Sessions resume seamlessly** when players return

### Phases Completed in v3.0
- Phase 11: Combat Trigger Detection ✅
- Phase 12: Dynamic Environment Generation ✅
- Phase 13: Autonomous Quest Management ✅
- Phase 14: Intelligent Travel & Exploration ✅
- Phase 15: Session Continuity & Auto-Resume ✅

---

## [0.20.0] - 2024-12-06
### Added
- **Session Continuity & Auto-Resume (Phase 15)**: Seamless session management
  - New `utils/session_manager.py` module (700+ lines) with complete session tracking
  - `SessionState`, `SessionSummary`, `PacingHint` dataclasses
  - `SessionStatus` enum: inactive, starting, active, paused, ending, crashed
  - `PacingPhase` enum: opening, rising, climax, falling, closing
- **Session Tracking**: Automatic activity monitoring
  - Session duration tracking from campaign start
  - Action, combat, and rest counting per session
  - Player activity tracking with timestamps
  - Last activity tracking for inactivity detection
- **Session Resume Detection**: Automatic resume offers
  - `on_voice_state_update` event handler detects player voice joins
  - Checks for resumable campaigns in text channels
  - Sends resume prompt with last session info
  - Auto-resumes paused sessions when players rejoin
- **Session Pacing System**: DM guidance based on time
  - Pacing phases: Opening (0-15m), Rising (15-60m), Climax (60-90m), Falling (90-120m), Closing (120m+)
  - Pacing hints injected into AI prompts at phase thresholds
  - Rest suggestions after 3 combats, 20 actions, or 60 minutes
  - `/session` command shows current pacing phase
- **Auto-Save & Recovery**: Crash protection
  - `AutoSaveManager` class with periodic saves (every 5 minutes)
  - Recovery points saved with full campaign state
  - `/recover` command to restore from crash
  - Inactivity timeout (30 minutes) pauses session automatically
- **Session Recap System**: Previous session summaries
  - `generate_session_recap()` builds narrative recap
  - `SessionSummary` stored with key events, location, quests
  - TTS narration of recap on resume
  - Last 10 sessions saved per channel
- **New Commands**
  - `/session` - View current session status (view/end/pause actions)
  - `/sessionrecap` - Get TTS recap of the previous session
  - `/sessionhistory` - View past session summaries
  - `/recover` - Recover from a crashed session

### Changed
- `/campaign` command now starts session tracking automatically
- `/do` command records activity (action/combat) for session tracking
- `build_system_prompt()` includes session pacing context
- Campaign state saved periodically via auto-save

### AI Prompt Changes
- Added SESSION PACING CONTEXT section to prompts
- AI sees session duration, pacing phase, action/combat counts
- DM guidance hints based on session length
- Rest suggestions when party has been very active

## [0.19.0] - 2024-12-06
### Added
- **Intelligent Travel & Exploration (Phase 14)**: Narrative-driven travel system
  - New `utils/world_map.py` module (900+ lines) with location graph and travel detection
  - `Location`, `TravelIntent`, `LocationDiscovery`, `WorldState` dataclasses
  - `LocationType` enum: city, town, village, dungeon, cave, ruins, tower, castle, temple, etc.
  - `DiscoveryStatus` enum: unknown, heard_of, known, visited, explored
- **Travel Intent Detection**: Automatic travel from narration
  - Structured travel tag: `[TRAVEL: destination="Phandalin", distance=15, terrain=forest]`
  - Location discovered tag: `[LOCATION_DISCOVERED: name="Ruined Tower", terrain=hills, poi=true]`
  - Arrival tag: `[ARRIVAL: "Phandalin"]` to mark journey completion
  - Distance revealed tag: `[DISTANCE_REVEALED: from="A" to="B" miles=100]`
  - Natural language detection: "We head to Phandalin", "Let's travel to the forest"
- **World Map System**: Automatic location tracking
  - Location graph with connections and distances
  - Visited/explored status tracking per location
  - Points of interest (POI) marking for significant locations
  - Total miles traveled tracking
  - Location notes and tags
- **Fast Travel System**: Quick travel to known locations
  - Fast travel available to visited/explored locations only
  - Reduced travel time with no encounter rolls
  - Automatic distance calculation from world map connections
- **New Commands**
  - `/worldmap` - View all known locations and travel connections
  - `/fasttravel` - Instantly travel to a visited location
  - `/addlocation` - Manually add a location to the world map
  - `/setlocation` - Set the party's current location
  - `/locationinfo` - View detailed information about a location

### Changed
- `/do` command now detects and processes travel-related tags
- Travel notifications displayed for journey start, arrival, and discoveries
- `build_system_prompt()` includes world map context with nearby locations
- Campaign state location updates automatically on arrival

### AI Prompt Changes
- Added TRAVEL & EXPLORATION TAGS section with structured tag formats
- AI can use `[TRAVEL:]`, `[LOCATION_DISCOVERED:]`, `[ARRIVAL:]`, `[DISTANCE_REVEALED:]`
- Examples show proper travel narration with tags
- World map context included showing current location and connections

## [0.18.0] - 2024-12-06
### Added
- **Autonomous Quest & Story Management (Phase 13)**: Quests auto-create from NPC dialogue
  - Structured quest tags: `[QUEST: name="...", type=rescue, difficulty=hard, giver="NPC"]`
  - Automatic quest creation when AI uses quest tags in narration
  - Quest completion tag: `[QUEST_COMPLETE: "Quest Name"]` auto-completes and awards rewards
  - Quest progress tag: `[QUEST_PROGRESS: "Quest Name", objective=1]` updates objectives
  - Quest objective tag: `[OBJECTIVE: "New objective"]` adds objectives dynamically
  - Quest hook tag: `[QUEST_HOOK: name="...", description="..."]` creates available quests
  - Quest chain tag: `[QUEST_CHAIN: parent="...", child="..."]` links quests sequentially
- **Rumor System**: Track overheard hints for future adventures
  - Rumor tag: `[RUMOR: "Strange lights near the cemetery"]` records rumors
  - Rumors stored per channel and can be investigated to become quests
  - New `/rumors` command: View all heard rumors
  - New `/investigaterumor` command: Convert rumor to active quest
- **Quest Chains**: Linked quest sequences
  - New `link_quests()` and `activate_chain_quest()` functions
  - Completing parent quest auto-unlocks child quest
  - New `/questchain` command: Link two quests in sequence
- **Enhanced Quest Detection**
  - Improved natural language detection for quest offers
  - Quest type detection from keywords (rescue, fetch, bounty, etc.)
  - Difficulty inference from context (dangerous→hard, simple→easy)
  - NPC quest giver detection from narration
- **New Commands**
  - `/rumors` - View all rumors the party has heard
  - `/investigaterumor` - Convert a rumor into an active quest
  - `/questchain` - Link two quests in sequence
  - `/acceptquest` - Accept an available quest

### Changed
- `process_narration_for_quests()` now accepts `source_npc` parameter
- Function handles structured tags before natural language detection
- Quest creation now supports `tags` parameter for categorization
- `/do` command displays quest creation, rumor, and chain notifications

### AI Prompt Changes
- Added QUEST TAGS section with structured tag formats and examples
- AI can use `[QUEST:]`, `[QUEST_COMPLETE:]`, `[QUEST_PROGRESS:]`
- AI can use `[RUMOR:]`, `[QUEST_HOOK:]`, `[OBJECTIVE:]`, `[QUEST_CHAIN:]`
- Examples show proper quest offer and completion narration

## [0.17.0] - 2024-12-06
### Added
- **Dynamic Environment Generation**: Automatic environment from AI narration
  - New `utils/world_generator.py` module (800+ lines) with environment detection and location memory
  - `TimeState`, `LocationMemory`, `EnvironmentChange` dataclasses for structured data
  - Structured environment tags: `[WEATHER: rain]`, `[LIGHTING: dim]`, `[LOCATION: cave]`
  - Additional tags: `[TIME: 3 hours pass]`, `[TRAP: pit trap]`, `[HAZARD: lava pool]`
  - Natural language detection fallback for weather, lighting, and location keywords
- **Time Tracking System**: In-game time management
  - Hour/day/month/year tracking starting at 8 AM, Day 1
  - Time periods: dawn, morning, midday, afternoon, evening, dusk, night
  - Automatic lighting updates based on time-of-day for outdoor locations
  - Time advancement through rests and travel
  - New `/time` command: view, advance, and set time
- **Location Memory System**: Persistent environment per location
  - Environment state saved when leaving a location
  - Automatic restoration when returning to a location
  - Indoor/outdoor classification affects lighting behavior
  - Weather, lighting, terrain tracked per location
- **Location Presets**: 25+ location types with automatic environment
  - Indoor: cave, dungeon, crypt, tavern, temple, castle, tower, mine, sewer
  - Outdoor: forest, swamp, mountain, desert, arctic, plains, road, city
  - Each preset configures lighting, weather, terrain automatically
  - New `/location` command to set location and apply presets

### Changed
- `/do` command now detects and applies environment changes from AI narration
- `build_system_prompt()` includes time/location context and environment tag instructions
- Environment changes display notifications (weather, lighting, location, time)

### AI Prompt Changes
- Added ENVIRONMENT TAGS section with structured tag formats
- AI can use `[WEATHER:]`, `[LIGHTING:]`, `[LOCATION:]`, `[TIME:]`, `[TRAP:]`, `[HAZARD:]`
- System auto-applies appropriate presets based on detected location type
- Time context included showing current time period

## [0.16.0] - 2024-12-06
### Added
- **AI Combat Trigger Detection**: Automatic combat initiation from AI narration and player intent
  - New `utils/combat_trigger.py` module (500+ lines) with combat detection and loot generation
  - `CombatTriggerResult`, `CombatInitiator`, `EnemySpec` dataclasses for structured combat data
  - Structured combat tags: AI uses `[COMBAT: 3 goblins, 1 hobgoblin]` format
  - Surprise round tags: `[SURPRISE: enemies]` for ambushes, `[SURPRISE: party]` for player surprise
  - AI combat phrase detection ("they attack", "roll for initiative", "combat begins")
  - Player attack intent detection ("I attack the goblin", "I cast fireball at")
- **Enemy Stat Lookup**: Automatic enemy stats from `dnd5e_data.py` MONSTERS database
  - `/fight goblin goblin orc` now auto-populates HP/AC from database
  - Custom stats still supported with name:hp:ac format
  - Fallback to CR-based defaults for unknown monsters
- **Post-Combat Loot Automation**: Automatic loot generation when combat ends
  - CR-based loot tables: gold, mundane items, magic items
  - Claimable loot piles using `/claimloot` command
  - Unidentified magic items prompt for `/identify`
  - Integration with existing `loot_manager.py` system
- **Surprise Round Mechanics**: Proper D&D 5e surprise handling
  - Surprised combatants skip their first turn
  - Clear surprise round notifications
  - Stealth vs Passive Perception calculations

### Changed
- `/do` command now detects player attack intent before AI call
- `/do` command detects AI combat triggers after narration
- `/fight` command accepts simple format (e.g., `goblin goblin orc`) with auto-lookup
- `build_system_prompt()` now includes combat trigger format instructions
- `process_post_combat()` uses new loot generation system

### AI Prompt Changes
- Added COMBAT TRIGGERS section instructing AI to use structured tags
- AI now outputs `[COMBAT: <count> <creature>, ...]` when hostilities begin
- AI outputs `[SURPRISE: enemies/party]` for surprise situations
- Action suggestions disabled during active combat

## [0.15.0] - 2024-12-06
### Added
- **Random Encounter & Travel System**: Complete travel and encounter management
  - New `utils/encounter_manager.py` module (900+ lines) with encounters, travel, and events
  - `Encounter`, `TravelState`, `Monster` dataclasses for structured encounter data
  - Enums: `TerrainType`, `EncounterDifficulty`, `TravelPace`, `EventType`
- **Travel System**: Track party journeys between locations
  - Pace-based travel: slow (stealth possible), normal, fast (-5 passive perception)
  - Terrain modifiers affecting travel speed and encounter chance
  - Distance tracking with miles traveled/remaining
  - Day/hour progress with 8-hour travel days
  - Automatic location updates on arrival
- **Combat Encounter Generation**: DMG-compliant encounter building
  - Party level-based XP thresholds for easy/medium/hard/deadly difficulties
  - Monster database: 50+ monsters organized by CR (0 to 10)
  - CR-appropriate monster selection based on party composition
  - Encounter multipliers for multiple monsters (DMG rules)
  - XP reward calculations
- **Terrain-Based Encounter Tables**: 14 terrain types with unique encounters
  - Terrain types: road, forest, plains, mountains, hills, swamp, desert, arctic, coastal, urban, underground, underdark, jungle, ruins
  - Each terrain has combat, social, and discovery encounter tables
  - Terrain modifiers for encounter chance and travel speed
- **Non-Combat Events**: Random events during travel
  - Social encounters: merchants, travelers, patrols, refugees
  - Discovery encounters: ruins, shrines, camps, natural wonders
  - Weather events: storm, fog, heat wave, cold snap
  - Rest sites: shelter, water source, defensible position
- **Enhanced AI Context**: Travel status included in AI prompts
  - Current journey progress shown to AI
  - Terrain and pace awareness for narration
- **New Commands**:
  - `/travel` - Start a journey with destination, distance, terrain, and pace
  - `/travelstatus` - View current travel progress with visual progress bar
  - `/traveladvance` - Advance travel by hours (checks for encounters)
  - `/travelcancel` - Cancel current journey
  - `/randomencounter` - Generate a random combat encounter for the party
  - `/encounter` - Generate a non-combat encounter (social, discovery, weather, etc.)
  - `/encountercheck` - Roll for a random encounter based on terrain and conditions

### Changed
- `build_system_prompt()` now includes travel context
- Travel arrival updates campaign location automatically
- Encounter system stores pending encounter for `/combat` integration

## [0.14.0] - 2024-12-06
### Added
- **Environmental Hazard Automation**: Complete environment management system
  - New `utils/environment_manager.py` module (1000+ lines) with traps, weather, lighting, terrain, and hazards
  - `Trap`, `Hazard`, `WeatherCondition`, `LightingCondition`, `EnvironmentState` dataclasses
  - Enums: `TrapTrigger`, `TrapType`, `WeatherType`, `LightLevel`, `CoverType`, `TerrainType`, `HazardType`
- **Trap System**: Complete trap creation, detection, and triggering
  - 10 pre-built trap templates: pit trap, poison dart, flame jet, spike trap, poison gas, net trap, blade trap, lightning rune, alarm, collapsing ceiling
  - Trap detection with Perception vs DC
  - Trap disarming with Thieves' Tools checks
  - Auto-trigger on movement keywords in `/do` actions
  - Trap states: hidden, detected, disarmed, triggered
- **Weather Effects**: 14 weather types with mechanical effects
  - Clear, cloudy, rain, heavy rain, thunderstorm, fog, dense fog, snow, blizzard, hail, sandstorm, extreme heat, extreme cold, wind, strong wind
  - Effects: perception modifiers, ranged attack modifiers, movement modifiers, disadvantage conditions, obscurement levels
  - Weather intensity (1-3) and duration tracking
- **Lighting System**: Light level tracking with vision checks
  - Bright light, dim light, darkness, magical darkness
  - Darkvision support
  - Advantage/disadvantage for attacks based on visibility
  - Light source tracking (torch, sunlight, spell)
- **Terrain Effects**: 11 terrain types with mechanical effects
  - Normal, difficult, shallow water, deep water, ice, lava, acid, rubble, mud, webs
  - Movement cost multipliers (1x to 3x)
  - Terrain damage on entry (lava, acid)
  - Saving throw effects (ice for prone, webs for restrained)
- **Hazard Zones**: Area-of-effect environmental hazards
  - Hazard types: fire, lava, acid, cold, lightning, poison, necrotic, radiant
  - Position-based hazard tracking
  - Duration and tick damage
- **Cover System**: Cover bonus calculations
  - No cover, half cover (+2 AC/Dex), three-quarters cover (+5 AC/Dex), full cover
  - Cover calculation between positions with obstacle detection
- **Enhanced AI Context**: Environment conditions included in AI prompts
  - Current weather, lighting, active hazards
  - Detected traps shown to AI for narrative awareness
- **New Commands**:
  - `/environment` - View full environment status summary
  - `/trap` - Create, list, view, remove, or trigger traps
  - `/detecttrap` - Roll Perception to detect a hidden trap
  - `/disarmtrap` - Attempt to disarm a detected trap
  - `/weather` - Set or view weather conditions
  - `/lighting` - Set or view lighting conditions
  - `/hazard` - Create, list, or remove environmental hazards
  - `/terrain` - Add, list, or remove terrain zones
  - `/cover` - Calculate cover between two positions

### Changed
- `/do` command now checks for trap triggers on movement actions
- `build_system_prompt()` now includes environment context
- Trap trigger notifications shown in `/do` output with save DC

## [0.13.0] - 2024-12-06
### Added
- **Quest & Objective Tracking System**: Comprehensive quest management with progress tracking
  - New `utils/quest_manager.py` module (800+ lines) with full quest management
  - `Quest`, `QuestObjective`, `QuestReward` dataclasses for structured quest data
  - Quest types: main, side, faction, personal, bounty, fetch, escort, explore, mystery
  - Quest difficulties: trivial, easy, medium, hard, deadly, legendary with XP/gold scaling
  - Multi-objective quests with progress tracking (e.g., "Kill 5 goblins: 3/5")
  - Optional and hidden objectives
  - Player notes on quests
- **Milestone Detection**: Automatic detection of quest progress from AI narration
  - Pattern matching for quest completion, item retrieval, enemy defeat, rescues
  - Objective progress detection from narration context
  - Quest failure detection
  - New quest offer detection
- **Quest Rewards System**: Automatic rewards on quest completion
  - XP rewards scaled by difficulty (50 XP trivial to 2500 XP legendary)
  - Gold rewards scaled by difficulty
  - Item rewards
  - Faction reputation changes
  - Special rewards
- **Quest Templates**: Pre-defined quest structures for quick creation
  - Bounty: Hunt a target
  - Fetch: Retrieve an item
  - Rescue: Save someone
  - Investigate: Solve a mystery
  - Clear Dungeon: Clear all threats
  - Escort: Protect during journey
- **Enhanced AI Context**: Active quests included in AI prompts
  - Current objectives listed for AI awareness
  - AI acknowledges quest progress naturally in narration
- **New Commands**:
  - `/quests` - View full quest log with active and available quests
  - `/quest` - View specific quest details or create new quest
  - `/questcomplete` - Mark a quest as completed
  - `/questabandon` - Abandon an active quest
  - `/questobjective` - Add an objective to a quest
  - `/questprogress` - Update progress on quest objective
  - `/questnote` - Add a note to a quest
  - `/questtemplate` - Create quest from pre-defined template

### Changed
- `/do` command now auto-detects quest progress from AI narration
- `build_system_prompt()` now includes active quest context
- Quest completion triggers reward notifications in chat
- Completed objectives and quests shown in `/do` output

## [0.12.0] - 2024-12-06
### Added
- **NPC Memory & Dialogue System**: Complete NPC relationship and memory tracking
  - New `utils/npc_manager.py` module (900+ lines) with comprehensive NPC management
  - `NPC`, `Faction`, `NPCMemory`, `NPCDialogueState`, `ShopInventory` dataclasses
  - NPC disposition tracking (-2 Hostile to +2 Allied)
  - NPC mood tracking (happy, angry, sad, scared, suspicious, etc.)
  - NPC memory of player names and facts they've learned
  - Interaction counting and trust level tracking
- **Faction Standing System**: Numerical reputation with factions
  - Faction standings from -100 (Hunted Enemy) to +100 (Exalted Champion)
  - Standing titles: Unknown, Known, Friendly, Trusted, Honored, etc.
  - Faction relationships (allies/enemies)
  - Standing change notifications with title updates
- **Shop/Merchant System**: Persistent merchant inventories
  - Shop types: general, weapons, armor, potions, magic
  - Pre-defined inventory for each shop type
  - Buy/sell functionality with buy rate (50% default)
  - Shop gold reserves
  - Stock quantity tracking
- **Auto NPC Detection**: NPCs automatically registered from AI narration
  - Voice tag extraction `[Voice: Character Name]`
  - Race, gender, role, and mood detection from context
  - Automatic voice assignment based on characteristics
  - NPC notification when meeting new NPCs
- **Enhanced AI Context**: NPCs and factions included in prompts
  - Nearby NPCs listed with disposition and mood
  - Faction standings included for roleplay context
  - NPCs remember previous interactions
- **New Commands**:
  - `/npc` - View all NPCs or specific NPC details
  - `/npc name:"Name" description:"..."` - Create/update NPC manually
  - `/npcdisposition` - Modify NPC disposition toward party
  - `/faction` - View all factions or specific faction details
  - `/faction name:"Name" description:"..."` - Create faction
  - `/reputation` - Modify party standing with a faction
  - `/shop` - View or create merchant shop
  - `/buy` - Purchase items from a merchant
  - `/sell` - Sell items to a merchant

### Changed
- `/do` command now auto-detects NPCs from AI narration and registers them
- `build_system_prompt()` now accepts optional `channel_id` for NPC context
- AI prompts include nearby NPC dispositions and faction standings
- NPCs react based on previous interactions and party reputation

## [0.11.0] - 2024-12-06
### Added
- **Resource Auto-Consumption System**: Automatic detection and consumption of resources from narrative
  - New `utils/resource_manager.py` module (700+ lines) with comprehensive resource tracking
  - `DetectedSpell`, `DetectedAbility`, `DetectedConsumable` dataclasses
  - `ResourceConsumption` dataclass for tracking consumption results
  - Spell casting detection from narrative text with pattern matching
  - Class ability detection for all PHB classes
  - Consumable detection (potions, scrolls, ammunition)
- **Spell Detection**: Automatic spell slot consumption
  - `detect_spell_cast()` with regex patterns for casting phrases
  - Support for all SRD spells with aliases (e.g., "fire ball" → "Fireball")
  - Cantrip detection (no slot consumption)
  - Automatic upcast to available slot level if primary slot exhausted
  - Spell slot remaining display after cast
- **Class Resource Tracking**: All PHB class abilities tracked
  - Barbarian: Rage uses
  - Bard: Bardic Inspiration
  - Cleric/Paladin: Channel Divinity
  - Druid: Wild Shape uses
  - Fighter: Action Surge, Second Wind
  - Monk: Ki points (Flurry of Blows, Patient Defense, Step of the Wind, Stunning Strike)
  - Paladin: Divine Smite (uses spell slots), Lay on Hands pool
  - Sorcerer: Sorcery Points (Metamagic)
- **Consumable Tracking**: Automatic inventory management
  - Potion detection ("drink/quaff/use potion of X")
  - Scroll detection ("read/use scroll of X")
  - Ammunition tracking (arrows, bolts, darts, sling bullets)
  - Automatic removal from inventory on use
- **New Commands**:
  - `/resources` - View all character resources (spell slots, class abilities, consumables)

### Changed
- `/do` command now automatically detects and consumes resources from narrative
- Resource consumption notifications appear after narration
- Spell slots, class abilities, and consumables tracked in real-time

## [0.10.0] - 2024-12-06
### Added
- **Skill Check Resolution Loop**: Complete closed-loop skill check system with AI narration
  - New `utils/skill_check_manager.py` module (600+ lines) with comprehensive check handling
  - `SkillCheckRequest`, `SkillCheckResult`, `GroupCheckResult`, `PendingCheck` dataclasses
  - `parse_skill_check_request()` with enhanced regex for skills, abilities, and saving throws
  - Detection of group checks ("everyone roll", "the party must")
  - `roll_skill_check()` with automatic advantage/disadvantage from conditions
  - `resolve_group_check()` using majority rule (>50% success)
  - `calculate_passive_score()` with 10 + modifiers + feat bonuses (Observant, etc.)
  - Pending check state management for tracking awaiting responses
- **Interactive Skill Check Prompts**: Button-based player prompts
  - `SkillCheckRollButton` View with interactive 🎲 Roll button
  - 60-second timeout with auto-roll option for unresponsive players
  - Advantage/disadvantage automatically detected from character conditions
  - Clear display of check type, DC, and modifiers
- **Skill Check AI Narration**: GPT-4o narrates all check outcomes
  - `narrate_skill_check_outcome()` for dramatic individual check narration
  - `narrate_group_check_outcome()` for party-wide check results
  - `narrate_passive_notice()` for subtle perception discoveries
  - Results flow directly to AI for consequence narration
- **New Skill Check Commands**:
  - `/groupcheck <skill> [dc]` - Request group skill check from all players
  - `/savingthrow <ability> <dc> [player]` - Request saving throw from player(s)
  - `/passivecheck <dc> <description>` - DM tool to secretly check passive perception
- **v1.0 "Playable Automation" Milestone Complete**: All Phase 1-3 goals achieved

### Changed
- `/do` command now uses enhanced skill check detection with button prompts
- `/roll` command integrates with pending check system for AI narration flow
- Skill checks detected in AI narration now trigger interactive player prompts
- Roll results automatically re-injected to AI for consequence narration

## [0.9.0] - 2024-12-06
### Added
- **Combat Flow Auto-Advance System**: Complete turn automation and pacing
  - New `utils/combat_flow.py` module (600+ lines) with comprehensive combat flow management
  - `CombatTimerManager` class for configurable turn timeouts (default 60s)
  - Warning ping at 30s remaining via async callbacks
  - Auto-pass on timeout with defensive action selection (Dodge/Disengage)
  - `/turntimer` command to configure timeout and warning per channel
  - `/timeleft` command to check remaining time on current turn
- **Turn Start Automation**: Rich turn announcements
  - `build_turn_announcement()` with HP, conditions, and action summary
  - Player pings with full combat context
  - Quick action suggestions based on character state
  - Available movement, action, bonus action, reaction display
- **End-of-Round Processing**: Automatic effect resolution
  - `process_end_of_turn_effects()` for condition duration countdown
  - `process_start_of_turn_effects()` for ongoing damage (poison, fire, bleed)
  - `process_round_transition()` for regeneration and ability recharge
  - Automatic concentration check prompts when damage taken
  - Condition expiration notifications
- **Combat End Detection**: Victory and defeat handling
  - `check_combat_end()` with `CombatEndReason` enum (Victory, TPK, Fled, Surrendered)
  - Automatic combat resolution when all enemies/players defeated
  - `CombatEndResult` dataclass with XP, loot, and narrative hooks
- **Post-Combat Automation**: Session flow continuation
  - `process_post_combat()` for XP calculation and distribution
  - Loot generation prompts for defeated enemies
  - Short rest opportunity offers
  - Victory/defeat narrative suggestions

### Changed
- `/fight` command now initializes turn timer for player turns
- `/nextturn` command now uses enhanced turn announcements with timer
- `/nextturn` processes end-of-round effects automatically on round transition
- `/nextturn` checks for combat end conditions after each turn
- `/attack` command now cancels timer on action and checks for victory
- `/cast` command now cancels timer on spell cast
- `/endcombat` command now processes post-combat automation (XP, loot, rest offer)
- `/combatinfo` enhanced with timer display, health icons, and type indicators

## [0.8.0] - 2024-12-06
### Added
- **Enemy AI Turn Automation**: Complete AI-driven enemy behavior system
  - New `utils/enemy_ai.py` module (700+ lines) with tactical decision making
  - Target selection based on threat scoring (HP%, concentration, healing abilities)
  - Action selection prioritizing multiattack > recharge abilities > single attacks
  - Spell selection for intelligent casters with slot management
  - Movement AI for tactical positioning (melee approach, ranged maintain distance)
  - 7 enemy behavior profiles: mindless, beast, humanoid_soldier, humanoid_brute, spellcaster, boss, support
  - Monster-to-profile mapping for 50+ creature types
  - Flee logic based on morale thresholds per profile
- **Legendary Action Automation**: Reactive legendary actions between player turns
  - `check_legendary_actions()` triggers after player attacks and spells
  - `select_legendary_action()` chooses tactically appropriate legendary action
  - Dramatic AI narration for legendary action execution
- **Lair Action Processing**: Environmental effects at initiative count 20
  - `process_lair_actions()` for boss lair effects
  - AI-generated lair action narration
- **AI Combat Narration**: GPT-4o narrates all enemy actions
  - `narrate_enemy_action()` for dramatic combat descriptions
  - `narrate_legendary_action()` for special legendary moments
  - `narrate_lair_action()` for environmental effects
  - Fallback narration when AI unavailable
  - TTS voice output for all enemy actions

### Changed
- `/nextturn` command now auto-executes enemy turns and chains consecutive enemies
- `/attack` command now checks for legendary action opportunities after player attacks
- `/cast` command now checks for legendary action opportunities after spellcasting
- Combat flow automatically applies damage from enemy attacks to targets

## [0.7.0] - 2024-12-06
### Added
- **XP & Auto-Leveling System**: Automatic experience point tracking
  - XP awarded when combat ends based on enemy CR
  - Party XP split equally or by contribution
  - Auto-detection of level-up thresholds
  - `/xp` command to view character XP and progress bar
  - `/awardxp` DM command for milestone rewards
  - XP threshold table for levels 1-20
- **Loot & Treasure System**: Dynamic treasure generation
  - `/loot` command to generate treasure hoards by CR
  - Enemy loot drops based on creature type
  - Magic item tables by rarity (Common to Legendary)
  - Gems and art objects by value tier
  - `/treasure` command for DM-controlled loot distribution
- **Combat Reactions**: D&D 5e reaction mechanics
  - `/reaction` command with 8 reaction types
  - Opportunity Attacks when enemies leave reach
  - Shield spell (+5 AC as reaction)
  - Counterspell to interrupt enemy casting
  - Uncanny Dodge for Rogues (halve damage)
  - Absorb Elements, Hellish Rebuke, Cutting Words, Deflect Missiles
  - Reaction tracking per round (auto-reset on turn start)
  - Sentinel and Mage Slayer feat triggers
- **Ambient Music & SFX**: Background atmosphere system
  - AmbientMood presets: calm, tense, combat, mystery, celebration, horror, travel, dungeon
  - `/ambient` command to set mood
  - `/sfx` command for one-shot sound effects
  - Placeholder track URLs (replace with royalty-free sources)
- **NPC Voice Variety**: Distinct voices for different NPC archetypes
  - Voice archetypes: noble, peasant, merchant, guard, scholar, rogue, mystic, warrior, child, elder
  - Automatic voice selection based on NPC name/description
  - Edge TTS as default (free), ElevenLabs for premium voices
- **Auto-Combat Triggers**: AI-initiated combat detection
  - Combat trigger patterns in AI narration (attack phrases, initiative calls)
  - Automatic `/fight` initiation when hostilities begin
  - Enemy extraction from narrative descriptions
- **Party Dashboard**: Overview of all party members
  - `/party` command showing HP, AC, conditions for all players
  - Quick reference for DM and players
- **Playthrough Guide**: Comprehensive documentation
  - Session zero setup instructions
  - Command quick reference by category
  - Combat flow walkthrough
  - Voice and TTS configuration guide
  - Troubleshooting and tips

### Changed
- Combat turn advancement now resets reactions for the active combatant
- `/endcombat` now awards XP and generates loot automatically

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

