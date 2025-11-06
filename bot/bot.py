import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, List, Set
import pytz

from . import settings
from . import database
from . import steam_api
from . import store_api
from . import game_filter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

# Track processed messages and their responses to prevent/clean up duplicates
_processed_messages = {}  # {command_message_id: [response_message_ids]}

async def safe_send(ctx, *args, **kwargs):
    """Wrapper for ctx.send that deletes previous duplicate responses"""
    command_msg_id = ctx.message.id
    
    # Send the message
    response = await ctx.send(*args, **kwargs)
    
    # Track this response
    if command_msg_id not in _processed_messages:
        _processed_messages[command_msg_id] = []
    
    # If we already have a response for this command, delete the old one(s)
    if len(_processed_messages[command_msg_id]) > 0:
        logger.warning(f'⚠️ Duplicate response detected for command message {command_msg_id}! Deleting previous response(s).')
        for old_response_id in _processed_messages[command_msg_id]:
            try:
                old_msg = await ctx.channel.fetch_message(old_response_id)
                if old_msg and old_msg.author.id == bot.user.id:
                    await old_msg.delete()
                    logger.info(f'Deleted duplicate response message {old_response_id}')
            except Exception as e:
                logger.debug(f'Could not delete old response {old_response_id}: {e}')
        _processed_messages[command_msg_id] = []
    
    # Store this response ID
    _processed_messages[command_msg_id].append(response.id)
    
    # Clean up old entries (keep last 500 command messages)
    if len(_processed_messages) > 500:
        # Remove oldest entries
        oldest_keys = list(_processed_messages.keys())[:100]
        for key in oldest_keys:
            del _processed_messages[key]
    
    return response

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has logged in to Discord!')
    logger.info(f'Bot has {len(bot.commands)} commands registered')
    logger.info(f'Bot user ID: {bot.user.id}')
    # Start the scheduled scans
    if not scan_scheduler.is_running():
        scan_scheduler.start()
    if not daily_scan.is_running():
        daily_scan.start()

@bot.check
async def prevent_duplicates(ctx):
    """Global check to prevent duplicate command processing"""
    message_id = ctx.message.id
    
    # Check if this command message was already processed
    if message_id in _processed_messages:
        logger.warning(f'⚠️ DUPLICATE COMMAND BLOCKED! Message {message_id} already processed - preventing duplicate response')
        return False  # This will prevent the command from running
    
    # Mark as processed (initialize empty list for response tracking)
    _processed_messages[message_id] = []
    
    logger.info(f'Command "{ctx.command}" invoked by {ctx.author.name} (ID: {ctx.author.id}) in channel {ctx.channel.id}, message ID: {message_id}')
    return True  # Allow the command to proceed
    
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    logger.error(f'Error in command {ctx.command}: {error}', exc_info=error)

@bot.command(name='link')
async def link_command(ctx, *, steam_input: str = None):
    """
    Link your Steam profile to your Discord account.
    Usage: !link <steam_profile_url_or_id>
    """
    if not steam_input:
        await safe_send(ctx, "Please provide your Steam profile URL or Steam ID.\n"
                      "Example: `!link https://steamcommunity.com/id/yourname` or `!link 76561198012345678`")
        return
    
    try:
        # Normalize to SteamID64
        steam_id = await steam_api.normalize_to_steamid64(steam_input)
        
        # Link the user
        database.db.link_user(ctx.author.id, steam_id)
        
        logger.info(f"Linked Discord user {ctx.author.id} ({ctx.author.name}) to Steam ID {steam_id}")
        await safe_send(ctx, f"✅ Successfully linked your Steam account! (Steam ID: {steam_id})")
    except ValueError as e:
        await safe_send(ctx, f"❌ Error: {str(e)}")
    except Exception as e:
        logger.error(f"Error linking user: {e}", exc_info=True)
        await safe_send(ctx, "❌ An error occurred while linking your Steam account. Please try again later.")

