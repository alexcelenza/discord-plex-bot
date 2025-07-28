# Discord Plex Bot

A Discord Plex bot that allows users to check if a movie currently exists in your Plex Server. If the movie does not exist, the user can then request that movie. The bot uses slash commands for interaction and can notify the Plex owner when a request is made.

## Project Structure
```plaintext
discord-plex-bot/
├── .github/
│   └── workflows/
│       └── python-app.yml
├── bot.py
├── plex_utils.py
├── .env
├── requirements.txt
└── README.md
```

## Features
- `/query <movie_name>` - Check if a movie exists in your Plex library.
- `/request <movie_name>` - Request a movie to be added or sent to the user (if they dont have Plex access). If multiple matches are found in the Plex server, button selection is used for the requestor to specify which movie they would like.
- Admin gets notified of requests via a direct message.

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/alexcelenza/discord-plex-bot.git
cd discord-plex-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a .env file
Create a .env file in the root directory with the following:

```env
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_discord_guild_id
USER_ID=your_discord_user_id_for_notifications
PLEX_URL=http://your.plex.server:32400
PLEX_TOKEN=your_plex_api_token
```

### 4. Run the bot
```bash
python bot.py
```