import os
import re
import logging
import openai
from openai import OpenAI
from dotenv import load_dotenv
from config import Config

logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def _handle_openai_error(e: Exception, operation: str = "API call") -> str:
    """Return a themed user-friendly error message for OpenAI exceptions."""
    if isinstance(e, openai.APIConnectionError):
        logger.error(f"OpenAI connection failed during {operation}: {e}")
        return "The mystical energies are disrupted... (Connection error — try again)"
    elif isinstance(e, openai.RateLimitError):
        logger.warning(f"OpenAI rate limit during {operation}: {e}")
        return "The arcane forces need a moment to recharge... (Rate limited — wait a moment)"
    elif isinstance(e, openai.APIStatusError):
        logger.error(f"OpenAI API error {e.status_code} during {operation}: {e}")
        return "The cosmic threads are tangled... (API error)"
    else:
        logger.error(f"Unexpected error during {operation}: {e}", exc_info=True)
        return "The mystical energies are disrupted... please try again."

# Pattern to detect skill check requests from the AI
SKILL_CHECK_PATTERN = re.compile(
    r'roll\s+(?:a\s+)?(?:(?P<ability>strength|dexterity|constitution|intelligence|wisdom|charisma)\s*\()?'
    r'(?P<skill>acrobatics|animal handling|arcana|athletics|deception|history|insight|intimidation|'
    r'investigation|medicine|nature|perception|performance|persuasion|religion|sleight of hand|'
    r'stealth|survival|str|dex|con|int|wis|cha)'
    r'(?:\s*\))?\s*(?:check)?'
    r'(?:,?\s*dc\s*(?P<dc>\d+))?',
    re.IGNORECASE
)

# Backup pattern for simpler "DC X" mentions
DC_PATTERN = re.compile(r'dc\s*(\d+)', re.IGNORECASE)

LOOT_PATTERN = re.compile(r'you (?:find|found|pick up|obtain|grab) (?:a|an|the)?\s*"?([^"\n]+)"?', re.IGNORECASE)
XP_PATTERN = re.compile(r"(?:defeated?|killed?|vanquished?)\s+(?:the\s+)?(\w+)", re.I)

# Combat trigger patterns - detect when AI narrates combat starting
COMBAT_TRIGGER_PATTERN = re.compile(
    r'(?:roll\s+(?:for\s+)?initiative|'
    r'combat\s+begins|'
    r'(?:they|he|she|it)\s+attacks?\s+(?:you|the\s+party)|'
    r'(?:lunges?|charges?|swings?|strikes?)\s+at\s+(?:you|the\s+party)|'
    r'(?:draw|draws)\s+(?:their|his|her|its)\s+(?:weapon|sword|blade|axe)|'
    r'ambush!|'
    r'(?:battle|fight)\s+(?:begins|starts)|'
    r'hostile\s+(?:and\s+)?attacks?)',
    re.IGNORECASE
)

# Enemy extraction pattern - find enemy names/counts in combat narration
ENEMY_EXTRACT_PATTERN = re.compile(
    r'(\d+)?\s*(goblins?|orcs?|bandits?|skeletons?|zombies?|wolves?|spiders?|'
    r'kobolds?|cultists?|thugs?|guards?|soldiers?|knights?|trolls?|ogres?|'
    r'dire\s+wolves?|giant\s+spiders?|owlbears?|dragons?)',
    re.IGNORECASE
)


def detect_combat_trigger(text):
    """
    Detect if the AI is narrating the start of combat.
    Returns dict with 'trigger': True and 'enemies' list if found, else None.
    """
    if COMBAT_TRIGGER_PATTERN.search(text):
        enemies = []
        for match in ENEMY_EXTRACT_PATTERN.finditer(text):
            count = int(match.group(1)) if match.group(1) else 1
            enemy_type = match.group(2).lower()
            # Normalize to singular
            if enemy_type.endswith('s') and not enemy_type.endswith('ss'):
                enemy_type = enemy_type[:-1]
            for i in range(count):
                if count > 1:
                    enemies.append(f"{enemy_type}{i+1}")
                else:
                    enemies.append(enemy_type)
        return {'trigger': True, 'enemies': enemies} if enemies else {'trigger': True, 'enemies': []}
    return None