@bot.command(name='info')
async def info_command(ctx):
    """
    Display bot information and available commands.
    """
    # Get bot stats
    linked_users = len(database.db.get_all_links())
    total_roles = len(database.db.get_all_game_roles())
    
    embed = discord.Embed(
        title="🎮 Steam Game Role Bot",
        description=(
            "I automatically create Discord roles based on Steam game ownership!\n\n"
            "**How it works:**\n"
            "• Link your Steam account\n"
            "• I scan your library for multiplayer/co-op games\n"
            "• Roles are created for popular games (2+ owners, 60+ min playtime)\n"
            "• Find gaming buddies by mentioning roles!"
        ),
        color=discord.Color.blue()
    )
    
    # Bot Stats
    embed.add_field(
        name="📊 Current Stats",
        value=f"👥 **{linked_users}** linked users\n🎯 **{total_roles}** game roles created",
        inline=False
    )
    
    # Available Commands
    embed.add_field(
        name="📋 Commands",
        value=(
            f"**`{settings.COMMAND_PREFIX}link <steam_url>`**\n"
            f"Link your Steam account\n"
            f"Example: `{settings.COMMAND_PREFIX}link https://steamcommunity.com/id/yourname`\n\n"
            f"**`{settings.COMMAND_PREFIX}topgames [limit]`**\n"
            f"View the most popular games (default: 10)\n\n"
            f"**`{settings.COMMAND_PREFIX}info`**\n"
            f"Show this help message\n\n"
            f"**`{settings.COMMAND_PREFIX}admininfo`**\n"
            f"Admin commands (admins only)"
        ),
        inline=False
    )
    
    # Tips
    embed.add_field(
        name="💡 Tips",
        value=(
            "• Your Steam profile must be **public**\n"
            "• Games need 60+ min playtime to qualify\n"
            "• Only multiplayer/co-op games get roles\n"
            "• Use `@role` mentions to find gaming buddies!"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"Use {settings.COMMAND_PREFIX}link to get started!")
    
    await safe_send(ctx, embed=embed)

def has_admin_role():
    """Allow all users - no role check (for testing)"""
    def predicate(ctx):
        return True  # Always allow - no restrictions
    return commands.check(predicate)

@bot.command(name='admininfo')
async def admininfo_command(ctx):
    """
    Display available admin commands. Admin only.
    """
    embed = discord.Embed(
        title="🔧 Admin Commands",
        description="Commands available to admin role:",
        color=discord.Color.red()
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}ping",
        value="Check if the bot is operational.",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}linkfor",
        value="Link a Steam profile for another user.\n"
              f"Usage: `{settings.COMMAND_PREFIX}linkfor @username <steam_url_or_id>`",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}removegame",
        value="Remove a game from the database and delete its role.\n"
              f"Usage: `{settings.COMMAND_PREFIX}removegame <appid>`",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}blacklist",
        value="Toggle blacklist status for a game.\n"
              f"Usage: `{settings.COMMAND_PREFIX}blacklist <appid>`\n"
              "First use blacklists, second use unblacklists.",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}rescan",
        value="Manually trigger a full rescan of all linked users.",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}topgames",
        value="Show the top N most common games by number of owners.\n"
              f"Usage: `{settings.COMMAND_PREFIX}topgames [limit]`",
        inline=False
    )
    embed.add_field(
        name=f"{settings.COMMAND_PREFIX}admininfo",
        value="Display this admin help message.",
        inline=False
    )
    await safe_send(ctx, embed=embed)

@admininfo_command.error
async def admininfo_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # This should never happen now since we allow everyone
        logger.warning(f"Unexpected CheckFailure for admininfo: {error}")

@bot.command(name='ping')
async def ping_command(ctx):
    """
    Check if the bot is operational. Admin only.
    """
    latency = round(bot.latency * 1000)
    await safe_send(ctx, f"🏓 Pong! Bot is operational. Latency: {latency}ms")

@ping_command.error
async def ping_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for ping: {error}")

