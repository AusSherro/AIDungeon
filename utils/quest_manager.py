"""
Quest Manager - Comprehensive quest and objective tracking for D&D campaigns.

Features:
- Quest tracking with multiple objectives
- Milestone detection from AI narration
- XP, gold, and reputation rewards on completion
- Side quest generation hooks
- Quest log with progress indicators
"""

import os
import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging

from utils.tag_parser import parse_all_tags, parse_attributes, ParsedTags

logger = logging.getLogger(__name__)

# Directory for quest data storage
QUEST_DIR = os.path.join(os.path.dirname(__file__), '..', 'state', 'quests')
os.makedirs(QUEST_DIR, exist_ok=True)


# =============================================================================
# ENUMS
# =============================================================================

class QuestStatus(Enum):
    """Status of a quest."""
    AVAILABLE = "available"      # Quest is known but not accepted
    ACTIVE = "active"            # Quest has been accepted
    COMPLETED = "completed"      # All objectives done
    FAILED = "failed"            # Quest failed
    ABANDONED = "abandoned"      # Player gave up


class ObjectiveStatus(Enum):
    """Status of a quest objective."""
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"
    OPTIONAL = "optional"


class QuestType(Enum):
    """Type of quest."""
    MAIN = "main"               # Main story quest
    SIDE = "side"               # Side quest
    FACTION = "faction"         # Faction-related quest
    PERSONAL = "personal"       # Character backstory quest
    BOUNTY = "bounty"           # Kill/capture target
    FETCH = "fetch"             # Retrieve an item
    ESCORT = "escort"           # Protect someone
    EXPLORE = "explore"         # Discover a location
    MYSTERY = "mystery"         # Investigate/solve


class QuestDifficulty(Enum):
    """Difficulty tier of a quest."""
    TRIVIAL = "trivial"         # 50 XP base
    EASY = "easy"               # 100 XP base
    MEDIUM = "medium"           # 250 XP base
    HARD = "hard"               # 500 XP base
    DEADLY = "deadly"           # 1000 XP base
    LEGENDARY = "legendary"     # 2500 XP base


# XP rewards by difficulty
XP_REWARDS = {
    QuestDifficulty.TRIVIAL: 50,
    QuestDifficulty.EASY: 100,
    QuestDifficulty.MEDIUM: 250,
    QuestDifficulty.HARD: 500,
    QuestDifficulty.DEADLY: 1000,
    QuestDifficulty.LEGENDARY: 2500,
}

