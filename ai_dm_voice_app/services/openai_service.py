import openai
import os
import re
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

ROLL_PATTERN = re.compile(r'roll (?:a |an )?(\d*d\d+|d20)', re.IGNORECASE)
# Support "DC 15" or "need 15 or higher" styles
DC_PATTERN = re.compile(r'(?:dc\s*(\d+)|need (\d+) or higher)', re.IGNORECASE)

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

SYSTEM_PROMPT = (
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

def get_dm_response(user_input, state, player_id=None):
    messages = state.get('messages', [])
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
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=500,
            temperature=0.9
        )
        reply = response.choices[0].message['content']
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        reply = "The mystical energies are disrupted... please try again."
    
    # Update state and check for roll requests
    state['messages'] = messages + [{"role": "assistant", "content": reply}]
    pending = detect_roll_request(reply, player_id)
    if pending:
        state['pending_roll'] = pending
    return reply, state

def generate_campaign(state, prompt=None):
    """
    Generate a new campaign setup using GPT-4o.
    Optionally use a user prompt for inspiration.
    Returns (campaign_text, updated_state)
    """
    system_prompt = (
        "You're a worldbuilder AI. Generate a new D&D-style campaign with a title, setting, and plot hook. "
        "Format as: Title, Setting, Plot Hook."
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
        campaign_text = "A mysterious adventure awaits..."
    
    # Save campaign in state
    state['campaign'] = campaign_text
    return campaign_text, state
