import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from Config import MODULE_TOGGLES

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
MY_GUILD = discord.Object(id=#your server id)

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
        for module_name, is_enabled in MODULE_TOGGLES.items():
            if is_enabled:
                try:
                    await self.load_extension(module_name)
                    print(f"Loaded module: {module_name}")
                except Exception as e:
                    print(f"Failed to load {module_name}: {e}")
            else:
                print(f"Skipped module: {module_name} (Disabled)")
        
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
    
    success_messages = []
    
    for cog, is_enabled in MODULE_TOGGLES.items():
        if is_enabled:
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
        else:
            try:
                await bot.unload_extension(cog)
                success_messages.append(f"unloaded '{cog}': (disabled in config)")
            except discord.ext.commands.ExtensionNotLoaded:
                pass

    if not success_messages:
        success_messages.append(f"No config items processed.")
            
    await interaction.followup.send(" | ".join(success_messages))

if __name__ == "__main__":
    bot.run(TOKEN)
