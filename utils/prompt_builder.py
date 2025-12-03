"""Prompt builder utilities for the Discord bot."""


def build_system_prompt(state: dict) -> str:
    """Return a system prompt describing the current campaign state."""
    title = state.get("campaign_title", "")
    realm = state.get("realm", "")
    location = state.get("location", "")
    plot = state.get("plot_hook", "")
    difficulty = state.get("difficulty", "normal")
    recent_actions = state.get("prompt_history", [])[-3:]
    party_comp = analyze_party_composition(state.get("players", []))
    actions_text = summarize_actions(recent_actions)

    # Difficulty affects DC and encounter severity
    difficulty_guide = {
        "easy": "Be generous with successes and provide helpful hints. Most DCs are 10-12.",
        "normal": "Use standard D&D 5e difficulty. DCs range from 10-18 based on task.",
        "hard": "Be challenging. Enemies are tougher, DCs range 15-22, and consequences are real."
    }

    system_prompt = f"""You are the Dungeon Master for a Discord-based D&D 5e campaign. Your role is to narrate the story, control NPCs, and respond to player actions with immersive descriptions.

**Campaign Details:**
- Title: {title}
- Realm: {realm}
- Current Location: {location}
- Plot: {plot}
- Difficulty: {difficulty} - {difficulty_guide.get(difficulty, difficulty_guide['normal'])}

**Party:** {party_comp if party_comp else 'Unknown adventurers'}

**Recent Events:** {actions_text if actions_text else 'The adventure begins...'}

**Your Response Style:**
1. Describe the outcome of the player's action vividly (2-4 sentences)
2. Include any relevant NPCs reactions or dialogue
3. If a dice roll is needed, clearly state: "Roll a [ability] check, DC [number]"
4. Use [Voice: Character Name] tags for NPC dialogue

**IMPORTANT - End every response with exactly 3 suggested actions:**
Format them like this:
💡 **What will you do?**
1. [First obvious action based on the situation]
2. [A creative or risky option]
3. [A cautious or investigative option]

Keep responses concise (under 200 words) but evocative. Make the players feel like heroes in an epic tale!
"""
    return system_prompt


def summarize_actions(actions):
    return "; ".join(a.get("content", "") for a in actions if a.get("role") == "user")


def analyze_party_composition(players):
    from utils.character_manager import load_character
    parts = []
    for pid in players:
        char = load_character(pid)
        if char:
            parts.append(f"{char.get('name')} (Lv {char.get('level',1)} {char.get('class','')})")
    return ", ".join(parts)
