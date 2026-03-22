# AI Dungeon Master - Stabilization Plan

> **Goal:** Get this thing playable for a real session with friends.  
> **Approach:** Fix what's broken, wire up what's disconnected, don't add features.  
> **Audience:** Each cluster is a self-contained prompt for an AI coding agent.

---

## How To Use This Document

1. **Do clusters in order** -- later ones depend on earlier ones
2. **One cluster = one AI chat session.** Copy the cluster text as your prompt.
3. **After each cluster:** run the bot, test the acceptance criteria listed
4. **If something breaks:** paste the error back into the same session before moving on
5. Clusters marked 🔴 are critical. 🟡 are important. 🟢 are polish.

### After Completing Each Cluster

After all acceptance criteria pass for a cluster, the AI agent should also:

1. **Update `CHANGELOG.md`** — Add a descriptive entry under the current version for the cluster just completed. Include what changed and which files were affected. Follow the existing format in the changelog.
2. **Mark the cluster complete** — In this file, change the cluster's heading emoji from 🔴/🟡/🟢 to ✅ (e.g., `## Cluster 1.1 ✅ — Cog Infrastructure + Campaign Core`).
3. **Mark the phase complete** — If all clusters in a phase are now ✅, change the phase heading to include `✅ COMPLETE` (e.g., `# PHASE 1: THE COG SPLIT ✅ COMPLETE`).

---

## Cluster Map

```
PHASE 0: FOUNDATION ✅ COMPLETE
  0.1 ✅ State Manager Hardening
  0.2 ✅ Error Handling + Logging
  0.3 ✅ Config Consolidation

PHASE 1: THE COG SPLIT ✅ COMPLETE
  1.1 ✅ Cog Infrastructure + Campaign Core (/campaign, /do, /context, /summarize, /help)
  1.2 ✅ Combat Cog (/fight, /attack, /nextturn, /endcombat, /hp, /deathsave, timers)
  1.3 ✅ Character Cog (/character, /roll, /rest, /inventory, /spells, /cast, /levelup, etc.)
  1.4 ✅ World Cog (/environment, /trap, /weather, /lighting, /time, /location, /travel, /worldmap, etc.)
  1.5 ✅ Social Cog (/npc, /faction, /shop, /quest, /rumors, etc.)
  1.6 ✅ Utility Cog (/handout, /map, /ambient, /sfx, /loot, /session, /xp, etc.)

PHASE 2: CORE GAME LOOP ✅ COMPLETE
  2.1 ✅ /do Action Loop Reliability
  2.2 ✅ AI Tag Detection Overhaul
  2.3 ✅ Prompt Builder Overhaul
  2.4 ✅ OpenAI Service Hardening

PHASE 3: COMBAT ✅ COMPLETE
  3.1 ✅ Combat Manager Bug Fixes
  3.2 ✅ Combat Flow + Enemy AI Fixes
  3.3 ✅ Combat → Loot → Inventory Pipeline

PHASE 4: CHARACTER & PROGRESSION ✅ COMPLETE
  4.1 ✅ Character Manager Fixes
  4.2 ✅ Quest → XP → Rewards Pipeline

PHASE 5: WORLD SYSTEMS ✅ COMPLETE
  5.1 ✅ NPC Manager Fixes
  5.2 ✅ Environment & World Generator Fixes
  5.3 ✅ Travel & World Map Fixes

PHASE 6: POLISH ✅ COMPLETE
  6.1 ✅ TTS as Optional Feature
  6.2 ✅ Web Portal Update
  6.3 ✅ Basic Test Suite
```

---

## Dependencies

```
0.1 ──→ 0.2 ──→ 0.3 ──→ 1.1 ──→ 1.2 ──→ 1.3 ──→ 1.4 ──→ 1.5 ──→ 1.6
                                    │
                                    ▼
                          2.1 ──→ 2.2 ──→ 2.3 ──→ 2.4
                                    │
                                    ▼
                          3.1 ──→ 3.2 ──→ 3.3
                                    │
                                    ▼
                          4.1 ──→ 4.2
                                    │
                                    ▼
                          5.1 ──→ 5.2 ──→ 5.3
                                    │
                                    ▼
                          6.1, 6.2, 6.3 (independent)
```

---

---

# PHASE 0: FOUNDATION ✅ COMPLETE

---

## Cluster 0.1 ✅ — State Manager Hardening

### Prompt for AI Agent

> I need you to fix `utils/state_manager.py` in my Discord bot project. This file manages JSON persistence for campaign state. It currently has race conditions, no atomic writes, and incomplete default state. Here's what to fix:
>
> **File:** `utils/state_manager.py` (~196 lines)
>
> **Fix 1: Atomic file writes**
> Currently `save_state()` writes directly to the state file. If the bot crashes mid-write, the JSON is corrupted and unrecoverable. Change it to write to a temp file first, then use `os.replace()` to atomically swap it in.
>
> Before:
> ```python
> with open(path, 'w') as f:
>     json.dump(state, f, indent=2)
> ```
>
> After pattern:
> ```python
> import tempfile
> temp_fd, temp_path = tempfile.mkstemp(dir=STATE_DIR, suffix='.tmp')
> try:
>     with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
>         json.dump(state, f, indent=2)
>     os.replace(temp_path, path)  # Atomic on all platforms
> except:
>     os.unlink(temp_path)
>     raise
> ```
>
> Apply this same pattern to ALL save functions in the file.
>
> **Fix 2: Lock on load AND save**
> Currently `load_state()` doesn't acquire a lock but `save_state()` does. Two concurrent commands can load the same state, both modify it, and one write stomps the other. Wrap `load_state()` in the same lock.
>
> The lock creation itself has a race condition:
> ```python
> _state_locks.setdefault(session_id, Lock())
> ```
> Two threads can create different Lock objects. Fix by using a module-level lock to protect lock creation:
> ```python
> _meta_lock = Lock()
> def _get_lock(session_id):
>     with _meta_lock:
>         if session_id not in _state_locks:
>             _state_locks[session_id] = Lock()
>         return _state_locks[session_id]
> ```
>
> **Fix 3: Update DEFAULT_STATE**
> The current DEFAULT_STATE is missing keys that were added by later phases. Add these missing defaults:
> ```python
> "session_active": False,
> "session_started_at": None,
> "auto_advance": False,
> "tts_enabled": True,
> "free_form": True,
> ```
>
> **Fix 4: JSON decode error recovery**
> If a state file is corrupted JSON, `load_state()` currently returns empty defaults and the corrupted file stays. Rename the corrupted file to `{id}.json.corrupted` so it's preserved for debugging but doesn't keep failing.
>
> **Acceptance Criteria:**
> - [ ] All save operations use atomic write (temp file + os.replace)
> - [ ] Both load_state() and save_state() acquire locks
> - [ ] Lock creation uses a meta-lock to prevent race conditions
> - [ ] Corrupted JSON files are renamed, not silently ignored
> - [ ] DEFAULT_STATE has all required keys
> - [ ] No bare `except:` blocks in this file (use `except Exception as e:` with logging)

---

## Cluster 0.2 ✅ — Error Handling + Logging

### Prompt for AI Agent

> I need you to fix error handling across my Discord bot. There are 9 bare `except:` blocks in `discord_bot.py` that silently swallow ALL exceptions (including KeyboardInterrupt, SystemExit). I also need proper logging set up.
>
> **File 1: `utils/logger.py`** (~14 lines currently)
> This is almost empty. Expand it to set up proper Python logging:
> ```python
> import logging
> import os
> from logging.handlers import RotatingFileHandler
>
> def setup_logging():
>     """Configure logging for the bot. Call once at startup."""
>     log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
>     os.makedirs(log_dir, exist_ok=True)
>
>     # Root logger
>     root = logging.getLogger()
>     root.setLevel(logging.INFO)
>
>     # File handler (rotating, 5MB max, keep 3 backups)
>     fh = RotatingFileHandler(
>         os.path.join(log_dir, 'bot.log'),
>         maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
>     )
>     fh.setFormatter(logging.Formatter(
>         '%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s'
>     ))
>     root.addHandler(fh)
>
>     # Console handler
>     ch = logging.StreamHandler()
>     ch.setFormatter(logging.Formatter('%(levelname)-7s | %(name)-20s | %(message)s'))
>     ch.setLevel(logging.WARNING)
>     root.addHandler(ch)
> ```
> Keep the existing `log_message()` and `get_log_file()` functions as they are.
>
> **File 2: `discord_bot.py`** — Fix these 9 bare excepts:
>
> | Line | Location | Fix |
> |------|----------|-----|
> | 358 | `SkillCheckRollButton.disable_buttons()` | Change to `except discord.HTTPException as e:` and log warning |
> | 418 | Same class, duplicate | Same fix |
> | 4085 | `attack_cmd()` dice parsing | Change to `except (ValueError, IndexError) as e:` and send user error message |
> | 4404 | `send_handout()` DM send | Change to `except discord.Forbidden:` and log that DM send failed |
> | 4843 | Player notification send | Change to `except discord.Forbidden:` and log |
> | 4870 | Player notification send | Change to `except discord.Forbidden:` and log |
> | 5726 | `process_legendary_action()` | Change to `except Exception as e:` and log error, send fallback text message |
> | 5806 | `process_lair_action()` | Change to `except Exception as e:` and log error, send fallback text message |
> | 5911 | `on_voice_state_update()` | Change to `except Exception as e:` and log error — this is currently a bare except with NO handler body at all |
>
> **Also:** Add `from utils.logger import setup_logging` and call `setup_logging()` at the top of discord_bot.py before the bot starts.
>
> **Also:** Add `import logging` at the top of discord_bot.py and create a logger: `logger = logging.getLogger('discord_bot')`. Replace any `print()` calls with `logger.info()` or `logger.error()` as appropriate.
>
> **Acceptance Criteria:**
> - [ ] Zero bare `except:` blocks in discord_bot.py
> - [ ] All exception handlers log the error with `logger.error()` or `logger.warning()`
> - [ ] `setup_logging()` called at bot startup
> - [ ] Bot writes to `logs/bot.log` with rotation
> - [ ] Console shows warnings and errors only
> - [ ] `on_voice_state_update` has a real exception handler

