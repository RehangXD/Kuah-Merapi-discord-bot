import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MY_GUILD = discord.Object(id=#Your server id)

# SWITCH MODE TESTING:
# Change into True if you wanna edit your new feature (just change in test server).
# Change into False if the bot is ready to use for all other people in other server (Globally apply).
TESTING_MODE = False

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents
        )

    async def setup_hook(self):
        await self.load_extension("cogs.Music")
        await self.load_extension("cogs.Random")
        await self.load_extension("cogs.Ollama38")
        await self.load_extension("cogs.Greeting")
        
        if TESTING_MODE:
            print("🔧 Testing Mode Active: Synchronization Into Test Server...")
            self.tree.clear_commands(guild=None)
            await self.tree.sync(guild=None)

            self.tree.copy_global_to(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
        else:

            print("🌍 Global Mode Active: Synchronization Into Global Server...")
            self.tree.clear_commands(guild=MY_GUILD)
            await self.tree.sync(guild=MY_GUILD)
            
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
            await bot.reload_extension(cog)
            success_messages.append(f"reloaded `{cog}`")
        except discord.ext.commands.ExtensionNotLoaded:
            try:
                await bot.load_extension(cog)
                success_messages.append(f"loaded `{cog}` (was not active)")
            except Exception as e:
                success_messages.append(f"failed to load `{cog}`: {e}")
        except Exception as e:
            success_messages.append(f"error on `{cog}`: {e}")
            
    await interaction.followup.send(" | ".join(success_messages))

bot.run(TOKEN)