def detect_skill_check(text):
    """
    Detect if the AI is asking for a skill check.
    Returns dict with skill, dc if found, else None.
    """
    match = SKILL_CHECK_PATTERN.search(text)
    if match:
        skill = match.group('skill').lower().replace(' ', '_')
        dc = int(match.group('dc')) if match.group('dc') else None
        return {'skill': skill, 'dc': dc}
    return None


def award_xp_for_victory(text, player_id):
    """Detect enemy defeat in text and award XP."""
    match = XP_PATTERN.search(text)
    if not match or not player_id:
        return 0
    enemy = match.group(1).lower()
    xp_table = {'goblin': 50, 'orc': 100, 'dragon': 1000}
    xp = xp_table.get(enemy, 25)
    from utils.character_manager import load_character, set_xp
    char = load_character(player_id)
    if char:
        new_xp = char.get('xp', 0) + xp
        set_xp(player_id, new_xp)
    return xp

DEFAULT_SYSTEM_PROMPT = (
    "You are a Dungeon Master AI for a D&D 5e campaign. Respond to player actions with immersive narration and character dialogue. "
    "Label all character speech with [Voice: Character Name] tags. Narration should be labeled [Voice: Narrator] or left untagged. "
    "Keep track of the story, locations, and NPCs.\n\n"
    "Use the full range of difficulty classes when a check is required:\n"
    "- Very Easy DC 5\n"
    "- Easy DC 10\n"
    "- Medium DC 15\n"
    "- Hard DC 20\n"
    "- Very Hard DC 25\n"
    "- Nearly Impossible DC 30\n"
    "Mention the relevant ability or skill, saving throw, or attack roll. Include proficiency bonuses and whether the roll has advantage or disadvantage when appropriate. "
    "For combat, remind players about initiative, attacking against Armor Class, tracking hit points, and applying conditions. "
    "Keep it simple: ask for the roll, await the result, then narrate the outcome dramatically.\n\n"
    "Example:\n"
    "Player: 'I try to climb the wall'\n"
    "You: 'The wall is slick. Make a Strength (Athletics) check, DC 15.'\n"
    "Player: 'I got 17'\n"
    "You: 'You find purchase and haul yourself over the top!'"
)

def get_dm_response(user_input, state, player_id=None, system_prompt=None):
    from utils.state_manager import get_prompt_context_for_ai
    
    # Get context including campaign summary + recent history
    messages = get_prompt_context_for_ai(state)
    
    # Add character and combat state context
    char_state = state.get('characters', {})
    combat_state = state.get('combat', {})
    context = ''
    if char_state:
        context += '\nCharacters:\n' + '\n'.join([f"{c['name']} (Level {c.get('level',1)} {c.get('class','')}, HP: {c.get('hp','?')}/{c.get('max_hp','?')})" for c in char_state.values()])
    if combat_state:
        context += '\nCombatants:\n' + '\n'.join([f"{c['name']} (HP: {c['hp']}, AC: {c['ac']})" for c in combat_state.get('combatants',[])])
    if context:
        messages = [{"role": "system", "content": context}] + messages
    messages.append({"role": "user", "content": user_input})
    
    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[{"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}] + messages,
            max_tokens=Config.AI_MAX_TOKENS,
            temperature=Config.AI_TEMPERATURE,
            timeout=30
        )
        reply = response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        reply = _handle_openai_error(e, "get_dm_response")
    except Exception as e:
        reply = _handle_openai_error(e, "get_dm_response")
    
    # Update prompt history — preserve first 2 messages (campaign setup) + last N
    history = state.get('prompt_history', [])
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})
    max_history = Config.MAX_PROMPT_HISTORY
    if len(history) > max_history:
        # Keep first 2 messages (campaign context) + most recent entries
        keep_start = min(2, len(history))
        head = history[:keep_start]
        tail = history[-(max_history - keep_start):]
        state['prompt_history'] = head + tail
    else:
        state['prompt_history'] = history
    
    # Check if AI is asking for a skill check
    skill_check = detect_skill_check(reply)
    if skill_check:
        state['pending_roll'] = {
            'player_id': player_id,
            'skill': skill_check['skill'],
            'dc': skill_check.get('dc'),
            'action': user_input  # Remember what they were trying to do
        }
    else:
        state['pending_roll'] = None  # Clear if no roll requested
    
    # Check if AI is triggering combat
    combat_trigger = detect_combat_trigger(reply)
    if combat_trigger:
        state['pending_combat'] = {
            'trigger': True,
            'enemies': combat_trigger.get('enemies', []),
            'context': reply  # Store the narration for reference
        }
    else:
        # Only clear if there's no active combat already
        if not state.get('combat', {}).get('active'):
            state['pending_combat'] = None
    
    # Check for loot
    loot_match = LOOT_PATTERN.search(reply)
    if loot_match:
        state.setdefault('recent_loot', []).append(loot_match.group(1).strip())
    
    award_xp_for_victory(reply, player_id)
    return reply, state