---

## Cluster 0.3 ✅ — Config Consolidation

### Prompt for AI Agent

> I need you to consolidate scattered constants into `config.py`. Currently, timeouts, combat settings, and limits are hardcoded in random places across the codebase.
>
> **File:** `config.py` (currently ~39 lines)
>
> Add these settings (keep all existing ones):
>
> ```python
> # === Game Settings ===
> MAX_PROMPT_HISTORY = 20          # Rolling window of conversation exchanges (currently hardcoded as 10 in openai_service.py)
> MAX_MESSAGE_LENGTH = 2000        # Discord message limit (already exists but unused)
> DEFAULT_DIFFICULTY = "normal"
>
> # === Combat Settings ===
> COMBAT_TURN_TIMEOUT = 90         # Seconds before auto-advance (currently hardcoded in discord_bot.py)
> COMBAT_TURN_WARNING = 60         # Warning before timeout
> MAX_COMBAT_ROUNDS = 100          # Already exists
>
> # === Session Settings ===
> AUTO_SAVE_INTERVAL = 300         # Seconds between auto-saves (currently hardcoded as 5*60 in session_manager.py)
> INACTIVITY_TIMEOUT = 1800        # Seconds before session auto-pause (currently hardcoded as 30*60)
> SKILL_CHECK_TIMEOUT = 60         # Seconds to respond to skill check
>
> # === AI Settings ===
> AI_MODEL = "gpt-4o"             # Model for narration (currently hardcoded in openai_service.py)
> AI_MAX_TOKENS = 500              # Max response tokens (currently hardcoded)
> AI_TEMPERATURE = 0.9             # Creativity level (currently hardcoded)
>
> # === TTS Settings ===
> TTS_ENABLED = os.environ.get("TTS_ENABLED", "true").lower() == "true"
>
> # === NPC Settings ===
> MAX_NPC_MEMORY_FACTS = 50        # Cap on NPC knows_facts list to prevent memory bloat
> ```
>
> **Then update these files to import from config instead of using hardcoded values:**
>
> 1. `services/openai_service.py` — Replace hardcoded model name `"gpt-4o"`, `max_tokens=500`, `temperature=0.9`, and history window `10` with config imports
> 2. `utils/session_manager.py` — Replace hardcoded `AUTO_SAVE_INTERVAL` (300), `INACTIVITY_TIMEOUT` (1800) with config imports
> 3. `discord_bot.py` — Replace hardcoded timeout values (90, 60) with config imports. Replace `SkillCheckConfig.timeout = 60` with config import.
>
> **Do NOT change any logic.** Just move the constants and update the imports.
>
> **Acceptance Criteria:**
> - [ ] All game-relevant constants live in config.py
> - [ ] openai_service.py uses Config values for model, tokens, temperature, history window
> - [ ] session_manager.py uses Config values for save interval and timeout
> - [ ] discord_bot.py uses Config values for combat timeouts
> - [ ] No behavioral change — just consolidation

---

---

# PHASE 1: THE COG SPLIT ✅ COMPLETE

> **Why do this?** `discord_bot.py` is 7,000 lines. Every AI agent you ask to fix something in it will struggle with context limits. Splitting it into ~6 focused files (~800-1200 lines each) makes every future fix easier and faster.

---

## Cluster 1.1 ✅ — Cog Infrastructure + Campaign Core

### Prompt for AI Agent

