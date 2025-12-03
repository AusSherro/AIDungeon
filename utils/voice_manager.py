import asyncio
import os
import tempfile
import discord

class VoiceClientManager:
    """Manage Discord voice clients per guild."""

    def __init__(self):
        self.clients = {}
        self._disconnect_tasks = {}

    async def get_or_create(self, channel: discord.VoiceChannel):
        guild_id = channel.guild.id
        
        # Cancel any pending disconnect
        if guild_id in self._disconnect_tasks:
            self._disconnect_tasks[guild_id].cancel()
            del self._disconnect_tasks[guild_id]
        
        client = self.clients.get(guild_id)
        if client and client.is_connected():
            if client.channel != channel:
                await client.move_to(channel)
            return client
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        self.clients[guild_id] = await channel.connect()
        return self.clients[guild_id]

    async def play(self, channel: discord.VoiceChannel, audio_bytes: bytes, stay_connected: bool = True):
        """Play audio in voice channel. Stays connected by default for campaign flow."""
        if not audio_bytes:
            return  # TTS disabled or failed
            
        client = await self.get_or_create(channel)
        guild_id = channel.guild.id
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Wait for any current playback to finish
        while client.is_playing():
            await asyncio.sleep(0.5)
        
        client.play(discord.FFmpegPCMAudio(tmp_path))
        while client.is_playing():
            await asyncio.sleep(0.5)
        
        os.unlink(tmp_path)
        
        if not stay_connected:
            await self.disconnect(guild_id)
        else:
            # Schedule auto-disconnect after 5 minutes of inactivity
            self._schedule_disconnect(guild_id, delay=300)

    def _schedule_disconnect(self, guild_id: int, delay: int = 300):
        """Schedule a disconnect after delay seconds of inactivity."""
        if guild_id in self._disconnect_tasks:
            self._disconnect_tasks[guild_id].cancel()
        
        async def delayed_disconnect():
            await asyncio.sleep(delay)
            await self.disconnect(guild_id)
        
        self._disconnect_tasks[guild_id] = asyncio.create_task(delayed_disconnect())

    async def disconnect(self, guild_id: int):
        """Disconnect from voice in a guild."""
        if guild_id in self._disconnect_tasks:
            self._disconnect_tasks[guild_id].cancel()
            del self._disconnect_tasks[guild_id]
            
        client = self.clients.pop(guild_id, None)
        if client and client.is_connected():
            await client.disconnect()
