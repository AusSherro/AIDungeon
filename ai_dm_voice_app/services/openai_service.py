import openai
import os
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

ROLL_PATTERN = re.compile(r'roll (?:a |an )?(\d*d\d+|d20)', re.IGNORECASE)
# Support "DC 15" or "need 15 or higher" styles
DC_PATTERN = re.compile(r'(?:dc\s*(\d+)|need (\d+) or higher)', re.IGNORECASE)
LOOT_PATTERN = re.compile(r'you (?:find|found|pick up|obtain|grab) (?:a|an|the)?\s*"?([^"\n]+)"?', re.IGNORECASE)
XP_PATTERN = re.compile(r"(?:defeated?|killed?|vanquished?)\s+(?:the\s+)?(\w+)", re.I)

def detect_roll_request(text, player_id=None):
    """Return pending_roll dict if the text asks for a dice roll."""
    match = ROLL_PATTERN.search(text)
    if not match:
        return None
    dice = match.group(1)
    dc_match = DC_PATTERN.search(text)
    pending = {'type': dice, 'player_id': player_id}
    if dc_match:
        dc_value = dc_match.group(1) or dc_match.group(2)
        if dc_value:
            pending['dc'] = int(dc_value)
    return pending


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
    messages = state.get('prompt_history', [])
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
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT}] + messages,
            max_tokens=500,
            temperature=0.9
        )
        reply = response.choices[0].message['content']
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        reply = "The mystical energies are disrupted... please try again."
    
    # Update state and check for roll requests
    state['prompt_history'] = messages + [{"role": "assistant", "content": reply}]
    if len(state['prompt_history']) > 10:
        state['prompt_history'] = state['prompt_history'][-10:]
    pending = detect_roll_request(reply, player_id)
    if pending:
        state['pending_roll'] = pending
    loot_match = LOOT_PATTERN.search(reply)
    if loot_match:
        state.setdefault('recent_loot', []).append(loot_match.group(1).strip())
    award_xp_for_victory(reply, player_id)
    return reply, state

import json as _json


def generate_campaign(state, prompt=None):
    """
    Generate a new campaign setup using GPT-4o.
    Optionally use a user prompt for inspiration.
    Returns (campaign_text, updated_state)
    """
    system_prompt = (
        "You're a worldbuilder AI. Create a new D&D-style campaign intro."
        " Respond in JSON with keys: campaign_title, realm, plot_hook, location, intro."
    )
    user_input = prompt if prompt else "Begin a new adventure"
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=500,
            temperature=0.8
        )
        campaign_text = response.choices[0].message['content']
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        campaign_text = "{\"campaign_title\": \"Untitled Adventure\", \"realm\": \"Unknown Realm\", \"plot_hook\": \"\", \"location\": \"Nowhere\", \"intro\": \"A mysterious adventure awaits...\"}"

    try:
        data = _json.loads(campaign_text)
    except Exception:
        data = {
            "campaign_title": "Untitled Adventure",
            "realm": "Unknown Realm",
            "plot_hook": "",
            "location": "Starting Point",
            "intro": campaign_text,
        }

    state.update({
        "campaign_title": data.get("campaign_title", "Untitled Adventure"),
        "realm": data.get("realm", "Unknown Realm"),
        "plot_hook": data.get("plot_hook", ""),
        "location": data.get("location", "Starting Point"),
        "prompt_history": [],
    })

    formatted = (
        "=== NEW CAMPAIGN CREATED ===\n"
        f"Title: {state['campaign_title']}\n"
        f"Realm: {state['realm']}\n"
        f"Starting Location: {state['location']}\n\n"
        "[Plot Hook]\n"
        f"{state['plot_hook']}\n\n"
        "[Introduction]\n"
        f"{data.get('intro', campaign_text)}"
    )

    return formatted, state


def summarize_history(state, max_entries=10):
    """Summarize recent prompt history for a session."""
    history = state.get("prompt_history", [])[-max_entries:]
    messages = [
        {"role": "system", "content": "Summarize these recent campaign events into a brief recap, as a Dungeon Master would."}
    ]
    messages.extend(history)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message['content']
    except Exception as e:
        print(f"OpenAI Recap Error: {e}")
        return "Previously on your adventure..."
