import discord
from discord.ext import commands
from discord import Interaction, app_commands
import random
from Config import MODULE_TOGGLES

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.module_name = "Random"

    @commands.hybrid_command(name="hello", description="Greet the bot and get a random reply.")
    @app_commands.describe(member="Choose someone to greet (optional)")
    async def hello(self, ctx: commands.Context, member: discord.Member = None):
        
        target = member if member else ctx.author
        
            # List of phrases incorporating the mention ({target.mention})
        list_text = [
                f"hy mbot {target.mention}",
                f"hei kikir!",
                f"Yoo! Selamat datang!",
                f"{target.mention} Kuah mas",
                f"Wah ada sepuh {target.mention}, gimana puh",
                f"aku pergi"
        ]
        
        random_answer = random.choice(list_text)
        
        await ctx.send(random_answer)

        @commands.Cog.listener()
        async def on_message(self, message):
            if not MODULE_TOGGLES.get(self.module_name, True):
                return
            if message.author.bot:
                return


# This function is needed for main.py to know how to reload this files
async def setup(bot):
    await bot.add_cog(GeneralCog(bot))