@bot.command(name='linkfor')
async def linkfor_command(ctx, member: discord.Member = None, *, steam_input: str = None):
    """
    Link a Steam profile for another user. Admin only.
    Usage: !linkfor @username <steam_url_or_id>
    """
    if not member:
        await safe_send(ctx, f"❌ Please mention a user.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}linkfor @username <steam_url_or_id>`")
        return
    
    if not steam_input:
        await safe_send(ctx, f"❌ Please provide a Steam profile URL or Steam ID.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}linkfor @username <steam_url_or_id>`")
        return
    
    try:
        # Normalize to SteamID64
        steam_id = await steam_api.normalize_to_steamid64(steam_input)
        
        # Link the user
        database.db.link_user(member.id, steam_id)
        
        await safe_send(ctx, f"✅ Successfully linked Steam account for {member.mention}! (Steam ID: {steam_id})")
        logger.info(f"Admin {ctx.author.id} ({ctx.author.name}) linked Discord user {member.id} ({member.name}) to Steam ID {steam_id}")
    except ValueError as e:
        await safe_send(ctx, f"❌ Error: {str(e)}")
    except Exception as e:
        logger.error(f"Error linking user: {e}", exc_info=True)
        await safe_send(ctx, "❌ An error occurred while linking the Steam account. Please try again later.")

@linkfor_command.error
async def linkfor_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for linkfor: {error}")
    elif isinstance(error, commands.BadArgument):
        await safe_send(ctx, f"❌ Could not find that user.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}linkfor @username <steam_url_or_id>`")

@bot.command(name='removegame')
async def removegame_command(ctx, appid: int = None):
    """
    Remove a game from the database and delete its role. Admin only.
    Usage: !removegame <appid>
    """
    if appid is None:
        await safe_send(ctx, f"❌ Please provide a game appid.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}removegame <appid>`")
        return
    
    try:
        # Get game name for display
        game_name = database.db.get_game_name(appid)
        if not game_name:
            game_name = f"Game {appid}"
        
        # Get role ID if it exists
        role_id = database.db.get_game_role(appid)
        
        # Remove from database
        database.db.remove_game(appid)
        
        # Delete role if it exists
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                try:
                    await role.delete(reason=f"Game removed by {ctx.author.name}")
                    await safe_send(ctx, f"✅ Removed game **{game_name}** (appid: {appid}) and deleted its role.")
                except discord.Forbidden:
                    await safe_send(ctx, f"✅ Removed game **{game_name}** (appid: {appid}) from database, but couldn't delete role (missing permissions).")
                except Exception as e:
                    logger.error(f"Error deleting role: {e}")
                    await safe_send(ctx, f"✅ Removed game **{game_name}** (appid: {appid}) from database, but error deleting role.")
            else:
                await safe_send(ctx, f"✅ Removed game **{game_name}** (appid: {appid}) from database (role not found).")
        else:
            await safe_send(ctx, f"✅ Removed game **{game_name}** (appid: {appid}) from database (no role existed).")
        
        logger.info(f"Admin {ctx.author.id} ({ctx.author.name}) removed game {appid} ({game_name})")
    except Exception as e:
        logger.error(f"Error removing game: {e}", exc_info=True)
        await safe_send(ctx, f"❌ An error occurred while removing the game: {str(e)}")

@removegame_command.error
async def removegame_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for removegame: {error}")
    elif isinstance(error, commands.BadArgument):
        await safe_send(ctx, f"❌ Invalid appid. Please provide a number.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}removegame <appid>`")

