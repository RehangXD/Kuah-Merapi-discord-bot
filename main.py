import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MY_GUILD = discord.Object(id=763868387607969823)

# SAKLAR MODE TESTING:
# Ubah ke True jika sedang mengedit/menambah fitur (hanya muncul di server tes).
# Ubah ke False jika bot sudah siap dipakai oleh semua orang (Global).
TESTING_MODE = False

class MyBot(commands.Bot):
    def __init__(self):
        # 1. Intents wajib menyalakan message_content agar prefix '!' terbaca
        intents = discord.Intents.default()
        intents.message_content = True
        
        # 2. Menentukan prefix bot di sini (misal: "!")
        super().__init__(
            command_prefix="!", 
            intents=intents
        )

    async def setup_hook(self):
        # 1. Load semua fitur (Cog)
        await self.load_extension("cogs.Music")
        await self.load_extension("cogs.Random")
        await self.load_extension("cogs.Ollama38")
        await self.load_extension("cogs.Greeting")
        
        # 2. Cek posisi saklar
        if TESTING_MODE:
            # --- MODE TESTING ---
            print("🔧 Mode Testing Aktif: Sinkronisasi ke server lokal...")
            # Hapus command global sementara agar tidak double saat testing
            self.tree.clear_commands(guild=None)
            await self.tree.sync(guild=None)
            
            # Sync HANYA ke server testing (Muncul instan!)
            self.tree.copy_global_to(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
        else:
            # --- MODE GLOBAL (PUBLIK) ---
            print("🌍 Mode Global Aktif: Sinkronisasi ke semua server...")
            # Bersihkan sisa-sisa command testing di server lokalmu agar tidak double
            self.tree.clear_commands(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
            # Sync ke SELURUH SERVER (Bisa memakan waktu 1-60 menit dari sisi Discord)
            await self.tree.sync(guild=None)

bot = MyBot()

@bot.event
async def on_ready():
    print(f"{bot.user} is online and ready!")

@bot.tree.command(name="reload", description="Reloads cogs safely.")
async def reload(interaction: discord.Interaction):
    await interaction.response.defer()
    
    cogs_to_reload = ["cogs.Random", "cogs.Music", "cogs.Ollama38", "cogs.Greeting"]
    success_messages = []
    
    for cog in cogs_to_reload:
        try:
            # Try to reload if it's already loaded
            await bot.reload_extension(cog)
            success_messages.append(f"reloaded `{cog}`")
        except discord.ext.commands.ExtensionNotLoaded:
            # If it wasn't loaded yet, load it instead
            try:
                await bot.load_extension(cog)
                success_messages.append(f"loaded `{cog}` (was not active)")
            except Exception as e:
                success_messages.append(f"failed to load `{cog}`: {e}")
        except Exception as e:
            success_messages.append(f"error on `{cog}`: {e}")
            
    await interaction.followup.send(" | ".join(success_messages))

bot.run(TOKEN)