# AI Dungeon Master - Playthrough Guide

> A complete guide to running D&D 5e sessions with the AI Dungeon Master bot.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Setting Up a Campaign](#setting-up-a-campaign)
3. [Creating Characters](#creating-characters)
4. [Gameplay Commands](#gameplay-commands)
5. [Skill Checks](#skill-checks)
6. [Combat System](#combat-system)
7. [Combat Turn Timer](#combat-turn-timer)
8. [Combat Reactions](#combat-reactions)
9. [XP & Leveling](#xp--leveling)
10. [Loot & Treasure](#loot--treasure)
11. [Spellcasting](#spellcasting)
12. [Resource Auto-Consumption](#resource-auto-consumption)
13. [NPC Memory & Factions](#npc-memory--factions)
14. [Quest Tracking](#quest-tracking)
15. [Environment & Hazards](#environment--hazards)
16. [Travel & Random Encounters](#travel--random-encounters)
17. [Session Management](#session-management)
18. [Rest & Recovery](#rest--recovery)
19. [DM Tools](#dm-tools)
20. [Tactical Maps](#tactical-maps)
21. [Player Handouts](#player-handouts)
22. [Voice & Ambient](#voice--ambient)
23. [Example Session](#example-session)

---

## Quick Start

1. **Invite the bot** to your Discord server
2. **Join a voice channel** (optional, for TTS narration)
3. Run `/campaign` to start a new adventure
4. Create your character with `/character`
5. Use `/do` to take actions!

---

## Setting Up a Campaign

### Starting a New Campaign
```
/campaign
```
The AI generates a unique campaign intro with setting, hook, and starting location.

### Viewing Campaign Context
```
/context
```
Shows the current campaign summary, active NPCs, and quests.

### Getting a Recap
```
/recap
```
Summarizes recent events - great for starting a new session.

### Remembering Important Info
```
/remember <info>
```
Example: `/remember The innkeeper mentioned a secret passage behind the fireplace`

---

## Creating Characters

### Register a New Character
```
/character <name> <race> <class>
```
Example: `/character Thorin Dwarf Fighter`

**Available Races:** Human, Elf, Dwarf, Halfling, Gnome, Half-Elf, Half-Orc, Tiefling, Dragonborn

**Available Classes:** Fighter, Wizard, Rogue, Cleric, Ranger, Barbarian, Bard, Druid, Monk, Paladin, Sorcerer, Warlock

### View Character Sheet
```
/stats
```
Shows full character sheet with abilities, skills, HP, and equipment.

### Set Ability Scores
```
/stats set <ability> <value>
```
Example: `/stats set strength 16`

### Level Up
```
/levelup
```
Increases your level and adjusts HP and proficiency bonus.

---

## Gameplay Commands

### Take an Action
```
/do <action>
```
Example: `/do I search the room for hidden doors`

The AI DM narrates the result and may ask for skill checks.

### Say Something (In Character)
```
/say <dialogue>
```
Example: `/say "Greetings, traveler. What news from the north?"`

### Roll Dice
```
/roll <dice>
```
Examples:
- `/roll d20` - Standard d20 roll
- `/roll 2d6+3` - Two d6 plus 3
- `/roll d20+5 advantage` - Roll with advantage
- `/roll 4d6kh3` - Roll 4d6, keep highest 3

### Check Turn Order
```
/turns
```
Shows whose turn it is in the current scene.

### End Your Turn
```
/done
```
Passes to the next player in turn order.

---

## Skill Checks

The AI DM automatically detects when skill checks are needed and prompts players with interactive buttons.

### How It Works

1. **You take an action**: `/do I try to pick the lock`
2. **AI requests a check**: "The lock looks complex. Roll Sleight of Hand, DC 15."
3. **Button appears**: Click 🎲 **Roll** to make your check
4. **AI narrates outcome**: Success or failure is dramatically described

### Automatic Detection

The bot detects these patterns from AI narration:
- "Roll Perception" / "Make a Stealth check"
- "Roll Strength" / "Make a Constitution check"
- "Dexterity saving throw" / "Wisdom save, DC 14"
- "Everyone roll" / "The party must make"

### Advantage & Disadvantage

Advantage/disadvantage is **automatically applied** based on your conditions:
- **Advantage**: Invisible (attacking), target Blinded/Prone/Restrained
- **Disadvantage**: Blinded, Frightened, Poisoned, Prone, Restrained

### Group Checks (DM Command)
```
/groupcheck <skill> [dc]
```
Example: `/groupcheck stealth 14`

All players get prompted to roll. Uses **majority rule** - if more than half succeed, the group succeeds.

### Saving Throws (DM Command)
```
/savingthrow <ability> <dc> [player]
```
Examples:
- `/savingthrow dexterity 15` - All players roll DEX save
- `/savingthrow wisdom 13 @Thorin` - Only Thorin rolls

### Passive Perception (DM Command)
```
/passivecheck <dc> <description>
```
Example: `/passivecheck 14 a hidden tripwire`

Secretly checks all players' passive Perception. Only those who succeed are notified that they notice something.

### Passive Score Calculation

```
Passive Score = 10 + Skill Modifier + Bonuses
```

Bonuses include:
- **Observant feat**: +5 to passive Perception and Investigation
- **Advantage conditions**: +5
- **Disadvantage conditions**: -5

### Timeout & Auto-Roll

If you don't click the roll button within **60 seconds**, the system auto-rolls for you. This keeps the game moving!

---

## Combat System

### Starting Combat Manually
```
/fight <enemies>
```
Examples:
- `/fight goblin goblin orc` - Simple format, auto-looks up stats from database
- `/fight goblin*3 orc` - 3 goblins + 1 orc from monster database
- `/fight troll:84:15 Custom Boss:50:16` - Custom enemies with HP:AC

### Automatic Combat Triggers

Combat can start automatically in several ways:

**1. Player Attack Intent**
```
/do I attack the goblin
/do I cast fireball at the group
/do I draw my sword and charge at the bandit
```
The system detects attack intent and the AI will trigger combat with appropriate enemies.

**2. AI Combat Narration**
When the AI narrates hostilities, it uses structured tags:
```
"The goblins leap from hiding! [COMBAT: 3 goblins, 1 hobgoblin]"
```
Combat automatically starts with those enemies.

**3. Surprise Rounds**
```
"[SURPRISE: enemies]" - The party gets a surprise round
"[SURPRISE: party]" - Enemies ambushed you!
```
Surprised creatures skip their first turn.

### How Automatic Combat Works

1. You use `/do` with an attack action
2. AI receives hint about combat intent  
3. AI narrates the scene with `[COMBAT: enemy list]` tag
4. System parses enemies and looks up their stats
5. Combat starts automatically with proper initiative

### View Combat Status
```
/combatinfo
```
Shows all combatants with HP, AC, conditions, and initiative order.

### Attack an Enemy
```
/attack <target>
```
Example: `/attack goblin1`

Rolls to hit and damage automatically based on your equipped weapon.

### Advance to Next Turn
```
/nextturn
```
Moves to the next combatant in initiative order.

### End Combat
```
/endcombat
```
Ends the encounter, automatically awards XP to the party, and generates loot from defeated enemies.

### Post-Combat Loot

When combat ends, loot is automatically generated based on enemy CR:
- Gold appropriate to enemy difficulty
- Mundane weapons and armor
- Magic items for higher CR encounters

Use these commands to claim loot:
- `/claimloot` - Pick up items from the loot pile
- `/splitgold` - Divide gold among party members
- `/identify` - Identify unknown magic items

---

## Combat Turn Timer

Combat turns are timed to keep the action moving. Players have a set amount of time to act before their turn auto-passes.

### How It Works

1. **Turn starts**: You're pinged with "It's your turn!"
2. **Timer runs**: Default 60 seconds to take your action
3. **Warning ping**: At 30 seconds, you get a reminder
4. **Auto-pass**: If time runs out, you take the Dodge action

### Configure Timer (DM)
```
/turntimer timeout:<seconds> [warning:<seconds>] [enabled:<true/false>]
```
Examples:
- `/turntimer timeout:90` - Set 90-second turns
- `/turntimer timeout:60 warning:20` - Warn at 20 seconds left
- `/turntimer enabled:false` - Disable timer entirely

### Check Remaining Time
```
/timeleft
```
Shows how much time you have left on your current turn.

### Turn Announcements

When your turn starts, you see:
- Your current HP and conditions
- Available actions (Action, Bonus Action, Reaction, Movement)
- Quick suggestions based on your character state
- Enemies in range

### End-of-Turn Effects

The bot automatically processes:
- **Condition durations**: Frightened (1 round left), etc.
- **Ongoing damage**: Poison, fire, bleed effects
- **Regeneration**: Trolls and other regenerating creatures
- **Recharge abilities**: Dragon breath weapons, etc.
- **Concentration checks**: Prompted when you take damage

### Combat End Detection

Combat automatically ends when:
- ✅ **Victory**: All enemies defeated
- 💀 **TPK**: All players down
- 🏃 **Fled**: All enemies fled
- 🏳️ **Surrender**: Enemies surrendered

Post-combat, you get:
- XP calculation and distribution
- Loot generation from defeated enemies
- Short rest opportunity offer

---

## Combat Reactions

Reactions are special actions you can take on other creatures' turns. You get one reaction per round, which resets at the start of your turn.

### Using Reactions
```
/reaction <type> [target]
```

### Available Reactions

| Reaction | Trigger | Effect |
|----------|---------|--------|
| `opportunity_attack` | Enemy leaves your reach | Free melee attack |
| `shield` | When hit by attack | +5 AC until next turn (uses spell slot) |
| `counterspell` | Enemy casts spell within 60ft | Interrupt the spell (uses spell slot) |
| `uncanny_dodge` | When hit by attack you can see | Halve the damage (Rogue 5+) |
| `absorb_elements` | Take elemental damage | Resistance + bonus damage on next hit |
| `hellish_rebuke` | Take damage from creature | 2d10 fire damage to attacker |
| `cutting_words` | Enemy makes roll | Subtract Bardic Inspiration (Bard) |
| `deflect_missiles` | Hit by ranged attack | Reduce damage (Monk) |

### Examples
```
/reaction shield                    # Cast Shield when hit
/reaction counterspell 5            # Counter a 5th-level spell
/reaction uncanny_dodge 24          # Halve 24 damage to 12
/reaction opportunity_attack Goblin # Attack fleeing enemy
```

---

## XP & Leveling

Experience points are tracked automatically and award level-ups when thresholds are reached.

### View Your XP
```
/xp
```
Shows your current XP, level, and a progress bar to next level.

### Award XP to Party (DM)
```
/awardparty <amount>
```
Example: `/awardparty 500` - Awards 500 XP split among all party members.

### Automatic XP Awards
When combat ends with `/endcombat`, XP is automatically calculated from defeated enemies and distributed to the party.

### XP Thresholds

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

### Leveling Up
```
/levelup
```
When you have enough XP, use this command to increase your level and gain new features.

---

## Loot & Treasure

Generate treasure hoards and magic items based on Challenge Rating.

### Generate Random Loot
```
/loot [cr]
```
Example: `/loot 5` - Generate loot appropriate for CR 5 encounter.

### Generate Treasure Hoard
```
/treasure cr:<cr>
```
Example: `/treasure cr:10` - Generate a full treasure hoard.

### Loot Tiers

| CR Range | Typical Loot |
|----------|--------------|
| 0-4 | Coins, minor gems, mundane items |
| 5-10 | Uncommon magic items, art objects |
| 11-16 | Rare magic items, jewelry |
| 17+ | Very rare/legendary items |

### Automatic Loot
When combat ends, loot is automatically generated from the most powerful defeated enemy.

---

## Spellcasting

### Learn a Spell
```
/learn <spell_name>
```
Example: `/learn fireball`

### Learn a Cantrip
```
/learn cantrip <cantrip_name>
```
Example: `/learn cantrip fire bolt`

### Prepare Spells (for prepared casters)
```
/prepare <spell_name>
```
Example: `/prepare cure wounds`

### Cast a Spell
```
/cast <spell_name> [target]
```
Examples:
- `/cast magic missile goblin1`
- `/cast fireball` (area spell)
- `/cast cure wounds Thorin`

### View Your Spells
```
/spells
```
Shows known spells, prepared spells, and remaining spell slots.

### Check Spell Slots
```
/status
```
Shows current HP, conditions, and spell slot usage.

---

## Resource Auto-Consumption

The bot automatically detects when you use spells, class abilities, or consumables in your narrative actions and deducts the appropriate resources.

### How It Works

When you use `/do` with an action that involves a spell or ability, the bot:
1. **Detects** the spell or ability from your description
2. **Validates** you have the resource available
3. **Consumes** the appropriate slot/charge/item
4. **Notifies** you of the resource usage

### Examples

```
Player: /do I cast Fireball at the group of goblins
Bot: 🔥 Spell slot used: 3rd level (2/3 remaining)
     [AI narration of the Fireball effect...]

Player: /do Ragnar enters a rage and charges at the ogre
Bot: 💢 Rage activated! (2/3 uses remaining)
     [AI narration of the barbarian's fury...]

Player: /do I drink my healing potion
Bot: 🧪 Consumed: Potion of Healing (removed from inventory)
     [AI narration of drinking the potion...]
```

### View Your Resources
```
/resources
```
Shows a complete breakdown of your resource status:

```
📊 Resource Status for Thorin

⚔️ Class Resources:
  Rage: 2/3 remaining
  Reckless Attack: Available

📦 Consumables:
  Potion of Healing: 2
  Arrows: 18

🎒 Ammunition:
  Arrows: 18/20 used
```

### Detected Spell Patterns

The system recognizes many ways to describe casting:
- "I cast Fireball"
- "Elara speaks the words of Healing Word"
- "Using my action to cast Shield"
- "I invoke Sacred Flame"
- "Casting Cure Wounds at 3rd level" (upcasting)

### Detected Class Abilities

| Class | Abilities Tracked |
|-------|-------------------|
| **Barbarian** | Rage, Reckless Attack |
| **Bard** | Bardic Inspiration, Cutting Words |
| **Cleric** | Channel Divinity, Turn Undead |
| **Druid** | Wild Shape |
| **Fighter** | Action Surge, Second Wind |
| **Monk** | Ki Points (Flurry of Blows, Patient Defense, Step of the Wind, Stunning Strike) |
| **Paladin** | Divine Smite, Lay on Hands, Channel Divinity |
| **Sorcerer** | Sorcery Points, Metamagic |
| **Warlock** | Pact Magic slots |
| **Wizard** | Arcane Recovery |

### Detected Consumables

| Category | Examples |
|----------|----------|
| **Potions** | Healing Potion, Potion of Invisibility, Potion of Resistance |
| **Scrolls** | Scroll of Fireball, Spell Scroll (any level) |
| **Ammunition** | Arrows, Bolts, Darts, Sling Bullets, Blowgun Needles |

### Upcasting Detection

The system detects when you want to cast at a higher level:
```
Player: /do I cast Cure Wounds at 3rd level on Thorin
Bot: ✨ Spell slot used: 3rd level (for Cure Wounds upcast)
     Thorin is healed for 3d8+3 hit points!
```

### Resource Validation

If you try to use a resource you don't have:
```
Player: /do I cast Fireball
Bot: ❌ Cannot cast Fireball - no 3rd level or higher spell slots remaining!
```

### Manual Override

If the auto-detection gets it wrong, you can manually manage:
- Use `/cast` for explicit spell slot usage
- Use `/inventory remove` to manually remove items
- The DM can adjust resources as needed

---

## NPC Memory & Factions

The bot tracks NPCs you meet and your relationships with factions.

### NPC Tracking

NPCs are automatically detected from AI narration:
```
AI: **Gundren Rockseeker**, a stout dwarf merchant, greets you warmly...
Bot: 🎭 Met new NPC: Gundren Rockseeker (dwarf, merchant, friendly)
```

### Viewing NPCs
```
/npc action:list
```
Lists all NPCs you've encountered with their disposition and role.

```
/npc action:view name:"Gundren"
```
Shows detailed info about a specific NPC including:
- Disposition toward party
- Current mood
- Role (merchant, quest giver, etc.)
- What they know about you
- Previous interactions

### NPC Dispositions

The AI and DM actions affect how NPCs feel about the party:

| Disposition | Meaning |
|-------------|---------|
| **Allied** | Will risk their life for you |
| **Friendly** | Helpful, offers discounts and aid |
| **Neutral** | Standard interactions |
| **Unfriendly** | Reluctant, charges higher prices |
| **Hostile** | May attack or betray you |

### Adjusting Disposition (DM)
```
/npc action:disposition name:"Gundren" change:1 reason:"Rescued his brother"
```
- Positive numbers improve disposition
- Negative numbers worsen it
- Changes are logged to NPC memory

### Factions

Track your reputation with organizations and groups:
```
/npc action:factions
```
Lists all factions and your standing with each.

```
/npc action:faction-view name:"Thieves Guild"
```
View details about a specific faction.

```
/npc action:faction-create name:"Thieves Guild" description:"Underground criminal network"
```
Creates a new faction to track.

### Faction Standings

| Standing | Range | Effect |
|----------|-------|--------|
| **Revered** | 75+ | Best prices, special quests, faction aid |
| **Honored** | 50-74 | Good discounts, helpful members |
| **Friendly** | 25-49 | Minor benefits |
| **Neutral** | -24 to 24 | Standard treatment |
| **Unfriendly** | -49 to -25 | Higher prices, suspicion |
| **Hostile** | -74 to -50 | Refused service, active opposition |
| **Nemesis** | -100 to -75 | Attack on sight |

### Adjusting Reputation (DM)
```
/npc action:reputation faction:"Thieves Guild" change:15 reason:"Completed heist job"
```

### Merchants & Shops

Create NPC merchants with persistent inventory:
```
/shop action:create merchant:"Gundren" shop_type:general
```
Shop types: `general`, `weapons`, `armor`, `potions`, `magic`

### Buying Items
```
/shop action:view merchant:"Gundren"
```
Shows available inventory with prices.

```
/shop action:buy merchant:"Gundren" item:"Rope" quantity:2
```
Purchase items (gold auto-deducted).

### Selling Items
```
/shop action:sell merchant:"Gundren" item:"Longsword" base_price:15
```
Sell items for 50% of base value.

### NPC Voices

Each NPC automatically gets a unique voice based on:
- **Race** - Elves sound ethereal, dwarves gruff
- **Role** - Nobles commanding, merchants friendly
- **Gender** - Appropriate voice variants

---

## Quest Tracking

The quest system tracks your objectives, progress, and rewards throughout the adventure. Quests can be created manually by the DM, from templates, or **detected automatically from AI narration using structured tags**.

### Autonomous Quest Creation (Phase 13)

The AI can now create quests automatically by including special tags in its narration. When an NPC offers a quest, the AI includes:

```
"The old farmer looks desperate. 'Please, heroes! Goblins have taken my daughter!'"
[QUEST: name="Rescue the Farmers Daughter", type=rescue, difficulty=medium, giver="Old Farmer"]
```

This automatically creates the quest in your quest log. You'll see a notification:

```
📜 **New Quest:** Rescue the Farmers Daughter
*Quest from Old Farmer*
```

**Available Quest Tags:**

| Tag | Example | Effect |
|-----|---------|--------|
| `[QUEST:]` | `[QUEST: name="...", type=rescue, difficulty=hard]` | Creates new quest |
| `[QUEST_COMPLETE:]` | `[QUEST_COMPLETE: "Quest Name"]` | Completes quest, awards rewards |
| `[QUEST_PROGRESS:]` | `[QUEST_PROGRESS: "Quest", objective=1]` | Updates objective progress |
| `[RUMOR:]` | `[RUMOR: "Strange lights at cemetery"]` | Records rumor |
| `[QUEST_HOOK:]` | `[QUEST_HOOK: name="...", description="..."]` | Creates available quest |
| `[OBJECTIVE:]` | `[OBJECTIVE: "Find the entrance"]` | Adds new objective |
| `[QUEST_CHAIN:]` | `[QUEST_CHAIN: parent="...", child="..."]` | Links quests |

### Viewing Your Quest Log
```
/quest action:list
```
Shows all your active quests with objectives and progress:
```
📜 Quest Log

⚔️ ACTIVE QUESTS

The Lost Mine of Phandelver [main] ★★★
Escort Gundren to Phandalin and find Wave Echo Cave
├── ☑ Escort Gundren to Phandalin (1/1)
├── ○ Find out what happened to Gundren
└── ○ Locate Wave Echo Cave (0/1)

Goblin Bounty [bounty] ★
Clear out the goblin threat on the Triboar Trail
└── ○ Defeat goblins (3/10)
```

### Viewing a Specific Quest
```
/quest action:view name:"Lost Mine"
```
Shows detailed information including notes, rewards, and quest giver.

### Rumor System

NPCs can share rumors that hint at future adventures:

```
A drunk at the tavern mutters: "Ye hear about the lights at the cemetery?"
[RUMOR: "Strange lights at the old cemetery at night"]
```

You'll see: `👂 **Rumor heard:** *"Strange lights at the old cemetery at night"*`

**Viewing Rumors:**
```
/quest action:rumors
```
Shows all rumors the party has heard, both investigated and uninvestigated.

**Investigating Rumors:**
```
/quest action:investigate-rumor rumor_number:1 name:"Investigate the Cemetery"
```
Converts a rumor into an active quest for the party to pursue.

### Quest Chains

Quests can be linked so completing one unlocks another:

```
[QUEST_CHAIN: parent="Rescue the Daughter", child="Find the Goblin Lair"]
```

Or manually:
```
/quest action:chain parent:"Rescue the Daughter" child:"Find the Goblin Lair"
```

When the parent quest completes, you'll see:
```
🔓 **Quest Unlocked:** Find the Goblin Lair
```

### Accepting Available Quests

Quest hooks create "available" quests that aren't active yet:
```
/quest action:accept name:"Investigate the Cemetery"
```

### Creating Quests (DM)
```
/quest action:create name:"Rescue the Prisoners" description:"Free the captives from Cragmaw Hideout" difficulty:normal quest_type:rescue
```

**Quest Difficulties:**
| Difficulty | XP Reward | Gold Reward |
|------------|-----------|-------------|
| Trivial | 50 XP | 10 gp |
| Easy | 100 XP | 25 gp |
| Normal | 250 XP | 50 gp |
| Hard | 500 XP | 100 gp |
| Deadly | 1000 XP | 250 gp |
| Epic | 2500 XP | 2000 gp |

**Quest Types:** `main`, `side`, `bounty`, `fetch`, `rescue`, `investigate`, `escort`, `exploration`

### Using Quest Templates

Quickly create common quests using templates:
```
/quest action:template template:bounty name:"Goblin Hunt" target:"Goblins" count:10
```

**Available Templates:**
- `bounty` - Hunt X enemies for reward
- `fetch` - Retrieve a specific item
- `rescue` - Save someone from danger
- `investigate` - Uncover the truth about something
- `clear_dungeon` - Clear out a dangerous location
- `escort` - Protect someone on a journey

### Adding Objectives
```
/quest action:objective name:"Lost Mine" objective:"Find the secret entrance"
```

**Objective Types:**
- `kill` - Defeat enemies
- `collect` - Gather items
- `discover` - Find locations or information
- `talk` - Speak with NPCs
- `escort` - Protect targets
- `custom` - Anything else

### Tracking Progress
```
/quest action:progress name:"Goblin Bounty" objective_number:1 amount:5
```
Updates objective progress (e.g., 3/10 → 5/10).

### Adding Notes
```
/quest action:note name:"Lost Mine" note:"Gundren mentioned a map hidden in his boot"
```
Add player notes to quests for reference.

### Auto-Detection

The system automatically detects quest progress from AI narration:

**When you /do an action that completes an objective:**
```
/do I search the goblin chief's body for the map
```
*AI narrates finding the map...*
```
📜 Quest Progress!
"The Lost Mine" - Objective "Find the map" COMPLETE!
```

**Detection patterns include:**
- Item retrieval: "you found", "obtained", "picked up"
- Enemy defeat: "defeated", "slain", "killed"
- Rescue: "freed", "rescued", "saved"
- Discovery: "discovered", "found", "revealed"
- Delivery: "delivered", "handed over", "completed delivery"

### Completing Quests

Quests complete automatically when the AI includes:
```
[QUEST_COMPLETE: "Quest Name"]
```

Or manually:
```
/quest action:complete name:"Goblin Bounty"
```

Either way awards rewards:
```
🎉 Quest Complete: Goblin Bounty!

Rewards:
  ⭐ 100 XP
  💰 25 gp
  📈 +10 reputation with Town Guard
```

### Abandoning Quests
```
/quest action:abandon name:"Goblin Bounty" reason:"Too dangerous right now"
```
Abandons the quest (can be re-accepted later).

### Quest Commands Quick Reference

| Command | Description |
|---------|-------------|
| `/quest action:list` | View full quest log |
| `/quest action:view name:"..."` | View specific quest |
| `/quest action:create name:"..." description:"..."` | Create new quest |
| `/quest action:template template:bounty name:"..."` | Create from template |
| `/quest action:objective name:"..." objective:"..."` | Add objective |
| `/quest action:progress name:"..." objective_number:1` | Update progress |
| `/quest action:note name:"..." note:"..."` | Add note |
| `/quest action:complete name:"..."` | Complete a quest |
| `/quest action:abandon name:"..."` | Abandon a quest |
| `/quest action:rumors` | View heard rumors |
| `/quest action:investigate-rumor rumor_number:1` | Convert rumor to quest |
| `/quest action:chain parent:"..." child:"..."` | Link quests |
| `/quest action:accept name:"..."` | Accept available quest |

---

## Environment & Hazards

The environment system tracks traps, weather, lighting, terrain, and hazards. These conditions affect gameplay with mechanical modifiers and are included in AI narration context.

### Viewing Environment Status
```
/environment
```
Shows comprehensive environment summary:
```
🌍 Environment Status

🌧️ Weather: Heavy Rain (intensity 2)
   - Perception: -2
   - Ranged attacks: -2
   - Visibility: lightly obscured

🔦 Lighting: Dim Light
   - Source: Torches
   - Disadvantage on Perception

⚙️ Active Traps: 2 (1 detected)
☠️ Active Hazards: 1
```

### Managing Traps (DM)

#### Creating Traps from Templates
```
/trap action:create template:pit_trap
```

**Available Templates:**
| Template | DC | Damage | Effect |
|----------|-----|--------|--------|
| `pit_trap` | 15 | 2d6 bludgeoning | Fall into pit |
| `poison_dart` | 14 | 1d4+poison | DEX save or poisoned |
| `flame_jet` | 16 | 3d6 fire | DEX save for half |
| `spike_trap` | 14 | 2d6 piercing | Pressure plate |
| `poison_gas` | 15 | 3d6 poison | CON save for half |
| `net_trap` | 13 | None | Restrained until escape |
| `blade_trap` | 17 | 2d10 slashing | Swinging blade |
| `lightning_rune` | 16 | 4d6 lightning | Magical ward |
| `alarm` | 12 | None | Alerts guards |
| `collapsing_ceiling` | 18 | 4d10 bludgeoning | Everyone in room |

#### Creating Custom Traps
```
/trap action:create name:Acid Spray dc:15 save_dc:14 damage:3d6 damage_type:acid
```

#### Listing Traps
```
/trap action:list
```
Shows all traps (hidden traps show as "Hidden" unless detected).

### Detecting Traps

When players search for traps:
```
/trap action:detect name:"Pit Trap" roll:18
```

If the roll meets the trap DC:
```
👁️ Trap Detected!
You notice a pit trap: Covered Pit
*A thin layer of canvas covered with leaves conceals a 10-foot deep pit*
```

### Disarming Traps

Once detected, players can attempt to disarm:
```
/trap action:disarm name:"Pit Trap" roll:15
```

- **Success:** Trap is disarmed safely
- **Failure by 5+:** Trap triggers!

### Auto-Trigger on Movement

When using `/do` with movement keywords, traps may trigger automatically:
```
/do I walk down the corridor toward the chest
```

If a trap triggers:
```
💥 TRAP TRIGGERED! Poison Dart Trap
*A dart shoots from a hidden hole in the wall*
⚠️ Make a DEX saving throw DC 14!
Damage on fail: 1d4 piercing + 2d6 poison
```

### Weather Effects

#### Setting Weather
```
/weather weather_type:rain intensity:2
```

**Weather Types and Effects:**
| Weather | Perception | Ranged | Movement | Special |
|---------|------------|--------|----------|---------|
| Clear | — | — | — | — |
| Fog | -2 | -2 | — | Lightly obscured |
| Dense Fog | -5 | disadvantage | — | Heavily obscured |
| Rain | -2 | -2 | — | Puts out fires |
| Heavy Rain | -5 | disadvantage | 0.75x | Heavily obscured |
| Thunderstorm | -5 | disadvantage | 0.75x | Lightning strikes |
| Snow | -2 | — | 0.75x | Tracks visible |
| Blizzard | -5 | disadvantage | 0.5x | Heavily obscured |
| Sandstorm | -5 | disadvantage | 0.5x | Heavily obscured |
| Extreme Heat | — | — | — | CON save/hour or exhaustion |
| Extreme Cold | — | — | — | CON save/hour or exhaustion |
| Wind | — | -2 | — | Affects ranged |
| Strong Wind | — | disadvantage | 0.75x | Can knock prone |

#### Clearing Weather
```
/weather weather_type:clear
```

### Lighting Conditions

#### Setting Lighting
```
/lighting light_level:dim source:Torches radius:40
```

**Light Levels:**
| Level | Perception | Attacks | Notes |
|-------|------------|---------|-------|
| Bright | — | — | Normal vision |
| Dim | disadvantage | — | Lightly obscured |
| Darkness | auto-fail | disadvantage vs unseen | Heavily obscured |
| Magical Darkness | — | — | Darkvision doesn't work |

### Terrain Zones

#### Creating Terrain
```
/terrain action:create name:Rubble Field terrain_type:difficult x:5 y:5 width:3 height:3
```

**Terrain Types:**
| Type | Movement Cost | Effect |
|------|---------------|--------|
| Normal | 1x | Standard movement |
| Difficult | 2x | Rough terrain |
| Shallow Water | 2x | Splashing noise |
| Deep Water | 3x | Swimming required |
| Ice | 1x | DEX save or fall prone |
| Lava | 1x | 10d10 fire damage |
| Acid | 1x | 2d6 acid damage |
| Rubble | 2x | DEX save or fall prone |
| Mud | 2x | STR save or stuck |
| Webs | 3x | STR save or restrained |

### Environmental Hazards

#### Creating Hazards
```
/hazard action:create name:Burning Oil hazard_type:fire damage:2d6 damage_type:fire save_dc:13 duration:5
```

Hazards deal damage to anyone in the area at the start of their turn.

### Cover Calculations

Calculate cover between two positions:
```
/cover attacker_x:5 attacker_y:5 target_x:10 target_y:8
```

**Cover Bonuses:**
| Cover | AC Bonus | Dex Save Bonus |
|-------|----------|----------------|
| Half | +2 | +2 |
| Three-Quarters | +5 | +5 |
| Full | Cannot be targeted | Cannot be targeted |

### Dynamic Environment (Automatic)

The AI automatically detects environment changes from narration. No manual commands needed!

#### AI Environment Tags
The AI can use special tags to set environment:
```
[WEATHER: heavy rain, intensity 2]
[LIGHTING: darkness, source: no windows]
[LOCATION: Dark Cave]
[TIME: 3 hours pass]
[TRAP: pit trap at entrance]
[HAZARD: lava pool, 2d6 fire]
```

When you use `/do` and the AI mentions entering a cave, rain starting, or time passing, the environment auto-updates.

#### Location Presets
When entering known locations, presets apply automatically:
- **Cave/Dungeon/Crypt**: Darkness, no weather
- **Tavern/Inn/Temple**: Bright lighting from hearth/candles
- **Forest/Swamp**: Dim lighting, difficult terrain
- **Desert/Arctic**: Weather effects (heat/cold), time-based lighting

#### Time Tracking
The system tracks in-game time with time periods:
- Dawn (6 AM), Morning (8 AM), Midday (12 PM), Afternoon (2 PM)
- Evening (6 PM), Dusk (8 PM), Night (10 PM)

Time affects outdoor lighting automatically!

#### Time Commands
```
/time                          # View current time
/time action:advance hours:4   # Advance 4 hours
/time action:set period:night  # Set to night
```

#### Location Commands
```
/location                      # View current location
/location location:cave        # Set to cave (applies preset)
```

#### Location Memory
When you return to a location you've visited, the environment is restored:
- Weather, lighting, terrain remembered per location
- Changes you made persist (destroyed buildings, cleared traps)

### Environment Commands Quick Reference

| Command | Description |
|---------|-------------|
| `/environment` | View full environment status |
| `/time` | View or set in-game time |
| `/location` | Set location with auto-presets |
| `/trap action:create` | Create a trap |
| `/trap action:list` | List all traps |
| `/detecttrap` | Attempt to detect a trap |
| `/disarmtrap` | Attempt to disarm a trap |
| `/weather` | Set or view weather |
| `/lighting` | Set or view lighting |
| `/hazard action:create` | Create environmental hazard |
| `/terrain action:create` | Create terrain zone |
| `/cover` | Calculate cover between positions |

---

## Travel & Random Encounters

The travel system tracks party journeys between locations with distance, terrain, pace, and automatic encounter generation.

### Intelligent Travel (Phase 14)

The AI can automatically detect travel intent from your actions and narration:

#### Natural Language Travel
Just describe your intent to travel:
```
/do We head to Phandalin
/do Let's journey to the mountains
/do I want to travel to the tavern
```

The AI will narrate the journey and use structured tags to track progress:
- `[TRAVEL: destination="Phandalin", distance=15, terrain=forest]` - Starts journey
- `[ARRIVAL: "Phandalin"]` - Completes journey

#### Location Discovery
The AI discovers new locations during narration:
```
The innkeeper tells you about an abandoned mine in the hills...
[LOCATION_DISCOVERED: name="Wave Echo Cave", terrain=hills, type=mine, poi=true]
```

Locations are automatically added to your world map with connections.

### World Map Commands

#### View World Map
```
/worldmap action:view
```
Shows all discovered locations, connections, and distances.

#### Fast Travel
```
/worldmap action:fast-travel destination:"Phandalin"
```
Instantly travel to a previously **visited** location. Fast travel:
- Skips encounter rolls
- Calculates time automatically
- Only available for visited/explored locations

#### Add Location Manually
```
/worldmap action:add-location name:"Ruined Tower" terrain:hills location_type:ruins
```

#### Set Current Location
```
/worldmap action:set-location location:"Phandalin"
```

#### View Location Details
```
/worldmap action:location-info location:"Wave Echo Cave"
```

### Location Discovery Status

| Status | Description | Fast Travel |
|--------|-------------|-------------|
| Unknown | Just a name | ❌ No |
| Heard Of | Rumors only | ❌ No |
| Known | Know where it is | ❌ No |
| Visited | Been there | ✅ Yes |
| Explored | Fully explored | ✅ Yes |

### Manual Travel Commands

You can still use the original travel commands if you prefer more control:

### Starting a Journey
```
/travel action:start destination:"Phandalin" distance:30 terrain:road pace:normal origin:"Neverwinter"
```

**Parameters:**
- `destination` - Where you're traveling to
- `distance` - Distance in miles
- `terrain` - Type of terrain (affects speed and encounters)
- `pace` - Travel speed: slow, normal, or fast
- `origin` - Where you're starting (defaults to current location)

**Terrain Types:**
| Terrain | Encounter Chance | Travel Speed |
|---------|------------------|--------------|
| Road | 10% | 1.0x |
| Plains | 15% | 1.0x |
| Forest | 25% | 0.75x |
| Mountains | 30% | 0.5x |
| Hills | 20% | 0.75x |
| Swamp | 35% | 0.5x |
| Desert | 20% | 0.75x |
| Arctic | 25% | 0.5x |
| Coastal | 15% | 1.0x |
| Underground | 35% | 0.5x |
| Jungle | 35% | 0.5x |
| Ruins | 40% | 0.75x |

**Travel Paces:**
| Pace | Miles/Day | Effect |
|------|-----------|--------|
| Slow | 18 | Stealth possible |
| Normal | 24 | Standard travel |
| Fast | 30 | -5 to Passive Perception |

### Checking Travel Status
```
/travel action:status
```

Shows progress:
```
🗺️ Travel Status
Neverwinter → Phandalin

Terrain: Road    Pace: Normal    Day: 1

Progress: [████████░░] 80%
24.0 / 30.0 miles

Hours Today: 6.0/8    Remaining: 6.0 miles
```

### Advancing Travel
```
/travel action:advance hours:4
```

Advances travel by the specified hours (1-8). Each hour:
- Progress is calculated based on pace and terrain
- Encounter check is made
- If encounter occurs, it interrupts travel

When arriving:
```
⏰ 2 hour(s) pass...
Traveled: 6.0 miles

🎉 Arrived at Phandalin!
```
The campaign location is automatically updated.

### Canceling Travel
```
/travel action:cancel
```

Stops the current journey. The party remains in the wilderness at their current progress point.

### Generating Random Encounters

#### Combat Encounters
```
/encounter action:random-combat difficulty:medium terrain:forest
```

Generates a combat encounter scaled to your party:
```
⚔️ Goblin Ambush

A band of goblins lies in wait among the trees...

Difficulty: 🟠 Medium
Terrain: Forest
XP Reward: 400

Enemies:
• Goblin Boss (HP: 21, AC: 17)
• Goblin (HP: 7, AC: 15)
• Goblin (HP: 7, AC: 15)
• Goblin (HP: 7, AC: 15)

Use /combat to start combat with these enemies
```

**Difficulty Levels:**
| Difficulty | Description |
|------------|-------------|
| Easy | A simple fight, minor resource expenditure |
| Medium | Challenging but not deadly |
| Hard | Very dangerous, some characters may drop |
| Deadly | Potential for death, major resources needed |

#### Non-Combat Encounters
```
/encounter action:social terrain:road
```

**Event Types:**
- `social` - NPCs to interact with (merchants, travelers, patrols)
- `discovery` - Something interesting to find (ruins, shrines, camps)
- `weather` - Weather change event
- `rest_site` - Shelter or safe resting spot
- `random` - Random selection (re-rolls if combat)

Example social encounter:
```
👥 Traveling Merchant

A colorful wagon comes into view, pulled by a pair of mules. 
The merchant waves as he approaches.

Type: Social Encounter
Terrain: Road

Roleplay this encounter or use /do to interact
```

### Encounter Checks
```
/encounter action:check hours:4 terrain:forest is_night:false stealthy:true
```

Manually roll for random encounters. Returns whether something happens and what type.

### Monster Database

The encounter system includes monsters from CR 0 to CR 10:

**CR 0-1/4:** Bat, Rat, Spider, Commoner, Kobold
**CR 1/4-1/2:** Goblin, Wolf, Skeleton, Orc, Hobgoblin
**CR 1-2:** Bugbear, Ghoul, Giant Spider, Ogre, Ankheg
**CR 3-5:** Owlbear, Werewolf, Troll, Hill Giant, Shambling Mound
**CR 6-10:** Cyclops, Medusa, Stone Giant, Young Dragon, Aboleth

### XP Thresholds (by Party Level)

| Level | Easy | Medium | Hard | Deadly |
|-------|------|--------|------|--------|
| 1 | 25 | 50 | 75 | 100 |
| 2 | 50 | 100 | 150 | 200 |
| 3 | 75 | 150 | 225 | 400 |
| 4 | 125 | 250 | 375 | 500 |
| 5 | 250 | 500 | 750 | 1100 |
| ... | ... | ... | ... | ... |

### Travel Commands Quick Reference

| Command | Description |
|---------|-------------|
| `/travel action:start destination:"..."` | Start a journey |
| `/travel action:status` | View current travel progress |
| `/travel action:advance hours:4` | Advance travel by hours |
| `/travel action:cancel` | Cancel current journey |
| `/worldmap action:view` | View world map |
| `/worldmap action:fast-travel destination:"..."` | Fast travel |
| `/worldmap action:add-location name:"..."` | Add location |
| `/worldmap action:set-location location:"..."` | Set location |
| `/worldmap action:location-info location:"..."` | Location details |
| `/encounter action:random-combat` | Generate combat encounter |
| `/encounter action:social` | Generate social encounter |
| `/encounter action:check` | Roll for random encounter |

---

## Session Management

The bot automatically tracks session activity and provides seamless session continuity.

### Session Tracking

When you start a campaign with `/campaign`, the bot:
- Tracks session duration and pacing phase
- Counts actions, combats, and rests
- Auto-saves every 5 minutes
- Provides pacing hints to the AI

### View Session Status
```
/session action:view
```
Shows:
- Current session duration
- Pacing phase (Opening → Rising → Climax → Falling → Closing)
- Action/combat/rest counts
- Current pacing hints

### Ending a Session
```
/session action:end
```
- Generates session summary with stats
- Saves session for next time
- TTS announces session complete

### Pausing a Session
```
/session action:pause
```
- Pauses the session
- Progress is saved automatically
- Resume when players rejoin voice

### Session Recap

When returning to play:
```
/session action:recap
```
The AI narrates what happened last session:
- Previous session events
- Current location and active quests
- TTS plays the recap

### Session History
```
/session action:history
```
View past session summaries (last 10 sessions):
- Date and duration
- Combat and action counts
- Final location

### Auto-Resume

When players join a voice channel:
1. Bot detects if they have an active campaign
2. Sends resume prompt with last session info
3. Offers recovery if available
4. Auto-resumes paused session

### Crash Recovery
```
/session action:recover
```
If the bot crashes during play:
- Recovery points are saved every 5 minutes
- Use `/session action:recover` to restore from last save
- React ✅ to confirm restore

### Session Pacing

The AI receives pacing hints based on session length:

| Phase | Duration | AI Guidance |
|-------|----------|-------------|
| Opening | 0-15 min | Set mood, let players orient |
| Rising | 15-60 min | Introduce complications |
| Climax | 60-90 min | Peak tension, dramatic moments |
| Falling | 90-120 min | Start wrapping up |
| Closing | 120+ min | Find good stopping point |

The AI also suggests rests when:
- 3+ combats without rest
- 20+ actions without rest
- 60+ minutes of play without rest

---

## Rest & Recovery

### Short Rest (1 hour)
```
/rest short
```
- Spend Hit Dice to heal
- Warlocks recover spell slots
- Fighters recover some abilities

### Long Rest (8 hours)
```
/rest long
```
- Recover all HP
- Recover all spell slots
- Recover half your Hit Dice
- Remove exhaustion levels

---

## DM Tools

### Manage HP
```
/hp damage <amount> [target]
/hp heal <amount> [target]
/hp set <amount> [target]
```
Examples:
- `/hp damage 15` - Take 15 damage
- `/hp heal 10 Thorin` - Heal Thorin for 10
- `/hp set 50` - Set your HP to 50

### Death Saves
```
/deathsave
```
When at 0 HP, roll a death saving throw. Three successes = stabilize, three failures = death.

### Inventory Management
```
/inventory add <item>
/inventory remove <item>
/inventory list
```
Examples:
- `/inventory add rope 50ft`
- `/inventory remove torch`

---

## Tactical Maps

### Create a New Map
```
/map action:create name:"tavern_brawl" width:10 height:10 template:tavern
```
Examples:
- `/map action:create name:"dungeon_room" width:8 height:8 template:dungeon`
- `/map action:create name:"forest_ambush" width:15 height:12 template:forest`

**Templates:** `dungeon`, `forest`, `tavern`, `cave`

### View the Map
```
/map action:view
```
Displays the ASCII tactical map with all tokens.

### Add Tokens
```
/map action:add-token name:"Thorin" x:3 y:5 token_type:player
```
Examples:
- `/map action:add-token name:"Goblin1" x:7 y:5 token_type:enemy`
- `/map action:add-token name:"Chest" x:5 y:8 token_type:object`

### Move Tokens
```
/map action:move token_name:"Thorin" x:5 y:6
```

### Remove Tokens
```
/map action:remove token_name:"Goblin1"
```

### Set Terrain
```
/map action:terrain x:5 y:5 terrain_type:difficult
```
**Terrain Types:** `floor`, `wall`, `water`, `difficult`, `pit`, `door`, `stairs`, `altar`, `tree`, `bush`, `rock`, `fire`, `ice`, `lava`, `magic`

### Check Distance
```
/map action:distance token1:"Thorin" token2:"Goblin1"
```
Returns distance in feet (5ft per square).

### Check Range
```
/map action:range token_name:"Thorin" range_feet:30
```
Shows all tokens within 30 feet.

### Clear the Map
```
/map action:clear
```
Deletes the current tactical map.

---

## Player Handouts

### Create a Handout (DM)
```
/handout action:create title:"Mysterious Letter" content:"Meet me at midnight..." handout_type:letter visible_to:@Player1
```
Examples:
- `/handout action:create title:"Dungeon Map" content:"Shows a winding passage..." handout_type:map`

**Handout Types:** `note`, `letter`, `map`, `image`, `item`, `lore`, `clue`, `journal`, `wanted`, `secret`

### Create a Secret (DM)
```
/secret player:@Rogue title:"Hidden Knowledge" content:"You notice the merchant is lying..."
```
Only that player can see their secrets.

### View Your Handouts
```
/handout action:view
```
Shows all handouts shared with you.

### Read a Handout
```
/handout action:read handout_id:1
```

### Check Your Secrets
```
/mysecrets
```
Shows secrets only you can see.

### DM: View All Handouts
```
/handout action:list-all
```

### DM: Reveal a Handout
```
/handout action:reveal handout_id:1
```
Makes a hidden handout visible to everyone.

### DM: Share with Player
```
/handout action:share handout_id:1 player:@username
```

### DM: Delete a Handout
```
/handout action:delete handout_id:1
```

---

## Voice & Ambient

### Join Voice Channel
```
/voice
```
Bot joins your current voice channel for TTS narration.

### Leave Voice Channel
```
/leave
```
Bot disconnects from voice.

### Set Ambient Mood
```
/ambient <mood>
```
**Available Moods:**
- `calm` - Peaceful, relaxing atmosphere
- `tense` - Building suspense
- `combat` - Battle music
- `mystery` - Intrigue and investigation
- `celebration` - Victory and revelry
- `horror` - Dark and foreboding
- `travel` - Journey and exploration
- `dungeon` - Underground adventure

Example: `/ambient combat` - Set battle music when combat starts.

### Play Sound Effects
```
/sfx <effect>
```
**Available Effects:**
- `sword` - Sword clash
- `spell` - Magic casting
- `explosion` - Boom!
- `door` - Door opening/closing
- `coins` - Jingling coins
- `monster` - Creature roar
- `heal` - Healing magic
- `critical` - Critical hit flourish

### NPC Voice Variety
The AI automatically assigns unique voices to different NPCs:
- Elderly wizards get wise, gravelly voices
- Dwarves get deep, gruff voices
- Elves get ethereal, melodic voices
- Villains get dark, sinister voices

### Export Session Log
```
/exportlog
```
Downloads a markdown file of the entire session.

---

## Example Session

Here's a complete example of starting and playing a session:

### 1. Start the Campaign
```
DM: /campaign
Bot: 🎭 Welcome to "The Shattered Crown"...
     You find yourselves in the bustling port city of Saltmarsh...
```

### 2. Create Characters
```
Player1: /character Thorin Dwarf Fighter
Bot: ✅ Thorin the Dwarf Fighter has joined the adventure!

Player2: /character Elara Elf Wizard  
Bot: ✅ Elara the Elf Wizard has joined the adventure!
```

### 3. Set Up Stats
```
Player1: /stats set strength 16
Player1: /stats set constitution 14

Player2: /stats set intelligence 17
Player2: /learn magic missile
Player2: /learn cantrip fire bolt
```

### 4. Roleplay
```
Player1: /do I approach the barkeep and order an ale
Bot: 🎲 The grizzled barkeep slides a foaming mug across the counter...
     "Three copper, stranger. You're not from around here, are ye?"

Player1: /say "Just passing through. Heard there's work for adventurers."
Bot: The barkeep leans in conspiratorially...
     "Aye, there's been trouble at the old lighthouse..."
```

### 5. Skill Checks
```
Player1: /do I try to read the barkeep's expression to see if he's hiding something
Bot: 🔍 Make an Insight check, DC 12.
     [🎲 Roll] button appears

Player1: *clicks Roll button*
Bot: 🎲 Thorin rolls Insight: 15 (d20: 12 + 3) vs DC 12 - SUCCESS!
     
     The barkeep's eyes flicker briefly toward the cellar door. 
     There's more to this story than he's telling...

DM: /groupcheck perception 14
Bot: 🎯 Group Perception Check (DC 14)
     Everyone, roll Perception!
     [🎲 Roll] buttons appear for all players

     Results:
     ✅ Thorin: 16 - Success!
     ❌ Elara: 11 - Failure
     
     Group Result: FAILURE (need majority)
     The party fails to notice the hooded figure watching from the shadows...
```

### 6. Combat Encounter (Automatic Trigger)
```
Player1: /do I draw my sword and attack the hooded figure
Bot: 🔍 Attack intent detected: hooded figure

AI: The hooded figure spins around, revealing the face of a scarred 
    bandit! He whistles sharply, and a companion emerges from an alley!
    "You shouldn't have done that..." [COMBAT: 2 bandits]

Bot: ⚔️ COMBAT TRIGGERED!
     Enemies detected: 2 Bandits (HP: 11 each, AC: 12)
     
     Initiative Order:
     1. Elara (18)
     2. Bandit 1 (15)
     3. Thorin (12)
     4. Bandit 2 (8)
     
     ⏱️ Elara, it's your turn! (60 seconds)
     HP: 18/18 | AC: 12 | No conditions
     Available: Action, Bonus Action, Movement (30 ft)

Player2: /cast fire bolt bandit1
Bot: 🔥 Elara hurls a bolt of fire! (Attack: 17 vs AC 12 - HIT!)
     Damage: 8 fire damage! Bandit 1 staggers back, singed.

Bot: 🗡️ Bandit 1's turn...
     The bandit lunges at Elara with a rusted shortsword!
     Attack: 14 vs AC 12 - HIT! 5 slashing damage.
     Elara HP: 13/18
     
     ⏱️ Thorin, it's your turn! (60 seconds)
     HP: 30/30 | AC: 16 | No conditions

Player1: /attack bandit1
Bot: ⚔️ Thorin swings his battleaxe! (Attack: 21 vs AC 12 - HIT!)
     Damage: 11 slashing! Bandit 1 falls!
     
     ✅ Victory detected! All enemies defeated.
     🎉 Combat ends - processing rewards...
     
     XP Earned: 50 XP (25 each)
     💰 Loot generated: 18 gold, Rusty Shortsword, Leather Armor
     Use /claimloot to pick up items
```

### 6b. Combat Encounter (Manual Start)
```
DM: /fight bandit bandit
Bot: ⚔️ COMBAT BEGINS!
     Enemies: 2 Bandits (stats auto-loaded from database)
     ...
```

### 7. Using Maps
```
DM: /newmap lighthouse_fight 10 8 dungeon
DM: /addtoken Thorin 2 4 T blue
DM: /addtoken Elara 2 5 E green
DM: /addtoken Bandit1 7 3 B red
DM: /addtoken Bandit2 7 5 B red

Player1: /map
Bot: 
    0 1 2 3 4 5 6 7 8 9
  ┌─────────────────────┐
0 │ # # # # # # # # # # │
1 │ # . . . . . . . . # │
2 │ # . . . . . . . . # │
3 │ # . . . . . . B . # │
4 │ # . T . . . . . . # │
5 │ # . E . . . . B . # │
6 │ # . . . . . . . . # │
7 │ # # # # # # # # # # │
  └─────────────────────┘

Player1: /distance Thorin Bandit1
Bot: 📏 Distance: 25 feet (5 squares)
```

### 8. Rest and Recovery
```
Player1: /rest short
Bot: ⏰ Thorin takes a short rest (1 hour)
     Spent 1 Hit Die: Recovered 9 HP
     Current HP: 28/30

Player2: /rest long
Bot: 🌙 Elara takes a long rest (8 hours)
     HP fully restored: 18/18
     Spell slots restored: 1st: 2/2
```

### 9. Handouts
```
DM: /handout "Torn Page" "...the artifact lies beneath the old well..." clue @Player1
Bot: 📜 Handout created! Shared with Thorin.

Player1: /viewhandouts
Bot: 📚 Your Handouts:
     1. 📎 "Torn Page" (clue) - UNREAD
     
Player1: /readhandout 1
Bot: 📜 TORN PAGE (Clue)
     "...the artifact lies beneath the old well..."
```

---

## Tips for Great Sessions

1. **Be descriptive** - The AI responds better to detailed actions
2. **Stay in character** - Use `/say` for dialogue, `/do` for actions  
3. **Use the map** - Tactical positioning makes combat more strategic
4. **Take rests** - Manage resources like spell slots and HP
5. **Check context** - Use `/recap` if you forget what's happening
6. **Export logs** - Save memorable sessions with `/exportlog`

---

## Command Quick Reference

| Command | Description |
|---------|-------------|
| `/campaign` | Start new campaign |
| `/character` | Create character |
| `/do` | Take an action |
| `/say` | Speak in character |
| `/roll` | Roll dice |
| `/fight` | Start combat |
| `/attack` | Attack target |
| `/reaction` | Use reaction (Shield, Counterspell, etc.) |
| `/cast` | Cast a spell |
| `/resources` | View spell slots, abilities, consumables |
| `/nextturn` | Advance to next turn |
| `/turntimer` | Configure turn timer (DM) |
| `/timeleft` | Check remaining turn time |
| `/groupcheck` | Request group skill check (DM) |
| `/savingthrow` | Request saving throw (DM) |
| `/passivecheck` | Secret passive perception check (DM) |
| `/rest` | Short/long rest |
| `/xp` | View XP progress |
| `/party` | View party dashboard |
| `/loot` | Generate loot |
| `/treasure` | Generate treasure hoard |
| `/map` | View tactical map |
| `/handout` | Create handout |
| `/ambient` | Set ambient mood |
| `/sfx` | Play sound effect |
| `/help` | Show all commands |

---

*Happy adventuring! May your rolls be high and your stories legendary.* 🎲⚔️🐉