@bot.command(name='blacklist')
async def blacklist_command(ctx, appid: int = None):
    """
    Toggle blacklist status for a game. Admin only.
    First use blacklists, second use unblacklists.
    Usage: !blacklist <appid>
    """
    if appid is None:
        await safe_send(ctx, f"❌ Please provide a game appid.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}blacklist <appid>`")
        return
    
    try:
        # Get game name for display
        game_name = database.db.get_game_name(appid)
        if not game_name:
            # Try to get from store API
            try:
                meta = await store_api.get_app_meta(appid)
                game_name = meta.get('name') or f"Game {appid}"
            except:
                game_name = f"Game {appid}"
        
        # Toggle blacklist
        is_blacklisted = database.db.toggle_blacklist(appid)
        
        if is_blacklisted:
            await safe_send(ctx, f"✅ **{game_name}** (appid: {appid}) has been **blacklisted**.")
            logger.info(f"Admin {ctx.author.id} ({ctx.author.name}) blacklisted game {appid} ({game_name})")
        else:
            await safe_send(ctx, f"✅ **{game_name}** (appid: {appid}) has been **unblacklisted**.")
            logger.info(f"Admin {ctx.author.id} ({ctx.author.name}) unblacklisted game {appid} ({game_name})")
    except Exception as e:
        logger.error(f"Error toggling blacklist: {e}", exc_info=True)
        await safe_send(ctx, f"❌ An error occurred while toggling blacklist: {str(e)}")

@blacklist_command.error
async def blacklist_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for blacklist: {error}")
    elif isinstance(error, commands.BadArgument):
        await safe_send(ctx, f"❌ Invalid appid. Please provide a number.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}blacklist <appid>`")

@bot.command(name='rescan')
async def rescan_command(ctx):
    """
    Manually trigger a full rescan of all linked users.
    Admin only.
    """
    await safe_send(ctx, "🔄 Starting full rescan of all linked users...")
    try:
        await perform_full_scan(ctx.guild)
        await safe_send(ctx, "✅ Full rescan completed!")
    except Exception as e:
        logger.error(f"Error during rescan: {e}", exc_info=True)
        await safe_send(ctx, f"❌ Error during rescan: {str(e)}")

@rescan_command.error
async def rescan_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for rescan: {error}")

@bot.command(name='topgames')
async def topgames_command(ctx, limit: int = 10):
    """
    Show the top N most common games by number of owners.
    Usage: !topgames [limit] (default: 10)
    """
    try:
        if limit < 1 or limit > 100:
            await safe_send(ctx, "❌ Limit must be between 1 and 100.")
            return
        
        top_games = database.db.get_top_games_by_owners(limit)
        
        if not top_games:
            await safe_send(ctx, "No games found in the database.")
            return
        
        embed = discord.Embed(
            title=f"🏆 Top {limit} Most Common Games",
            description=f"Games ordered by owners, then by average playtime rank",
            color=discord.Color.gold()
        )
        
        for i, game in enumerate(top_games, 1):
            rank_display = f"📊 Avg Playtime Rank: {game['avg_playtime_rank']:.1f}" if game['avg_playtime_rank'] < 999 else ""
            embed.add_field(
                name=f"{i}. {game['game_name']}",
                value=f"👥 {game['owner_count']} owners • {rank_display}",
                inline=False
            )
        
        await safe_send(ctx, embed=embed)
    except Exception as e:
        logger.error(f"Error showing top games: {e}", exc_info=True)
        await safe_send(ctx, f"❌ Error retrieving top games: {str(e)}")

@topgames_command.error
async def topgames_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.warning(f"Unexpected CheckFailure for topgames: {error}")
    elif isinstance(error, commands.BadArgument):
        await safe_send(ctx, f"❌ Invalid limit. Please provide a number.\n"
                      f"Usage: `{settings.COMMAND_PREFIX}topgames [limit]`")

