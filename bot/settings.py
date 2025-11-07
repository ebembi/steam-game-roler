import os
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (parent of bot/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Load .env file from project root
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
STEAM_API_KEY = os.getenv('STEAM_API_KEY')
GUILD_ID = int(os.getenv('GUILD_ID', '0'))
ADMIN_CHANNEL_ID = int(os.getenv('ADMIN_CHANNEL_ID', '0'))
TIMEZONE = os.getenv('TIMEZONE', 'Europe/London')

# thresholds
PLAYTIME_MINUTES = int(os.getenv('PLAYTIME_MINUTES', '60'))
MIN_PLAYERS = int(os.getenv('MIN_PLAYERS', '2'))
MAX_ROLES = int(os.getenv('MAX_ROLES', '10'))  # Maximum number of game roles to create during full scans

# prefix (used for text commands like !info)
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Admin role ID (set to 0 to disable, or provide the role ID)
ADMIN_ROLE_ID = int(os.getenv('ADMIN_ROLE_ID', '0'))

# Role settings
ROLE_SUFFIX = os.getenv('ROLE_SUFFIX', ' 🎮')  # Suffix added to all bot-created roles
if not ROLE_SUFFIX or not ROLE_SUFFIX.strip():
    raise ValueError("ROLE_SUFFIX must not be empty. Set a suffix like ' 🎮' to identify bot-created roles.")
ROLE_COLOR = int(os.getenv('ROLE_COLOR', '5865F2'), 16)  # Discord blurple color (hex)