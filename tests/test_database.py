"""Test database operations"""

import pytest


def test_user_linking(temp_db):
    """Test linking Discord users to Steam accounts"""
    # Link a user
    temp_db.link_user(123456, "76561198012345678")

    # Verify link
    steam_id = temp_db.get_steam_id(123456)
    assert steam_id == "76561198012345678"


def test_user_game_storage(temp_db, mock_steam_games):
    """Test storing and retrieving user games"""
    discord_id = 123456

    # Link user first
    temp_db.link_user(discord_id, "76561198012345678")

    # Store games
    temp_db.update_user_games(discord_id, mock_steam_games)

    # Retrieve games
    games = temp_db.get_user_games(discord_id)
    assert 730 in games
    assert 570 in games
    assert len(games) == 4


def test_game_playtime(temp_db, mock_steam_games):
    """Test playtime tracking"""
    discord_id = 123456
    temp_db.link_user(discord_id, "76561198012345678")
    temp_db.update_user_games(discord_id, mock_steam_games)

    # Check playtime
    playtime = temp_db.get_game_playtime(discord_id, 730)
    assert playtime == 120


def test_game_role_creation(temp_db):
    """Test creating and retrieving game roles"""
    appid = 730
    role_id = 999888777
    game_name = "Counter-Strike 2"
    owner_count = 5

    # Create role
    temp_db.create_game_role(appid, role_id, game_name, owner_count)

    # Verify role
    retrieved_role_id = temp_db.get_game_role(appid)
    assert retrieved_role_id == role_id

    # Verify game name
    retrieved_name = temp_db.get_game_name(appid)
    assert retrieved_name == game_name

    # Verify owner count
    retrieved_count = temp_db.get_game_owner_count(appid)
    assert retrieved_count == owner_count


def test_owner_count_updates(temp_db):
    """Test updating owner counts"""
    appid = 730
    temp_db.create_game_role(appid, 123456, "CS2", 5)

    # Update count
    temp_db.update_game_owner_count(appid, 10)

    # Verify update
    count = temp_db.get_game_owner_count(appid)
    assert count == 10


def test_top_games_ordering(temp_db):
    """Test getting top games by owner count"""
    # Create multiple games with different owner counts
    temp_db.create_game_role(730, 111, "CS2", 10)
    temp_db.create_game_role(570, 222, "Dota 2", 8)
    temp_db.create_game_role(440, 333, "TF2", 15)
    temp_db.create_game_role(620, 444, "Portal 2", 5)

    # Get top 3
    top_games = temp_db.get_top_games_by_owners(3)

    # Verify ordering (highest first)
    assert len(top_games) == 3
    assert top_games[0]["appid"] == 440  # TF2 with 15 owners
    assert top_games[1]["appid"] == 730  # CS2 with 10 owners
    assert top_games[2]["appid"] == 570  # Dota 2 with 8 owners


def test_blacklist_toggle(temp_db):
    """Test blacklisting games"""
    appid = 730

    # Blacklist
    is_blacklisted = temp_db.toggle_blacklist(appid)
    assert is_blacklisted is True
    assert temp_db.is_blacklisted(appid) is True

    # Unblacklist
    is_blacklisted = temp_db.toggle_blacklist(appid)
    assert is_blacklisted is False
    assert temp_db.is_blacklisted(appid) is False


def test_game_removal(temp_db, mock_steam_games):
    """Test removing games from database"""
    discord_id = 123456
    appid = 730

    # Setup
    temp_db.link_user(discord_id, "76561198012345678")
    temp_db.update_user_games(discord_id, mock_steam_games)
    temp_db.create_game_role(appid, 999, "CS2", 1)

    # Remove game
    temp_db.remove_game(appid)

    # Verify removal
    assert temp_db.get_game_role(appid) is None
    assert temp_db.get_game_name(appid) is None


def test_multiple_users_same_game(temp_db, mock_steam_games):
    """Test multiple users owning the same game"""
    user1 = 111111
    user2 = 222222

    # Link users
    temp_db.link_user(user1, "76561198000000001")
    temp_db.link_user(user2, "76561198000000002")

    # Both users have the same games
    temp_db.update_user_games(user1, mock_steam_games)
    temp_db.update_user_games(user2, mock_steam_games)

    # Get game owners
    owners = temp_db.get_game_owners(730)
    assert user1 in owners
    assert user2 in owners
    assert len(owners) == 2


def test_scan_history(temp_db):
    """Test scan history tracking"""
    # Update scan time
    temp_db.update_scan_time("full_scan")

    # Retrieve scan time
    last_scan = temp_db.get_last_scan_time("full_scan")
    assert last_scan is not None
