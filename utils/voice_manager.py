import asyncio
import os
import tempfile
import discord

class VoiceClientManager:
    """Manage Discord voice clients per guild with robust reconnection handling."""

    def __init__(self):
        self.clients = {}
        self._disconnect_tasks = {}
        self._connecting = {}  # Track ongoing connections to prevent race conditions

    async def get_or_create(self, channel: discord.VoiceChannel, max_retries: int = 3):
        guild_id = channel.guild.id
        
        # Cancel any pending disconnect
        if guild_id in self._disconnect_tasks:
            self._disconnect_tasks[guild_id].cancel()
            del self._disconnect_tasks[guild_id]
        
        # Prevent concurrent connection attempts
        if guild_id in self._connecting:
            # Wait for existing connection attempt
            for _ in range(30):  # Wait up to 15 seconds
                await asyncio.sleep(0.5)
                if guild_id not in self._connecting:
                    break
            client = self.clients.get(guild_id)
            if client and client.is_connected():
                return client
        
        # Check existing voice client from guild
        existing_vc = channel.guild.voice_client
        if existing_vc and existing_vc.is_connected():
            if existing_vc.channel.id == channel.id:
                self.clients[guild_id] = existing_vc
                return existing_vc
            else:
                # Move to new channel
                try:
                    await existing_vc.move_to(channel)
                    self.clients[guild_id] = existing_vc
                    return existing_vc
                except Exception as e:
                    print(f"Failed to move voice client: {e}")
        
        # Clean up any stale clients
        client = self.clients.get(guild_id)
        if client:
            try:
                await client.disconnect(force=True)
            except Exception:
                pass
            self.clients.pop(guild_id, None)
        
        # Force disconnect any existing voice client
        if existing_vc:
            try:
                await existing_vc.disconnect(force=True)
            except Exception:
                pass
            await asyncio.sleep(0.5)
        
        # Connect with retry logic
        self._connecting[guild_id] = True
        try:
            for attempt in range(max_retries):
                try:
                    print(f"Voice connection attempt {attempt + 1} to {channel.name}...")
                    # Use longer timeout, self_deaf helps with stability
                    new_client = await asyncio.wait_for(
                        channel.connect(timeout=30.0, reconnect=True, self_deaf=True),
                        timeout=40.0
                    )
                    self.clients[guild_id] = new_client
                    print(f"✅ Voice connected to {channel.name}")
                    return new_client
                except asyncio.TimeoutError:
                    print(f"Voice connection attempt {attempt + 1} timed out")
                except discord.errors.ClientException as e:
                    if "already connected" in str(e).lower():
                        # Already connected - try to get existing client
                        await asyncio.sleep(1)
                        if channel.guild.voice_client:
                            self.clients[guild_id] = channel.guild.voice_client
                            return channel.guild.voice_client
                    print(f"Voice ClientException: {e}")
                except Exception as e:
                    print(f"Voice connection attempt {attempt + 1} failed: {type(e).__name__}: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 3 * (attempt + 1)  # 3, 6, 9 seconds
                    print(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
            
            print(f"❌ Failed to connect to voice after {max_retries} attempts")
            return None  # Return None instead of raising exception
        finally:
            self._connecting.pop(guild_id, None)

    async def play(self, channel: discord.VoiceChannel, audio_bytes: bytes, stay_connected: bool = True):
        """Play audio in voice channel. Stays connected by default for campaign flow."""
        if not audio_bytes:
            return  # TTS disabled or failed
        
        tmp_path = None
        try:
            client = await self.get_or_create(channel)
            
            # If connection failed, skip TTS silently
            if not client:
                print("TTS skipped: Could not connect to voice")
                return
            
            guild_id = channel.guild.id
            
            # Verify connection is still valid
            if not client.is_connected():
                print("TTS Error: Voice client not connected")
                return
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            # Wait for any current playback to finish (with timeout)
            wait_count = 0
            while client.is_playing() and wait_count < 60:  # Max 30 seconds wait
                await asyncio.sleep(0.5)
                wait_count += 1
            
            # Stop any stuck playback
            if client.is_playing():
                client.stop()
                await asyncio.sleep(0.5)
            
            # Double-check connection before playing
            if not client.is_connected():
                print("TTS Error: Connection lost before playback")
                return
            
            # Play the audio
            try:
                client.play(discord.FFmpegPCMAudio(tmp_path))
                print("🔊 Playing TTS audio...")
            except discord.errors.ClientException as e:
                print(f"TTS Playback Error: {e}")
                return
            
            # Wait for playback to complete
            wait_count = 0
            while client.is_playing() and wait_count < 120:  # Max 60 seconds playback
                await asyncio.sleep(0.5)
                wait_count += 1
            
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            # Clean up temp file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        
        if not stay_connected:
            await self.disconnect(channel.guild.id)
        else:
            # Schedule auto-disconnect after 5 minutes of inactivity
            self._schedule_disconnect(channel.guild.id, delay=300)

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
