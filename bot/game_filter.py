from typing import Dict, List, Set
from . import database
from . import store_api

async def filter_games(
    games_by_appid: Dict[int, List[int]],  # {appid: [discord_ids]}
    min_playtime: int = 60,
    min_players: int = 2,
    require_multiplayer: bool = True
) -> Dict[int, List[int]]:
    """
    Filter games based on criteria:
    - Multiplayer/Cooperative
    - Minimum playtime (60+ minutes)
    - Minimum players (2+ server members)
    
    Returns filtered {appid: [discord_ids]}
    """
    filtered = {}
    
    for appid, discord_ids in games_by_appid.items():
        # Check if blacklisted
        if database.db.is_blacklisted(appid):
            continue
        
        # Check minimum players
        if len(discord_ids) < min_players:
            continue
        
        # Check playtime for each owner
        valid_owners = []
        for discord_id in discord_ids:
            playtime = database.db.get_game_playtime(discord_id, appid)
            if playtime >= min_playtime:
                valid_owners.append(discord_id)
        
        # Need at least min_players with sufficient playtime
        if len(valid_owners) < min_players:
            continue
        
        # Check multiplayer/cooperative if required
        if require_multiplayer:
            meta = await store_api.get_app_meta(appid)
            categories = meta.get('categories', [])
            
            # Check for multiplayer or cooperative categories
            is_multiplayer = any(
                cat.lower() in ['multi-player', 'co-op', 'cooperative', 'online co-op', 'local co-op']
                for cat in categories
            )
            
            if not is_multiplayer:
                continue
        
        # All checks passed
        filtered[appid] = valid_owners
    
    return filtered

async def get_new_games_for_user(
    discord_id: int,
    existing_games: Set[int],
    min_playtime: int = 60
) -> Set[int]:
    """
    Get new games for a user that meet the playtime requirement.
    Returns set of appids that are new and have >= min_playtime.
    """
    user_games = database.db.get_user_games(discord_id)
    new_games = user_games - existing_games
    
    # Filter by playtime
    filtered = set()
    for appid in new_games:
        playtime = database.db.get_game_playtime(discord_id, appid)
        if playtime >= min_playtime:
            filtered.add(appid)
    
    return filtered