import json as _json


def generate_campaign(state, prompt=None):
    """
    Generate a new campaign setup using GPT-4o.
    Returns natural narration suitable for TTS, plus updates state with campaign details.
    Returns (display_text, tts_text, updated_state)
    """
    system_prompt = """You are a Dungeon Master beginning a new D&D campaign. Create an exciting campaign opening.

Your response must be valid JSON with these keys:
- campaign_title: A dramatic campaign name (2-5 words)
- realm: The world/setting name
- location: Starting location name
- plot_hook: One sentence hook (what draws adventurers in)
- narration: 2-3 paragraphs of immersive scene-setting narration that a DM would read aloud to players. Write it as if you're speaking directly to the players at the table. End with a question or prompt to engage them.

Example narration style:
"The evening mist rolls through the cobblestone streets as you arrive at the village of Thornhaven. Lanterns flicker in windows, but the streets are eerily empty for this hour. A weathered notice board near the inn catches your eye - several pages flutter in the breeze, all bearing the same desperate message: 'MISSING - Reward Offered.' The innkeeper waves you inside urgently. What do you do?"

Make it vivid, atmospheric, and end with something that invites player action."""

    user_input = prompt if prompt else "Create an original fantasy adventure with an intriguing mystery"
    
    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=600,
            temperature=Config.AI_TEMPERATURE,
            timeout=30
        )
        raw_response = response.choices[0].message.content
        
        # Try to extract JSON from response (handle markdown code blocks)
        json_str = raw_response
        if "```json" in raw_response:
            json_str = raw_response.split("```json")[1].split("```")[0]
        elif "```" in raw_response:
            json_str = raw_response.split("```")[1].split("```")[0]
        
        data = _json.loads(json_str.strip())
    except _json.JSONDecodeError:
        # If JSON parsing fails, use the raw response as narration
        data = {
            "campaign_title": "The Adventure Begins",
            "realm": "The Realm",
            "location": "Starting Point",
            "plot_hook": "Adventure awaits...",
            "narration": raw_response if 'raw_response' in dir() else "You stand at the threshold of adventure. The path ahead is shrouded in mystery. What do you do?"
        }
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "generate_campaign")
        data = {
            "campaign_title": "The Adventure Begins",
            "realm": "The Realm", 
            "location": "Starting Point",
            "plot_hook": "Adventure awaits...",
            "narration": "You stand at the threshold of adventure. The path ahead is shrouded in mystery. What do you do?"
        }
    except Exception as e:
        _handle_openai_error(e, "generate_campaign")
        data = {
            "campaign_title": "The Adventure Begins",
            "realm": "The Realm", 
            "location": "Starting Point",
            "plot_hook": "Adventure awaits...",
            "narration": "You stand at the threshold of adventure. The path ahead is shrouded in mystery. What do you do?"
        }

    # Update state
    state.update({
        "campaign_title": data.get("campaign_title", "The Adventure Begins"),
        "realm": data.get("realm", "The Realm"),
        "plot_hook": data.get("plot_hook", ""),
        "location": data.get("location", "Starting Point"),
        "prompt_history": [],
    })

    narration = data.get("narration", "Your adventure begins...")
    
    # Display text (for Discord chat) - nicely formatted
    display_text = (
        f"# ⚔️ {state['campaign_title']}\n"
        f"*{state['realm']} • {state['location']}*\n\n"
        f"{narration}"
    )
    
    # TTS text (for voice) - just the narration, clean
    tts_text = narration

    return display_text, tts_text, state


