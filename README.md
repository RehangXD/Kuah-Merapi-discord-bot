# [Kuah Merapi]

A multi-purpose Discord bot built with `discord.py` that handles music, and server utilities.

## Features
*   **Music:** Supports YouTube and Spotify links, queue management, looping (single/all), and playlist support.
        ![Image](https://github.com/user-attachments/assets/222840fa-b8a6-4bc8-b2db-3067ffbf34ff)

*   **Greetings:** Automated messages trigger for your server.
        ```![Image](https://github.com/user-attachments/assets/2e53e3bb-bf81-4a12-98aa-1578771afff2)```

*   **Utilities:** Random tools and module-based configuration (Toggle features on/off easily).

## Prerequisites
*   Python  3.10+
*   FFmpeg  (required for music playback)
*   yt_dlp  (required for fetch music ID in yt)
*   spotipy (required for fetch music in Spotify (required Premium Spotify to work))
*   PyNaCl  (required to function)

## Installation

1. Download the zip file in Code button above, or
   Clone the repository:
   ```bash
   git clone [https://github.com/RehangXD/basic-discord-bot.git](https://github.com/RehangXD/basic-discord-bot.git)
   cd basic-discord-bot

2. Virtual Environment Setup Instructions
    *   **Create the virtual environment**
        Execute the following command in the project's root directory to generate a folder named venv:
        
        *Bash*
        ```
        python -m venv venv #at the very end of this code(venv) is your folder name
        ```


    *   **Activate the virtual environment**
        The activation command depends on the operating system:

        **Windows (Command Prompt)**
        
        *DOS*
        ```
        venv\Scripts\activate.bat
        ```

        **Windows (PowerShell)**
        
        *PowerShell*
        ```
        venv\Scripts\Activate.ps1
        ```

        **macOS and Linux**
        
        *Bash*
        ```
        source venv/bin/activate
        ```


## Install dependencies

**Bash**
``` 
pip install -r requirements.txt
```

## Create or Edit a .env file in the root folder and add your credentials

*inside the .env file*  

DISCORD_TOKEN=your_token_here  
SPOTIPY_CLIENT_ID=your_id  
SPOTIPY_CLIENT_SECRET=your_secret  


## Run the bot

**Bash**
```
python main.py
```

## Configuration
You can toggle modules on or off by editing Config.py:

cogs.Music: True/False  
cogs.greeting: True/False  
etc...  


## Security Warning
Never share your DISCORD_TOKEN or .env file. If you accidentally push your token to GitHub, reset it immediately in the Discord Developer Portal.


## License
[e.g., MIT]