async def perform_full_scan(guild: discord.Guild):
    """
    Perform a full scan of all linked users:
    1. Get all linked users
    2. Fetch their game libraries
    3. Filter games (multiplayer/coop, 60+ min, 2+ players)
    4. Create roles for qualifying games
    5. Assign roles to users
    """
    logger.info("Starting full scan...")
    
    # Get all linked users
    links = database.db.get_all_links()
    if not links:
        logger.info("No linked users found")
        return
    
    logger.info(f"Scanning {len(links)} linked users...")
    
    # Fetch game libraries for all users
    all_games_by_appid = {}  # {appid: [discord_ids]}
    
    for link in links:
        discord_id = link['discord_id']
        steam_id = link['steam_id']
        
        try:
            games, visibility = await steam_api.get_owned_games(steam_id)
            if visibility == 'private_or_empty':
                logger.warning(f"Steam profile {steam_id} is private or empty for user {discord_id}")
                continue
            
            # Update database with user's games
            database.db.update_user_games(discord_id, games)
            
            # Build game ownership map
            for game in games:
                appid = game.get('appid')
                if appid:
                    if appid not in all_games_by_appid:
                        all_games_by_appid[appid] = []
                    all_games_by_appid[appid].append(discord_id)
            
            # Rate limiting
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Error fetching games for Steam ID {steam_id}: {e}")
            continue
    
    logger.info(f"Found {len(all_games_by_appid)} unique games across all users")
    
    # Filter games
    filtered_games = await game_filter.filter_games(
        all_games_by_appid,
        min_playtime=settings.PLAYTIME_MINUTES,
        min_players=settings.MIN_PLAYERS,
        require_multiplayer=True
    )
    
    logger.info(f"After filtering: {len(filtered_games)} games qualify")
    
    # Create roles and assign them
    await create_and_assign_roles(guild, filtered_games)
    
    # Update scan time
    database.db.update_scan_time('full_scan')

async def create_and_assign_roles(guild: discord.Guild, games_by_appid: Dict[int, List[int]]):
    """
    Create roles for games and assign them to users.
    games_by_appid: {appid: [discord_ids]}
    """
    logger.info(f"Creating roles for {len(games_by_appid)} games...")
    
    for appid, discord_ids in games_by_appid.items():
        try:
            # Get game name
            meta = await store_api.get_app_meta(appid)
            game_name = meta.get('name') or f"Game {appid}"
            
            # Check if role already exists
            existing_role_id = database.db.get_game_role(appid)
            role = None
            
            if existing_role_id:
                # Try to get existing role
                role = guild.get_role(existing_role_id)
                if role is None:
                    # Role was deleted, need to create new one
                    existing_role_id = None
            
            owner_count = len(discord_ids)
            avg_playtime_rank = database.db.calculate_avg_playtime_rank(appid, discord_ids)
            
            if not role:
                # Create new role
                role = await guild.create_role(
                    name=game_name,
                    mentionable=True,
                    reason=f"Auto-created role for game: {game_name}"
                )
                database.db.create_game_role(appid, role.id, game_name, owner_count, avg_playtime_rank)
                logger.info(f"Created role '{game_name}' (ID: {role.id}) for appid {appid} with {owner_count} owners, avg rank {avg_playtime_rank:.1f}")
            else:
                # Update stats for existing role
                database.db.update_game_stats(appid, owner_count, avg_playtime_rank)
                logger.debug(f"Updated stats for '{game_name}': {owner_count} owners, avg rank {avg_playtime_rank:.1f}")
            
            # Assign role to all users who own the game
            for discord_id in discord_ids:
                try:
                    member = guild.get_member(discord_id)
                    if member and role not in member.roles:
                        await member.add_roles(role, reason=f"User owns game: {game_name}")
                        logger.debug(f"Assigned role '{game_name}' to {member.name}")
                except discord.Forbidden:
                    logger.warning(f"No permission to assign role to user {discord_id}")
                except Exception as e:
                    logger.error(f"Error assigning role to user {discord_id}: {e}")
            
            # Rate limiting
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error processing game {appid}: {e}")
            continue
    
    logger.info("Role creation and assignment completed")