def summarize_history(state, max_entries=10):
    """Summarize recent prompt history for a session."""
    history = state.get("prompt_history", [])[-max_entries:]
    messages = [
        {"role": "system", "content": "Summarize these recent campaign events into a brief recap, as a Dungeon Master would."}
    ]
    messages.extend(history)

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=messages,
            max_tokens=150,
            temperature=0.7,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "summarize_history")
        return "Previously on your adventure..."
    except Exception as e:
        _handle_openai_error(e, "summarize_history")
        return "Previously on your adventure..."


def generate_campaign_summary(state):
    """
    Generate a comprehensive summary of the campaign so far.
    This is used to condense the prompt history into long-term memory.
    """
    from utils.state_manager import get_context_summary
    
    current_context = get_context_summary(state)
    history = state.get("prompt_history", [])
    
    if not history:
        return state.get("campaign_summary", "")
    
    system_prompt = """You are a D&D campaign chronicler. Your job is to update the campaign summary with new events.

You will receive:
1. The existing campaign summary (if any)
2. Recent conversation history

Create an UPDATED summary that:
- Preserves important past events from the existing summary
- Adds significant new developments from recent history
- Notes any major NPC interactions, discoveries, or plot developments
- Keeps it concise (2-3 paragraphs max)
- Writes in past tense, as a historical record
- Focuses on WHAT HAPPENED, not dialogue

Do NOT include:
- Moment-to-moment details
- Exact dice rolls or mechanics
- Things the party discussed but didn't act on

Return ONLY the updated summary text, no other formatting."""

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    if current_context:
        messages.append({"role": "user", "content": f"EXISTING CAMPAIGN CONTEXT:\n{current_context}"})
    
    if history:
        messages.append({"role": "user", "content": f"RECENT EVENTS:\n{_json.dumps(history, indent=2)}"})
    
    messages.append({"role": "user", "content": "Generate the updated campaign summary."})
    
    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.7,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "generate_campaign_summary")
        return state.get("campaign_summary", "")
    except Exception as e:
        _handle_openai_error(e, "generate_campaign_summary")
        return state.get("campaign_summary", "")


