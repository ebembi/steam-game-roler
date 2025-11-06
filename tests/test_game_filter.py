"""Test game filtering logic"""
import pytest
from bot import game_filter, database
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_filter_by_minimum_players(temp_db):
    """Test filtering games by minimum player count"""
    # Setup users and games
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    temp_db.link_user(333, "76561198000000003")
    
    temp_db.update_user_games(111, [{'appid': 730, 'playtime_forever': 100}])
    temp_db.update_user_games(222, [{'appid': 730, 'playtime_forever': 100}])
    temp_db.update_user_games(333, [{'appid': 570, 'playtime_forever': 100}])
    
    games_by_appid = {
        730: [111, 222],  # 2 players
        570: [333],       # 1 player
    }
    
    # Mock store API to skip multiplayer check and use temp_db
    with patch('bot.game_filter.store_api.get_app_meta', new_callable=AsyncMock), \
         patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=2,
            require_multiplayer=False
        )
    
    # Should only include game with 2+ players
    assert 730 in filtered
    assert 570 not in filtered


@pytest.mark.asyncio
async def test_filter_by_playtime(temp_db):
    """Test filtering games by minimum playtime"""
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    
    # User 1 has good playtime, User 2 has low playtime
    temp_db.update_user_games(111, [{'appid': 730, 'playtime_forever': 100}])
    temp_db.update_user_games(222, [{'appid': 730, 'playtime_forever': 30}])
    
    games_by_appid = {730: [111, 222]}
    
    with patch('bot.game_filter.store_api.get_app_meta', new_callable=AsyncMock), \
         patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=1,  # Only need 1 player with good playtime
            require_multiplayer=False
        )
    
    # Should be included, but only user 111
    assert 730 in filtered
    assert 111 in filtered[730]
    assert 222 not in filtered[730]


@pytest.mark.asyncio
async def test_filter_blacklisted_games(temp_db):
    """Test that blacklisted games are filtered out"""
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    
    temp_db.update_user_games(111, [{'appid': 730, 'playtime_forever': 100}])
    temp_db.update_user_games(222, [{'appid': 730, 'playtime_forever': 100}])
    
    # Blacklist the game
    temp_db.toggle_blacklist(730)
    
    games_by_appid = {730: [111, 222]}
    
    with patch('bot.game_filter.store_api.get_app_meta', new_callable=AsyncMock), \
         patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=2,
            require_multiplayer=False
        )
    
    # Should be filtered out due to blacklist
    assert 730 not in filtered


@pytest.mark.asyncio
async def test_filter_by_multiplayer(temp_db):
    """Test filtering games by multiplayer category"""
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    
    temp_db.update_user_games(111, [
        {'appid': 730, 'playtime_forever': 100},  # Multiplayer
        {'appid': 999, 'playtime_forever': 100},  # Single-player
    ])
    temp_db.update_user_games(222, [
        {'appid': 730, 'playtime_forever': 100},
        {'appid': 999, 'playtime_forever': 100},
    ])
    
    games_by_appid = {
        730: [111, 222],
        999: [111, 222],
    }
    
    # Mock multiplayer/single-player metadata
    async def mock_get_app_meta(appid):
        if appid == 730:
            return {'name': 'CS2', 'categories': ['Multi-player']}
        else:
            return {'name': 'Single Game', 'categories': ['Single-player']}
    
    with patch('bot.game_filter.store_api.get_app_meta', side_effect=mock_get_app_meta), \
         patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=2,
            require_multiplayer=True
        )
    
    # Should only include multiplayer game
    assert 730 in filtered
    assert 999 not in filtered


@pytest.mark.asyncio
async def test_filter_cooperative_games(temp_db):
    """Test that co-op games are included"""
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    
    temp_db.update_user_games(111, [{'appid': 620, 'playtime_forever': 100}])
    temp_db.update_user_games(222, [{'appid': 620, 'playtime_forever': 100}])
    
    games_by_appid = {620: [111, 222]}
    
    # Mock co-op metadata
    async def mock_get_app_meta(appid):
        return {'name': 'Portal 2', 'categories': ['Co-op', 'Online Co-op']}
    
    with patch('bot.game_filter.store_api.get_app_meta', side_effect=mock_get_app_meta), \
         patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=2,
            require_multiplayer=True
        )
    
    # Co-op games should be included
    assert 620 in filtered


@pytest.mark.asyncio
async def test_no_multiplayer_requirement(temp_db):
    """Test filtering without multiplayer requirement"""
    temp_db.link_user(111, "76561198000000001")
    temp_db.link_user(222, "76561198000000002")
    
    temp_db.update_user_games(111, [{'appid': 999, 'playtime_forever': 100}])
    temp_db.update_user_games(222, [{'appid': 999, 'playtime_forever': 100}])
    
    games_by_appid = {999: [111, 222]}
    
    # Don't require multiplayer
    with patch('bot.game_filter.database.db', temp_db):
        filtered = await game_filter.filter_games(
            games_by_appid,
            min_playtime=60,
            min_players=2,
            require_multiplayer=False
        )
    
    # Should be included even if not multiplayer
    assert 999 in filtered