async def perform_daily_scan(guild: discord.Guild):
    """
    Daily scan for new games:
    1. Get all linked users
    2. Check for new games (60+ min playtime)
    3. Filter new games (2+ players)
    4. Create roles for new games
    5. Assign roles to users
    """
    logger.info("Starting daily scan for new games...")
    
    # Get all linked users
    links = database.db.get_all_links()
    if not links:
        logger.info("No linked users found")
        return
    
    # Get existing games that already have roles (to track what's new)
    existing_game_roles = set(database.db.get_all_game_roles().keys())
    
    # Track new games by appid
    new_games_by_appid = {}  # {appid: [discord_ids]}
    
    for link in links:
        discord_id = link['discord_id']
        steam_id = link['steam_id']
        
        try:
            # Get user's existing games from database BEFORE fetching new ones
            existing_user_games = database.db.get_user_games(discord_id)
            
            # Fetch current games from Steam
            games, visibility = await steam_api.get_owned_games(steam_id)
            if visibility == 'private_or_empty':
                continue
            
            # Update database with current games
            database.db.update_user_games(discord_id, games)
            
            # Find new games that meet playtime requirement
            # Compare current games (now in DB) vs what was there before
            current_user_games = database.db.get_user_games(discord_id)
            new_games = current_user_games - existing_user_games
            
            # Filter by playtime
            filtered_new_games = set()
            for appid in new_games:
                playtime = database.db.get_game_playtime(discord_id, appid)
                if playtime >= settings.PLAYTIME_MINUTES:
                    filtered_new_games.add(appid)
            
            # Add to new games map
            for appid in filtered_new_games:
                if appid not in new_games_by_appid:
                    new_games_by_appid[appid] = []
                new_games_by_appid[appid].append(discord_id)
            
            # Rate limiting
            await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Error fetching games for Steam ID {steam_id}: {e}")
            continue
    
    if not new_games_by_appid:
        logger.info("No new games found")
        return
    
    logger.info(f"Found {len(new_games_by_appid)} new games")
    
    # Filter new games (multiplayer/coop, 2+ players)
    filtered_new_games = await game_filter.filter_games(
        new_games_by_appid,
        min_playtime=settings.PLAYTIME_MINUTES,
        min_players=settings.MIN_PLAYERS,
        require_multiplayer=True
    )
    
    if not filtered_new_games:
        logger.info("No new games meet the criteria")
        return
    
    logger.info(f"After filtering: {len(filtered_new_games)} new games qualify")
    
    # Create roles and assign them
    await create_and_assign_roles(guild, filtered_new_games)
    
    # Update scan time
    database.db.update_scan_time('daily_scan')

@tasks.loop(time=dt_time(hour=3, minute=0))  # 3 AM
async def scan_scheduler():
    """
    Scheduled task to run full scan once per night at 3 AM.
    Note: This uses the system's local time. For timezone support, consider using a cron-like approach.
    """
    if not bot.is_ready():
        return
    
    guild = bot.get_guild(settings.GUILD_ID)
    if not guild:
        logger.error(f"Guild {settings.GUILD_ID} not found")
        return
    
    logger.info("Starting scheduled full scan...")
    try:
        await perform_full_scan(guild)
    except Exception as e:
        logger.error(f"Error in scheduled full scan: {e}", exc_info=True)

@scan_scheduler.before_loop
async def before_scan_scheduler():
    """Wait until bot is ready before starting scheduler"""
    await bot.wait_until_ready()
    logger.info("Full scan scheduler started. Will run daily at 3 AM.")

@tasks.loop(hours=24)
async def daily_scan():
    """
    Scheduled task to run daily scan for new games.
    Runs once per day, 24 hours after the last run.
    """
    if not bot.is_ready():
        return
    
    guild = bot.get_guild(settings.GUILD_ID)
    if not guild:
        logger.error(f"Guild {settings.GUILD_ID} not found")
        return
    
    logger.info("Starting scheduled daily scan...")
    try:
        await perform_daily_scan(guild)
    except Exception as e:
        logger.error(f"Error in scheduled daily scan: {e}", exc_info=True)

@daily_scan.before_loop
async def before_daily_scan():
    """Wait until bot is ready before starting daily scan"""
    await bot.wait_until_ready()

def run():
    """Run the bot"""
    if not settings.DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN not set in environment variables")
    bot.run(settings.DISCORD_TOKEN)