# Gold rewards by difficulty (base amounts, scaled by party level)
GOLD_REWARDS = {
    QuestDifficulty.TRIVIAL: 10,
    QuestDifficulty.EASY: 25,
    QuestDifficulty.MEDIUM: 50,
    QuestDifficulty.HARD: 150,
    QuestDifficulty.DEADLY: 500,
    QuestDifficulty.LEGENDARY: 2000,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class QuestObjective:
    """A single objective within a quest."""
    id: str                                 # Unique ID (e.g., "obj_1")
    description: str                        # What needs to be done
    status: str = "incomplete"              # incomplete, complete, failed, optional
    progress: int = 0                       # Current progress count
    required: int = 1                       # Required count (for "kill 5 goblins" etc.)
    is_optional: bool = False               # Optional bonus objective
    is_hidden: bool = False                 # Hidden until discovered
    completion_text: str = ""               # Text shown on completion
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QuestObjective':
        return cls(**data)
    
    def is_complete(self) -> bool:
        return self.status == "complete" or self.progress >= self.required
    
    def add_progress(self, amount: int = 1) -> bool:
        """Add progress to objective. Returns True if newly completed."""
        if self.status == "complete":
            return False
        self.progress = min(self.progress + amount, self.required)
        if self.progress >= self.required:
            self.status = "complete"
            return True
        return False


@dataclass
class QuestReward:
    """Rewards for completing a quest."""
    xp: int = 0                             # Experience points
    gold: int = 0                           # Gold pieces
    items: List[str] = field(default_factory=list)  # Item names
    reputation: Dict[str, int] = field(default_factory=dict)  # faction -> change
    special: str = ""                       # Special reward description
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QuestReward':
        return cls(**data)


@dataclass
class Quest:
    """A quest with objectives and rewards."""
    id: str                                 # Unique quest ID
    name: str                               # Quest name
    description: str                        # Full description
    status: str = "active"                  # available, active, completed, failed, abandoned
    quest_type: str = "side"                # main, side, faction, personal, etc.
    difficulty: str = "medium"              # trivial, easy, medium, hard, deadly, legendary
    giver_npc: str = ""                     # NPC who gave the quest
    location: str = ""                      # Where the quest takes place
    objectives: List[Dict] = field(default_factory=list)  # List of objectives
    rewards: Dict = field(default_factory=dict)  # Quest rewards
    deadline: str = ""                      # Optional time limit description
    notes: List[str] = field(default_factory=list)  # Player notes
    created_at: str = ""                    # Timestamp
    completed_at: str = ""                  # Timestamp when completed
    tags: List[str] = field(default_factory=list)  # For categorization
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        # Convert objective dicts to QuestObjective if needed
        if self.objectives and isinstance(self.objectives[0], dict):
            pass  # Keep as dicts for JSON serialization
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Quest':
        return cls(**data)
    
    def get_objectives(self) -> List[QuestObjective]:
        """Get objectives as QuestObjective instances."""
        return [QuestObjective.from_dict(obj) for obj in self.objectives]
    
    def set_objectives(self, objectives: List[QuestObjective]):
        """Set objectives from QuestObjective instances."""
        self.objectives = [obj.to_dict() for obj in objectives]
    
    def get_rewards(self) -> QuestReward:
        """Get rewards as QuestReward instance."""
        return QuestReward.from_dict(self.rewards) if self.rewards else QuestReward()
    
    def set_rewards(self, rewards: QuestReward):
        """Set rewards from QuestReward instance."""
        self.rewards = rewards.to_dict()
    
    def is_complete(self) -> bool:
        """Check if all required objectives are complete."""
        objectives = self.get_objectives()
        required = [obj for obj in objectives if not obj.is_optional]
        return all(obj.is_complete() for obj in required)
    
    def get_progress(self) -> Tuple[int, int]:
        """Get (completed, total) required objectives."""
        objectives = self.get_objectives()
        required = [obj for obj in objectives if not obj.is_optional]
        completed = sum(1 for obj in required if obj.is_complete())
        return (completed, len(required))
    
    def get_progress_percent(self) -> float:
        """Get completion percentage (0-100)."""
        completed, total = self.get_progress()
        return (completed / total * 100) if total > 0 else 100


# =============================================================================
# MILESTONE DETECTION PATTERNS
# =============================================================================

# Patterns to detect quest completion/progress from AI narration
COMPLETION_PATTERNS = [
    # Direct completion mentions
    r"(?:quest|mission|task).*(?:complete|accomplished|finished|done|fulfilled)",
    r"(?:you(?:'ve| have)|party has?).*(?:completed|finished|accomplished).*(?:quest|mission|task)",
    r"(?:objective|goal).*(?:achieved|reached|complete)",
    
    # Item retrieval
    r"(?:retrieved|obtained|acquired|found|recovered).*(?:artifact|relic|item|treasure|sword|weapon|armor)",
    r"(?:you(?:'ve| have)).*(?:the|a).*(?:artifact|relic|item|treasure)",
    
    # Defeat/kill patterns
    r"(?:defeated|slain|killed|vanquished|destroyed).*(?:boss|leader|dragon|monster|villain)",
    r"(?:enemy|foe|villain|monster).*(?:has been|is).*(?:defeated|slain|destroyed)",
    
    # Rescue/save patterns
    r"(?:rescued|saved|freed|liberated).*(?:prisoner|captive|hostage|villager)",
    r"(?:safely|successfully).*(?:escorted|delivered|returned)",
    
    # Discovery patterns
    r"(?:discovered|found|uncovered|revealed).*(?:secret|truth|location|passage)",
    r"(?:mystery|puzzle|riddle).*(?:solved|unraveled|resolved)",
    
    # Delivery/escort patterns
    r"(?:delivered|brought|transported).*(?:package|letter|message|cargo)",
    r"(?:safely arrived|reached.*destination|made it to)",
    
    # Negotiation patterns
    r"(?:negotiated|brokered|secured).*(?:peace|alliance|deal|treaty)",
    r"(?:convinced|persuaded).*(?:to help|to join|to surrender)",
]

# Patterns for quest failure
FAILURE_PATTERNS = [
    r"(?:quest|mission|task).*(?:failed|lost|impossible)",
    r"(?:too late|couldn't save|didn't make it)",
    r"(?:objective|goal).*(?:failed|lost|unreachable)",
    r"(?:NPC name).*(?:died|killed|perished)",
]

# Patterns for new objective discovery
OBJECTIVE_PATTERNS = [
    r"(?:must|need to|should|have to).*(?:find|retrieve|defeat|rescue|deliver|discover)",
    r"(?:next step|first|then|after that).*(?:is to|you must|you need)",
    r"(?:objective|goal|task):?\s*(.+)",
]


# =============================================================================
# STRUCTURED TAG PATTERNS (Phase 13)
# =============================================================================

# [QUEST: name="Rescue the Princess", type=rescue, difficulty=hard, giver="King Aldric"]
QUEST_TAG_PATTERN = re.compile(
    r'\[QUEST:\s*([^\]]+)\]',
    re.IGNORECASE
)

# [QUEST_COMPLETE: "Rescue the Princess"] or [QUEST_COMPLETE: quest_id]
QUEST_COMPLETE_TAG_PATTERN = re.compile(
    r'\[QUEST_COMPLETE:\s*["\']?([^"\'\]]+)["\']?\]',
    re.IGNORECASE
)

# [QUEST_PROGRESS: "Rescue the Princess", objective=1] or objective="Find the tower"
QUEST_PROGRESS_TAG_PATTERN = re.compile(
    r'\[QUEST_PROGRESS:\s*([^\]]+)\]',
    re.IGNORECASE
)

# [RUMOR: "Strange lights have been seen near the old cemetery"]
RUMOR_TAG_PATTERN = re.compile(
    r'\[RUMOR:\s*["\']?([^"\'\]]+)["\']?\]',
    re.IGNORECASE
)

# [QUEST_HOOK: name="The Missing Merchant", description="A merchant went missing on the road"]
QUEST_HOOK_TAG_PATTERN = re.compile(
    r'\[QUEST_HOOK:\s*([^\]]+)\]',
    re.IGNORECASE
)

# [OBJECTIVE: "Find the hidden entrance"] - add to current quest
OBJECTIVE_TAG_PATTERN = re.compile(
    r'\[OBJECTIVE:\s*["\']?([^"\'\]]+)["\']?\]',
    re.IGNORECASE
)

# [QUEST_CHAIN: parent="Main Quest", child="Side Quest"]
QUEST_CHAIN_TAG_PATTERN = re.compile(
    r'\[QUEST_CHAIN:\s*([^\]]+)\]',
    re.IGNORECASE
)

# Natural language quest offer patterns (improved)
QUEST_OFFER_PATTERNS = [
    # Direct requests for help
    r"(?:please|i beg you|you must).*(?:help|save|rescue|find|retrieve|stop|defeat)",
    r"(?:will you|would you|can you|could you).*(?:help|save|rescue|find|retrieve|deliver)",
    # Reward mentions
    r"(?:reward|payment|gold|coin|treasure).*(?:if you|for your|upon completion|when you)",
    r"(?:i('ll| will)|we('ll| will)).*(?:pay|reward|compensate).*(?:handsomely|well|generously)",
    # Quest assignment
    r"(?:offers?|gives?|assigns?|presents?).*(?:quest|mission|task|job)",
    r"(?:your (?:new )?(?:quest|mission|task|objective)).*(?:is|will be)",
    # Need/seek patterns
    r"(?:we need|i need|the (?:village|town|kingdom) needs?).*(?:heroes?|adventurers?|someone)",
    r"(?:seeking|looking for).*(?:brave|capable|skilled).*(?:adventurers?|heroes?)",
]


# =============================================================================
# QUEST PERSISTENCE
# =============================================================================

def _get_quest_path(channel_id: str) -> str:
    """Get the file path for a channel's quest data."""
    return os.path.join(QUEST_DIR, f'{channel_id}_quests.json')


def load_quests(channel_id: str) -> List[Quest]:
    """Load all quests for a channel."""
    path = _get_quest_path(channel_id)
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Quest.from_dict(q) for q in data]
    except Exception as e:
        logger.error(f"Error loading quests for {channel_id}: {e}")
        return []


