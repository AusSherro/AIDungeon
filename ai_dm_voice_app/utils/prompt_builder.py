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

    system_prompt = f"""
You are the Dungeon Master for a Discord-based D&D-style campaign.
Tone: {difficulty}.

Campaign Title: {title}
Realm: {realm}
Current Location: {location}
Plot Summary: {plot}

Recent actions: {actions_text}
Party composition: {party_comp}

The player is acting in this setting. Maintain consistency with the world and events so far. End your response with 2–3 actions the player could take next.
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
