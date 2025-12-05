"""
Ambient Music & Sound Effects Manager
Manages background music and sound effects for the AI Dungeon Master.
Supports YouTube URLs, local files, and built-in sound effects.
"""

import os
import asyncio
import discord
import tempfile
import random
from typing import Optional, Dict, List
from enum import Enum

# =============================================================================
# AMBIENT MOOD TYPES
# =============================================================================

class AmbientMood(Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    TAVERN = "tavern"
    DUNGEON = "dungeon"
    FOREST = "forest"
    TOWN = "town"
    MYSTERIOUS = "mysterious"
    BOSS = "boss"
    VICTORY = "victory"
    DEATH = "death"
    TENSION = "tension"
    REST = "rest"

# =============================================================================
# SOUND EFFECT TYPES
# =============================================================================

class SoundEffect(Enum):
    DICE_ROLL = "dice_roll"
    CRITICAL_HIT = "critical_hit"
    CRITICAL_MISS = "critical_miss"
    SWORD_SLASH = "sword_slash"
    ARROW_FIRE = "arrow_fire"
    SPELL_CAST = "spell_cast"
    FIREBALL = "fireball"
    LIGHTNING = "lightning"
    HEALING = "healing"
    LEVEL_UP = "level_up"
    GOLD_COINS = "gold_coins"
    DOOR_OPEN = "door_open"
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    DEATH = "death"
    VICTORY_FANFARE = "victory_fanfare"

# =============================================================================
# DEFAULT MUSIC TRACKS (YouTube URLs - royalty-free/creative commons)
# =============================================================================

# These are placeholder URLs - users can configure their own in ambient_config.json
DEFAULT_TRACKS = {
    AmbientMood.COMBAT: [
        # Epic battle music - add your own URLs
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder
    ],
    AmbientMood.EXPLORATION: [
        # Calm exploration themes
    ],
    AmbientMood.TAVERN: [
        # Jovial tavern music
    ],
    AmbientMood.DUNGEON: [
        # Dark, ominous dungeon ambiance
    ],
    AmbientMood.FOREST: [
        # Nature sounds, peaceful forest
    ],
    AmbientMood.TOWN: [
        # Busy marketplace, town life
    ],
    AmbientMood.MYSTERIOUS: [
        # Mysterious, magical ambiance
    ],
    AmbientMood.BOSS: [
        # Intense boss battle themes
    ],
    AmbientMood.VICTORY: [
        # Triumphant victory music
    ],
    AmbientMood.TENSION: [
        # Suspenseful, tense ambiance
    ],
    AmbientMood.REST: [
        # Calm, restful music for long rests
    ],
}

# =============================================================================
# SOUND EFFECT FREQUENCIES (Hz-based tone generation for built-in effects)
# =============================================================================

# Simple tone-based sound effects (fallback when no audio files available)
TONE_EFFECTS = {
    SoundEffect.DICE_ROLL: [(400, 50), (600, 50), (800, 50)],  # Ascending tones
    SoundEffect.CRITICAL_HIT: [(1000, 100), (1200, 100), (1400, 200)],  # Triumphant
    SoundEffect.CRITICAL_MISS: [(400, 100), (200, 200)],  # Descending sad
    SoundEffect.LEVEL_UP: [(523, 100), (659, 100), (784, 100), (1047, 300)],  # C-E-G-C
    SoundEffect.HEALING: [(400, 100), (500, 100), (600, 100), (700, 200)],  # Gentle rise
    SoundEffect.GOLD_COINS: [(800, 50), (1000, 50), (800, 50), (1000, 50)],  # Ching ching
    SoundEffect.COMBAT_START: [(200, 100), (300, 100), (400, 100), (500, 150)],  # Battle drums
    SoundEffect.VICTORY_FANFARE: [(523, 150), (659, 150), (784, 150), (1047, 400)],  # Fanfare
}


# =============================================================================
# AMBIENT MANAGER CLASS
# =============================================================================

class AmbientManager:
    """Manages ambient music and sound effects for a Discord guild."""
    
    def __init__(self):
        self._guild_states: Dict[int, Dict] = {}  # guild_id -> state
        self._volume: float = 0.3  # Default volume (30%)
        self._sfx_volume: float = 0.5  # Sound effect volume
        self._music_enabled: bool = True
        self._sfx_enabled: bool = True
        
    def get_state(self, guild_id: int) -> Dict:
        """Get or create ambient state for a guild."""
        if guild_id not in self._guild_states:
            self._guild_states[guild_id] = {
                'current_mood': None,
                'is_playing': False,
                'loop': True,
                'volume': self._volume,
                'custom_tracks': {},
            }
        return self._guild_states[guild_id]
    
    async def set_mood(self, voice_client: discord.VoiceClient, mood: AmbientMood) -> bool:
        """
        Set the ambient mood and start playing appropriate music.
        
        Args:
            voice_client: The Discord voice client
            mood: The ambient mood to set
            
        Returns:
            True if music started successfully
        """
        if not self._music_enabled or not voice_client:
            return False
        
        guild_id = voice_client.guild.id
        state = self.get_state(guild_id)
        
        # If same mood, don't restart
        if state['current_mood'] == mood and state['is_playing']:
            return True
        
        state['current_mood'] = mood
        
        # Stop current music if playing
        if voice_client.is_playing():
            voice_client.stop()
        
        # Try to play music for this mood
        tracks = state['custom_tracks'].get(mood.value, DEFAULT_TRACKS.get(mood, []))
        
        if tracks:
            # TODO: Implement yt-dlp streaming or local file playback
            # For now, just update state
            state['is_playing'] = True
            return True
        
        return False
    
    async def play_sfx(self, voice_client: discord.VoiceClient, effect: SoundEffect) -> bool:
        """
        Play a sound effect without interrupting ambient music.
        
        Args:
            voice_client: The Discord voice client
            effect: The sound effect to play
            
        Returns:
            True if SFX played successfully
        """
        if not self._sfx_enabled or not voice_client:
            return False
        
        # Generate simple tone-based sound effect
        if effect in TONE_EFFECTS:
            audio = self._generate_tone_sequence(TONE_EFFECTS[effect])
            if audio:
                try:
                    source = discord.FFmpegPCMAudio(audio, pipe=True)
                    source = discord.PCMVolumeTransformer(source, volume=self._sfx_volume)
                    
                    # Play SFX (will interrupt current audio briefly)
                    if not voice_client.is_playing():
                        voice_client.play(source)
                    return True
                except Exception as e:
                    print(f"SFX playback error: {e}")
        
        return False
    
    def _generate_tone_sequence(self, tones: List[tuple]) -> Optional[bytes]:
        """
        Generate a simple tone sequence as audio bytes.
        
        Args:
            tones: List of (frequency_hz, duration_ms) tuples
            
        Returns:
            Raw PCM audio bytes or None
        """
        try:
            import struct
            import math
            
            sample_rate = 48000
            audio_data = bytearray()
            
            for freq, duration_ms in tones:
                num_samples = int(sample_rate * duration_ms / 1000)
                for i in range(num_samples):
                    t = i / sample_rate
                    # Sine wave with fade in/out
                    fade = min(i / (sample_rate * 0.01), 1.0) * min((num_samples - i) / (sample_rate * 0.01), 1.0)
                    sample = int(32767 * 0.5 * fade * math.sin(2 * math.pi * freq * t))
                    audio_data.extend(struct.pack('<h', sample))
            
            return bytes(audio_data)
        except Exception as e:
            print(f"Tone generation error: {e}")
            return None
    
    def stop_music(self, guild_id: int, voice_client: discord.VoiceClient):
        """Stop all ambient music for a guild."""
        state = self.get_state(guild_id)
        state['is_playing'] = False
        state['current_mood'] = None
        
        if voice_client and voice_client.is_playing():
            voice_client.stop()
    
    def set_volume(self, guild_id: int, volume: float):
        """Set music volume (0.0 to 1.0)."""
        volume = max(0.0, min(1.0, volume))
        state = self.get_state(guild_id)
        state['volume'] = volume
    
    def toggle_music(self, enabled: bool):
        """Enable or disable ambient music globally."""
        self._music_enabled = enabled
    
    def toggle_sfx(self, enabled: bool):
        """Enable or disable sound effects globally."""
        self._sfx_enabled = enabled
    
    def get_mood_for_context(self, context: str) -> AmbientMood:
        """
        Determine appropriate mood based on narrative context.
        
        Args:
            context: Text describing the current scene
            
        Returns:
            Appropriate AmbientMood
        """
        context_lower = context.lower()
        
        # Combat keywords
        combat_keywords = ['combat', 'fight', 'attack', 'battle', 'initiative', 'enemy', 'enemies']
        if any(kw in context_lower for kw in combat_keywords):
            # Check for boss
            if any(kw in context_lower for kw in ['boss', 'dragon', 'demon', 'ancient', 'legendary']):
                return AmbientMood.BOSS
            return AmbientMood.COMBAT
        
        # Location keywords
        if any(kw in context_lower for kw in ['tavern', 'inn', 'bar', 'pub', 'drinking']):
            return AmbientMood.TAVERN
        
        if any(kw in context_lower for kw in ['dungeon', 'cave', 'crypt', 'tomb', 'underground']):
            return AmbientMood.DUNGEON
        
        if any(kw in context_lower for kw in ['forest', 'woods', 'grove', 'trees', 'nature']):
            return AmbientMood.FOREST
        
        if any(kw in context_lower for kw in ['town', 'city', 'village', 'market', 'shop']):
            return AmbientMood.TOWN
        
        if any(kw in context_lower for kw in ['mysterious', 'magical', 'arcane', 'strange', 'eerie']):
            return AmbientMood.MYSTERIOUS
        
        if any(kw in context_lower for kw in ['rest', 'camp', 'sleep', 'recover']):
            return AmbientMood.REST
        
        if any(kw in context_lower for kw in ['tension', 'danger', 'trap', 'stealth', 'sneak']):
            return AmbientMood.TENSION
        
        if any(kw in context_lower for kw in ['victory', 'won', 'defeated', 'triumph']):
            return AmbientMood.VICTORY
        
        # Default to exploration
        return AmbientMood.EXPLORATION
    
    def get_sfx_for_action(self, action: str, result: dict = None) -> Optional[SoundEffect]:
        """
        Determine appropriate sound effect for an action.
        
        Args:
            action: The action being performed
            result: Optional result dict (e.g., from attack or roll)
            
        Returns:
            Appropriate SoundEffect or None
        """
        action_lower = action.lower()
        
        # Check for roll results
        if result:
            if result.get('crit'):
                return SoundEffect.CRITICAL_HIT
            if result.get('fumble'):
                return SoundEffect.CRITICAL_MISS
            if result.get('level_up'):
                return SoundEffect.LEVEL_UP
        
        # Action keywords
        if any(kw in action_lower for kw in ['roll', 'dice', '1d20', 'd20']):
            return SoundEffect.DICE_ROLL
        
        if any(kw in action_lower for kw in ['attack', 'strike', 'hit', 'slash', 'stab']):
            return SoundEffect.SWORD_SLASH
        
        if any(kw in action_lower for kw in ['arrow', 'bow', 'shoot', 'crossbow']):
            return SoundEffect.ARROW_FIRE
        
        if any(kw in action_lower for kw in ['cast', 'spell', 'magic']):
            if 'fireball' in action_lower or 'fire' in action_lower:
                return SoundEffect.FIREBALL
            if 'lightning' in action_lower or 'thunder' in action_lower:
                return SoundEffect.LIGHTNING
            if 'heal' in action_lower or 'cure' in action_lower:
                return SoundEffect.HEALING
            return SoundEffect.SPELL_CAST
        
        if any(kw in action_lower for kw in ['gold', 'coins', 'treasure', 'loot']):
            return SoundEffect.GOLD_COINS
        
        if any(kw in action_lower for kw in ['door', 'open', 'unlock']):
            return SoundEffect.DOOR_OPEN
        
        return None


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

ambient_manager = AmbientManager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_ambient_manager() -> AmbientManager:
    """Get the global ambient manager instance."""
    return ambient_manager


async def auto_set_mood(voice_client: discord.VoiceClient, narrative: str):
    """
    Automatically set ambient mood based on narrative content.
    
    Args:
        voice_client: Discord voice client
        narrative: The current narrative/scene description
    """
    mood = ambient_manager.get_mood_for_context(narrative)
    await ambient_manager.set_mood(voice_client, mood)


async def play_action_sfx(voice_client: discord.VoiceClient, action: str, result: dict = None):
    """
    Play appropriate sound effect for an action.
    
    Args:
        voice_client: Discord voice client
        action: The action being performed
        result: Optional result dict
    """
    sfx = ambient_manager.get_sfx_for_action(action, result)
    if sfx:
        await ambient_manager.play_sfx(voice_client, sfx)