def save_quests(channel_id: str, quests: List[Quest]):
    """Save all quests for a channel."""
    path = _get_quest_path(channel_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([q.to_dict() for q in quests], f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving quests for {channel_id}: {e}")


def get_quest(channel_id: str, quest_id: str) -> Optional[Quest]:
    """Get a specific quest by ID."""
    quests = load_quests(channel_id)
    for quest in quests:
        if quest.id == quest_id or quest.name.lower() == quest_id.lower():
            return quest
    return None


def get_quest_by_name(channel_id: str, name: str) -> Optional[Quest]:
    """Get a quest by name (case-insensitive partial match)."""
    quests = load_quests(channel_id)
    name_lower = name.lower()
    
    # Exact match first
    for quest in quests:
        if quest.name.lower() == name_lower:
            return quest
    
    # Partial match
    for quest in quests:
        if name_lower in quest.name.lower():
            return quest
    
    return None


# =============================================================================
# QUEST MANAGEMENT
# =============================================================================

def create_quest(
    channel_id: str,
    name: str,
    description: str,
    quest_type: str = "side",
    difficulty: str = "medium",
    giver_npc: str = "",
    objectives: List[str] = None,
    rewards: QuestReward = None,
    status: str = "active",
    tags: List[str] = None
) -> Quest:
    """
    Create a new quest.
    
    Args:
        channel_id: Discord channel ID
        name: Quest name
        description: Quest description
        quest_type: main, side, faction, personal, etc.
        difficulty: trivial, easy, medium, hard, deadly, legendary
        giver_npc: NPC who gave the quest
        objectives: List of objective descriptions (creates simple objectives)
        rewards: Quest rewards
        status: Initial status (active, available)
        tags: List of tags for categorization
    
    Returns:
        The created Quest
    """
    quests = load_quests(channel_id)
    
    # Generate unique ID
    quest_id = f"quest_{len(quests) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Create objectives from descriptions
    quest_objectives = []
    if objectives:
        for i, obj_desc in enumerate(objectives):
            quest_objectives.append(QuestObjective(
                id=f"obj_{i + 1}",
                description=obj_desc
            ).to_dict())
    else:
        # Default objective: Complete the quest
        quest_objectives.append(QuestObjective(
            id="obj_1",
            description=description
        ).to_dict())
    
    # Create default rewards if not provided
    if rewards is None:
        try:
            diff = QuestDifficulty(difficulty)
        except ValueError:
            diff = QuestDifficulty.MEDIUM
        rewards = QuestReward(
            xp=XP_REWARDS.get(diff, 250),
            gold=GOLD_REWARDS.get(diff, 50)
        )
    
    quest = Quest(
        id=quest_id,
        name=name,
        description=description,
        status=status,
        quest_type=quest_type,
        difficulty=difficulty,
        giver_npc=giver_npc,
        objectives=quest_objectives,
        rewards=rewards.to_dict() if isinstance(rewards, QuestReward) else rewards,
        tags=tags or []
    )
    
    quests.append(quest)
    save_quests(channel_id, quests)
    
    logger.info(f"Created quest '{name}' in channel {channel_id}")
    return quest


def update_quest(channel_id: str, quest: Quest):
    """Update an existing quest."""
    quests = load_quests(channel_id)
    for i, q in enumerate(quests):
        if q.id == quest.id:
            quests[i] = quest
            save_quests(channel_id, quests)
            return True
    return False


def delete_quest(channel_id: str, quest_id: str) -> bool:
    """Delete a quest by ID."""
    quests = load_quests(channel_id)
    original_count = len(quests)
    quests = [q for q in quests if q.id != quest_id and q.name.lower() != quest_id.lower()]
    if len(quests) < original_count:
        save_quests(channel_id, quests)
        return True
    return False


def get_active_quests(channel_id: str) -> List[Quest]:
    """Get all active quests for a channel."""
    quests = load_quests(channel_id)
    return [q for q in quests if q.status == "active"]


def get_completed_quests(channel_id: str) -> List[Quest]:
    """Get all completed quests for a channel."""
    quests = load_quests(channel_id)
    return [q for q in quests if q.status == "completed"]


def get_available_quests(channel_id: str) -> List[Quest]:
    """Get quests that are available but not yet accepted."""
    quests = load_quests(channel_id)
    return [q for q in quests if q.status == "available"]


# =============================================================================
# OBJECTIVE MANAGEMENT
# =============================================================================

def add_objective(
    channel_id: str,
    quest_id: str,
    description: str,
    required: int = 1,
    is_optional: bool = False,
    is_hidden: bool = False
) -> Optional[QuestObjective]:
    """Add an objective to a quest."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return None
    
    objectives = quest.get_objectives()
    new_obj = QuestObjective(
        id=f"obj_{len(objectives) + 1}",
        description=description,
        required=required,
        is_optional=is_optional,
        is_hidden=is_hidden
    )
    objectives.append(new_obj)
    quest.set_objectives(objectives)
    update_quest(channel_id, quest)
    
    return new_obj


def update_objective_progress(
    channel_id: str,
    quest_id: str,
    objective_id: str,
    progress: int = 1
) -> Tuple[bool, Optional[str]]:
    """
    Add progress to an objective.
    
    Returns:
        (objective_completed, completion_message)
    """
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False, None
    
    objectives = quest.get_objectives()
    for obj in objectives:
        if obj.id == objective_id:
            completed = obj.add_progress(progress)
            quest.set_objectives(objectives)
            update_quest(channel_id, quest)
            
            if completed:
                msg = obj.completion_text or f"✅ Objective complete: {obj.description}"
                return True, msg
            return False, None
    
    return False, None


def complete_objective(
    channel_id: str,
    quest_id: str,
    objective_id: str
) -> Tuple[bool, Optional[str]]:
    """Mark an objective as complete."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False, None
    
    objectives = quest.get_objectives()
    for obj in objectives:
        if obj.id == objective_id:
            if obj.status != "complete":
                obj.status = "complete"
                obj.progress = obj.required
                quest.set_objectives(objectives)
                update_quest(channel_id, quest)
                
                msg = obj.completion_text or f"✅ Objective complete: {obj.description}"
                return True, msg
            return False, "Already complete"
    
    return False, "Objective not found"


def fail_objective(channel_id: str, quest_id: str, objective_id: str) -> bool:
    """Mark an objective as failed."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False
    
    objectives = quest.get_objectives()
    for obj in objectives:
        if obj.id == objective_id:
            obj.status = "failed"
            quest.set_objectives(objectives)
            update_quest(channel_id, quest)
            return True
    
    return False


# =============================================================================
# QUEST COMPLETION & REWARDS
# =============================================================================

def complete_quest(channel_id: str, quest_id: str) -> Tuple[bool, Optional[QuestReward], str]:
    """
    Complete a quest and return rewards.
    
    Returns:
        (success, rewards, message)
    """
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False, None, "Quest not found"
    
    if quest.status == "completed":
        return False, None, "Quest already completed"
    
    # Mark quest as completed
    quest.status = "completed"
    quest.completed_at = datetime.now().isoformat()
    
    # Complete any remaining objectives
    objectives = quest.get_objectives()
    for obj in objectives:
        if not obj.is_optional and obj.status == "incomplete":
            obj.status = "complete"
            obj.progress = obj.required
    quest.set_objectives(objectives)
    
    update_quest(channel_id, quest)
    
    rewards = quest.get_rewards()
    message = f"🎉 Quest Complete: **{quest.name}**!"
    
    return True, rewards, message


def fail_quest(channel_id: str, quest_id: str, reason: str = "") -> bool:
    """Mark a quest as failed."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False
    
    quest.status = "failed"
    if reason:
        quest.notes.append(f"Failed: {reason}")
    update_quest(channel_id, quest)
    
    return True


def abandon_quest(channel_id: str, quest_id: str) -> bool:
    """Abandon a quest (player choice to give up)."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False
    
    quest.status = "abandoned"
    quest.notes.append(f"Abandoned at {datetime.now().isoformat()}")
    update_quest(channel_id, quest)
    
    return True


def accept_quest(channel_id: str, quest_id: str) -> bool:
    """Accept an available quest, making it active."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False
    
    if quest.status != "available":
        return False
    
    quest.status = "active"
    update_quest(channel_id, quest)
    
    return True


# =============================================================================
# MILESTONE DETECTION
# =============================================================================

def detect_quest_progress(channel_id: str, narration: str) -> List[Dict[str, Any]]:
    """
    Analyze AI narration for quest progress/completion.
    
    Returns:
        List of detected progress events: [{"quest": Quest, "type": "complete"|"progress", "details": str}]
    """
    detected = []
    narration_lower = narration.lower()
    active_quests = get_active_quests(channel_id)
    
    for quest in active_quests:
        # Check for quest name mention + completion patterns
        quest_name_lower = quest.name.lower()
        
        # Check if quest is mentioned
        quest_mentioned = quest_name_lower in narration_lower
        
        # Check objectives
        objectives = quest.get_objectives()
        for obj in objectives:
            if obj.status == "complete":
                continue
            
            obj_words = obj.description.lower().split()
            key_words = [w for w in obj_words if len(w) > 4]  # Skip small words
            
            # Check if objective keywords appear in narration
            matches = sum(1 for word in key_words if word in narration_lower)
            if matches >= min(2, len(key_words)):
                # Check for completion patterns
                for pattern in COMPLETION_PATTERNS:
                    if re.search(pattern, narration_lower):
                        detected.append({
                            "quest": quest,
                            "objective": obj,
                            "type": "objective_complete",
                            "details": f"Objective '{obj.description}' appears completed"
                        })
                        break
        
        # Check for overall quest completion
        if quest_mentioned:
            for pattern in COMPLETION_PATTERNS:
                if re.search(pattern, narration_lower):
                    detected.append({
                        "quest": quest,
                        "type": "quest_complete",
                        "details": f"Quest '{quest.name}' appears completed"
                    })
                    break
            
            # Check for failure
            for pattern in FAILURE_PATTERNS:
                if re.search(pattern, narration_lower):
                    detected.append({
                        "quest": quest,
                        "type": "quest_failed",
                        "details": f"Quest '{quest.name}' may have failed"
                    })
                    break
    
    return detected


def detect_new_quest(narration: str) -> Optional[Dict[str, str]]:
    """
    Detect if a new quest is being offered in the narration.
    
    Returns:
        {"name": str, "description": str, "giver": str} or None
    """
    quest_offer_patterns = [
        r"(?:offers?|gives?|assigns?).*(?:quest|mission|task)",
        r"(?:will you|would you|can you).*(?:help|save|rescue|retrieve|find|defeat)",
        r"(?:need|require|seek).*(?:adventurers?|heroes?|help)",
        r"(?:reward|payment|gold|coin).*(?:if you|for your|upon completion)",
    ]
    
    narration_lower = narration.lower()
    
    for pattern in quest_offer_patterns:
        if re.search(pattern, narration_lower):
            # Found a quest offer pattern
            return {
                "detected": True,
                "narration_excerpt": narration[:200]
            }
    
    return None


# =============================================================================
# STRUCTURED TAG DETECTION (Phase 13)
# =============================================================================

def parse_quest_tag_attributes(attr_string: str) -> Dict[str, str]:
    """
    Parse attributes from a quest tag string.
    
    Examples:
        'name="Rescue the Princess", type=rescue, difficulty=hard'
        -> {"name": "Rescue the Princess", "type": "rescue", "difficulty": "hard"}
    """
    result = {}
    
    # Match key="value" (double-quoted — allows apostrophes inside)
    dq_pattern = r'(\w+)\s*=\s*"([^"]*)"'
    for match in re.finditer(dq_pattern, attr_string):
        result[match.group(1).lower()] = match.group(2)
    
    # Match key='value' (single-quoted — allows double quotes inside)
    sq_pattern = r"(\w+)\s*=\s*'([^']*)'"
    for match in re.finditer(sq_pattern, attr_string):
        key = match.group(1).lower()
        if key not in result:
            result[key] = match.group(2)
    
    # Then handle unquoted values (avoiding already-matched parts)
    remaining = re.sub(dq_pattern, '', attr_string)
    remaining = re.sub(sq_pattern, '', remaining)
    unquoted_pattern = r'(\w+)\s*=\s*(\w+)'
    for match in re.finditer(unquoted_pattern, remaining):
        key = match.group(1).lower()
        if key not in result:
            result[key] = match.group(2)
    
    return result


def detect_structured_quest_tags(narration: str, parsed: Optional[ParsedTags] = None) -> Dict[str, Any]:
    """
    Detect structured quest-related tags in AI narration.
    
    Returns dict with keys: new_quests, completions, progress, rumors, hooks, objectives, chains
    """
    if parsed is None:
        parsed = parse_all_tags(narration)

    result = {
        "new_quests": [],
        "completions": [],
        "progress": [],
        "rumors": [],
        "hooks": [],
        "objectives": [],
        "chains": []
    }
    
    # [QUEST: name="...", type=..., difficulty=..., giver="..."]
    for attrs in parsed.quests:
        if "name" in attrs:
            quest_data = {
                "name": attrs.get("name", "Unknown Quest"),
                "description": attrs.get("description", attrs.get("desc", "")),
                "type": attrs.get("type", "side"),
                "difficulty": attrs.get("difficulty", "medium"),
                "giver": attrs.get("giver", attrs.get("npc", "")),
                "location": attrs.get("location", ""),
                "objectives": [],
            }
            if "objectives" in attrs:
                quest_data["objectives"] = [o.strip() for o in attrs["objectives"].split("|")]
            result["new_quests"].append(quest_data)
    
    # [QUEST_COMPLETE: "Quest Name"]
    for quest_name in parsed.quest_completions:
        result["completions"].append(quest_name.strip())
    
    # [QUEST_PROGRESS: "Quest Name", objective=1]
    for progress in parsed.quest_progress:
        result["progress"].append({
            "quest": progress["quest"],
            "objective": progress.get("objective", "1"),
            "amount": int(progress.get("amount", "1"))
        })
    
    # [RUMOR: "Strange lights near the cemetery"]
    for rumor_text in parsed.rumors:
        result["rumors"].append(rumor_text.strip())
    
    # [QUEST_HOOK: name="...", description="..."]
    for attrs in parsed.quest_hooks:
        if attrs:
            result["hooks"].append({
                "name": attrs.get("name", "Unknown"),
                "description": attrs.get("description", attrs.get("desc", "")),
                "type": attrs.get("type", "side"),
                "difficulty": attrs.get("difficulty", "medium"),
            })
    
    # [OBJECTIVE: "New objective text"]
    for obj_text in parsed.objectives:
        result["objectives"].append(obj_text.strip())
    
    # [QUEST_CHAIN: parent="Main Quest", child="Side Quest"]
    for chain in parsed.quest_chains:
        if "parent" in chain and "child" in chain:
            result["chains"].append({
                "parent": chain["parent"],
                "child": chain["child"]
            })
    
    return result


def detect_natural_language_quest_offer(narration: str) -> Optional[Dict[str, Any]]:
    """
    Detect quest offers from natural language patterns.
    
    Returns quest data if a clear offer is detected, None otherwise.
    """
    narration_lower = narration.lower()
    
    # Check for quest offer patterns
    offer_detected = False
    for pattern in QUEST_OFFER_PATTERNS:
        if re.search(pattern, narration_lower):
            offer_detected = True
            break
    
    if not offer_detected:
        return None
    
    # Try to extract quest details from the narration
    quest_data = {
        "detected": True,
        "type": "side",
        "difficulty": "medium",
        "excerpt": narration[:300]
    }
    
    # Detect quest type from keywords
    type_keywords = {
        "rescue": ["rescue", "save", "free", "liberate", "captive", "prisoner", "kidnap"],
        "fetch": ["retrieve", "find", "bring", "fetch", "recover", "lost", "stolen"],
        "bounty": ["kill", "defeat", "slay", "eliminate", "hunt", "bounty"],
        "escort": ["escort", "protect", "guard", "accompany", "deliver safely"],
        "explore": ["explore", "discover", "map", "investigate location", "find the way"],
        "mystery": ["investigate", "solve", "mystery", "truth", "uncover", "discover what"],
    }
    
    for quest_type, keywords in type_keywords.items():
        if any(kw in narration_lower for kw in keywords):
            quest_data["type"] = quest_type
            break
    
    # Try to detect difficulty from context
    if any(w in narration_lower for w in ["dangerous", "deadly", "dragon", "powerful", "ancient evil"]):
        quest_data["difficulty"] = "hard"
    elif any(w in narration_lower for w in ["simple", "easy", "quick", "small favor"]):
        quest_data["difficulty"] = "easy"
    
    # Try to extract NPC name (look for quoted speech attribution)
    giver_match = re.search(r'\*\*([A-Z][a-zA-Z\s]+)\*\*', narration)
    if giver_match:
        quest_data["giver"] = giver_match.group(1).strip()
    
    return quest_data


# =============================================================================
# RUMOR SYSTEM (Phase 13)
# =============================================================================

def _get_rumors_path(channel_id: str) -> str:
    """Get the file path for a channel's rumors data."""
    return os.path.join(QUEST_DIR, f'{channel_id}_rumors.json')


def load_rumors(channel_id: str) -> List[Dict[str, Any]]:
    """Load all rumors for a channel."""
    path = _get_rumors_path(channel_id)
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading rumors for {channel_id}: {e}")
        return []


def save_rumors(channel_id: str, rumors: List[Dict[str, Any]]):
    """Save all rumors for a channel."""
    path = _get_rumors_path(channel_id)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rumors, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving rumors for {channel_id}: {e}")


def add_rumor(channel_id: str, rumor_text: str, source: str = "") -> Dict[str, Any]:
    """Add a new rumor to the channel's rumor list."""
    rumors = load_rumors(channel_id)
    
    rumor = {
        "id": f"rumor_{len(rumors) + 1}",
        "text": rumor_text,
        "source": source,
        "heard_at": datetime.now().isoformat(),
        "investigated": False,
        "led_to_quest": ""
    }
    
    # Avoid duplicate rumors
    if not any(r["text"].lower() == rumor_text.lower() for r in rumors):
        rumors.append(rumor)
        save_rumors(channel_id, rumors)
        return rumor
    
    return None


def get_uninvestigated_rumors(channel_id: str) -> List[Dict[str, Any]]:
    """Get all rumors that haven't been investigated yet."""
    rumors = load_rumors(channel_id)
    return [r for r in rumors if not r.get("investigated", False)]


def convert_rumor_to_quest(
    channel_id: str, 
    rumor_id: str, 
    quest_name: str,
    description: str,
    quest_type: str = "side",
    difficulty: str = "medium"
) -> Optional[Quest]:
    """Convert an investigated rumor into an active quest."""
    rumors = load_rumors(channel_id)
    
    rumor = None
    for r in rumors:
        if r["id"] == rumor_id:
            rumor = r
            break
    
    if not rumor:
        return None
    
    # Prevent duplicate quests
    existing = get_quest_by_name(channel_id, quest_name)
    if existing:
        return None
    
    # Create the quest
    quest = create_quest(
        channel_id=channel_id,
        name=quest_name,
        description=description,
        quest_type=quest_type,
        difficulty=difficulty,
        objectives=["Investigate the rumor", "Complete the task"],
        tags=["from_rumor", rumor_id]
    )
    
    if quest:
        # Mark rumor as investigated
        rumor["investigated"] = True
        rumor["led_to_quest"] = quest.id
        save_rumors(channel_id, rumors)
    
    return quest


# =============================================================================
# QUEST CHAIN SYSTEM (Phase 13)
# =============================================================================

def link_quests(channel_id: str, parent_quest_id: str, child_quest_id: str) -> bool:
    """
    Link two quests in a chain. Child quest unlocks when parent completes.
    """
    parent = get_quest(channel_id, parent_quest_id)
    child = get_quest(channel_id, child_quest_id)
    
    if not parent or not child:
        return False
    
    # Add chain info to both quests
    if "chain_next" not in parent.tags:
        parent.tags.append(f"chain_next:{child_quest_id}")
    
    if "chain_prev" not in child.tags:
        child.tags.append(f"chain_prev:{parent_quest_id}")
    
    # Save
    quests = load_quests(channel_id)
    for i, q in enumerate(quests):
        if q.id == parent.id:
            quests[i] = parent
        elif q.id == child.id:
            quests[i] = child
    save_quests(channel_id, quests)
    
    return True


def get_next_quest_in_chain(channel_id: str, quest_id: str) -> Optional[Quest]:
    """Get the next quest in a chain after the given quest."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return None
    
    for tag in quest.tags:
        if tag.startswith("chain_next:"):
            next_id = tag.replace("chain_next:", "")
            return get_quest(channel_id, next_id)
    
    return None


def activate_chain_quest(channel_id: str, completed_quest_id: str) -> Optional[Quest]:
    """
    When a quest completes, check if it has a chained quest to activate.
    Returns the newly activated quest or None.
    """
    next_quest = get_next_quest_in_chain(channel_id, completed_quest_id)
    
    if next_quest and next_quest.status == "available":
        next_quest.status = "active"
        quests = load_quests(channel_id)
        for i, q in enumerate(quests):
            if q.id == next_quest.id:
                quests[i] = next_quest
                break
        save_quests(channel_id, quests)
        return next_quest
    
    return None


# =============================================================================
# QUEST LOG FORMATTING
# =============================================================================

def format_quest_summary(quest: Quest, show_rewards: bool = False) -> str:
    """Format a single quest for display."""
    lines = []
    
    # Status emoji
    status_emoji = {
        "available": "📋",
        "active": "⚔️",
        "completed": "✅",
        "failed": "❌",
        "abandoned": "🚫"
    }
    emoji = status_emoji.get(quest.status, "📜")
    
    # Type indicator
    type_indicator = {
        "main": "🌟",
        "side": "📌",
        "faction": "🏛️",
        "personal": "💭",
        "bounty": "🎯",
        "fetch": "📦",
        "escort": "🛡️",
        "explore": "🗺️",
        "mystery": "🔍"
    }
    type_emoji = type_indicator.get(quest.quest_type, "📜")
    
    # Header
    lines.append(f"{emoji} **{quest.name}** {type_emoji}")
    lines.append(f"*{quest.description}*")
    
    # Progress
    if quest.status == "active":
        completed, total = quest.get_progress()
        progress_bar = "▓" * completed + "░" * (total - completed)
        lines.append(f"Progress: [{progress_bar}] {completed}/{total}")
    
    # Objectives
    if quest.status == "active":
        objectives = quest.get_objectives()
        visible_objs = [obj for obj in objectives if not obj.is_hidden]
        if visible_objs:
            lines.append("\n**Objectives:**")
            for obj in visible_objs:
                if obj.is_complete():
                    check = "☑️"
                elif obj.status == "failed":
                    check = "❌"
                else:
                    check = "☐"
                
                optional = " *(optional)*" if obj.is_optional else ""
                
                if obj.required > 1:
                    lines.append(f"  {check} {obj.description} ({obj.progress}/{obj.required}){optional}")
                else:
                    lines.append(f"  {check} {obj.description}{optional}")
    
    # Rewards
    if show_rewards and quest.status in ["active", "available"]:
        rewards = quest.get_rewards()
        reward_parts = []
        if rewards.xp > 0:
            reward_parts.append(f"{rewards.xp} XP")
        if rewards.gold > 0:
            reward_parts.append(f"{rewards.gold} gp")
        if rewards.items:
            reward_parts.append(", ".join(rewards.items))
        if reward_parts:
            lines.append(f"\n**Rewards:** {', '.join(reward_parts)}")
    
    # Quest giver
    if quest.giver_npc:
        lines.append(f"\n*Quest Giver: {quest.giver_npc}*")
    
    return "\n".join(lines)


def format_quest_log(channel_id: str, include_completed: bool = False) -> str:
    """Format the full quest log for display."""
    active = get_active_quests(channel_id)
    available = get_available_quests(channel_id)
    
    lines = ["# 📜 Quest Log\n"]
    
    # Active quests
    if active:
        lines.append("## ⚔️ Active Quests\n")
        for quest in active:
            lines.append(format_quest_summary(quest, show_rewards=True))
            lines.append("")
    else:
        lines.append("*No active quests*\n")
    
    # Available quests
    if available:
        lines.append("## 📋 Available Quests\n")
        for quest in available:
            lines.append(format_quest_summary(quest, show_rewards=True))
            lines.append("")
    
    # Completed quests
    if include_completed:
        completed = get_completed_quests(channel_id)
        if completed:
            lines.append("## ✅ Completed Quests\n")
            for quest in completed[-10:]:  # Last 10 completed
                lines.append(f"✅ **{quest.name}** - {quest.completed_at[:10] if quest.completed_at else 'Unknown'}")
    
    return "\n".join(lines)


def format_quest_rewards_message(quest: Quest, rewards: QuestReward) -> str:
    """Format the rewards message for a completed quest."""
    lines = [f"🎉 **Quest Complete: {quest.name}**\n"]
    
    lines.append("**Rewards:**")
    
    if rewards.xp > 0:
        lines.append(f"  ⭐ {rewards.xp} Experience Points")
    
    if rewards.gold > 0:
        lines.append(f"  💰 {rewards.gold} Gold Pieces")
    
    if rewards.items:
        lines.append(f"  🎁 Items: {', '.join(rewards.items)}")
    
    if rewards.reputation:
        for faction, change in rewards.reputation.items():
            sign = "+" if change > 0 else ""
            lines.append(f"  🏛️ {faction}: {sign}{change} reputation")
    
    if rewards.special:
        lines.append(f"  ✨ {rewards.special}")
    
    return "\n".join(lines)


# =============================================================================
# AI CONTEXT INTEGRATION
# =============================================================================

def get_quest_context_for_ai(channel_id: str) -> str:
    """
    Get quest context to include in AI prompts.
    
    Returns:
        String describing active quests and objectives for AI context
    """
    active = get_active_quests(channel_id)
    
    if not active:
        return ""
    
    lines = ["ACTIVE QUESTS:"]
    
    for quest in active:
        objectives = quest.get_objectives()
        incomplete = [obj for obj in objectives if not obj.is_complete() and not obj.is_hidden]
        
        lines.append(f"\n• {quest.name} ({quest.quest_type})")
        lines.append(f"  Description: {quest.description}")
        
        if quest.giver_npc:
            lines.append(f"  Quest Giver: {quest.giver_npc}")
        
        if incomplete:
            lines.append("  Current Objectives:")
            for obj in incomplete:
                if obj.required > 1:
                    lines.append(f"    - {obj.description} ({obj.progress}/{obj.required})")
                else:
                    lines.append(f"    - {obj.description}")
    
    lines.append("\nWhen the party makes progress on these quests, acknowledge it naturally in your narration.")
    
    return "\n".join(lines)


def process_narration_for_quests(channel_id: str, narration: str, source_npc: str = "") -> List[Dict[str, Any]]:
    """
    Main entry point: Process AI narration for quest progress.
    
    Phase 13 Enhanced: Now detects structured tags AND natural language.
    
    Returns:
        List of events that occurred: [{"type": str, "quest": Quest, "message": str}]
    """
    events = []
    
    # =========================================================================
    # PHASE 13: Detect structured quest tags first (highest priority)
    # =========================================================================
    
    tag_results = detect_structured_quest_tags(narration)
    
    # Process new quests from [QUEST:] tags
    for quest_data in tag_results["new_quests"]:
        # Check if quest already exists
        existing = get_quest_by_name(channel_id, quest_data["name"])
        if not existing:
            # Create new quest from tag
            quest = create_quest(
                channel_id=channel_id,
                name=quest_data["name"],
                description=quest_data.get("description", f"Quest from {quest_data.get('giver', 'unknown')}"),
                quest_type=quest_data.get("type", "side"),
                difficulty=quest_data.get("difficulty", "medium"),
                giver_npc=quest_data.get("giver", source_npc),
                objectives=quest_data.get("objectives", []),
                tags=["auto_created"]
            )
            if quest:
                events.append({
                    "type": "quest_created",
                    "quest": quest,
                    "message": f"📜 **New Quest:** {quest.name}\n*{quest.description}*"
                })
    
    # Process quest completions from [QUEST_COMPLETE:] tags
    for quest_name in tag_results["completions"]:
        quest = get_quest_by_name(channel_id, quest_name)
        if quest and quest.status == "active":
            success, rewards, msg = complete_quest(channel_id, quest.id)
            if success:
                events.append({
                    "type": "quest_complete",
                    "quest": quest,
                    "rewards": rewards,
                    "message": msg
                })
                # Check for chain quest
                chain_quest = activate_chain_quest(channel_id, quest.id)
                if chain_quest:
                    events.append({
                        "type": "quest_unlocked",
                        "quest": chain_quest,
                        "message": f"🔓 **Quest Unlocked:** {chain_quest.name}"
                    })
    
    # Process objective progress from [QUEST_PROGRESS:] tags
    for progress_data in tag_results["progress"]:
        quest = get_quest_by_name(channel_id, progress_data["quest"])
        if quest:
            obj_idx = int(progress_data.get("objective", "1")) - 1
            objectives = quest.get_objectives()
            if 0 <= obj_idx < len(objectives):
                obj = objectives[obj_idx]
                amount = progress_data.get("amount", 1)
                success, msg = update_objective_progress(
                    channel_id, quest.id, obj.id, 
                    obj.progress + amount
                )
                if success:
                    events.append({
                        "type": "objective_progress",
                        "quest": quest,
                        "message": msg
                    })
    
    # Process rumors from [RUMOR:] tags
    for rumor_text in tag_results["rumors"]:
        rumor = add_rumor(channel_id, rumor_text, source=source_npc)
        if rumor:
            events.append({
                "type": "rumor_heard",
                "rumor": rumor,
                "message": f"👂 **Rumor heard:** *\"{rumor_text}\"*"
            })
    
    # Process quest hooks from [QUEST_HOOK:] tags (create as available quests)
    for hook_data in tag_results["hooks"]:
        existing = get_quest_by_name(channel_id, hook_data["name"])
        if not existing:
            quest = create_quest(
                channel_id=channel_id,
                name=hook_data["name"],
                description=hook_data.get("description", ""),
                quest_type=hook_data.get("type", "side"),
                difficulty=hook_data.get("difficulty", "medium"),
                status="available",  # Not active yet
                tags=["quest_hook"]
            )
            if quest:
                events.append({
                    "type": "quest_hook",
                    "quest": quest,
                    "message": f"📌 **Quest Available:** {quest.name}"
                })
    
    # Process new objectives from [OBJECTIVE:] tags
    for obj_text in tag_results["objectives"]:
        # Find active quest to add objective to
        active = get_active_quests(channel_id)
        if active:
            quest = active[0]  # Add to first active quest
            success, msg = add_objective(channel_id, quest.id, obj_text)
            if success:
                events.append({
                    "type": "objective_added",
                    "quest": quest,
                    "message": f"📋 **New Objective:** {obj_text}"
                })
    
    # Process quest chains from [QUEST_CHAIN:] tags
    for chain_data in tag_results["chains"]:
        parent = get_quest_by_name(channel_id, chain_data["parent"])
        child = get_quest_by_name(channel_id, chain_data["child"])
        if parent and child:
            link_quests(channel_id, parent.id, child.id)
            events.append({
                "type": "quest_chain",
                "message": f"🔗 Quests linked: {parent.name} → {child.name}"
            })
    
    # =========================================================================
    # EXISTING: Natural language quest progress detection
    # =========================================================================
    
    progress = detect_quest_progress(channel_id, narration)
    
    for item in progress:
        if item["type"] == "objective_complete":
            quest = item["quest"]
            obj = item["objective"]
            
            # Complete the objective
            success, msg = complete_objective(channel_id, quest.id, obj.id)
            if success:
                events.append({
                    "type": "objective_complete",
                    "quest": quest,
                    "message": msg
                })
                
                # Check if quest is now complete
                updated_quest = get_quest(channel_id, quest.id)
                if updated_quest and updated_quest.is_complete():
                    success, rewards, msg = complete_quest(channel_id, quest.id)
                    if success:
                        events.append({
                            "type": "quest_complete",
                            "quest": updated_quest,
                            "rewards": rewards,
                            "message": msg
                        })
                        # Check for chain quest
                        chain_quest = activate_chain_quest(channel_id, quest.id)
                        if chain_quest:
                            events.append({
                                "type": "quest_unlocked",
                                "quest": chain_quest,
                                "message": f"🔓 **Quest Unlocked:** {chain_quest.name}"
                            })
        
        elif item["type"] == "quest_complete":
            quest = item["quest"]
            success, rewards, msg = complete_quest(channel_id, quest.id)
            if success:
                events.append({
                    "type": "quest_complete",
                    "quest": quest,
                    "rewards": rewards,
                    "message": msg
                })
                # Check for chain quest
                chain_quest = activate_chain_quest(channel_id, quest.id)
                if chain_quest:
                    events.append({
                        "type": "quest_unlocked",
                        "quest": chain_quest,
                        "message": f"🔓 **Quest Unlocked:** {chain_quest.name}"
                    })
        
        elif item["type"] == "quest_failed":
            quest = item["quest"]
            if fail_quest(channel_id, quest.id, "Detected from narration"):
                events.append({
                    "type": "quest_failed",
                    "quest": quest,
                    "message": f"❌ Quest Failed: **{quest.name}**"
                })
    
    # =========================================================================
    # PHASE 13: Natural language quest offer detection (fallback)
    # =========================================================================
    
    # Only trigger if no structured quest tags were found
    if not tag_results["new_quests"] and not tag_results["hooks"]:
        quest_offer = detect_natural_language_quest_offer(narration)
        if quest_offer:
            events.append({
                "type": "quest_offer_detected",
                "data": quest_offer,
                "message": f"💡 *A quest may have been offered. Use `/quest create` to add it, or the AI can use structured tags.*"
            })
    
    return events


# =============================================================================
# QUICK QUEST TEMPLATES
# =============================================================================

QUEST_TEMPLATES = {
    "bounty": {
        "objectives": ["Locate the target", "Defeat the target", "Return for reward"],
        "difficulty": "medium",
        "quest_type": "bounty"
    },
    "fetch": {
        "objectives": ["Find the location", "Retrieve the item", "Deliver the item"],
        "difficulty": "easy",
        "quest_type": "fetch"
    },
    "rescue": {
        "objectives": ["Find the captive's location", "Defeat the captors", "Escort the captive to safety"],
        "difficulty": "medium",
        "quest_type": "escort"
    },
    "investigate": {
        "objectives": ["Gather clues", "Interview witnesses", "Uncover the truth"],
        "difficulty": "medium",
        "quest_type": "mystery"
    },
    "clear_dungeon": {
        "objectives": ["Enter the dungeon", "Clear all threats", "Secure the area"],
        "difficulty": "hard",
        "quest_type": "explore"
    },
    "escort": {
        "objectives": ["Meet the client", "Protect during journey", "Deliver safely to destination"],
        "difficulty": "medium",
        "quest_type": "escort"
    }
}


def create_quest_from_template(
    channel_id: str,
    template_name: str,
    quest_name: str,
    description: str,
    giver_npc: str = "",
    custom_objectives: List[str] = None
) -> Optional[Quest]:
    """
    Create a quest from a template.
    
    Args:
        channel_id: Discord channel ID
        template_name: Template key (bounty, fetch, rescue, investigate, clear_dungeon, escort)
        quest_name: Name for the quest
        description: Quest description
        giver_npc: NPC who gave the quest
        custom_objectives: Override template objectives
    
    Returns:
        Created Quest or None if template not found
    """
    template = QUEST_TEMPLATES.get(template_name.lower())
    if not template:
        return None
    
    objectives = custom_objectives or template["objectives"]
    
    return create_quest(
        channel_id=channel_id,
        name=quest_name,
        description=description,
        quest_type=template["quest_type"],
        difficulty=template["difficulty"],
        giver_npc=giver_npc,
        objectives=objectives
    )


def add_note_to_quest(channel_id: str, quest_id: str, note: str) -> bool:
    """Add a player note to a quest."""
    quest = get_quest(channel_id, quest_id)
    if not quest:
        return False
    
    quest.notes.append(f"[{datetime.now().strftime('%Y-%m-%d')}] {note}")
    update_quest(channel_id, quest)
    return True

