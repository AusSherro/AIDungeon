import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}] + messages,
            max_tokens=500,
            temperature=0.9
        )
        reply = response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        reply = "The mystical energies are disrupted... please try again."
    
    # Update prompt history (just the recent conversation, summary is separate)
    history = state.get('prompt_history', [])
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})
    # Keep rolling window of 10 recent exchanges
    if len(history) > 10:
        state['prompt_history'] = history[-10:]
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
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=600,
            temperature=0.9
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
    except Exception as e:
        print(f"OpenAI API Error: {e}")
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
            model="gpt-4o",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Recap Error: {e}")
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
            model="gpt-4o",
            messages=messages,
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI Summary Error: {e}")
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
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": recent_response}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        
        # Parse JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        return _json.loads(raw.strip())
    except Exception as e:
        print(f"NPC/Quest extraction error: {e}")
        return {"npcs": [], "quests": []}