def extract_npcs_and_quests(state, recent_response):
    """
    Analyze recent AI response to extract NPCs and quests to remember.
    Returns dict with 'npcs' and 'quests' lists.
    """
    system_prompt = """Analyze this D&D session text and extract:

1. NPCs mentioned (name, brief description, status - alive/dead/unknown)
2. Quests mentioned (name, description, status - active/completed/failed)

Return valid JSON:
{
    "npcs": [{"name": "Name", "description": "Brief desc", "status": "alive"}],
    "quests": [{"name": "Quest Name", "description": "Brief desc", "status": "active"}]
}

Only include NAMED characters (not "the guard" or "some villagers").
Only include explicit quests/missions, not casual conversations.
Return empty arrays if nothing notable found."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": recent_response}
            ],
            max_tokens=300,
            temperature=0.3,
            timeout=30
        )
        raw = response.choices[0].message.content
        
        # Parse JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        return _json.loads(raw.strip())
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "extract_npcs_and_quests")
        return {"npcs": [], "quests": []}
    except Exception as e:
        logger.error(f"NPC/Quest extraction error: {e}")
        return {"npcs": [], "quests": []}


# =============================================================================
# ENEMY AI NARRATION
# =============================================================================

async def narrate_enemy_action(enemy_turn_result: dict, combat_context: dict = None) -> str:
    """
    Generate dramatic narration for enemy actions during combat.
    
    Args:
        enemy_turn_result: Result from execute_enemy_turn() containing actions, damage, etc.
        combat_context: Optional additional context about the combat situation
    
    Returns:
        Dramatic narration string suitable for TTS
    """
    enemy_name = enemy_turn_result.get('enemy_name', 'The creature')
    actions = enemy_turn_result.get('actions', [])
    damage_dealt = enemy_turn_result.get('damage_dealt', 0)
    targets_hit = enemy_turn_result.get('targets_hit', [])
    movement = enemy_turn_result.get('movement', {})
    context = enemy_turn_result.get('narration_context', {})
    
    # Build prompt for AI
    action_descriptions = []
    for action in actions:
        if action.get('description'):
            action_descriptions.append(action['description'])
        elif action.get('type') == 'attack':
            if action.get('hit'):
                action_descriptions.append(
                    f"Hits {action.get('target', 'a target')} for {action.get('damage', 0)} damage"
                )
            else:
                action_descriptions.append(f"Misses {action.get('target', 'the attack')}")
    
    # Build the prompt
    prompt = f"""As a D&D Dungeon Master, narrate this enemy's combat turn dramatically in 2-3 sentences.

Enemy: {enemy_name}
Enemy Type: {context.get('enemy_type', enemy_name)}
HP Status: {context.get('hp_status', 'unknown')}

Actions taken:
{chr(10).join('- ' + a for a in action_descriptions) if action_descriptions else '- No actions'}

Movement: {movement.get('description', 'None')}

Total damage dealt: {damage_dealt}
Targets affected: {', '.join(targets_hit) if targets_hit else 'None'}
Critical hit: {'Yes!' if context.get('did_crit') else 'No'}
Missed all attacks: {'Yes' if context.get('did_miss_all') else 'No'}

Write immersive, dramatic narration from the DM's perspective. Describe the enemy's actions vividly.
Use [Voice: {enemy_name}] tags for any sounds or battle cries the creature makes.
Keep it concise but impactful."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a dramatic D&D Dungeon Master narrating combat. Keep narrations vivid but brief (2-3 sentences). Use [Voice: CharacterName] tags for creature sounds."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.8,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_enemy_action")
        return _generate_fallback_narration(enemy_turn_result)
    except Exception as e:
        logger.error(f"Enemy narration error: {e}")
        # Fallback to simple narration
        return _generate_fallback_narration(enemy_turn_result)


def _generate_fallback_narration(enemy_turn_result: dict) -> str:
    """Generate simple fallback narration if AI fails."""
    enemy_name = enemy_turn_result.get('enemy_name', 'The creature')
    actions = enemy_turn_result.get('actions', [])
    damage_dealt = enemy_turn_result.get('damage_dealt', 0)
    targets_hit = enemy_turn_result.get('targets_hit', [])
    
    parts = []
    
    # Movement
    movement = enemy_turn_result.get('movement', {})
    if movement.get('description'):
        parts.append(movement['description'])
    
    # Attacks
    for action in actions:
        if action.get('type') == 'flee':
            return f"{enemy_name} turns and flees from combat!"
        elif action.get('type') == 'dodge':
            return f"{enemy_name} takes a defensive stance, ready to dodge attacks."
        elif action.get('description'):
            parts.append(action['description'])
    
    if not parts:
        return f"{enemy_name} readies for combat."
    
    return " ".join(parts)


