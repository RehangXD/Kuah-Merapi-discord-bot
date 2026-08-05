import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import json
from Config import MODULE_TOGGLES

class OllamaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "http://localhost:11434/api/generate"
        self.model_name = "qwen3"
        self.module_name = "Ollama38"

    @commands.hybrid_command(name="ask", description="Send a prompt to the local AI model.")
    @app_commands.describe(prompt="The question or statement for the AI.")
    async def ask(self, ctx: commands.Context, prompt: str):
        await ctx.defer()
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 1024 
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        answer = data.get("response", "No response generated.")
                        
                        if len(answer) > 1999:
                            answer = answer[:1996] + "..."
                            
                        await ctx.send(answer)
                    else:
                        await ctx.send(f"API Error: HTTP {response.status}")
            except Exception as e:
                await ctx.send(f"Connection failed: {e}")

    @commands.hybrid_command(name="stop_ai", description="Unload the AI model from RAM.")
    async def stop_ai(self, ctx: commands.Context):
        await ctx.defer()
        
        payload = {
            "model": self.model_name,
            "keep_alive": 0
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        await ctx.send("Model unloaded from system memory.")
                    else:
                        await ctx.send(f"API Error: HTTP {response.status}")
            except Exception as e:
                await ctx.send(f"Connection failed: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not MODULE_TOGGLES.get(self.module_name, True):
            return

async def setup(bot):
    await bot.add_cog(OllamaCog(bot))