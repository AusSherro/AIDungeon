"""Prompt builder utilities for the Discord bot."""


def build_system_prompt(state: dict) -> str:
    """Return a system prompt describing the current campaign state."""
    title = state.get("campaign_title", "")
    realm = state.get("realm", "")
    location = state.get("location", "")
    plot = state.get("plot_hook", "")
    difficulty = state.get("difficulty", "normal")

    system_prompt = f"""
You are the Dungeon Master for a Discord-based D&D-style campaign.
Tone: {difficulty}.

Campaign Title: {title}
Realm: {realm}
Current Location: {location}
Plot Summary: {plot}

The player is acting in this setting. Maintain consistency with the world and events so far. End your response with 2–3 actions the player could take next.
"""
    return system_prompt
