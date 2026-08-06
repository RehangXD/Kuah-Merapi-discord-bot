# [Kuah Merapi]

A multi-purpose Discord bot built with `discord.py` that handles music, and server utilities.

## Features
*   **Music:** Supports YouTube and Spotify links, queue management, looping (single/all), and playlist support.
*   **Greetings:** Automated messages trigger for your server.
*   **Utilities:** Random tools and module-based configuration (Toggle features on/off easily).

## Prerequisites
*   Python  3.10+
*   FFmpeg  (required for music playback)
*   yt_dlp  (required for fetch music ID in yt)
*   spotipy (required for fetch music in Spotify (required Premium Spotify to work))
*   PyNaCl  (required to function)

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/RehangXD/basic-discord-bot.git](https://github.com/RehangXD/basic-discord-bot.git)
   cd basic-discord-bot




## Install dependencies

**Bash**  
pip install -r requirements.txt


## Create a .env file in the root folder and add your credentials

*inside the .env file*  

DISCORD_TOKEN=your_token_here  
SPOTIPY_CLIENT_ID=your_id  
SPOTIPY_CLIENT_SECRET=your_secret  


## Run the bot

**Bash**  
python main.py


## Configuration
You can toggle modules on or off by editing Config.py:

cogs.Music: True/False  
cogs.greeting: True/False  
etc...  


## Security Warning
Never share your DISCORD_TOKEN or .env file. If you accidentally push your token to GitHub, reset it immediately in the Discord Developer Portal.


## License
[e.g., MIT]
