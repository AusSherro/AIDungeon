import asyncio
import os
import tempfile
import discord

class VoiceClientManager:
    """Manage Discord voice clients per guild."""

    def __init__(self):
        self.clients = {}

    async def get_or_create(self, channel: discord.VoiceChannel):
        guild_id = channel.guild.id
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

    async def play(self, channel: discord.VoiceChannel, audio_bytes: bytes):
        client = await self.get_or_create(channel)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        client.play(discord.FFmpegPCMAudio(tmp_path))
        while client.is_playing():
            await asyncio.sleep(1)
        await client.disconnect()
        os.unlink(tmp_path)
        self.clients.pop(channel.guild.id, None)

    async def disconnect(self, guild_id: int):
        client = self.clients.pop(guild_id, None)
        if client and client.is_connected():
            await client.disconnect()