> I'm splitting a 7,000-line `discord_bot.py` into discord.py Cogs. This is cluster 1 of 6 — setting up the infrastructure and extracting the most important commands.
>
> **Current structure:** Everything is in `discord_bot.py` using `@bot.tree.command()` decorators with a global `bot` object.
>
> **Target structure:**
> ```
> discord_bot.py          (300 lines - just bot setup + cog loading)
> cogs/
>   __init__.py
>   campaign.py           (core game loop: /campaign, /do, /context, /summarize, /remember, /help)
>   combat.py             (cluster 1.2)
>   character.py          (cluster 1.3)
>   world.py              (cluster 1.4)
>   social.py             (cluster 1.5)
>   utility.py            (cluster 1.6)
> ```
>
> **Step 1: Create `cogs/__init__.py`**
> ```python
> COGS = [
>     "cogs.campaign",
>     "cogs.combat",
>     "cogs.character",
>     "cogs.world",
>     "cogs.social",
>     "cogs.utility",
> ]
> ```
>
> **Step 2: Create `cogs/campaign.py`**
> Extract these commands from discord_bot.py into a `CampaignCog(commands.Cog)`:
> - `/campaign` (start a new campaign) — currently around lines 671-735
> - `/do` (player action — THE core game loop) — currently around lines 739-1157
> - `/context` — currently around line 1205
> - `/summarize` — currently around line 1229
> - `/remember` — currently around line 1282
> - `/help` — currently around line 6443
>
> The cog pattern should be:
> ```python
> import discord
> from discord.ext import commands
> from discord import app_commands
> import logging
> # ... other imports this cog needs
>
> logger = logging.getLogger(__name__)
>
> class CampaignCog(commands.Cog):
>     def __init__(self, bot: commands.Bot):
>         self.bot = bot
>
>     @app_commands.command(name="campaign", description="Start a new D&D campaign")
>     @app_commands.describe(theme="Optional theme")
>     async def campaign_start(self, interaction: discord.Interaction, theme: str = ""):
>         # ... moved code, with `self.bot` instead of `bot`
>
> async def setup(bot: commands.Bot):
>     await bot.add_cog(CampaignCog(bot))
> ```
>
> **Key conversion rules:**
> - `@bot.tree.command(...)` → `@app_commands.command(...)`
> - Functions get `self` as first parameter
> - References to `bot` become `self.bot`
> - Module-level state shared between cogs should stay in the utility modules (state_manager, etc.), NOT in the cog
> - Any helper functions that ONLY one cog uses should move into that cog
> - Any helper functions shared between cogs should stay in discord_bot.py for now (we'll clean up in 1.6)
>
> **Step 3: Modify `discord_bot.py`**
> - Remove the extracted commands
> - Add cog loading in `on_ready()`:
> ```python
> from cogs import COGS
>
> @bot.event
> async def on_ready():
>     for cog in COGS:
>         try:
>             await bot.load_extension(cog)
>             logger.info(f"Loaded cog: {cog}")
>         except Exception as e:
>             logger.error(f"Failed to load cog {cog}: {e}")
>     synced = await bot.tree.sync()
>     logger.info(f"Synced {len(synced)} commands")
> ```
> - Keep everything else in discord_bot.py for now (will be extracted in clusters 1.2-1.6)
> - Keep ALL imports at the top of discord_bot.py for now — cogs will import what they need independently
>
> **IMPORTANT:** The `/do` command is ~418 lines and is the heart of the bot. When extracting it, keep every piece of its existing logic intact. Don't refactor it, just move it. It references helper functions like `play_tts()`, `_active_channels`, `SkillCheckRollButton`, etc. These shared helpers should stay in discord_bot.py for now and be imported by the cog:
> ```python
> # In cogs/campaign.py:
> from discord_bot import play_tts, SkillCheckRollButton, _active_channels
> ```
> (We'll clean up circular imports in cluster 1.6)
>
> **Handling shared state:** The `play_tts()` function, `VoiceClientManager`, `SkillCheckRollButton` class, `SkillCheckConfig`, `CombatTimerManager` callbacks, and `_active_channels` dict are used by multiple cogs. For now, keep them in discord_bot.py and import them. In cluster 1.6 we'll extract them into a `cogs/shared.py`.
>
> **Acceptance Criteria:**
> - [ ] `cogs/` directory exists with `__init__.py`
> - [ ] `cogs/campaign.py` has CampaignCog with `/campaign`, `/do`, `/context`, `/summarize`, `/remember`, `/help`
> - [ ] `discord_bot.py` loads cogs in `on_ready()`
> - [ ] Bot starts without errors
> - [ ] `/campaign` command works (creates a campaign)
> - [ ] `/do` command works (sends action, gets AI response)
> - [ ] `/help` command works

---

## Cluster 1.2 ✅ — Combat Cog

### Prompt for AI Agent

> Continuing the cog split. Extract all combat commands from `discord_bot.py` into `cogs/combat.py`.
>
> **Commands to extract into `CombatCog(commands.Cog)`:**
> - `/fight` (start combat) — parses enemy strings, starts combat
> - `/attack` — player attack in combat  
> - `/nextturn` — advance to next combatant  
> - `/endcombat` — end combat encounter
> - `/hp` — modify HP (heal/damage)
> - `/deathsave` — death saving throw
> - `/turntimer` — toggle turn timer
> - `/timeleft` — check time remaining
>
> **Also extract these related pieces:**
> - `CombatTimerManager` class and its callbacks (`_on_turn_warning`, `_on_turn_timeout`)
> - `_active_channels` dict (move to `cogs/shared.py` — create this file)
> - `setup_timer_callbacks()` function
> - Any combat-specific helper functions
>
> **Create `cogs/shared.py`** for state/helpers shared between cogs:
> ```python
> """Shared state and helpers used across multiple cogs."""
> import discord
> from typing import Dict
> import logging
>
> logger = logging.getLogger(__name__)
>
> # Shared mutable state
> _active_channels: Dict[str, discord.TextChannel] = {}
>
> async def play_tts(interaction, text, voice_name):
>     """Play TTS in voice channel. Shared by campaign + combat cogs."""
>     # Move the play_tts implementation here
>     ...
> ```
>
> **Conversion rules (same as cluster 1.1):**
> - `@bot.tree.command(...)` → `@app_commands.command(...)`
> - Functions get `self` as first parameter
> - `bot` → `self.bot`
> - Import shared state from `cogs.shared`
>
> **Don't forget:** After extracting, remove the moved code from `discord_bot.py`. Update `cogs/campaign.py` to import `play_tts` from `cogs.shared` instead of from `discord_bot`.
>
> **Acceptance Criteria:**
> - [ ] `cogs/combat.py` has CombatCog with all 8 combat commands
> - [ ] `cogs/shared.py` exists with `play_tts`, `_active_channels`
> - [ ] `cogs/campaign.py` imports from `cogs.shared` (not discord_bot)
> - [ ] Combat commands removed from discord_bot.py
> - [ ] Bot starts without errors
> - [ ] `/fight goblin` starts combat
> - [ ] `/attack` `/nextturn` `/endcombat` all work

---

## Cluster 1.3 ✅ — Character Cog

### Prompt for AI Agent

> Continuing the cog split. Extract all character management commands from `discord_bot.py` into `cogs/character.py`.
>
> **Commands to extract into `CharacterCog(commands.Cog)`:**
> - `/character` — view/create character
> - `/roll` — dice rolls
> - `/rest` — long/short rest
> - `/inventory` — view/add/remove items
> - `/spells` — view spell list
> - `/cast` — cast a spell
> - `/prepare` — prepare spells
> - `/learn` — learn spell/cantrip
> - `/levelup` — level up character
> - `/resources` — view class resources
> - `/attune` — attune to magic item
> - `/unattune` — remove attunement
> - `/attunement` — view attunement slots
> - `/encumbrance` — check carry weight
> - `/groupcheck` — group skill check
> - `/savingthrow` — saving throw
> - `/passivecheck` — passive perception etc.
> - `/xp` — view/award XP
> - `/awardparty` — award XP to whole party
>
> This is the biggest extraction (~19 commands). Many are simple CRUD operations on character data.
>
> **Also extract:** `SkillCheckRollButton` class and `SkillCheckConfig` → move to `cogs/shared.py`
>
> **Acceptance Criteria:**
> - [ ] `cogs/character.py` has CharacterCog with all character commands
> - [ ] `SkillCheckRollButton` moved to `cogs/shared.py`
> - [ ] All extracted commands removed from discord_bot.py
> - [ ] Bot starts without errors
> - [ ] `/character` `/roll 1d20` `/inventory` all work

---

## Cluster 1.4 ✅ — World & Environment Cog

### Prompt for AI Agent

> Continuing the cog split. Extract all world/environment commands from `discord_bot.py` into `cogs/world.py`.
>
> **Commands to extract into `WorldCog(commands.Cog)`:**
> - `/environment` — view environment status
> - `/trap` — create/list/trigger traps
> - `/detecttrap` — attempt trap detection
> - `/disarmtrap` — attempt trap disarm
> - `/weather` — set/view weather
> - `/lighting` — set/view lighting
> - `/time` — view/advance/set in-game time
> - `/location` — set location with auto-preset
> - `/hazard` — create/list hazards
> - `/terrain` — create/list terrain zones
> - `/cover` — calculate cover between positions
> - `/travel` — start a journey
> - `/travelstatus` — view travel progress
> - `/traveladvance` — advance travel by hours
> - `/travelcancel` — cancel journey
> - `/randomencounter` — generate combat encounter
> - `/encounter` — generate non-combat encounter
> - `/encountercheck` — roll for random encounter
> - `/worldmap` — view all known locations
> - `/fasttravel` — travel to visited location
> - `/addlocation` — add location to world map
> - `/setlocation` — set party's current location
> - `/locationinfo` — view location details
>
> **Acceptance Criteria:**
> - [ ] `cogs/world.py` has WorldCog with all 23 world commands
> - [ ] All extracted commands removed from discord_bot.py
> - [ ] Bot starts without errors
> - [ ] `/weather`, `/time`, `/worldmap` all work

---

## Cluster 1.5 ✅ — Social Cog (NPCs + Quests)

### Prompt for AI Agent

> Continuing the cog split. Extract all NPC and quest commands from `discord_bot.py` into `cogs/social.py`.
>
> **Commands to extract into `SocialCog(commands.Cog)`:**
> - `/npc` — view NPCs or specific NPC
> - `/npcdisposition` — adjust NPC disposition
> - `/faction` — view/create factions
> - `/reputation` — adjust faction standing
> - `/shop` — view/create merchant shop
> - `/buy` — purchase from merchant
> - `/sell` — sell to merchant
> - `/quest` — view/create quests
> - `/quests` — view full quest log
> - `/questtemplate` — create from template
> - `/questobjective` — add objective
> - `/questprogress` — update progress
> - `/questnote` — add note
> - `/questcomplete` — complete quest
> - `/questabandon` — abandon quest
> - `/rumors` — view rumors
> - `/investigaterumor` — convert rumor to quest
> - `/questchain` — link quests
> - `/acceptquest` — accept available quest
>
> **Acceptance Criteria:**
> - [ ] `cogs/social.py` has SocialCog with all 19 NPC/quest commands
> - [ ] All extracted commands removed from discord_bot.py
> - [ ] Bot starts without errors
> - [ ] `/npc`, `/quest`, `/shop` all work

---

## Cluster 1.6 ✅ — Utility Cog + Final Cleanup

### Prompt for AI Agent

> Final cluster of the cog split. Extract all remaining commands from `discord_bot.py` into `cogs/utility.py` and `cogs/session.py`, then clean up discord_bot.py to be just the bot shell.
>
> **Commands for `UtilityCog` in `cogs/utility.py`:**
> - `/handout` — create/distribute handouts
> - `/secret` — whisper secret to player
> - `/mysecrets` — view received secrets
> - `/map` — display battle map
> - `/ambient` — set ambient mood
> - `/sfx` — play sound effect
> - `/reaction` — NPC reaction roll
> - `/loot` — generate loot
> - `/treasure` — generate treasure
> - `/identify` — identify magic item
> - `/lootpile` — view pending loot
> - `/claimloot` — claim item from loot pile
> - `/claimgold` — claim gold
> - `/splitgold` — split gold evenly
>
> **Commands for `SessionCog` in `cogs/session.py`:**
> - `/session` — view/end/pause session
> - `/sessionrecap` — TTS recap
> - `/recover` — restore from crash
> - `on_voice_state_update` event listener (move from discord_bot.py)
>
> **Clean up `discord_bot.py`:**
> After all extractions, discord_bot.py should ONLY contain:
> ```python
> """AI Dungeon Master Discord Bot"""
> import discord
> from discord.ext import commands
> import os
> import logging
> from dotenv import load_dotenv
> from config import Config
> from utils.logger import setup_logging
> from cogs import COGS
>
> load_dotenv()
> setup_logging()
> logger = logging.getLogger(__name__)
>
> intents = discord.Intents.default()
> intents.message_content = True
> intents.voice_states = True
> intents.members = True
>
> bot = commands.Bot(command_prefix="!", intents=intents)
>
> @bot.event
> async def on_ready():
>     logger.info(f'{bot.user} connected to Discord')
>     for cog in COGS:
>         try:
>             await bot.load_extension(cog)
>             logger.info(f"Loaded: {cog}")
>         except Exception as e:
>             logger.error(f"Failed to load {cog}: {e}")
>     try:
>         synced = await bot.tree.sync()
>         logger.info(f"Synced {len(synced)} commands")
>     except Exception as e:
>         logger.error(f"Sync failed: {e}")
>
> if __name__ == "__main__":
>     bot.run(Config.DISCORD_TOKEN)
> ```
>
> **Verify:** Make sure `cogs/shared.py` contains all shared utilities (`play_tts`, `_active_channels`, `SkillCheckRollButton`, `SkillCheckConfig`, `VoiceClientManager` instance). Every cog should import from `cogs.shared`, never from `discord_bot`.
>
> **Fix circular imports:** If any cog imports from discord_bot.py or vice versa, move the shared code to `cogs/shared.py`.
>
> **Acceptance Criteria:**
> - [ ] discord_bot.py is under 50 lines
> - [ ] All ~60 commands distributed across 6 cog files
> - [ ] No circular imports
> - [ ] `cogs/shared.py` has all shared state and helpers
> - [ ] Bot starts and all commands register
> - [ ] Run `/help` to verify all commands are listed
> - [ ] Test at least 1 command from each cog

---

---

# PHASE 2: CORE GAME LOOP ✅ COMPLETE

---

## Cluster 2.1 ✅ — /do Action Loop Reliability

### Prompt for AI Agent

> The `/do` command in `cogs/campaign.py` is the heart of the bot — it's how players take actions. It's ~418 lines and currently has a fragile pipeline of subsystem calls where any failure breaks the whole thing. I need it made reliable.
>
> **Current flow (lines ~739-1157 in original, now in cogs/campaign.py):**
> ```
> 1. Load character & state
> 2. Process inline dice rolls
> 3. Resource consumption (Phase 4)
> 4. Trap trigger checks (Phase 7)
> 5. Detect player attack intent (Phase 11)
> 6. Build system prompt + call OpenAI API
> 7. Auto-detect NPCs from narration (Phase 5)
> 8. Parse quest progress (Phase 6/13)
> 9. Environment changes (Phase 12)
> 10. Travel & exploration tags (Phase 14)
> 11. Process loot items
> 12. Parse skill checks
> 13. Combat trigger detection (Phase 11)
> 14. Format output + save state + TTS
> ```
>
> **Problem:** Steps 3-13 are each wrapped in their own try/except blocks, but many use bare `except:` or `except Exception: pass`. If step 7 (NPCs) crashes, the error is swallowed and steps 8-13 still run with potentially corrupted state.
>
> **Fix: Wrap each subsystem call in a resilient pattern:**
> ```python
> notifications = []  # Collect all UI notifications
>
> # Each subsystem gets its own isolated try/except with logging
> # Failures are logged and skipped — they don't break the pipeline
> try:
>     npc_results = process_npc_from_narration(channel_id, ai_response)
>     if npc_results:
>         notifications.extend(npc_results)
> except Exception as e:
>     logger.error(f"NPC processing failed: {e}", exc_info=True)
>     # Continue — NPC detection failing shouldn't break the game
> ```
>
> Apply this pattern to ALL subsystem calls (steps 3-13). Each one:
> 1. Has its own try/except
> 2. Logs the full exception with traceback (`exc_info=True`)
> 3. Collects notifications into a list (not inline string building)
> 4. Never uses bare `except:` — always `except Exception as e:`
>
> **Also fix:** The massive notification string that's built by concatenation throughout the function. Replace it with a `notifications: list[str]` that each subsystem appends to, then join at the end:
> ```python
> # At the end, before sending:
> notification_text = "\n".join(notifications) if notifications else ""
> ```
>
> **Also fix:** State is loaded at the top and saved at the bottom, but if the function errors out mid-way, state changes from steps 1-6 are lost. Move `save_state()` to a `finally` block:
> ```python
> try:
>     # ... all the processing ...
> finally:
>     save_state(channel_id, state)
> ```
>
> **Acceptance Criteria:**
> - [ ] Every subsystem call in /do has isolated error handling
> - [ ] All errors logged with full tracebacks
> - [ ] If OpenAI fails, user gets a clear error message (not silent failure)
> - [ ] If NPC/quest/environment detection fails, the AI response still reaches the player
> - [ ] State always saved (even on partial failure)
> - [ ] Notifications collected in a list, not built by string concatenation

---

## Cluster 2.2 ✅ — AI Tag Detection Overhaul

### Prompt for AI Agent

> The bot relies on the AI outputting structured tags like `[COMBAT: 3 goblins]` or `[QUEST: name="Rescue"]`. Currently, tag detection is spread across 5 different modules with inconsistent regex patterns that fail on minor format variations. I need a unified tag parser.
>
> **Create `utils/tag_parser.py`** — a single module that handles ALL tag detection:
>
> ```python
> """
> Unified parser for structured tags in AI narration.
> 
> Supported tags:
>   [COMBAT: 3 goblins, 1 hobgoblin]
>   [SURPRISE: enemies]
>   [QUEST: name="Rescue the Princess", type=rescue, difficulty=hard]
>   [QUEST_COMPLETE: "Rescue the Princess"]
>   [QUEST_PROGRESS: "Quest Name", objective=1]
>   [RUMOR: "Strange lights at the cemetery"]
>   [QUEST_HOOK: name="Mystery", description="Investigate the lights"]
>   [OBJECTIVE: "Find the hidden entrance"]
>   [QUEST_CHAIN: parent="Main Quest", child="Sequel"]
>   [WEATHER: heavy rain]
>   [LIGHTING: dim]
>   [LOCATION: Dark Cave]
>   [TIME: 3 hours pass]
>   [TRAP: pit trap at entrance]
>   [HAZARD: lava pool, 2d6 fire]
>   [TRAVEL: destination="Phandalin", distance=15, terrain=forest]
>   [LOCATION_DISCOVERED: name="Ruined Tower", terrain=hills, poi=true]
>   [ARRIVAL: "Phandalin"]
>   [DISTANCE_REVEALED: from="A" to="B" miles=100]
>   [LOOT: 50gp, Longsword, Potion of Healing]
>   [SKILL_CHECK: Perception DC 15]
> ```
>
> **Design principles:**
> 1. **One regex per tag type**, but **forgiving**: optional spaces, case-insensitive tag names, flexible quoting
> 2. **One entry point**: `parse_all_tags(text: str) -> ParsedTags` that returns a dataclass with all detected tags
> 3. **Attribute parser** that handles `key="value"`, `key='value'`, `key=value` and values with apostrophes (Bob's Quest)
> 4. **Strip tags from display text**: `strip_tags(text: str) -> str` removes all `[TAG: ...]` blocks so players don't see them
>
> **The key regex should be forgiving:**
> ```python
> # Match [TAG_NAME: content] with flexible whitespace
> TAG_PATTERN = re.compile(
>     r'\[\s*(\w+)\s*:\s*([^\]]+)\]',
>     re.IGNORECASE
> )
> ```
>
> **Attribute parsing should handle edge cases:**
> ```python
> # These should ALL parse correctly:
> # name="Bob's Quest"      → {"name": "Bob's Quest"}
> # name='Rescue Mission'   → {"name": "Rescue Mission"}
> # name=Rescue              → {"name": "Rescue"}
> # distance=15              → {"distance": "15"}
> # terrain = forest         → {"terrain": "forest"}
> ```
>
> **Return type:**
> ```python
> @dataclass
> class ParsedTags:
>     combat: list[dict]          # [{enemies: "3 goblins, 1 orc", surprise: "enemies"}]
>     quests: list[dict]          # [{name: "...", type: "...", difficulty: "..."}]
>     quest_completions: list[str]  # ["Quest Name"]
>     quest_progress: list[dict]
>     rumors: list[str]
>     quest_hooks: list[dict]
>     objectives: list[str]
>     quest_chains: list[dict]
>     weather: list[str]
>     lighting: list[str]
>     locations: list[str]
>     time_changes: list[str]
>     traps: list[str]
>     hazards: list[str]
>     travel: list[dict]
>     discoveries: list[dict]
>     arrivals: list[str]
>     distances: list[dict]
>     loot: list[str]
>     skill_checks: list[dict]
>     raw_tags: list[tuple]       # All (tag_name, content) pairs found
> ```
>
> **Then update the existing modules** to use `tag_parser.parse_all_tags()` instead of their own regex:
> - `utils/combat_trigger.py` — use `parsed.combat` instead of its own `STRUCTURED_COMBAT_PATTERN`
> - `utils/quest_manager.py` — use `parsed.quests`, `parsed.quest_completions`, etc. instead of its 7 separate patterns
> - `utils/world_generator.py` — use `parsed.weather`, `parsed.lighting`, etc.
> - `utils/world_map.py` — use `parsed.travel`, `parsed.discoveries`, etc.
>
> Each of those modules should keep their **processing logic** (what to do when a tag is found) but delegate **detection** to tag_parser.
>
> **Acceptance Criteria:**
> - [ ] `utils/tag_parser.py` exists with `parse_all_tags()` and `strip_tags()`
> - [ ] All tag types detected with single forgiving regex approach
> - [ ] Attribute parser handles quotes, apostrophes, missing quotes
> - [ ] `strip_tags()` removes all tags from display text
> - [ ] Other modules updated to use tag_parser for detection
> - [ ] `[COMBAT:3 goblins]` (no space after colon) works
> - [ ] `[combat: 3 goblins]` (lowercase) works
> - [ ] `[QUEST: name="Bob's Quest"]` (apostrophe in value) works

---

## Cluster 2.3 ✅ — Prompt Builder Overhaul

### Prompt for AI Agent

> The prompt builder (`utils/prompt_builder.py`, ~258 lines) constructs the system prompt sent to GPT-4o. It currently dumps EVERYTHING into the prompt — all NPCs, all quests, all environment, all travel, all world map, all session pacing — creating a massive context that costs more and makes the AI lose focus.
>
> **Read the full file first**, then apply these fixes:
>
> **Fix 1: Add a token budget system**
> The system prompt should aim for ~1500 tokens max. Build context in priority order and stop when budget is reached:
> ```python
> CONTEXT_PRIORITY = [
>     ("combat", get_combat_context),          # If in combat, this is #1
>     ("active_quests", get_quest_context),     # Current objectives
>     ("nearby_npcs", get_npc_context),         # Who's here
>     ("environment", get_environment_context), # Where are we
>     ("world", get_world_context),             # Broader world
>     ("travel", get_travel_context),           # Travel progress
>     ("pacing", get_pacing_context),           # Session pacing
>     ("map", get_map_context),                 # World map
> ]
>
> def build_context_sections(state, channel_id):
>     sections = []
>     total_chars = 0
>     MAX_CHARS = 6000  # ~1500 tokens
>     for name, getter in CONTEXT_PRIORITY:
>         try:
>             section = getter(channel_id) if channel_id else ""
>             if section and total_chars + len(section) < MAX_CHARS:
>                 sections.append(section)
>                 total_chars += len(section)
>         except Exception:
>             continue  # Skip failed context sources
>     return "\n\n".join(sections)
> ```
>
> **Fix 2: Better tag instructions**
> Currently the prompt lists all tag formats in a big block. Restructure it so:
> - Tags are listed concisely with one-line examples
> - Instructions clearly say tags are OPTIONAL — the AI should only use them when relevant
> - Remove the "example narration" blocks (wastes tokens)
>
> **Fix 3: Conditional sections**
> Only include combat tag instructions when NOT in combat. Only include travel instructions when NOT already traveling. Only include quest tag instructions when there are active quests to reference.
>
> **Fix 4: Fix the try/except import blocks**
> Currently each context source is wrapped in:
> ```python
> try:
>     from utils.npc_manager import get_nearby_npcs
> except:
>     pass
> ```
> These should be top-level imports that fail early on startup, not silent runtime failures.
>
> **Fix 5: Add the campaign summary context**
> The `campaign_summary` from state should be included near the top — it's the AI's "memory" of what happened previously and is critical for continuity.
>
> **Acceptance Criteria:**
> - [ ] Token budget system limits context size
> - [ ] Context sections prioritized (combat > quests > NPCs > etc.)
> - [ ] Failed context sources don't break prompt building
> - [ ] Tag instructions are concise (not verbose examples)
> - [ ] Tag instructions conditional on game state
> - [ ] Imports are at top-level, not in try/except blocks
> - [ ] Campaign summary included as high-priority context

---

## Cluster 2.4 ✅ — OpenAI Service Hardening

### Prompt for AI Agent

> Fix `services/openai_service.py` (~695 lines) for reliability and better conversation memory.
>
> **Fix 1: Conversation history window too small**
> Currently hardcoded to keep last 10 messages (5 exchanges). After that, the AI forgets EVERYTHING. The `campaign_summary` field exists but isn't being leveraged well.
>
> Change the history management:
> - Import `MAX_PROMPT_HISTORY` from config (set to 20 in Cluster 0.3)
> - Use that value instead of hardcoded 10
> - When trimming history, keep the first 2 messages (initial campaign setup) and the last N messages. Don't just slice from the end — the opening context matters.
>
> **Fix 2: Specific exception handling**
> Replace the generic `except Exception as e:` in API calls with specific OpenAI errors:
> ```python
> import openai
> 
> try:
>     response = client.chat.completions.create(...)
> except openai.APIConnectionError as e:
>     logger.error(f"OpenAI connection failed: {e}")
>     return "The mystical energies are disrupted... (Connection error - try again)"
> except openai.RateLimitError as e:
>     logger.warning(f"OpenAI rate limit: {e}")
>     return "The arcane forces need a moment to recharge... (Rate limited - wait a moment)"
> except openai.APIStatusError as e:
>     logger.error(f"OpenAI API error {e.status_code}: {e}")
>     return "The cosmic threads are tangled... (API error)"
> ```
>
> **Fix 3: Use model from config**
> Replace hardcoded `"gpt-4o"`, `max_tokens=500`, `temperature=0.9` with Config imports (from Cluster 0.3).
>
> **Fix 4: Add timeout to API calls**
> Add `timeout=30` to `client.chat.completions.create()` calls to prevent hanging forever if OpenAI is slow.
>
> **Acceptance Criteria:**
> - [ ] History window uses Config value (20 exchanges)
> - [ ] History trimming preserves first 2 messages + last N
> - [ ] Specific OpenAI error types caught with user-friendly messages
> - [ ] Model/tokens/temperature from config
> - [ ] API calls have 30-second timeout
> - [ ] All error paths return a string (not None or exception)

---

---

# PHASE 3: COMBAT ✅ COMPLETE

---

## Cluster 3.1 ✅ — Combat Manager Bug Fixes

### Prompt for AI Agent

> Fix bugs in `utils/combat_manager.py` (~703 lines). These are actual D&D rules violations and crash bugs.
>
> **Bug 1: Critical hit damage calculation is WRONG**
> Current code (around line 202):
> ```python
> if is_crit:
>     damage = damage_result * 2  # WRONG
> ```
> D&D 5e rules: On a crit, you roll the damage dice TWICE, then add the modifier once.
> - Example: `1d8+3` → crit → roll `2d8+3` (not `(1d8+3)*2`)
>
> Fix:
> ```python
> if is_crit:
>     # Roll damage dice twice, keep single modifier
>     crit_roll = roll_dice(damage_dice)[0]  # Roll again
>     # Extract modifier from original roll
>     base_roll = damage_result
>     # For crits: add an extra dice roll (simplified)
>     damage = damage_result + roll_dice(damage_dice.split('+')[0].split('-')[0])[0]
> ```
> Actually, the cleanest approach: parse the dice expression to separate dice from modifier, roll dice portion twice, add modifier once.
>
> **Bug 2: Initiative tiebreaker**
> Current code sorts by initiative only. D&D 5e uses Dex modifier as tiebreaker.
> ```python
> # Current:
> state['turn_order'] = sorted(state['combatants'], key=lambda x: x['initiative'], reverse=True)
>
> # Fix:
> state['turn_order'] = sorted(
>     state['combatants'],
>     key=lambda x: (x['initiative'], x.get('init_bonus', 0)),
>     reverse=True
> )
> ```
>
> **Bug 3: Condition duration tracking**
> Conditions (stunned, poisoned, etc.) never expire. Add a duration field:
> ```python
> # When adding a condition:
> condition = {"name": "stunned", "duration": 1}  # 1 = until end of next turn
>
> # In next_turn(), decrement durations:
> for condition in combatant.get('conditions', []):
>     if 'duration' in condition and condition['duration'] is not None:
>         condition['duration'] -= 1
>
> # Remove expired:
> combatant['conditions'] = [c for c in combatant.get('conditions', [])
>                            if c.get('duration') is None or c['duration'] > 0]
> ```
>
> **Bug 4: Combatant ID type normalization**
> IDs are sometimes strings (user IDs), sometimes ints. Normalize to always be strings:
> ```python
> # In start_combat() and any function that creates combatants:
> combatant['id'] = str(combatant['id'])
> ```
>
> **Bug 5: Missing initiative key crash**
> If a combatant dict somehow has no 'initiative' key, sorting crashes. Add a default:
> ```python
> key=lambda x: (x.get('initiative', 0), x.get('init_bonus', 0))
> ```
>
> **Acceptance Criteria:**
> - [ ] Crit damage rolls dice twice (not doubles result)
> - [ ] Initiative uses Dex modifier as tiebreaker
> - [ ] Conditions have optional duration that auto-decrements
> - [ ] Expired conditions auto-removed at start of turn
> - [ ] All combatant IDs stored as strings
> - [ ] No KeyError crashes on missing initiative

---

## Cluster 3.2 ✅ — Combat Flow + Enemy AI Fixes

### Prompt for AI Agent

> Fix issues in `utils/combat_flow.py` (~868 lines) and `utils/enemy_ai.py` (~929 lines).
>
> **Fix 1: Timer race condition in combat_flow.py**
> The `_run_timer()` method checks if a timer is still active, then sleeps, then checks again. Between the check and the action, the timer could be cancelled. Use `asyncio.Event` instead:
> ```python
> class TurnTimerState:
>     def __init__(self, ...):
>         self.cancelled = asyncio.Event()
>         ...
>
> async def _run_timer(self, timer_state):
>     try:
>         # Wait for warning time OR cancellation
>         await asyncio.wait_for(
>             timer_state.cancelled.wait(),
>             timeout=warning_wait
>         )
>         return  # Cancelled
>     except asyncio.TimeoutError:
>         pass  # Timer expired naturally, send warning
>     
>     # ... send warning ...
>     
>     try:
>         await asyncio.wait_for(
>             timer_state.cancelled.wait(),
>             timeout=remaining
>         )
>         return  # Cancelled
>     except asyncio.TimeoutError:
>         pass  # Timer expired, auto-advance
> ```
>
> **Fix 2: Channel reference cleanup**
> In `_active_channels` (now in `cogs/shared.py`), references are stored but never cleaned up except in combat end. Add cleanup:
> ```python
> # In end_combat or wherever combat cleanup happens:
> _active_channels.pop(channel_id, None)  # Safe delete
> ```
>
> **Fix 3: Graceful AI narration fallback**
> When `narrate_enemy_action()` fails (OpenAI down), the entire enemy turn fails silently. Add a fallback:
> ```python
> try:
>     narration = await narrate_enemy_action(turn_result, combat_state)
> except Exception as e:
>     logger.error(f"AI narration failed: {e}")
>     # Build a simple mechanical description
>     narration = f"**{attacker['name']}** attacks **{target['name']}**"
>     if turn_result.get('hit'):
>         narration += f" and deals {turn_result.get('damage', 0)} damage!"
>     else:
>         narration += " but misses!"
> ```
>
> **Fix 4: Post-combat loot consolidation**
> There are currently two loot systems competing. `process_post_combat()` tries Phase 11 loot generation, falls back to an old system. Remove the old fallback and just use one system:
> - Use `generate_loot_for_enemies()` from `combat_trigger.py` as the single loot source
> - If it fails, generate NO loot (don't fall back to a broken system)
> - Log the error
>
> **Acceptance Criteria:**
> - [ ] Turn timer uses asyncio.Event for cancellation (no race conditions)
> - [ ] Channel references cleaned up when combat ends
> - [ ] Enemy turns still work when OpenAI is unreachable (fallback text)
> - [ ] Single loot generation system (no competing fallbacks)

---

## Cluster 3.3 ✅ — Combat → Loot → Inventory Pipeline

### Prompt for AI Agent

> The loot pipeline is currently broken end-to-end. Loot gets generated but doesn't reliably reach player inventories. Fix the full pipeline.
>
> **File 1: `utils/inventory_manager.py`**
>
> Problem: `_pending_loot` dict is in-memory only. Bot restart = all unclaimed loot lost.
>
> Fix: Persist pending loot to JSON files in `state/loot/`:
> ```python
> LOOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'state', 'loot')
> os.makedirs(LOOT_DIR, exist_ok=True)
>
> def _save_pending_loot(channel_id, loot_data):
>     path = os.path.join(LOOT_DIR, f'{channel_id}_loot.json')
>     # Use atomic writes (same pattern as state_manager)
>     ...
>
> def _load_pending_loot(channel_id):
>     path = os.path.join(LOOT_DIR, f'{channel_id}_loot.json')
>     ...
> ```
>
> Problem: Gold splitting loses remainder. `13 // 3 = 4` each, 1gp vanishes.
>
> Fix:
> ```python
> def split_gold_evenly(channel_id):
>     per_player = total_gp // num_players
>     remainder = total_gp % num_players
>     # Give remainder to first player (or add to party fund)
>     ...
>     return f"Split {total_gp}gp: {per_player}gp each" + (f" ({remainder}gp remainder to {first_player})" if remainder else "")
> ```
>
> Problem: `claim_loot_gold(channel_id, user_id, amount=None)` — if amount is None, first claimant takes everything.
>
> Fix: When `amount is None`, split evenly among party instead of giving all to one player.
>
> **File 2: `utils/loot_manager.py`**
> Review this file. If it duplicates functionality in inventory_manager.py or combat_trigger.py, consolidate. There should be ONE loot generation path, not three.
>
> **File 3: `utils/combat_trigger.py`**
> The `generate_loot_for_enemies()` function generates loot but doesn't call anything in inventory_manager to create a claimable loot pile. Wire it up:
> ```python
> def generate_and_register_loot(channel_id, defeated_enemies):
>     loot = generate_loot_for_enemies(defeated_enemies)
>     from utils.inventory_manager import create_loot_pile
>     create_loot_pile(channel_id, loot['items'], loot['currency'])
>     return loot
> ```
>
> **Acceptance Criteria:**
> - [ ] Pending loot persisted to disk (survives bot restart)
> - [ ] Gold splitting handles remainders (no gold lost)
> - [ ] `claim_loot_gold(amount=None)` splits evenly (not all to one player)
> - [ ] Single loot generation path: combat_trigger generates → inventory_manager stores → claim commands distribute
> - [ ] No duplicate loot generation code across modules

---

---

# PHASE 4: CHARACTER & PROGRESSION ✅ COMPLETE

---

## Cluster 4.1 ✅ — Character Manager Fixes

### Prompt for AI Agent

> Fix bugs in `utils/character_manager.py` (~1359 lines).
>
> **Bug 1: HP can go negative on CON decrease**
> When CON decreases via `set_stat()`, `max_hp` is recalculated but could theoretically go to 0 or negative for very low level characters with massive CON loss.
> ```python
> # After recalculating max_hp:
> data['max_hp'] = max(1, new_max_hp)  # Minimum 1 HP
> data['hp'] = min(data['hp'], data['max_hp'])  # Current can't exceed max
> ```
>
> **Bug 2: Death save doesn't clear "Dead" condition**
> After 3 successful death saves, character is set to 1 HP but if a "Dead" or "Unconscious" condition was manually added, it persists.
> ```python
> # After stabilizing (3 successes):
> data['hp'] = 1
> data['death_saves'] = {'successes': 0, 'failures': 0}
> # Clear death-related conditions
> data['conditions'] = [c for c in data.get('conditions', [])
>                       if c.lower() not in ('dead', 'unconscious', 'dying')]
> ```
>
> **Bug 3: long_rest() Lay on Hands is semantically wrong but functionally fine**
> `data['lay_on_hands_pool'] = data['level'] * 5` — this is actually correct per D&D 5e Paladin rules. The pool IS `level * 5`. No fix needed, but add a comment clarifying this.
>
> **Bug 4: Spell slot recovery doesn't handle Warlock pact magic**
> Warlocks recover all slots on short rest (not long rest). Currently `short_rest()` doesn't recover any spell slots.
>
> Fix: Check class and recover warlock slots on short rest:
> ```python
> def short_rest(user_id):
>     data = load_character(user_id)
>     # ... existing healing ...
>     
>     # Warlocks recover spell slots on short rest
>     if data.get('class', '').lower() == 'warlock':
>         data['spell_slots'] = data.get('max_spell_slots', {}).copy()
> ```
>
> **Bug 5: dnd5e_data import try/except**
> The file wraps `from .dnd5e_data import ...` in try/except. Since dnd5e_data.py exists, this should be a normal import that fails loudly on startup if missing:
> ```python
> from .dnd5e_data import (
>     CLASSES, RACES, SPELLS, get_class_data, get_spell,
>     get_ability_modifier as _dnd_get_ability_modifier
> )
> ```
> Remove the `try/except ImportError` wrapper and the `DND_DATA_AVAILABLE` flag. Just let it fail on startup.
>
> **Acceptance Criteria:**
> - [ ] max_hp never goes below 1
> - [ ] Death save stabilization clears death-related conditions
> - [ ] Warlock spell slots recovered on short rest
> - [ ] dnd5e_data import fails loudly (no silent fallback)
> - [ ] All existing character tests pass (run manually)

---

## Cluster 4.2 ✅ — Quest → XP → Rewards Pipeline

### Prompt for AI Agent

> Wire up quest completion to actually award XP and items to characters. Currently quest completion is tracked but rewards never reach the characters.
>
> **File 1: `utils/quest_manager.py`**
>
> Fix 1: The `complete_quest()` function should return the rewards so the caller can distribute them:
> ```python
> def complete_quest(channel_id, quest_name):
>     # ... mark complete ...
>     return {
>         "quest_name": quest.name,
>         "xp": quest.rewards.xp,
>         "gold": quest.rewards.gold,
>         "items": quest.rewards.items,
>         "reputation": quest.rewards.reputation
>     }
> ```
>
> Fix 2: Tag parsing for `[QUEST: name="Bob's Quest"]` breaks on apostrophes. The attribute parser uses this regex:
> ```python
> re.findall(r'(\w+)\s*=\s*"([^"]*)"', content)
> ```
> This fails on `name="Bob's Quest"` because the content works fine (no issue with apostrophes inside double quotes), BUT it also fails on `name='Bob\'s Quest'` with single quotes. The real issue is the parser doesn't try `key=value_without_quotes`:
>
> Use the tag_parser from Cluster 2.2 instead. If that cluster hasn't been done yet, fix the regex:
> ```python
> # Match key="value" OR key='value' OR key=unquoted_value
> attrs = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))', content)
> ```
>
> Fix 3: `convert_rumor_to_quest()` creates duplicates. Add a check:
> ```python
> existing = get_quest_by_name(channel_id, quest_name)
> if existing:
>     return None, f"Quest '{quest_name}' already exists"
> ```
>
> **File 2: `cogs/social.py` (or wherever /questcomplete lives after cog split)**
>
> When `/questcomplete` is called, distribute rewards:
> ```python
> rewards = complete_quest(channel_id, quest_name)
> if rewards:
>     # Award XP to all party members
>     from utils.xp_manager import award_xp
>     state = load_state(channel_id)
>     for player in state.get('players', []):
>         user_id = player.get('user_id')
>         if user_id:
>             award_xp(user_id, rewards['xp'] // len(state['players']))
>     
>     # Award gold to party (split)
>     # ... distribute gold and items ...
> ```
>
> **Acceptance Criteria:**
> - [ ] Quest completion returns reward data
> - [ ] XP distributed to party members on quest completion
> - [ ] Gold distributed on quest completion
> - [ ] Quest tag parsing handles apostrophes in names
> - [ ] Rumor → quest conversion won't create duplicates
> - [ ] User sees reward summary after quest completion

---

---

# PHASE 5: WORLD SYSTEMS ✅ COMPLETE

---

## Cluster 5.1 ✅ — NPC Manager Fixes

### Prompt for AI Agent

> Fix bugs in `utils/npc_manager.py` (~963 lines).
>
> **Bug 1: Gender detection is useless**
> `detect_gender()` counts gendered pronouns in the ENTIRE narration text. "He walked into the tavern where she was waiting" has both. It returns whichever has more matches, which is basically random for typical narration.
>
> Fix: Only look at pronouns in the same sentence as the NPC's name:
> ```python
> def detect_gender(text: str, npc_name: str) -> str:
>     # Find sentences containing the NPC's name
>     sentences = re.split(r'[.!?]', text)
>     relevant = [s for s in sentences if npc_name.lower() in s.lower()]
>     if not relevant:
>         return "unknown"
>     relevant_text = " ".join(relevant)
>     # Count pronouns only in relevant sentences
>     male = len(re.findall(r'\b(he|him|his)\b', relevant_text, re.I))
>     female = len(re.findall(r'\b(she|her|hers)\b', relevant_text, re.I))
>     if male > female:
>         return "male"
>     elif female > male:
>         return "female"
>     return "unknown"
> ```
>
> **Bug 2: Shop buy_rate not applied**
> `buy_from_shop()` computes price with faction discount but the `buy_rate` multiplier from the shop object is calculated and then ignored. Find where `buy_rate` is set and ensure it's actually multiplied into the final price.
>
> **Bug 3: Shop gold not saved after transactions**
> After `buy_from_shop()` modifies the shop's gold and inventory, it doesn't call `save_npcs()`. The changes are lost.
> ```python
> def buy_from_shop(channel_id, npc_name, item_name, user_id, quantity=1):
>     # ... existing logic ...
>     shop.gold += final_price
>     shop.items[item_name]['quantity'] -= quantity
>     save_npcs(channel_id, npcs)  # ADD THIS
>     save_character(user_id, char_data)
> ```
> Same for `sell_to_shop()`.
>
> **Bug 4: NPC memory unbounded growth**
> `record_npc_interaction()` appends to `npc.memory.knows_facts` forever. Cap it:
> ```python
> from config import MAX_NPC_MEMORY_FACTS
>
> def record_npc_interaction(channel_id, npc_name, fact):
>     npc = get_npc(channel_id, npc_name)
>     npc.memory.knows_facts.append(fact)
>     # Cap memory to prevent bloat
>     if len(npc.memory.knows_facts) > MAX_NPC_MEMORY_FACTS:
>         npc.memory.knows_facts = npc.memory.knows_facts[-MAX_NPC_MEMORY_FACTS:]
>     save_npcs(...)
> ```
>
> **Bug 5: Voice assignment crash**
> `assign_voice_to_npc()` imports from `utils.voice_map` which exists but the function may reference things that don't exist. Make it graceful:
> ```python
> def assign_voice_to_npc(npc):
>     try:
>         from utils.voice_map import get_voice_id
>         voice_id = get_voice_id(npc.name)
>         npc.voice_id = voice_id
>     except Exception:
>         npc.voice_id = None  # No voice, no problem
> ```
>
> **Acceptance Criteria:**
> - [ ] Gender detection only considers sentences mentioning the NPC
> - [ ] Shop buy_rate applies to prices
> - [ ] Shop state saved after buy/sell
> - [ ] NPC memory capped at MAX_NPC_MEMORY_FACTS
> - [ ] Voice assignment doesn't crash

---

## Cluster 5.2 ✅ — Environment & World Generator Fixes

### Prompt for AI Agent

> Fix bugs in `utils/world_generator.py` (~1147 lines) and `utils/environment_manager.py` (~1350 lines).
>
> **Bug 1: Time parsing too strict (world_generator.py)**
> `parse_time_string()` only matches `\d+\s*hours?`. Fails on "about 3 hours", "4 to 5 hours", "a few hours".
>
> Fix — be more forgiving:
> ```python
> def parse_time_string(text: str) -> int:
>     """Parse time strings into hours. Returns 0 if can't parse."""
>     text = text.lower().strip()
>     
>     # Direct number: "3 hours"
>     m = re.search(r'(\d+)\s*hours?', text)
>     if m:
>         return int(m.group(1))
>     
>     # Range: "4 to 5 hours" → take average
>     m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*hours?', text)
>     if m:
>         return (int(m.group(1)) + int(m.group(2))) // 2
>     
>     # Vague: "a few hours" = 3, "several hours" = 5
>     if 'few' in text: return 3
>     if 'several' in text: return 5
>     if 'couple' in text: return 2
>     
>     # Minutes: "30 minutes" = 1
>     m = re.search(r'(\d+)\s*minutes?', text)
>     if m:
>         return max(1, int(m.group(1)) // 60)
>     
>     return 0
> ```
>
> **Bug 2: Outdoor lighting overwrites indoor (world_generator.py)**
> `update_lighting_for_time()` checks if a location is outdoor based on the light source string. But the default source is empty string, so EVERY location gets time-based lighting, including dungeons.
>
> Fix: Use the location type (from LOCATION_PRESETS) to determine if outdoor, not the light source:
> ```python
> def update_lighting_for_time(channel_id, time_state):
>     location = get_current_location_type(channel_id)
>     preset = LOCATION_PRESETS.get(location)
>     if preset and not preset.get('is_outdoor', False):
>         return  # Don't change lighting in indoor locations
>     # ... proceed with time-based lighting for outdoor locations ...
> ```
>
> **Bug 3: Location preset can't be overridden (world_generator.py)**
> `apply_location_preset()` always overwrites lighting even if manually set. Add an `override` parameter:
> ```python
> def apply_location_preset(channel_id, location_type, override=True):
>     if not override:
>         # Only apply if no custom lighting has been set
>         current = get_current_lighting(channel_id)
>         if current and current != "default":
>             return
>     # ... existing logic ...
> ```
>
> **Bug 4: TimeState rollover (world_generator.py)**
> Calendar math with hardcoded 30-day months can produce invalid dates.
> ```python
> def advance(self, hours):
>     self.hour += hours
>     while self.hour >= 24:
>         self.hour -= 24
>         self.day += 1
>     while self.day > 30:
>         self.day -= 30
>         self.month += 1
>     while self.month > 12:
>         self.month -= 12
>         self.year += 1
> ```
> This is fine for a fantasy calendar. Just make sure it uses `while` not `if` to handle multi-day advances. Check it currently does — if not, fix it.
>
> **Acceptance Criteria:**
> - [ ] Time parsing handles "about 3 hours", "4 to 5 hours", "a few hours", "30 minutes"
> - [ ] Indoor locations (cave, dungeon, tavern) not affected by time-of-day lighting
> - [ ] Manual lighting overrides aren't stomped by location presets
> - [ ] Calendar rollover works for multi-day advances

---

## Cluster 5.3 ✅ — Travel & World Map Fixes

### Prompt for AI Agent

> Fix bugs in `utils/world_map.py` (~988 lines) and `utils/encounter_manager.py` (~916 lines).
>
> **Bug 1: Travel detection regex too broad (world_map.py)**
> `TRAVEL_INTENT_PATTERNS` match "we travel to [capitalized words]". "We travel towards madness" captures "madness" as a destination.
>
> Fix: Only match if the destination is a KNOWN location or follows a very specific pattern:
> ```python
> def detect_natural_language_travel(text: str, known_locations: list[str]) -> Optional[str]:
>     """Detect travel intent, but only to known locations or very clear destinations."""
>     # First, check for travel to known locations
>     text_lower = text.lower()
>     for loc in known_locations:
>         patterns = [
>             rf'(?:travel|head|go|journey|march|ride|walk|trek)\s+(?:to|toward|towards)\s+{re.escape(loc)}',
>         ]
>         for p in patterns:
>             if re.search(p, text_lower):
>                 return loc
>     
>     # Then fall back to capitalized proper nouns only
>     m = re.search(r'(?:travel|head|go)\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
>     if m:
>         return m.group(1)
>     
>     return None
> ```
>
> **Bug 2: Fast travel crashes on terrain typos (world_map.py)**
> `fast_travel()` does `TERRAIN_MODIFIERS[terrain]` with no fallback. If terrain is "forrest" (typo), KeyError.
> ```python
> speed_mult = TERRAIN_MODIFIERS.get(terrain, TERRAIN_MODIFIERS.get('road', {'speed_modifier': 1.0}))['speed_modifier']
> ```
>
> **Bug 3: Location case inconsistency (world_map.py)**
> Locations are stored as dict keys with original casing ("Phandalin") but looked up case-insensitively. This works for `get_location()` but fails for any direct dict access.
>
> Fix: Normalize all location keys to lowercase internally:
> ```python
> def add_location(self, name, **kwargs):
>     key = name.lower()
>     self.locations[key] = Location(name=name, **kwargs)  # Keep original name as display name
>
> def get_location(self, name):
>     return self.locations.get(name.lower())
> ```
>
> **Bug 4: Encounter time-of-day desync (encounter_manager.py)**
> `roll_for_encounter()` uses `is_night=hours_since_check > 12` which has nothing to do with actual in-game time. Use world_generator's time tracking:
> ```python
> def roll_for_encounter(channel_id, terrain, ...):
>     try:
>         from utils.world_generator import get_time_state
>         time_state = get_time_state(channel_id)
>         is_night = time_state.hour >= 20 or time_state.hour < 6
>     except Exception:
>         is_night = False  # Default to day if time system unavailable
> ```
>
> **Bug 5: ENCOUNTER_MULTIPLIERS dict uses tuple keys but never accessed (encounter_manager.py)**
> The dict has `{(3, 6): 2.0}` style keys but `get_encounter_multiplier()` doesn't use the dict at all. Either fix the function to use the dict or replace the dict with a simple if/elif chain. The simpler approach:
> ```python
> def get_encounter_multiplier(num_monsters):
>     if num_monsters <= 1: return 1.0
>     if num_monsters == 2: return 1.5
>     if num_monsters <= 6: return 2.0
>     if num_monsters <= 10: return 2.5
>     if num_monsters <= 14: return 3.0
>     return 4.0
> ```
>
> **Acceptance Criteria:**
> - [ ] Travel detection only matches known locations or clear proper nouns
> - [ ] Fast travel handles terrain typos with fallback
> - [ ] Location keys normalized to lowercase
> - [ ] Night encounters use actual in-game time
> - [ ] Encounter multiplier function actually works

---

---

# PHASE 6: POLISH ✅ COMPLETE

---

## Cluster 6.1 ✅ — TTS as Optional Feature

### Prompt for AI Agent

> TTS (text-to-speech via ElevenLabs) should be completely optional. If ElevenLabs isn't configured, the bot should work fine without voice.
>
> **File 1: `config.py`**
> Already has `TTS_ENABLED` from Cluster 0.3. Verify it exists.
>
> **File 2: `cogs/shared.py` (where `play_tts` lives)**
> Gate all TTS on the config flag:
> ```python
> async def play_tts(interaction, text, voice_name):
>     from config import Config
>     if not Config.TTS_ENABLED:
>         return  # TTS disabled, skip silently
>     
>     if not text or not text.strip():
>         return
>     
>     try:
>         # ... existing TTS logic ...
>     except Exception as e:
>         logger.warning(f"TTS failed (non-fatal): {e}")
>         # Don't raise — TTS failure should never break gameplay
> ```
>
> **File 3: `cogs/campaign.py` (and any other cog calling play_tts)**
> Make sure `play_tts()` is always called with `await` but its result is never required for the game to proceed. It should be a fire-and-forget enhancement:
> ```python
> # After sending the narration text to the channel:
> await play_tts(interaction, tts_text, voice_name)  # Best effort, won't fail the command
> ```
>
> **File 4: `services/elevenlabs_service.py`**
> Add a check at import time:
> ```python
> def is_available():
>     """Check if ElevenLabs is configured and available."""
>     return bool(os.environ.get('ELEVENLABS_API_KEY'))
> ```
>
> **Acceptance Criteria:**
> - [ ] Bot works perfectly with `TTS_ENABLED=false` or missing ElevenLabs key
> - [ ] TTS errors never crash commands
> - [ ] TTS errors logged as warnings (not errors)
> - [ ] `/campaign`, `/do`, `/nextturn` all work without voice

---

## Cluster 6.2 ✅ — Web Portal Update

### Prompt for AI Agent

> Update `webportal/routes.py` (~331 lines) to work with the new cog-based structure. The web portal provides a read-only dashboard for viewing characters, campaigns, and spell management.
>
> **Main issue:** The web portal imports directly from various utility modules. After the cog split, discord_bot.py is tiny and imports are different. BUT the utility modules (`utils/character_manager.py`, `utils/state_manager.py`, etc.) are unchanged — the cog split only moved the Discord commands.
>
> **So the web portal should mostly still work.** But verify:
> 1. All imports in `webportal/routes.py` still resolve
> 2. The `dnd5e_data` import works (it wraps in try/except — make it a direct import)
> 3. Routes that read state files still work with whatever schema changes were made in Cluster 0.1
>
> **Also fix:** The web portal has no authentication. For now this is fine (it's a local tool), but add a comment noting this for future:
> ```python
> # WARNING: No authentication. For local use only.
> # TODO: Add basic auth before exposing to internet
> ```
>
> **Acceptance Criteria:**
> - [ ] Web portal starts without import errors
> - [ ] Character list page loads
> - [ ] Character detail page loads
> - [ ] Campaign summary page loads
> - [ ] DM dashboard page loads

---

## Cluster 6.3 ✅ — Basic Test Suite

### Prompt for AI Agent

> Add a minimal test suite to catch regressions. The project has ZERO tests. We don't need 100% coverage — just enough to catch the worst breaks.
>
> **Create `tests/__init__.py`** (empty)
>
> **Create `tests/test_dice_roller.py`:**
> ```python
> """Tests for the dice roller — the simplest, most testable module."""
> import pytest
> from utils.dice_roller import roll_dice, parse_dice
>
> def test_basic_roll():
>     total, rolls, modifier = roll_dice("1d20")
>     assert 1 <= total <= 20
>     assert len(rolls) == 1
>     assert modifier == 0
>
> def test_multiple_dice():
>     total, rolls, modifier = roll_dice("3d6")
>     assert 3 <= total <= 18
>     assert len(rolls) == 3
>
> def test_modifier():
>     total, rolls, modifier = roll_dice("1d20+5")
>     assert 6 <= total <= 25
>     assert modifier == 5
>
> def test_negative_modifier():
>     total, rolls, modifier = roll_dice("1d20-2")
>     assert -1 <= total <= 18
>     assert modifier == -2
>
> def test_d100():
>     total, rolls, modifier = roll_dice("1d100")
>     assert 1 <= total <= 100
> ```
>
> **Create `tests/test_state_manager.py`:**
> ```python
> """Tests for state persistence."""
> import pytest
> import os
> import json
> from utils.state_manager import load_state, save_state, STATE_DIR
>
> TEST_ID = "test_channel_999"
>
> @pytest.fixture(autouse=True)
> def cleanup():
>     yield
>     # Clean up test files
>     path = os.path.join(STATE_DIR, f'{TEST_ID}.json')
>     if os.path.exists(path):
>         os.remove(path)
>
> def test_load_missing_state_returns_defaults():
>     state = load_state(TEST_ID)
>     assert state["campaign_title"] == ""
>     assert state["players"] == []
>
> def test_save_and_load_roundtrip():
>     state = load_state(TEST_ID)
>     state["campaign_title"] = "Test Campaign"
>     save_state(TEST_ID, state)
>     loaded = load_state(TEST_ID)
>     assert loaded["campaign_title"] == "Test Campaign"
>
> def test_corrupted_file_recovery():
>     path = os.path.join(STATE_DIR, f'{TEST_ID}.json')
>     with open(path, 'w') as f:
>         f.write("{invalid json!!")
>     state = load_state(TEST_ID)
>     assert state["campaign_title"] == ""  # Should return defaults
>     assert os.path.exists(path + ".corrupted")  # Should rename bad file
> ```
>
> **Create `tests/test_tag_parser.py`:** (if Cluster 2.2 has been done)
> ```python
> """Tests for AI tag parsing."""
> from utils.tag_parser import parse_all_tags, strip_tags
>
> def test_combat_tag():
>     tags = parse_all_tags("[COMBAT: 3 goblins, 1 hobgoblin]")
>     assert len(tags.combat) == 1
>     assert "goblin" in tags.combat[0]['enemies'].lower()
>
> def test_combat_tag_no_space():
>     tags = parse_all_tags("[COMBAT:3 goblins]")
>     assert len(tags.combat) == 1
>
> def test_combat_tag_lowercase():
>     tags = parse_all_tags("[combat: 2 wolves]")
>     assert len(tags.combat) == 1
>
> def test_quest_with_apostrophe():
>     tags = parse_all_tags('[QUEST: name="Bob\'s Adventure", type=rescue]')
>     assert len(tags.quests) == 1
>
> def test_strip_tags():
>     text = "The goblins attack! [COMBAT: 3 goblins] Roll for initiative!"
>     clean = strip_tags(text)
>     assert "[COMBAT" not in clean
>     assert "goblins attack" in clean
>
> def test_multiple_tags():
>     text = "[WEATHER: rain] The sky darkens. [LIGHTING: dim]"
>     tags = parse_all_tags(text)
>     assert len(tags.weather) == 1
>     assert len(tags.lighting) == 1
> ```
>
> **Create `tests/test_character_manager.py`:**
> ```python
> """Tests for character CRUD."""
> import pytest
> import os
> from utils.character_manager import (
>     register_character, load_character, save_character,
>     damage_character, heal_character
> )
>
> TEST_USER = "test_user_999"
>
> @pytest.fixture(autouse=True)
> def cleanup():
>     yield
>     # Clean up test character file
>     from utils.character_manager import CHARACTERS_DIR
>     path = os.path.join(CHARACTERS_DIR, f'{TEST_USER}.json')
>     if os.path.exists(path):
>         os.remove(path)
>
> def test_register_and_load():
>     register_character(TEST_USER, "Test Hero", "Fighter", "Human")
>     data = load_character(TEST_USER)
>     assert data['name'] == "Test Hero"
>     assert data['class'] == "Fighter"
>
> def test_damage_and_heal():
>     register_character(TEST_USER, "Test Hero", "Fighter", "Human")
>     damage_character(TEST_USER, 5)
>     data = load_character(TEST_USER)
>     assert data['hp'] == data['max_hp'] - 5
>     heal_character(TEST_USER, 3)
>     data = load_character(TEST_USER)
>     assert data['hp'] == data['max_hp'] - 2
>
> def test_damage_cant_go_below_zero():
>     register_character(TEST_USER, "Test Hero", "Fighter", "Human")
>     damage_character(TEST_USER, 9999)
>     data = load_character(TEST_USER)
>     assert data['hp'] == 0
> ```
>
> **Add to `requirements.txt`:** `pytest` (if not already there)
>
> **Test runner command:** `pytest tests/ -v`
>
> **Acceptance Criteria:**
> - [ ] `tests/` directory with 4 test files
> - [ ] `pytest tests/ -v` passes all tests
> - [ ] Tests cover: dice rolling, state save/load, tag parsing, character CRUD
> - [ ] Tests clean up after themselves (no test artifacts left)

---

---

# APPENDIX A: Quick Reference — Files Changed Per Cluster

| Cluster | Files Created | Files Modified |
|---------|--------------|----------------|
| 0.1 | — | `utils/state_manager.py` |
| 0.2 | — | `utils/logger.py`, `discord_bot.py` |
| 0.3 | — | `config.py`, `services/openai_service.py`, `utils/session_manager.py`, `discord_bot.py` |
| 1.1 | `cogs/__init__.py`, `cogs/campaign.py` | `discord_bot.py` |
| 1.2 | `cogs/combat.py`, `cogs/shared.py` | `discord_bot.py`, `cogs/campaign.py` |
| 1.3 | `cogs/character.py` | `discord_bot.py`, `cogs/shared.py` |
| 1.4 | `cogs/world.py` | `discord_bot.py` |
| 1.5 | `cogs/social.py` | `discord_bot.py` |
| 1.6 | `cogs/utility.py`, `cogs/session.py` | `discord_bot.py` |
| 2.1 | — | `cogs/campaign.py` |
| 2.2 | `utils/tag_parser.py` | `utils/combat_trigger.py`, `utils/quest_manager.py`, `utils/world_generator.py`, `utils/world_map.py` |
| 2.3 | — | `utils/prompt_builder.py` |
| 2.4 | — | `services/openai_service.py` |
| 3.1 | — | `utils/combat_manager.py` |
| 3.2 | — | `utils/combat_flow.py`, `utils/enemy_ai.py` |
| 3.3 | — | `utils/inventory_manager.py`, `utils/loot_manager.py`, `utils/combat_trigger.py` |
| 4.1 | — | `utils/character_manager.py` |
| 4.2 | — | `utils/quest_manager.py`, `cogs/social.py` |
| 5.1 | — | `utils/npc_manager.py` |
| 5.2 | — | `utils/world_generator.py`, `utils/environment_manager.py` |
| 5.3 | — | `utils/world_map.py`, `utils/encounter_manager.py` |
| 6.1 | — | `cogs/shared.py`, `config.py`, `services/elevenlabs_service.py` |
| 6.2 | — | `webportal/routes.py` |
| 6.3 | `tests/__init__.py`, `tests/test_*.py` (4 files) | `requirements.txt` |

---

# APPENDIX B: Minimum Viable Session

After completing through **Phase 2**, the bot should be able to run a basic game:
- `/campaign` → creates a campaign, AI narrates intro
- `/do I look around` → AI responds with description, detects tags
- `/do I attack the goblin` → triggers combat automatically
- `/attack` `/nextturn` → combat works with correct damage
- `/endcombat` → loot generated
- `/quest` → view quest log
- Errors logged, not swallowed
- Bot survives OpenAI hiccups

**Phases 3-6 make it good. Phases 0-2 make it work.**

---

# APPENDIX C: What I'd Cut

If you want to get to a playable state faster, these features are over-engineered for where the project is and could be simplified or removed:

| Feature | Status | Recommendation |
|---------|--------|----------------|
| Session pacing hints | Over-engineered | Simplify to just session duration tracking |
| Encounter multiplier tables | Dead code | Replace with simple function (done in 5.3) |
| 25+ location presets | Nice but unused | Keep, they're just data |
| Terrain zones with coordinates | Over-engineered | Simplify to single terrain type per location |
| Cover calculations | Rarely needed | Keep but deprioritize |
| Handout system | Niche | Keep but don't fix bugs unless hit |
| Map system | Niche | Same |
| Ambient/SFX | Nice to have | Same |
