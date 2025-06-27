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

    return data.get("intro", campaign_text), state


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

# --- Storytelling helpers ---

def get_system_message(genre=None):
    base_prompt = """You are an immersive AI Dungeon Master running an interactive text adventure game.

CORE RULES:
1. Always write in second-person perspective ("You..." not "I..." or "He/She...")
2. Present tense for actions, past tense for completed events
3. Respond to player actions as if they are attempting to do something, not automatically succeeding
4. Maintain story continuity - remember names, places, items, and events
5. Keep responses 2-4 paragraphs (100-200 words) unless the situation demands more
6. End each response with an open situation that encourages player action

RESPONSE STYLE:
- Use vivid sensory details (sights, sounds, smells, textures)
- Show character emotions through actions and dialogue
- Create tension through obstacles and consequences
- Balance success and failure based on logical outcomes
- Include environmental details that can be interacted with

HANDLING PLAYER ACTIONS:
- "Do" actions: Describe the attempt and outcome realistically
- "Say" actions: Include the dialogue and NPC responses
- "Story" actions: Continue the narrative naturally

MAINTAIN IMMERSION:
- Never break character or mention being an AI
- Don't ask what the player wants to do next (they'll tell you)
- Don't summarize or skip time unless the player indicates it
- React to player actions even if they seem unusual"""

    genre_additions = {
        "fantasy": "\n\nGENRE: High Fantasy\n- Include magic, mythical creatures, and medieval elements\n- Magic has rules and limitations\n- Maintain internal consistency with fantasy logic",
        "mystery": "\n\nGENRE: Mystery/Detective\n- Include clues, red herrings, and suspects\n- Build suspense and uncertainty\n- Let the player uncover information through investigation",
        "apocalypse": "\n\nGENRE: Post-Apocalyptic\n- Emphasize survival, scarcity, and danger\n- Include environmental hazards and hostile survivors\n- Create moral dilemmas around resources",
        "cyberpunk": "\n\nGENRE: Cyberpunk\n- Include futuristic technology, corporations, and social inequality\n- Blend high-tech with low-life elements\n- Create a noir atmosphere with neon-lit urban settings",
        "zombies": "\n\nGENRE: Zombie Survival\n- Include zombie encounters, survival mechanics, and safe zones\n- Create tension through limited resources\n- Balance action with human drama",
    }

    if genre and genre in genre_additions:
        return base_prompt + genre_additions[genre]
    return base_prompt


def generate_text(prompt, action_type="continue", story_context=None, genre=None):
    messages = [{"role": "system", "content": get_system_message(genre)}]
    if story_context:
        messages.append({"role": "assistant", "content": story_context})

    if action_type == "do":
        user_message = f"I attempt to: {prompt}"
    elif action_type == "say":
        user_message = f"I say: \"{prompt}\""
    elif action_type == "story":
        user_message = f"Continue the story: {prompt}"
    else:
        user_message = prompt

    messages.append({"role": "user", "content": user_message})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.85,
        max_tokens=250,
        presence_penalty=0.3,
        frequency_penalty=0.3,
    )

    return response.choices[0].message.content
