"""
Unified parser for structured tags in AI narration.

All tag detection goes through this module. Other modules keep their
processing logic but delegate detection here.

Supported tags:
  [COMBAT: 3 goblins, 1 hobgoblin]
  [SURPRISE: enemies]
  [QUEST: name="Rescue the Princess", type=rescue, difficulty=hard]
  [QUEST_COMPLETE: "Rescue the Princess"]
  [QUEST_PROGRESS: "Quest Name", objective=1]
  [RUMOR: "Strange lights at the cemetery"]
  [QUEST_HOOK: name="Mystery", description="Investigate the lights"]
  [OBJECTIVE: "Find the hidden entrance"]
  [QUEST_CHAIN: parent="Main Quest", child="Sequel"]
  [WEATHER: heavy rain]
  [LIGHTING: dim]
  [LOCATION: Dark Cave]
  [TIME: 3 hours pass]
  [TRAP: pit trap at entrance]
  [HAZARD: lava pool, 2d6 fire]
  [ENVIRONMENT: dark cave, cold]
  [TRAVEL: destination="Phandalin", distance=15, terrain=forest]
  [LOCATION_DISCOVERED: name="Ruined Tower", terrain=hills, poi=true]
  [ARRIVAL: "Phandalin"]
  [DISTANCE_REVEALED: from="A" to="B" miles=100]
  [LOOT: 50gp, Longsword, Potion of Healing]
  [SKILL_CHECK: Perception DC 15]
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any


# =============================================================================
# CORE REGEX — one forgiving pattern that captures any [TAG_NAME: content]
# =============================================================================

TAG_PATTERN = re.compile(
    r'\[\s*([A-Z_]+)\s*:\s*([^\]]+?)\s*\]',
    re.IGNORECASE
)


# =============================================================================
# ATTRIBUTE PARSER
# =============================================================================

def parse_attributes(attr_string: str) -> Dict[str, str]:
    """
    Parse key=value pairs from tag content.

    Handles:
      name="Bob's Quest"      -> {"name": "Bob's Quest"}
      name='Rescue Mission'   -> {"name": "Rescue Mission"}
      name=Rescue              -> {"name": "Rescue"}
      distance=15              -> {"distance": "15"}
      terrain = forest         -> {"terrain": "forest"}
      poi=true                 -> {"poi": "true"}
    """
    result: Dict[str, str] = {}

    # Pass 1: quoted values (double or single), allowing apostrophes inside
    # key="value with spaces and Bob's stuff"
    quoted = re.compile(r'''(\w+)\s*=\s*"([^"]*)"''')
    for m in quoted.finditer(attr_string):
        result[m.group(1).lower()] = m.group(2)

    single_quoted = re.compile(r"(\w+)\s*=\s*'([^']*)'")
    for m in single_quoted.finditer(attr_string):
        key = m.group(1).lower()
        if key not in result:
            result[key] = m.group(2)

    # Pass 2: unquoted values (word chars, dots, digits) — skip already-matched
    remaining = re.sub(r'''(\w+)\s*=\s*["'][^"']*["']''', '', attr_string)
    unquoted = re.compile(r'(\w+)\s*=\s*([\w.]+)')
    for m in unquoted.finditer(remaining):
        key = m.group(1).lower()
        if key not in result:
            result[key] = m.group(2)

    return result


# =============================================================================
# PARSED TAGS DATACLASS
# =============================================================================

@dataclass
class ParsedTags:
    """All structured tags detected in a block of text."""

    combat: List[Dict[str, Any]] = field(default_factory=list)
    surprise: List[str] = field(default_factory=list)
    quests: List[Dict[str, Any]] = field(default_factory=list)
    quest_completions: List[str] = field(default_factory=list)
    quest_progress: List[Dict[str, Any]] = field(default_factory=list)
    rumors: List[str] = field(default_factory=list)
    quest_hooks: List[Dict[str, Any]] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    quest_chains: List[Dict[str, Any]] = field(default_factory=list)
    weather: List[str] = field(default_factory=list)
    lighting: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    time_changes: List[str] = field(default_factory=list)
    traps: List[str] = field(default_factory=list)
    hazards: List[str] = field(default_factory=list)
    environment: List[str] = field(default_factory=list)
    travel: List[Dict[str, Any]] = field(default_factory=list)
    discoveries: List[Dict[str, Any]] = field(default_factory=list)
    arrivals: List[str] = field(default_factory=list)
    distances: List[Dict[str, Any]] = field(default_factory=list)
    loot: List[str] = field(default_factory=list)
    skill_checks: List[Dict[str, Any]] = field(default_factory=list)
    raw_tags: List[Tuple[str, str]] = field(default_factory=list)

    def has_any(self) -> bool:
        """Return True if any tags were detected."""
        return bool(self.raw_tags)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def parse_all_tags(text: str) -> ParsedTags:
    """
    Parse all structured tags from *text* and return a ParsedTags instance.

    Each tag is routed to the appropriate list based on its name.  Unknown
    tag names are still captured in ``raw_tags``.
    """
    tags = ParsedTags()

    for match in TAG_PATTERN.finditer(text):
        tag_name = match.group(1).upper()
        content = match.group(2).strip()
        tags.raw_tags.append((tag_name, content))

        # ---- Combat / Surprise ----
        if tag_name == "COMBAT":
            tags.combat.append({"enemies": content})
        elif tag_name == "SURPRISE":
            tags.surprise.append(content.lower())

        # ---- Quest family ----
        elif tag_name == "QUEST":
            attrs = parse_attributes(content)
            if attrs.get("name") or not any(k in content for k in ("=",)):
                # If no key=value pairs, treat whole content as quest name
                if not attrs.get("name"):
                    attrs["name"] = content.strip("\"'")
                tags.quests.append(attrs)
        elif tag_name == "QUEST_COMPLETE":
            tags.quest_completions.append(content.strip("\"'"))
        elif tag_name == "QUEST_PROGRESS":
            attrs = parse_attributes(content)
            quest_ref = content.split(",")[0].strip().strip("\"'")
            tags.quest_progress.append({
                "quest": quest_ref,
                "objective": attrs.get("objective", "1"),
                "amount": attrs.get("amount", "1"),
            })
        elif tag_name == "RUMOR":
            tags.rumors.append(content.strip("\"'"))
        elif tag_name == "QUEST_HOOK":
            attrs = parse_attributes(content)
            tags.quest_hooks.append(attrs)
        elif tag_name == "OBJECTIVE":
            tags.objectives.append(content.strip("\"'"))
        elif tag_name == "QUEST_CHAIN":
            attrs = parse_attributes(content)
            if "parent" in attrs and "child" in attrs:
                tags.quest_chains.append(attrs)

        # ---- Environment family ----
        elif tag_name == "WEATHER":
            tags.weather.append(content)
        elif tag_name == "LIGHTING":
            tags.lighting.append(content)
        elif tag_name == "LOCATION":
            tags.locations.append(content)
        elif tag_name == "TIME":
            tags.time_changes.append(content)
        elif tag_name == "TRAP":
            tags.traps.append(content)
        elif tag_name == "HAZARD":
            tags.hazards.append(content)
        elif tag_name == "ENVIRONMENT":
            tags.environment.append(content)

        # ---- Travel family ----
        elif tag_name == "TRAVEL":
            attrs = parse_attributes(content)
            tags.travel.append(attrs)
        elif tag_name == "LOCATION_DISCOVERED":
            attrs = parse_attributes(content)
            tags.discoveries.append(attrs)
        elif tag_name == "ARRIVAL":
            tags.arrivals.append(content.strip("\"'"))
        elif tag_name == "DISTANCE_REVEALED":
            attrs = parse_attributes(content)
            tags.distances.append(attrs)

        # ---- Misc ----
        elif tag_name == "LOOT":
            tags.loot.append(content)
        elif tag_name == "SKILL_CHECK":
            attrs = parse_attributes(content)
            if not attrs:
                attrs["raw"] = content
            tags.skill_checks.append(attrs)

    return tags


# =============================================================================
# STRIP TAGS — remove all [TAG: ...] blocks from display text
# =============================================================================

def strip_tags(text: str) -> str:
    """Remove all structured tags so players don't see them."""
    cleaned = TAG_PATTERN.sub('', text)
    # Collapse double-newlines left behind
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()
