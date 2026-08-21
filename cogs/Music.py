import os
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
from collections import deque
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from urllib.parse import urlparse
from Config import MODULE_TOGGLES

load_dotenv()

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)
    
class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.module_name = "Music"
        self.SONG_QUEUES = {}
        self.LOOP_STATES = {}
        self.TEXT_CHANNELS = {}
        self.INACTIVITY_TIMERS = {}
        self.is_processing = {}
        self.is_stopping = {}
        
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
        ))

    def _get_spotify_tracks_sync(self, url: str) -> list:
        tracks_data = []
        try:
            if "track" in url:
                track = self.spotify.track(url)
                artist = track['artists'][0]['name']
                title = track['name']
                thumb = track['album']['images'][0]['url'] if track['album']['images'] else None
                tracks_data.append({"query": f"{title} {artist}", "title": title, "thumb": thumb})
                
            elif "playlist" in url:
                results = self.spotify.playlist_tracks(url)
                tracks = results['items']
                
                while results['next']:
                    results = self.spotify.next(results)
                    tracks.extend(results['items'])
                    
                for item in tracks:
                    track = item.get('track')
                    if track:
                        artist = track['artists'][0]['name']
                        title = track['name']
                        thumb = track['album']['images'][0]['url'] if track['album']['images'] else None
                        tracks_data.append({"query": f"{title} {artist}", "title": title, "thumb": thumb})

            elif "album" in url:
                album_info = self.spotify.album(url)
                thumb = album_info['images'][0]['url'] if album_info['images'] else None
                
                results = self.spotify.album_tracks(url)
                tracks = results['items']
                
                while results['next']:
                    results = self.spotify.next(results)
                    tracks.extend(results['items'])
                    
                for track in tracks:
                    artist = track['artists'][0]['name']
                    title = track['name']
                    tracks_data.append({"query": f"{title} {artist}", "title": title, "thumb": thumb})
                    
        except Exception as e:
            print(f"[Spotify Error] {e}")
            
        return tracks_data

    async def get_spotify_tracks_async(self, url: str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_spotify_tracks_sync, url)

    async def search_ytdlp_async(self, query, ydl_opts):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _extract, query, ydl_opts)

    def cancel_inactivity_timer(self, guild_id):
        timer = self.INACTIVITY_TIMERS.get(guild_id)
        if timer:
            timer.cancel()
            del self.INACTIVITY_TIMERS[guild_id]

    def start_inactivity_timer(self, guild_id, voice_client, channel, reason):
        self.cancel_inactivity_timer(guild_id)
        self.INACTIVITY_TIMERS[guild_id] = self.bot.loop.create_task(
            self._inactivity_countdown(guild_id, voice_client, channel, reason)
        )

    async def _inactivity_countdown(self, guild_id, voice_client, channel, reason):
        await asyncio.sleep(180)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            if channel:
                embed = discord.Embed(description=f"Disconnected from voice channel. {reason}", color=discord.Color.red())
                await channel.send(embed=embed)
        
        self.LOOP_STATES[guild_id] = "off"
        if guild_id in self.SONG_QUEUES:
            self.SONG_QUEUES[guild_id].clear()
        if guild_id in self.INACTIVITY_TIMERS:
            del self.INACTIVITY_TIMERS[guild_id]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        voice_client = member.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        guild_id = str(member.guild.id)
        bot_channel = voice_client.channel
        humans = [m for m in bot_channel.members if not m.bot]

        if len(humans) == 0:
            channel = self.TEXT_CHANNELS.get(guild_id)
            self.start_inactivity_timer(guild_id, voice_client, channel, "No users in the voice channel for 5 minutes.")
        else:
            if voice_client.is_playing() or voice_client.is_paused() or self.SONG_QUEUES.get(guild_id):
                self.cancel_inactivity_timer(guild_id)

    async def prefetch_next_song(self, guild_id):
        if self.SONG_QUEUES.get(guild_id) and len(self.SONG_QUEUES[guild_id]) > 0:
            first_item = self.SONG_QUEUES[guild_id][0]
            if len(first_item) == 3:
                web_url, title, tumb = first_item
                ydl_option = {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                    "ignoreerrors": True,
                    "nocheckcertificate": True,
                    "no_warnings": True,
                    "skip_download": True,
                }
                try:
                    loop =asyncio.get_running_loop()
                    info =await loop.run_in_executor(None, _extract, web_url,ydl_option)
                    if info and 'entries' in info and info['entries']:
                        info = info['entries'][0]
                    stream_url = info.get('url') if info else None
                    if stream_url and len(self.SONG_QUEUES[guild_id]) > 0 and self.SONG_QUEUES[guild_id][0][0] == web_url:
                        self.SONG_QUEUES[guild_id][0] = (web_url, title, thumb, stream_url)
                except Exception as e:
                    print(f"[Prefetch Error] {e}")

    async def play_next_song(self, voice_client, guild_id, channel=None, current_song=None):
        if self.is_stopping.get(guild_id, False):
            self.is_stopping[guild_id] = False
            return
        
        if channel is None:
            channel = self.TEXT_CHANNELS.get(guild_id)

        if self.is_processing.get(guild_id, False):
            return

        self.is_processing[guild_id] = True
        loop_state = self.LOOP_STATES.get(guild_id, "off")
        
        # Handle current_song format: (web_url, title, thumb)
        stream_url = None
        if loop_state == "single" and current_song:
            web_url, title, thumb = current_song[:3]
            if len(current_song) == 4:
                stream_url = current_song[3]
        elif self.SONG_QUEUES.get(guild_id) and len(self.SONG_QUEUES[guild_id]) > 0:
            song_data = self.SONG_QUEUES[guild_id].popleft()
            web_url, title, thumb = song_data[:3]
            if len(song_data) == 4:
                stream_url = song_data[3]
        else:
            self.is_processing[guild_id] = False
            if channel:
                self.bot.loop.create_task(channel.send("👀 **Queue is empty**"))
            self.start_inactivity_timer(guild_id, voice_client, channel, "Queue is empty.")
            return

        # Fetch actual stream data just before playing (Lazy Load)
        ydl_option = {
            "format": "bestaudio/best",
            "noplaylist": True, 
            "quiet": True,
            "ignoreerrors": True,
            "nocheckcertificate": True,
            "no_warnings": True,
            "skip_download": True,
        }
            
        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, _extract, web_url, ydl_option)
            if info is None:
                raise Exception("Video is unavailable.")
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            stream_url = info.get('url')
            if not stream_url:
                raise Exception("Stream URL could not be extracted.")
            title = info.get('title', title)
            thumb = info.get('thumbnail', thumb)
        except Exception as e:
            print(f"[Queue Error] Extraction failed: {e}")
            self.is_processing[guild_id] = False
            if channel:
                self.bot.loop.create_task (channel.send(f"⚠️ Skipping **{title}** (Video unavailable or restricted)."))
            self.bot.loop.create_task(self.play_next_song(voice_client, guild_id, channel, None))
            return

        valid_song = (web_url, title, thumb)

        # If loopall is active, push the metadata back to the end of the queue
        if loop_state == "all":
            self.SONG_QUEUES[guild_id].append((web_url, title, thumb))
            
        if loop_state != "single" and channel:
            embed = discord.Embed(title="🎶 Now Playing", description=f"**{title}**", color=discord.Color.blue())
            if thumb:
                embed.set_thumbnail(url=thumb)
            self.bot.loop.create_task(channel.send(embed=embed))
        
        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }
                
        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options, executable="C:/Users/RehangXD/Music/DiscordBot/bin/ffmpeg/ffmpeg.exe")
        
        def after_play(error):
            self.is_processing[guild_id] = False
            if error:
                print(f"[Audio Error] Issue playing {title}: {error}")
            try:
                self.bot.loop.create_task(self.play_next_song(voice_client, guild_id, channel, valid_song))
            except Exception as e:
                print(f"[System Error] Failed to schedule next song: {e}")

        self.is_processing[guild_id] = False
        voice_client.play(source, after=after_play)

    @commands.hybrid_command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(query="The YouTube URL, Spotify URL, or search term.")
    async def play(self, ctx: commands.Context, *, query: str):
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                try:
                    await ctx.defer()
                except discord.NotFound:
                    return

        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if voice_channel is None:
            await ctx.send("You must be in a voice channel.")
            return
    
        voice_client = ctx.guild.voice_client
        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)
    
        guild_id = str(ctx.guild.id)
        self.TEXT_CHANNELS[guild_id] = ctx.channel
        self.cancel_inactivity_timer(guild_id)
        
        if self.SONG_QUEUES.get(guild_id) is None:
            self.SONG_QUEUES[guild_id] = deque()

        parsed_url = urlparse(query)
        is_spotify = parsed_url.hostname in ["spotify.com", "open.spotify.com"]
        is_link = "http://" in query or "https://" in query or "www." in query

        # THE FIX: Using "in_playlist" forces yt-dlp to correctly output the array of songs
        # when dealing with a combined watch?v=...&list=... URL.
        ydl_option = {
            "extract_flat": "in_playlist",
            "noplaylist": False,
            "ignoreerrors": True,
            "playlistend": 250 # Max limit of playlist songs to extract
        }

        if is_spotify:
            tracks = await self.get_spotify_tracks_async(query)
            if not tracks:
                await ctx.send("Could not extract tracks from the provided Spotify link.")
                return
            
            for t in tracks:
                self.SONG_QUEUES[guild_id].append((f"ytsearch1:{t['query']}", t['title'], t['thumb']))
                
            embed = discord.Embed(title="Spotify Added", description=f"Added **{len(tracks)}** tracks to the queue.", color=discord.Color.green())
            if tracks[0]['thumb']:
                embed.set_thumbnail(url=tracks[0]['thumb'])
            await ctx.send(embed=embed)

        else:
            search_query = query if is_link else f"ytsearch1:{query}"
        
            try:
                results = await self.search_ytdlp_async(search_query, ydl_option)
            except Exception as e:
                await ctx.send(f"An error occurred while searching: {e}")
                return
        
            if not results:
                await ctx.send("No results found.")
                return
        
            added_count = 0
            first_thumb = None
            
            if "entries" in results:
                raw_entries = results["entries"]
                
                # If it's a search term (not a playlist link), only queue the top result
                if not is_link:
                    raw_entries = [next(iter(raw_entries), None)]
                    
                for entry in raw_entries:
                    if entry:
                        web_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                        if web_url and not web_url.startswith("http"):
                            web_url = f"https://www.youtube.com/watch?v={web_url}"
                            
                        title = entry.get("title", "Untitled")
                        thumb = None
                        if entry.get("thumbnails"):
                            thumb = entry["thumbnails"][0].get("url")
                        elif entry.get("thumbnail"):
                            thumb = entry.get("thumbnail")
                            
                        if added_count == 0:
                            first_thumb = thumb
                            
                        self.SONG_QUEUES[guild_id].append((web_url, title, thumb))
                        added_count += 1

                        if added_count == 1 and not voice_client.is_playing() and not voice_client.is_paused():
                            await self.play_next_song(voice_client, guild_id, ctx.channel)
            else:
                web_url = results.get("url") or results.get("webpage_url") or results.get("id")
                if web_url and not web_url.startswith("http"):
                    web_url = f"https://www.youtube.com/watch?v={web_url}"
                    
                title = results.get("title", "Untitled")
                thumb = results.get("thumbnail")
                first_thumb = thumb
                self.SONG_QUEUES[guild_id].append((web_url, title, thumb))
                added_count = 1
                
            if added_count > 0:
                embed = discord.Embed(title="Added to Queue", description=f"Queued **{added_count}** track(s).", color=discord.Color.green())
                if first_thumb:
                    embed.set_thumbnail(url=first_thumb)
                await ctx.send(embed=embed)
            else:
                await ctx.send("No valid tracks could be extracted.")
    
        if not voice_client.is_playing() and not voice_client.is_paused() and len(self.SONG_QUEUES[guild_id]) > 0:
            await self.play_next_song(voice_client, guild_id, ctx.channel)
            
    @commands.hybrid_command(name="skip", description="Skip the current playing song.")
    async def skip(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            guild_id = str(ctx.guild.id)
            if self.LOOP_STATES.get(guild_id) == "single":
                self.LOOP_STATES[guild_id] = "off"
                description_skip = "⏩ Skipped. Single loop mode automatically disabled."
            else:
                description_skip = "⏩ Skipped. Loading next track..."
            embed = discord.Embed(
                title="Track Skipped",
                description=description_skip,
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
                
            if voice_client.is_paused():
                voice_client.resume()
                
            voice_client.stop()
        else:
            embed = discord.Embed(
                description="There is no song currently playing.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="skipall", description="Clear all song from the queue.")
    async def skipall(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)

        if guild_id in self.SONG_QUEUES and len(self.SONG_QUEUES[guild_id]) > 0:
            self.SONG_QUEUES[guild_id].clear()
            embed = discord.Embed(
                title="Queue Clear",
                description="**All songs have been removed from queue.**",
                color=discord.Color.Green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="❌ The queue is already empty.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="pause", description="Pause the current song.")
    async def pause(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            embed = discord.Embed(description="⏸️ Music paused.",color=discord.Color.red())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="There is no song currently playing.",color=discord.Color.red())
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="resume", description="Resume a paused song.")
    async def resume(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            embed = discord.Embed(
                description="▶️ Music resumed.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="The music is not paused.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="stop", description="Stop the music and clear the queue.")
    async def stop(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        voice_client = ctx.guild.voice_client
        
        if voice_client and voice_client.is_connected():
            self.is_stopping[guild_id] = True
            
            if guild_id in self.SONG_QUEUES:
                self.SONG_QUEUES[guild_id].clear()
            self.LOOP_STATES[guild_id] = "off"
            self.cancel_inactivity_timer(guild_id)

            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            
            await voice_client.disconnect()
            embed = discord.Embed(
                description="⏹️ Music stopped and queue cleared.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="I am not connected to a voice channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="loop", description="Toggle looping for the current song.")
    async def loop(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        current_state = self.LOOP_STATES.get(guild_id, "off")
        
        if current_state == "single":
            self.LOOP_STATES[guild_id] = "off"
            embed = discord.Embed(
                description="➡️ Single track loop disabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            self.LOOP_STATES[guild_id] = "single"
            embed = discord.Embed(
                description="🔂 Single track loop enabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @commands.hybrid_command(name="loopall", description="Toggle looping for the entire queue.")
    async def loopall(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        current_state = self.LOOP_STATES.get(guild_id, "off")
        
        if current_state == "all":
            self.LOOP_STATES[guild_id] = "off"
            embed = discord.Embed(
                description="➡️ Queue loop disabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            self.LOOP_STATES[guild_id] = "all"
            embed = discord.Embed(
                description="🔁 Queue loop enabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
            if not MODULE_TOGGLES.get(self.module_name, True):
                return

            if message.author.bot:
                  return

async def setup(bot):
    await bot.add_cog(MusicCog(bot))