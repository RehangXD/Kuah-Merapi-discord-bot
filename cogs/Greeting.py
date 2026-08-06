import random
import discord
from discord.ext import commands
from Config import MODULE_TOGGLES


class GreetingCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.module_name = "Greeting" 

    self.greeting_map = {
        "bot": ["apa bot", "bot", "APA",
        ],    
        "casual": [
            "Yoo! Selamat datang!",
            "Halo halo!",
            "Hai juga!",
            "Wah, ada pendatang baru!",
            "Eh, halo! Mau ngobrol apa nih?",
            "Halo bro, ada yang seru?",
            "Yoo, ada apa nih?",
            "Halo, gimana kabarmu?",
            "Hai, salam kenal ya!",
            "Eh halo, ada yang bisa dibantu?",
        ],
        "formal": [
            "Halo, ada yang perlu dibantu?",
            "Selamat datang di server!",
            "Ada yang bisa kubantu?",
            "Silakan nikmati server ini.",
            "Ada yang ingin ditanyakan?",
            "Halo, selamat bergabung!",
            "Selamat datang, silakan duduk!",
            "Halo, siap bantu hari ini.",
        ],
        "time_based_pagi": [
            "Halo, selamat pagi!",
            "Halo, selamat pagi semuanya.",
            "Hai, selamat pagi kawan.",
            "Halo, selamat beraktivitas!",
            "Eh halo, selamat pagi!",
        ],
        "time_based_siang": [
                    "Halo, selamat siang!",
                    "Halo, selamat siang semuanya.",
                    "Hai, selamat siang kawan.",
                    "Halo, selamat beraktivitas!",
                    "Eh halo, selamat siang!",
        ],
        "time_based_sore": [
                    "Halo, selamat sore!",
                    "Halo, selamat sore semuanya.",
                    "Hai, selamat sore kawan.",
                    "Halo, selamat beraktivitas!",
                    "Eh halo, selamat sore!",
        ],
        "time_based_malam": [
                    "Halo, selamat malam!",
                    "Halo, selamat malam semuanya.",
                    "Hai, selamat malam kawan.",
                    "Halo, selamat beraktivitas!",
                    "Eh halo, selamat malam!",
        ],
        "islamic": [
            "Waalaikumsalam warahmatullahi wabarakatuh! Selamat datang.",
            "Waalaikumsalam! Ada yang bisa dibantu?",
            "Waalaikumsalam kawan, mari bergabung.",
        ],
        "p": ["p", "P",
        ],
        "apa_kabar_mu": ["iya baik, bagaimana dengan mu?",
        ],
        "iya_baik_juga": ["alhamdullilah/syukurlah kalo begitu", 
        ],
        "info_kuah_merapi": ["info info", 
        ]

    }
    self.trigger_map = {
        "bot": ["bot", "Bot",
        ],
        "casual": ["halo kuah merapi", "hai kuah merapi", "yoo kuah merapi", "p kuah merapi", 
                   "halo kuah", "hai kuah", "yoo kuah", "p kuah", "halo bot", "hai bot", 
                   "yoo bot", "p bot", "yow bot", "yow kuah", "yow kuah merapi", 
                   "hey bot", "hey kuah", "hey kuah merapi",
        ],
        "formal": ["permisi kuah merapi", "bantuan kuah merapi", "info kuah merapi", "permisi kuah merapi", 
                   "bantuan kuah", "info kuah", "permisi bot", "bantuan bot", "info bot", 
        ],
        "time_based_pagi": ["selamat pagi kuah merapi", "selamat pagi kuah", "selamat pagi bot", "pagi kuah merapi", "pagi kuah", "pagi bot" 
        ],
        "time_based_siang": ["selamat siang kuah merapi", "selamat siang kuah", "selamat siang bot", "siang kuah merapi", "siang kuah", "siang bot",
        ],
        "time_based_sore": ["selamat sore kuah merapi", "selamat sore kuah", "selamat sore bot", "sore kuah merapi", "sore kuah", "sore bot",
        ],
        "time_based_malam": ["selamat malam kuah merapi", "selamat malam kuah", "selamat malam bot", "malam kuah merapi", "malam kuah", "malam bot"
        ],
        "islamic": ["assalamualaikum kuah merapi", "assalamu'alaikum kuah merapi", "assalamualaikum kuah", "assalamu'alaikum kuah", 
                    "assalamualaikum bot", "assalamu'alaikum bot", 
        ],
        "p": ["p", "P", 
        ],
        "apa_kabar_mu": ["apa kabar mu", "apa kabar bot",
                         "Apa kabar mu", 
        ],
        "iya_baik_juga": ["iya baik juga", "Iya baik juga", 
        ],
        "info_kuah_merapi": ["info kuah merapi", "Info kuah merapi", "INFO KUAH MERAPI", 
        ]

    }

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):
    if not MODULE_TOGGLES.get(self.module_name, True):
      return

    if message.author.bot:
      return

    content = message.content.strip()

    for category, triggers in self.trigger_map.items():
      if content in triggers:
        response = random.choice(self.greeting_map[category])
        await message.reply(response)
        break


async def setup(bot):
  await bot.add_cog(GreetingCog(bot))