async def narrate_legendary_action(enemy_name: str, action: dict, 
                                    remaining: int, combat_context: dict = None) -> str:
    """
    Generate dramatic narration for a legendary action.
    
    Args:
        enemy_name: Name of the legendary creature
        action: The legendary action being used
        remaining: Legendary actions remaining after this use
        combat_context: Optional combat context
    
    Returns:
        Dramatic narration string
    """
    action_name = action.get('name', 'Unknown Action')
    action_desc = action.get('description', '')
    cost = action.get('cost', 1)
    
    prompt = f"""As a D&D Dungeon Master, narrate this legendary action dramatically in 1-2 sentences.

Legendary Creature: {enemy_name}
Legendary Action: {action_name}
Description: {action_desc}
Cost: {cost} legendary action(s)
Remaining after use: {remaining}

This happens between player turns - make it feel sudden and powerful!
Use [Voice: {enemy_name}] for any sounds or roars.
Keep it brief but impactful."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a dramatic D&D Dungeon Master narrating legendary actions. These should feel powerful and sudden. Keep it to 1-2 sentences."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.8,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_legendary_action")
        return f"[Voice: {enemy_name}] {enemy_name} uses {action_name}! {action_desc}"
    except Exception as e:
        logger.error(f"Legendary action narration error: {e}")
        return f"[Voice: {enemy_name}] {enemy_name} uses {action_name}! {action_desc}"


async def narrate_lair_action(lair_action: dict, combat_context: dict = None) -> str:
    """
    Generate dramatic narration for a lair action.
    
    Args:
        lair_action: The lair action being triggered
        combat_context: Optional combat context
    
    Returns:
        Dramatic narration string for the lair action
    """
    description = lair_action.get('description', 'The lair itself seems to attack!')
    round_num = lair_action.get('round', 1)
    
    prompt = f"""As a D&D Dungeon Master, narrate this lair action dramatically in 1-2 sentences.

Round: {round_num}
Lair Action: {description}

This happens at initiative count 20 - the very environment turns against the party!
Make it feel environmental and ominous.
Use [Voice: Narrator] for the narration.
Keep it atmospheric but brief."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a D&D Dungeon Master narrating lair actions. These are environmental effects that feel like the dungeon itself is alive and hostile. Keep to 1-2 dramatic sentences."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.8,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_lair_action")
        return f"[Voice: Narrator] {description}"
    except Exception as e:
        logger.error(f"Lair action narration error: {e}")
        return f"[Voice: Narrator] {description}"


# =============================================================================
# SKILL CHECK OUTCOME NARRATION
# =============================================================================

async def narrate_skill_check_outcome(
    player_name: str,
    skill_name: str,
    total: int,
    dc: int,
    success: bool,
    natural_20: bool,
    natural_1: bool,
    original_action: str,
    context: dict = None
) -> str:
    """
    Generate dramatic narration for a skill check outcome.
    
    Args:
        player_name: Name of the character who rolled
        skill_name: The skill or ability checked
        total: Total roll result
        dc: Difficulty class
        success: Whether the check succeeded
        natural_20: Was it a natural 20
        natural_1: Was it a natural 1
        original_action: What the player was attempting
        context: Optional additional context
    
    Returns:
        Dramatic narration of the outcome
    """
    # Build outcome description
    if natural_20:
        outcome_type = "critical success"
        outcome_desc = "With remarkable skill and a touch of luck"
    elif natural_1:
        outcome_type = "critical failure"
        outcome_desc = "Despite their best efforts, disaster strikes"
    elif success:
        outcome_type = "success"
        outcome_desc = "With practiced skill"
    else:
        outcome_type = "failure"
        outcome_desc = "Unfortunately"
    
    margin = abs(total - dc) if dc else 0
    
    prompt = f"""As a D&D Dungeon Master, narrate this skill check outcome in 2-3 vivid sentences.

Character: {player_name}
Skill Check: {skill_name}
Attempting: {original_action}
Roll Total: {total} vs DC {dc}
Outcome: {outcome_type.upper()} (by {margin})

Narrate what happens as a result of this {outcome_type}. Be specific about the consequences.
{outcome_desc}. Do NOT ask for any additional rolls.
Use [Voice: Narrator] or [Voice: {player_name}] tags as appropriate."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a D&D Dungeon Master narrating skill check outcomes. Be dramatic but concise. Describe specific consequences of success or failure. Never ask for more rolls in your narration."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_skill_check_outcome")
        if success:
            return f"[Voice: Narrator] {player_name} succeeds at the {skill_name} check!"
        else:
            return f"[Voice: Narrator] {player_name} fails the {skill_name} check."
    except Exception as e:
        logger.error(f"Skill check narration error: {e}")
        # Fallback narration
        if success:
            return f"[Voice: Narrator] {player_name} succeeds at the {skill_name} check!"
        else:
            return f"[Voice: Narrator] {player_name} fails the {skill_name} check."


async def narrate_group_check_outcome(
    skill_name: str,
    dc: int,
    successes: int,
    failures: int,
    group_success: bool,
    individual_results: list,
    original_context: str
) -> str:
    """
    Generate dramatic narration for a group skill check outcome.
    
    Args:
        skill_name: The skill being checked
        dc: Difficulty class
        successes: Number of successes
        failures: Number of failures
        group_success: Whether the group succeeded overall
        individual_results: List of (name, total, success) tuples
        original_context: What triggered the group check
    
    Returns:
        Dramatic narration of the group outcome
    """
    # Build individual results description
    results_desc = ", ".join([
        f"{name} ({'succeeded' if success else 'failed'})"
        for name, total, success in individual_results
    ])
    
    prompt = f"""As a D&D Dungeon Master, narrate this group skill check outcome in 2-3 sentences.

