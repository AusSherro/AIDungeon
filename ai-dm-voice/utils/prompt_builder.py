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
1. Describe the scene and NPC reactions vividly (2-3 sentences)
2. Use [Voice: Character Name] tags for NPC dialogue
3. Keep narration under 150 words

**CRITICAL - SKILL CHECKS:**
Most actions in D&D require dice rolls! ALWAYS ask for a skill check when the player attempts:
- Sneaking, hiding → "Roll Stealth"
- Picking pockets, lockpicking → "Roll Sleight of Hand, DC [12-20]"
- Lying, bluffing → "Roll Deception"
- Intimidating → "Roll Intimidation"
- Persuading, charming → "Roll Persuasion"
- Climbing, jumping, swimming → "Roll Athletics"
- Balancing, tumbling → "Roll Acrobatics"
- Noticing things → "Roll Perception"
- Searching → "Roll Investigation"
- Recalling lore → "Roll History/Arcana/Religion/Nature"
- Reading intentions → "Roll Insight"
- Treating wounds → "Roll Medicine"
- Tracking, foraging → "Roll Survival"
- Handling animals → "Roll Animal Handling"
- Performing → "Roll Performance"

Format: "Roll [Skill], DC [number]." Then STOP and wait for the result before narrating the outcome.

**End with 3 short action suggestions** (for display only, not TTS):
💡 **What will you do?**
1. [Action option]
2. [Action option]
3. [Action option]
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
