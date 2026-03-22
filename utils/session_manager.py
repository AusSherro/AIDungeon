# ============================================================================
# SESSION MANAGER - Session Continuity & Auto-Resume (Phase 15)
# ============================================================================
"""
This module provides:
1. Session state tracking (start time, duration, activity)
2. Auto-resume detection for returning players
3. Session recap generation with TTS support
4. Session pacing hints for AI prompts
5. Auto-save with crash recovery
6. Inactivity detection and session end handling

Session Lifecycle:
1. Player joins voice with active campaign → offer resume
2. Session starts → track duration, activity
3. Periodic auto-save during play
4. Pacing hints injected based on duration
5. Extended inactivity → pause state
6. Session ends → save summary for next time
"""

import os
import json
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Try to import state manager for integration
try:
    from utils.state_manager import load_state, save_state
    HAS_STATE_MANAGER = True
except ImportError:
    HAS_STATE_MANAGER = False

try:
    from config import Config
    _CONFIG_AVAILABLE = True
except ImportError:
    _CONFIG_AVAILABLE = False


# ============================================================================
# ENUMS
# ============================================================================

class SessionStatus(Enum):
    """Current status of a session."""
    INACTIVE = "inactive"       # No active session
    STARTING = "starting"       # Session starting up
    ACTIVE = "active"           # Session in progress
    PAUSED = "paused"           # Temporarily paused (inactivity)
    ENDING = "ending"           # Session wrapping up
    CRASHED = "crashed"         # Session ended unexpectedly


class PacingPhase(Enum):
    """Pacing phases for session management."""
    OPENING = "opening"         # First 15 minutes - exposition
    RISING = "rising"           # 15-60 minutes - building action
    CLIMAX = "climax"           # 60-90 minutes - peak tension
    FALLING = "falling"         # 90-120 minutes - resolution
    CLOSING = "closing"         # 120+ minutes - wrap up


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SessionState:
    """Tracks the current session's state."""
    channel_id: str
    status: str = "inactive"  # SessionStatus value
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    last_save: Optional[str] = None
    active_players: List[str] = field(default_factory=list)
    action_count: int = 0
    combat_count: int = 0
    rest_count: int = 0
    current_pacing_phase: str = "opening"
    pacing_hints_sent: List[str] = field(default_factory=list)
    recovery_available: bool = False
    recovery_point: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        return cls(**data)


@dataclass
class SessionSummary:
    """Summary of a session for recap purposes."""
    channel_id: str
    started_at: str
    ended_at: str
    duration_minutes: int
    players: List[str]
    action_count: int
    combat_count: int
    key_events: List[str]
    final_location: str
    active_quests: List[str]
    campaign_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionSummary':
        return cls(**data)


@dataclass 
class PacingHint:
    """A pacing hint to inject into AI prompts."""
    phase: str
    hint: str
    trigger_minutes: int
    priority: int = 1  # 1=low, 2=medium, 3=high


# ============================================================================
# CONSTANTS
# ============================================================================

# Auto-save interval in seconds
AUTO_SAVE_INTERVAL = Config.AUTO_SAVE_INTERVAL if _CONFIG_AVAILABLE else 300

# Inactivity timeout in seconds  
INACTIVITY_TIMEOUT = Config.INACTIVITY_TIMEOUT if _CONFIG_AVAILABLE else 1800

# Pacing phase thresholds (in minutes)
PACING_THRESHOLDS = {
    PacingPhase.OPENING: 0,
    PacingPhase.RISING: 15,
    PacingPhase.CLIMAX: 60,
    PacingPhase.FALLING: 90,
    PacingPhase.CLOSING: 120,
}

# Pacing hints for each phase
PACING_HINTS = {
    PacingPhase.OPENING: [
        PacingHint("opening", "Session just started. Establish scene, remind players of situation.", 0, 2),
        PacingHint("opening", "Set the mood and context. Let players get oriented.", 5, 1),
    ],
    PacingPhase.RISING: [
        PacingHint("rising", "Build tension. Introduce complications or new information.", 20, 2),
        PacingHint("rising", "Present meaningful choices. Let consequences matter.", 35, 2),
        PacingHint("rising", "Players have been active for a while. Consider an encounter or challenge.", 45, 1),
    ],
    PacingPhase.CLIMAX: [
        PacingHint("climax", "Session approaching peak. Consider a dramatic moment or revelation.", 60, 3),
        PacingHint("climax", "This is the high point. Make stakes feel real.", 75, 2),
    ],
    PacingPhase.FALLING: [
        PacingHint("falling", "Session has been going 90+ minutes. Start wrapping up current thread.", 90, 2),
        PacingHint("falling", "Resolve immediate conflicts. Set up future hooks.", 100, 2),
    ],
    PacingPhase.CLOSING: [
        PacingHint("closing", "Session running long (2+ hours). Find a good stopping point.", 120, 3),
        PacingHint("closing", "Consider suggesting a rest or safe location to pause.", 135, 2),
        PacingHint("closing", "Wrap up the session. Summarize achievements and tease next time.", 150, 3),
    ],
}

