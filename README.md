# Steam Discord Bot

A Discord bot that automatically creates roles based on Steam game ownership. Users can link their Steam accounts, and the bot will scan for multiplayer/cooperative games and assign roles accordingly.

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the bot
python main.py
```

## Features

- **Link Steam Accounts**: Users can link their Steam profile using `!link <steam_url_or_id>`
- **Automatic Role Creation**: Bot creates roles for games that meet the criteria
- **Smart Filtering**: Only creates roles for games that are:
  - Multiplayer or Cooperative
  - Played for at least 60 minutes (configurable)
  - Owned by at least 2 server members (configurable)
- **Owner Tracking**: Tracks how many users own each game
- **Top Games**: View most popular games with `!topgames` command
- **Scheduled Scans**:
  - **Full Scan**: Runs once per night (3 AM by default) to scan all linked users
  - **Daily Scan**: Runs once per day to check for new games
- **Blacklist System**: Prevent specific games from getting roles

## Setup

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Discord Bot Token
- Steam API Key

### Installation

1. Clone this repository

2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync
   ```

4. Create a `.env` file in the root directory (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` with your values:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   STEAM_API_KEY=your_steam_api_key_here
   GUILD_ID=your_guild_id_here
   ADMIN_CHANNEL_ID=your_admin_channel_id_here (optional)
   TIMEZONE=Europe/London (optional, default: Europe/London)
   PLAYTIME_MINUTES=60 (optional, default: 60)
   MIN_PLAYERS=2 (optional, default: 2)
   COMMAND_PREFIX=! (optional, default: !)
   ADMIN_ROLE_ID=0 (optional, set to role ID for admin restrictions)
   ```

5. Get your Discord Bot Token:
   - Go to https://discord.com/developers/applications
   - Create a new application or select an existing one
   - Go to the "Bot" section
   - Copy the token

6. Get your Steam API Key:
   - Go to https://steamcommunity.com/dev/apikey
   - Register for an API key

7. Get your Guild ID:
   - Enable Developer Mode in Discord
   - Right-click your server → Copy Server ID

### Bot Permissions

The bot needs the following permissions:
- Manage Roles
- Send Messages
- Read Message History

### Running the Bot

Make sure your virtual environment is activated, then:

```bash
python main.py
```

Or using uv directly:

```bash
uv run python main.py
```

## Commands

### User Commands

All users can use these commands:

- **`!info`** - Display available commands and bot information
- **`!link <steam_url_or_id>`** - Link your Steam account to your Discord profile
  - Examples:
    - `!link https://steamcommunity.com/id/yourname`
    - `!link https://steamcommunity.com/profiles/76561198012345678`
    - `!link 76561198012345678`

### Admin Commands

Server administrators have access to additional commands:

- **`!admininfo`** - Display all admin commands
- **`!ping`** - Check if the bot is operational (shows latency)
- **`!rescan`** - Manually trigger a full rescan of all linked users
- **`!topgames [limit]`** - Show the top N most common games by number of owners
  - Default limit: 10
  - Example: `!topgames 20`
- **`!linkfor @user <steam_url_or_id>`** - Link a Steam account for another user
  - Example: `!linkfor @JohnDoe https://steamcommunity.com/id/johndoe`
- **`!removegame <appid>`** - Remove a game from the database and delete its role
  - Example: `!removegame 730`
- **`!blacklist <appid>`** - Toggle blacklist status for a game
  - First use blacklists the game (prevents role creation)
  - Second use unblacklists the game
  - Example: `!blacklist 730`

## How It Works

1. **Initial Setup**: Users link their Steam accounts using the `!link` command
2. **Full Scan** (Nightly at 3 AM):
   - Scans all linked Steam accounts
   - Filters games by multiplayer/cooperative, playtime, and ownership
   - Creates roles for qualifying games
   - Assigns roles to users who own those games
3. **Daily Scan** (Once per day):
   - Checks for new games in linked libraries
   - Applies the same filters
   - Creates roles for new qualifying games
   - Assigns roles to users

## Data Storage

The bot uses SQLite to store:
- Discord user to Steam ID mappings
- User game libraries with playtime
- Game role mappings with owner counts
- Scan history
- Blacklisted games

Data is stored in `data/bot_data.db` and cached game metadata in `data/app_cache.json`.

## Configuration

All configuration is done through environment variables in the `.env` file:
- `PLAYTIME_MINUTES`: Minimum playtime required (default: 60)
- `MIN_PLAYERS`: Minimum number of server members who must own a game (default: 2)
- `TIMEZONE`: Timezone for scheduled scans (default: Europe/London)
- `COMMAND_PREFIX`: Command prefix for bot commands (default: !)

## Testing

Run the test suite to verify functionality:

```bash
pytest
```

See `tests/README.md` for more details on the test suite.

## Notes

- Steam profiles must be public for the bot to access game libraries
- The bot respects Steam API rate limits
- Roles are automatically created and assigned, but can be manually edited/deleted
- The bot tracks which games have roles to avoid duplicates
- Use `!topgames` to see which games are most popular among your server members
- Blacklisted games will not have roles created even if they meet all criteria

