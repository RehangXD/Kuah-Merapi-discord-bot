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
from Config import MODULE_TOGGLES

load_dotenv()

def _extract(query, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(query, download=False)
    
class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SONG_QUEUES = {}
        self.LOOP_STATES = {}
        self.TEXT_CHANNELS = {}
        self.INACTIVITY_TIMERS = {}
        self.module_name = "Music"

        sp_id = os.getenv("SPOTIPY_CLIENT_ID")
        sp_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

        print(f"--- Pengecekan Spotify ---")
        print(f"Client ID terbaca: {sp_id}")
        
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=sp_id,
            client_secret=sp_secret
        ))
        
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
                # Mengambil foto album Spotify
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
        except Exception as e:
            print(f"Spotify API Error: {e}")
            
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
        await asyncio.sleep(300)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            if channel:
                embed = discord.Embed(description=f"Terputus dari voice channel. {reason}", color=discord.Color.red())
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
            self.start_inactivity_timer(guild_id, voice_client, channel, "Tidak ada orang di voice channel selama 3 menit.")
        else:
            if voice_client.is_playing() or voice_client.is_paused() or self.SONG_QUEUES.get(guild_id):
                self.cancel_inactivity_timer(guild_id)

    async def play_next_song(self, voice_client, guild_id, channel, current_song=None):
        loop_state = self.LOOP_STATES.get(guild_id, "off")
        
        if current_song and loop_state == "all":
            self.SONG_QUEUES[guild_id].append(current_song)
            
        if loop_state == "single" and current_song:
            web_url, title, thumb = current_song
        elif self.SONG_QUEUES.get(guild_id):
            web_url, title, thumb = self.SONG_QUEUES[guild_id].popleft()
        else:
            self.start_inactivity_timer(guild_id, voice_client, channel, "Antrean lagu habis.")
            return
        
        ydl_option = {
            "format": "bestaudio[abr<96]/bestaudio",
            "noplaylist": True, 
            "quiet": True,
            "ignoreerrors": True,
        }
            
        try:
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, _extract, web_url, ydl_option)
            
            # Validasi jika video dihapus atau tidak tersedia
            if info is None:
                raise Exception("Video tidak tersedia.")
            
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                
            stream_url = info.get('url')
            if not stream_url:
                raise Exception("URL stream gagal diekstrak.")
                
            title = info.get('title', title)
            thumb = info.get('thumbnail', thumb)
            
            # Menyimpan data valid untuk fungsi pengulangan
            valid_song = (web_url, title, thumb)
            
        except Exception as e:
            print(f"Extraction error: {e}")
            await channel.send(f"Melewati **{title}** karena video tidak tersedia.")
            # Melompat ke lagu berikutnya dengan mengirim parameter None 
            # agar lagu yang rusak tidak dimasukkan kembali ke antrean
            await self.play_next_song(voice_client, guild_id, channel, None)
            return
        
        # --- EMBED: SEDANG MEMUTAR ---
        if loop_state != "single":
            embed = discord.Embed(title="Sedang Memutar", description=f"**{title}**", color=discord.Color.blue())
            if thumb:
                embed.set_thumbnail(url=thumb)
            asyncio.create_task(channel.send(embed=embed))
        
        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -headers \"{header_str}\"",
            "options": "-vn",
        }
                
        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")
        
        def after_play(error):
            if error:
                print(f"Error playing {title}: {error}")
            # Menggunakan valid_song untuk mencegah error pada lagu yang rusak
            asyncio.run_coroutine_threadsafe(self.play_next_song(voice_client, guild_id, channel, valid_song), self.bot.loop)
        
        voice_client.play(source, after=after_play)

    @commands.hybrid_command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(query="The YouTube URL, Spotify URL, or search term.")
    async def play(self, ctx: commands.Context, *, query: str):
        await ctx.defer()

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

        is_spotify = "spotify.com" in query
        is_link = query.startswith("http://") or query.startswith("https://")

        ydl_option = {
            "format": "bestaudio[abr<96]/bestaudio",
            "noplaylist": False,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
            "extract_flat": True,
            "ignoreerrors": True,
        }

        if is_spotify:
            tracks = await self.get_spotify_tracks_async(query)
            if not tracks:
                await ctx.send("Could not extract tracks from the provided Spotify link.")
                return
                
            first_track = tracks[0]
            first_query = f"ytsearch1:{first_track['query']}"
            try:
                results = await self.search_ytdlp_async(first_query, ydl_option)
                if results and "entries" in results and results["entries"]:
                    entry = results["entries"][0]
                    audio_url = entry.get("url") or entry.get("webpage_url")
                    title = entry.get("title", first_track['title'])
                    thumb = entry.get("thumbnail", first_track['thumb'])
                    self.SONG_QUEUES[guild_id].append((audio_url, title, thumb))
                else:
                    self.SONG_QUEUES[guild_id].append((first_query, first_track['title'], first_track['thumb']))
            except Exception:
                self.SONG_QUEUES[guild_id].append((first_query, first_track['title'], first_track['thumb']))

            for t in tracks[1:]:
                self.SONG_QUEUES[guild_id].append((f"ytsearch1:{t['query']}", t['title'], t['thumb']))
                
            # --- EMBED: SPOTIFY ADDED ---
            if len(tracks) > 1:
                embed = discord.Embed(title="Spotify Playlist Ditambahkan", description=f"Menambahkan **{len(tracks)}** lagu ke antrean.", color=discord.Color.green())
                if first_track['thumb']:
                    embed.set_thumbnail(url=first_track['thumb'])
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="Menambahkan ke Antrean", description=f"**{first_track['title']}**", color=discord.Color.green())
                if first_track['thumb']:
                    embed.set_thumbnail(url=first_track['thumb'])
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
        
            if "entries" in results:
                entries = results["entries"]
                if not is_link:
                    entries = [entries[0]]
                    
                for entry in entries:
                    audio_url = entry.get("url") or entry.get("webpage_url")
                    title = entry.get("title", "Untitled")
                    thumb = entry.get("thumbnail")
                    self.SONG_QUEUES[guild_id].append((audio_url, title, thumb))
        
                # --- EMBED: YOUTUBE PLAYLIST ADDED ---
                if len(entries) > 1:
                    embed = discord.Embed(title="Playlist Ditambahkan", description=f"Menambahkan **{len(entries)}** lagu ke antrean.", color=discord.Color.green())
                    if entries[0].get("thumbnail"):
                        embed.set_thumbnail(url=entries[0].get("thumbnail"))
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(title="Menambahkan ke Antrean", description=f"**{entries[0].get('title', 'Untitled')}**", color=discord.Color.green())
                    if entries[0].get("thumbnail"):
                        embed.set_thumbnail(url=entries[0].get("thumbnail"))
                    await ctx.send(embed=embed)
            else:
                audio_url = results.get("url") or results.get("webpage_url")
                title = results.get("title", "Untitled")
                thumb = results.get("thumbnail")
                self.SONG_QUEUES[guild_id].append((audio_url, title, thumb))
                
                # --- EMBED: YOUTUBE SINGLE ADDED ---
                embed = discord.Embed(title="Menambahkan ke Antrean", description=f"**{title}**", color=discord.Color.green())
                if thumb:
                    embed.set_thumbnail(url=thumb)
                await ctx.send(embed=embed)
    
        if not voice_client.is_playing() and not voice_client.is_paused():
            await self.play_next_song(voice_client, guild_id, ctx.channel)
            
    @commands.hybrid_command(name="skip", description="Skip the current playing song.")
    async def skip(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            guild_id = str(ctx.guild.id)
            
            # Matikan single loop sementara jika user memaksa skip
            if self.LOOP_STATES.get(guild_id) == "single":
                self.LOOP_STATES[guild_id] = "off"
                await ctx.send("⏩ Melewati lagu... *(Mode loop 1 lagu dimatikan otomatis)*")
            else:
                await ctx.send("⏩ Melewati lagu... *(Memuat lagu selanjutnya)*")
                
            # Menghentikan pemutaran memicu bot untuk langsung membaca antrean berikutnya
            voice_client.stop()
        else:
            await ctx.send("Tidak ada lagu yang sedang diputar.")
    
    @commands.hybrid_command(name="pause", description="Pause the current song.")
    async def pause(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸️ Musik dijeda.")
        else:
            await ctx.send("Tidak ada musik yang sedang diputar.")
    
    @commands.hybrid_command(name="resume", description="Resume a paused song.")
    async def resume(self, ctx: commands.Context):
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ Musik dilanjutkan.")
        else:
            await ctx.send("Musik tidak sedang dijeda.")
    
    @commands.hybrid_command(name="stop", description="Stop the music and clear the queue.")
    async def stop(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        voice_client = ctx.guild.voice_client
        
        if voice_client:
            if guild_id in self.SONG_QUEUES:
                self.SONG_QUEUES[guild_id].clear()
            self.LOOP_STATES[guild_id] = "off"
            self.cancel_inactivity_timer(guild_id)
            
            voice_client.stop()
            await voice_client.disconnect()
            await ctx.send("⏹️ Musik dihentikan dan antrean dibersihkan.")
        else:
            await ctx.send("Saya tidak berada di voice channel.")
    
    @commands.hybrid_command(name="loop", description="Toggle looping for the current song.")
    async def loop(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        current_state = self.LOOP_STATES.get(guild_id, "off")
        
        if current_state == "single":
            self.LOOP_STATES[guild_id] = "off"
            await ctx.send("➡️ Pengulangan 1 lagu dimatikan.")
        else:
            self.LOOP_STATES[guild_id] = "single"
            await ctx.send("🔂 Pengulangan 1 lagu diaktifkan.")
            
    @commands.hybrid_command(name="loopall", description="Toggle looping for the entire queue.")
    async def loopall(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        current_state = self.LOOP_STATES.get(guild_id, "off")
        
        if current_state == "all":
            self.LOOP_STATES[guild_id] = "off"
            await ctx.send("➡️ Pengulangan seluruh antrean dimatikan.")
        else:
            self.LOOP_STATES[guild_id] = "all"
            await ctx.send("🔁 Pengulangan seluruh antrean diaktifkan.")

        @commands.Cog.listener()
        async def on_message(self, message):
            if not MODULE_TOGGLES.get(self.module_name, True):
                return

async def setup(bot):
    await bot.add_cog(MusicCog(bot))