# Rest suggestion triggers
REST_SUGGESTION_THRESHOLDS = {
    "combat": 3,      # Suggest rest after 3 combats
    "actions": 20,    # Suggest rest after 20 actions
    "time": 60,       # Suggest rest after 60 minutes
}


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def get_session_path(channel_id: str) -> str:
    """Get path to session state file for a channel."""
    os.makedirs("state", exist_ok=True)
    return os.path.join("state", f"session_{channel_id}.json")


def get_summary_path(channel_id: str) -> str:
    """Get path to session summaries file for a channel."""
    os.makedirs("state", exist_ok=True)
    return os.path.join("state", f"session_summaries_{channel_id}.json")


def get_recovery_path(channel_id: str) -> str:
    """Get path to recovery state file for a channel."""
    os.makedirs("state", exist_ok=True)
    return os.path.join("state", f"recovery_{channel_id}.json")


def load_session_state(channel_id: str) -> SessionState:
    """Load session state from file."""
    path = get_session_path(channel_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return SessionState.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error loading session state: {e}")
    return SessionState(channel_id=channel_id)


def save_session_state(channel_id: str, state: SessionState):
    """Save session state to file."""
    path = get_session_path(channel_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state.to_dict(), f, indent=2)


def load_session_summaries(channel_id: str) -> List[SessionSummary]:
    """Load all session summaries for a channel."""
    path = get_summary_path(channel_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [SessionSummary.from_dict(s) for s in data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error loading session summaries: {e}")
    return []


def save_session_summary(channel_id: str, summary: SessionSummary):
    """Save a session summary, appending to existing summaries."""
    summaries = load_session_summaries(channel_id)
    summaries.append(summary)
    
    # Keep only last 10 sessions
    if len(summaries) > 10:
        summaries = summaries[-10:]
    
    path = get_summary_path(channel_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump([s.to_dict() for s in summaries], f, indent=2)


def save_recovery_point(channel_id: str, campaign_state: dict):
    """Save a recovery point for crash recovery."""
    path = get_recovery_path(channel_id)
    recovery_data = {
        "saved_at": datetime.now().isoformat(),
        "campaign_state": campaign_state
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(recovery_data, f, indent=2)


def load_recovery_point(channel_id: str) -> Optional[Dict[str, Any]]:
    """Load a recovery point if available."""
    path = get_recovery_path(channel_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading recovery point: {e}")
    return None


def clear_recovery_point(channel_id: str):
    """Clear recovery point after successful session start."""
    path = get_recovery_path(channel_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            logger.error(f"Error clearing recovery point: {e}")


# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

def start_session(
    channel_id: str,
    player_ids: List[str]
) -> SessionState:
    """Start a new session."""
    now = datetime.now().isoformat()
    
    session = SessionState(
        channel_id=channel_id,
        status=SessionStatus.ACTIVE.value,
        started_at=now,
        last_activity=now,
        last_save=now,
        active_players=player_ids,
        action_count=0,
        combat_count=0,
        rest_count=0,
        current_pacing_phase=PacingPhase.OPENING.value,
        pacing_hints_sent=[],
        recovery_available=False,
        recovery_point=None
    )
    
    save_session_state(channel_id, session)
    
    # Clear any old recovery point
    clear_recovery_point(channel_id)
    
    return session


def end_session(
    channel_id: str,
    campaign_state: Optional[dict] = None
) -> Optional[SessionSummary]:
    """End the current session and generate summary."""
    session = load_session_state(channel_id)
    
    if session.status == SessionStatus.INACTIVE.value:
        return None
    
    now = datetime.now()
    started = datetime.fromisoformat(session.started_at) if session.started_at else now
    duration = int((now - started).total_seconds() / 60)
    
    # Get campaign info for summary
    key_events = []
    final_location = "Unknown"
    active_quests = []
    campaign_summary = ""
    
    if campaign_state:
        key_events = campaign_state.get("key_events", [])[-5:]  # Last 5 events
        final_location = campaign_state.get("location", "Unknown")
        active_quests = [q.get("name", "") for q in campaign_state.get("quests", []) if q.get("status") == "active"][:5]
        campaign_summary = campaign_state.get("campaign_summary", "")
    
    summary = SessionSummary(
        channel_id=channel_id,
        started_at=session.started_at or now.isoformat(),
        ended_at=now.isoformat(),
        duration_minutes=duration,
        players=session.active_players,
        action_count=session.action_count,
        combat_count=session.combat_count,
        key_events=key_events,
        final_location=final_location,
        active_quests=active_quests,
        campaign_summary=campaign_summary
    )
    
    # Save summary
    save_session_summary(channel_id, summary)
    
    # Reset session state
    session.status = SessionStatus.INACTIVE.value
    save_session_state(channel_id, session)
    
    # Clear recovery point
    clear_recovery_point(channel_id)
    
    return summary


def pause_session(channel_id: str):
    """Pause session due to inactivity."""
    session = load_session_state(channel_id)
    if session.status == SessionStatus.ACTIVE.value:
        session.status = SessionStatus.PAUSED.value
        save_session_state(channel_id, session)


def resume_session(channel_id: str, player_ids: List[str]) -> SessionState:
    """Resume a paused session."""
    session = load_session_state(channel_id)
    
    session.status = SessionStatus.ACTIVE.value
    session.last_activity = datetime.now().isoformat()
    session.active_players = player_ids
    
    save_session_state(channel_id, session)
    return session


# ============================================================================
# ACTIVITY TRACKING
# ============================================================================

def record_activity(
    channel_id: str,
    activity_type: str = "action",
    player_id: Optional[str] = None
):
    """Record player activity and update session state."""
    session = load_session_state(channel_id)
    
    if session.status != SessionStatus.ACTIVE.value:
        return
    
    session.last_activity = datetime.now().isoformat()
    
    if activity_type == "action":
        session.action_count += 1
    elif activity_type == "combat":
        session.combat_count += 1
    elif activity_type == "rest":
        session.rest_count += 1
    
    if player_id and player_id not in session.active_players:
        session.active_players.append(player_id)
    
    # Update pacing phase
    session.current_pacing_phase = get_current_pacing_phase(channel_id).value
    
    save_session_state(channel_id, session)


def get_session_duration_minutes(channel_id: str) -> int:
    """Get the current session duration in minutes."""
    session = load_session_state(channel_id)
    
    if not session.started_at:
        return 0
    
    started = datetime.fromisoformat(session.started_at)
    return int((datetime.now() - started).total_seconds() / 60)


def get_time_since_activity(channel_id: str) -> int:
    """Get seconds since last activity."""
    session = load_session_state(channel_id)
    
    if not session.last_activity:
        return 0
    
    last_activity = datetime.fromisoformat(session.last_activity)
    return int((datetime.now() - last_activity).total_seconds())


def check_inactivity(channel_id: str) -> bool:
    """Check if session has been inactive too long."""
    seconds = get_time_since_activity(channel_id)
    return seconds > INACTIVITY_TIMEOUT


# ============================================================================
# PACING SYSTEM
# ============================================================================

def get_current_pacing_phase(channel_id: str) -> PacingPhase:
    """Determine current pacing phase based on session duration."""
    duration = get_session_duration_minutes(channel_id)
    
    current_phase = PacingPhase.OPENING
    for phase, threshold in PACING_THRESHOLDS.items():
        if duration >= threshold:
            current_phase = phase
    
    return current_phase


def get_pacing_hints(channel_id: str) -> List[PacingHint]:
    """Get applicable pacing hints for current session state."""
    session = load_session_state(channel_id)
    duration = get_session_duration_minutes(channel_id)
    phase = get_current_pacing_phase(channel_id)
    
    applicable_hints = []
    
    for hint in PACING_HINTS.get(phase, []):
        # Check if hint applies and hasn't been sent
        if duration >= hint.trigger_minutes:
            hint_id = f"{hint.phase}_{hint.trigger_minutes}"
            if hint_id not in session.pacing_hints_sent:
                applicable_hints.append(hint)
    
    return sorted(applicable_hints, key=lambda h: h.priority, reverse=True)


def mark_hint_sent(channel_id: str, hint: PacingHint):
    """Mark a pacing hint as sent."""
    session = load_session_state(channel_id)
    hint_id = f"{hint.phase}_{hint.trigger_minutes}"
    if hint_id not in session.pacing_hints_sent:
        session.pacing_hints_sent.append(hint_id)
        save_session_state(channel_id, session)


def should_suggest_rest(channel_id: str) -> Optional[str]:
    """Check if we should suggest a rest based on activity."""
    session = load_session_state(channel_id)
    duration = get_session_duration_minutes(channel_id)
    
    # Check combat count
    if session.combat_count >= REST_SUGGESTION_THRESHOLDS["combat"] and session.rest_count == 0:
        return f"The party has had {session.combat_count} combats. Consider suggesting a short or long rest."
    
    # Check action count
    if session.action_count >= REST_SUGGESTION_THRESHOLDS["actions"] and session.rest_count == 0:
        return f"The party has been very active ({session.action_count} actions). A rest opportunity might be welcome."
    
    # Check time without rest
    if duration >= REST_SUGGESTION_THRESHOLDS["time"] and session.rest_count == 0:
        return f"Session has been running {duration} minutes without a rest. Consider a natural pause point."
    
    return None


def get_pacing_context_for_ai(channel_id: str) -> str:
    """Build pacing context for AI prompts."""
    session = load_session_state(channel_id)
    
    if session.status != SessionStatus.ACTIVE.value:
        return ""
    
    duration = get_session_duration_minutes(channel_id)
    phase = get_current_pacing_phase(channel_id)
    
    lines = [
        "## SESSION PACING CONTEXT",
        f"**Session Duration:** {duration} minutes",
        f"**Pacing Phase:** {phase.value.title()}",
        f"**Actions This Session:** {session.action_count}",
        f"**Combats This Session:** {session.combat_count}",
        f"**Rests This Session:** {session.rest_count}",
    ]
    
    # Get current pacing hints
    hints = get_pacing_hints(channel_id)
    if hints:
        lines.append("")
        lines.append("**DM Guidance:**")
        for hint in hints[:2]:  # Only show top 2
            lines.append(f"- {hint.hint}")
    
    # Check for rest suggestion
    rest_hint = should_suggest_rest(channel_id)
    if rest_hint:
        lines.append("")
        lines.append(f"**Rest Suggestion:** {rest_hint}")
    
    return "\n".join(lines)


# ============================================================================
# SESSION RESUME & RECAP
# ============================================================================

def check_for_resume(channel_id: str) -> Dict[str, Any]:
    """Check if there's a session to resume."""
    session = load_session_state(channel_id)
    recovery = load_recovery_point(channel_id)
    summaries = load_session_summaries(channel_id)
    
    result = {
        "has_paused_session": session.status == SessionStatus.PAUSED.value,
        "has_recovery": recovery is not None,
        "has_previous_sessions": len(summaries) > 0,
        "last_session": summaries[-1] if summaries else None,
        "recovery_time": recovery.get("saved_at") if recovery else None
    }
    
    return result


def generate_session_recap(channel_id: str, campaign_state: Optional[dict] = None) -> str:
    """Generate a recap of the last session for narration."""
    summaries = load_session_summaries(channel_id)
    
    if not summaries:
        return ""
    
    last_session = summaries[-1]
    
    lines = [
        "**Previously on your adventure...**",
        ""
    ]
    
    # Add campaign summary if available
    if last_session.campaign_summary:
        lines.append(last_session.campaign_summary)
        lines.append("")
    
    # Add key events
    if last_session.key_events:
        for event in last_session.key_events[-3:]:
            lines.append(f"• {event}")
        lines.append("")
    
    # Current location
    lines.append(f"You find yourselves in **{last_session.final_location}**.")
    
    # Active quests
    if last_session.active_quests:
        quest_text = ", ".join(last_session.active_quests[:3])
        lines.append(f"Your current objectives: {quest_text}")
    
    # Session duration note
    time_ago = calculate_time_since(last_session.ended_at)
    lines.append("")
    lines.append(f"*Last session ended {time_ago}.*")
    
    return "\n".join(lines)


def generate_quick_recap(channel_id: str, campaign_state: dict) -> str:
    """Generate a quick recap for session start."""
    location = campaign_state.get("location", "Unknown")
    campaign_title = campaign_state.get("campaign_title", "Your Adventure")
    quests = campaign_state.get("quests", [])
    active_quests = [q.get("name") for q in quests if q.get("status") == "active"][:3]
    
    lines = [
        f"🎮 **Resuming: {campaign_title}**",
        f"📍 Location: {location}",
    ]
    
    if active_quests:
        lines.append(f"📜 Active Quests: {', '.join(active_quests)}")
    
    return "\n".join(lines)


def calculate_time_since(iso_timestamp: str) -> str:
    """Calculate human-readable time since a timestamp."""
    try:
        then = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        delta = now - then
        
        if delta.days > 0:
            if delta.days == 1:
                return "yesterday"
            elif delta.days < 7:
                return f"{delta.days} days ago"
            elif delta.days < 30:
                weeks = delta.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                months = delta.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            hours = delta.seconds // 3600
            if hours > 0:
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    except Exception:
        return "some time ago"


# ============================================================================
# AUTO-SAVE SYSTEM
# ============================================================================

class AutoSaveManager:
    """Manages automatic saving of session state."""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._save_callbacks: Dict[str, Callable] = {}
    
    def register_channel(
        self,
        channel_id: str,
        save_callback: Callable[[str], dict]
    ):
        """Register a channel for auto-save."""
        self._save_callbacks[channel_id] = save_callback
    
    def unregister_channel(self, channel_id: str):
        """Unregister a channel from auto-save."""
        if channel_id in self._tasks:
            self._tasks[channel_id].cancel()
            del self._tasks[channel_id]
        if channel_id in self._save_callbacks:
            del self._save_callbacks[channel_id]
    
    async def start_auto_save(self, channel_id: str):
        """Start the auto-save loop for a channel."""
        if channel_id in self._tasks:
            return  # Already running
        
        self._tasks[channel_id] = asyncio.create_task(
            self._auto_save_loop(channel_id)
        )
    
    async def stop_auto_save(self, channel_id: str):
        """Stop the auto-save loop for a channel."""
        if channel_id in self._tasks:
            self._tasks[channel_id].cancel()
            try:
                await self._tasks[channel_id]
            except asyncio.CancelledError:
                pass
            del self._tasks[channel_id]
    
    async def _auto_save_loop(self, channel_id: str):
        """Auto-save loop that runs periodically."""
        while True:
            try:
                await asyncio.sleep(AUTO_SAVE_INTERVAL)
                
                # Check if session is still active
                session = load_session_state(channel_id)
                if session.status != SessionStatus.ACTIVE.value:
                    break
                
                # Check for inactivity
                if check_inactivity(channel_id):
                    logger.info(f"Session {channel_id} paused due to inactivity")
                    pause_session(channel_id)
                    break
                
                # Perform auto-save
                if channel_id in self._save_callbacks:
                    campaign_state = self._save_callbacks[channel_id](channel_id)
                    if campaign_state:
                        save_recovery_point(channel_id, campaign_state)
                        session.last_save = datetime.now().isoformat()
                        save_session_state(channel_id, session)
                        logger.debug(f"Auto-saved session {channel_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-save loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying


# Global auto-save manager
auto_save_manager = AutoSaveManager()


# ============================================================================
# FORMATTING
# ============================================================================

def format_session_status(channel_id: str) -> str:
    """Format current session status for display."""
    session = load_session_state(channel_id)
    
    if session.status == SessionStatus.INACTIVE.value:
        # Check for previous sessions
        summaries = load_session_summaries(channel_id)
        if summaries:
            last = summaries[-1]
            time_ago = calculate_time_since(last.ended_at)
            return f"📊 **No Active Session**\nLast session: {time_ago} ({last.duration_minutes} min)"
        return "📊 **No Active Session**"
    
    duration = get_session_duration_minutes(channel_id)
    phase = get_current_pacing_phase(channel_id)
    
    lines = [
        f"📊 **Session Status: {session.status.title()}**",
        f"⏱️ Duration: {duration} minutes",
        f"🎭 Phase: {phase.value.title()}",
        f"👥 Players: {len(session.active_players)}",
        "",
        f"⚔️ Combats: {session.combat_count}",
        f"🎯 Actions: {session.action_count}",
        f"💤 Rests: {session.rest_count}",
    ]
    
    if session.last_save:
        save_time = calculate_time_since(session.last_save)
        lines.append(f"💾 Last save: {save_time}")
    
    return "\n".join(lines)


def format_recap(channel_id: str) -> str:
    """Format a session recap for display."""
    recap = generate_session_recap(channel_id)
    if not recap:
        return "📖 No previous session found."
    return f"📖 **Session Recap**\n\n{recap}"


def format_session_end_summary(summary: SessionSummary) -> str:
    """Format session end summary for display."""
    lines = [
        "🎬 **Session Complete!**",
        "",
        f"⏱️ Duration: {summary.duration_minutes} minutes",
        f"👥 Players: {len(summary.players)}",
        f"⚔️ Combats: {summary.combat_count}",
        f"🎯 Actions: {summary.action_count}",
        "",
        f"📍 Final Location: {summary.final_location}",
    ]
    
    if summary.active_quests:
        lines.append(f"📜 Active Quests: {', '.join(summary.active_quests)}")
    
    if summary.key_events:
        lines.append("")
        lines.append("**Key Events:**")
        for event in summary.key_events[-3:]:
            lines.append(f"• {event}")
    
    lines.append("")
    lines.append("*Use `/recap` next session to refresh your memory!*")
    
    return "\n".join(lines)