Group Check: {skill_name} (DC {dc})
Situation: {original_context}
Individual Results: {results_desc}
Successes: {successes}, Failures: {failures}
Overall Outcome: {"SUCCESS" if group_success else "FAILURE"}

Narrate what happens to the party as a whole. Mention how individual performances affected the outcome.
Do NOT ask for any additional rolls.
Use [Voice: Narrator] tag."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a D&D Dungeon Master narrating group skill check outcomes. Describe how the party's combined efforts led to success or failure. Be dramatic but concise."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_group_check_outcome")
        if group_success:
            return f"[Voice: Narrator] Working together, the party succeeds at the {skill_name} check!"
        else:
            return f"[Voice: Narrator] Despite their efforts, the party fails the {skill_name} check."
    except Exception as e:
        logger.error(f"Group check narration error: {e}")
        if group_success:
            return f"[Voice: Narrator] Working together, the party succeeds at the {skill_name} check!"
        else:
            return f"[Voice: Narrator] Despite their efforts, the party fails the {skill_name} check."


async def narrate_passive_notice(
    player_name: str,
    what_noticed: str,
    passive_score: int,
    hidden_dc: int
) -> str:
    """
    Generate narration for when a player's passive perception notices something.
    
    Args:
        player_name: Character who noticed
        what_noticed: Description of what was noticed
        passive_score: The character's passive perception
        hidden_dc: DC that was beaten
    
    Returns:
        Subtle narration of the discovery
    """
    prompt = f"""As a D&D Dungeon Master, subtly narrate that {player_name} notices something.

{player_name}'s passive perception ({passive_score}) beat the DC ({hidden_dc}).
What they noticed: {what_noticed}

Write 1-2 sentences describing {player_name}'s realization. Make it feel natural, not mechanical.
Do not mention the passive score or DC. Use [Voice: Narrator] tag."""

    try:
        response = client.chat.completions.create(
            model=Config.AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a D&D Dungeon Master revealing information that a perceptive character notices. Be subtle and immersive. Don't break immersion by mentioning game mechanics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7,
            timeout=30
        )
        return response.choices[0].message.content
    except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as e:
        _handle_openai_error(e, "narrate_passive_notice")
        return f"[Voice: Narrator] {player_name} notices {what_noticed}."
    except Exception as e:
        logger.error(f"Passive notice narration error: {e}")
        return f"[Voice: Narrator] {player_name} notices {what_noticed}."
