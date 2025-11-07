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


def test_avg_playtime_rank_calculation(temp_db):
    """Test calculating average playtime rank for a game"""
    # Setup users with different playtime patterns
    user1 = 111111
    user2 = 222222
    user3 = 333333

    temp_db.link_user(user1, "76561198000000001")
    temp_db.link_user(user2, "76561198000000002")
    temp_db.link_user(user3, "76561198000000003")

    # User 1: CS2 is #1 (highest playtime)
    temp_db.update_user_games(
        user1,
        [
            {"appid": 730, "playtime_forever": 200},  # Rank 1
            {"appid": 570, "playtime_forever": 150},  # Rank 2
            {"appid": 440, "playtime_forever": 100},  # Rank 3
        ],
    )

    # User 2: CS2 is #2
    temp_db.update_user_games(
        user2,
        [
            {"appid": 570, "playtime_forever": 300},  # Rank 1
            {"appid": 730, "playtime_forever": 200},  # Rank 2
            {"appid": 440, "playtime_forever": 50},  # Rank 3
        ],
    )

    # User 3: CS2 is #3
    temp_db.update_user_games(
        user3,
        [
            {"appid": 570, "playtime_forever": 400},  # Rank 1
            {"appid": 440, "playtime_forever": 250},  # Rank 2
            {"appid": 730, "playtime_forever": 100},  # Rank 3
        ],
    )

    # Calculate avg rank for CS2 (730): (1 + 2 + 3) / 3 = 2.0
    avg_rank = temp_db.calculate_avg_playtime_rank(730, [user1, user2, user3])
    assert avg_rank == 2.0

    # Calculate avg rank for Dota (570): (2 + 1 + 1) / 3 = 1.33...
    avg_rank = temp_db.calculate_avg_playtime_rank(570, [user1, user2, user3])
    assert abs(avg_rank - 1.333) < 0.01


def test_game_role_with_avg_rank(temp_db):
    """Test creating and retrieving games with different avg playtime ranks"""
    # Create multiple games with different ranks
    temp_db.create_game_role(730, 111, "CS2", 5, 2.5)
    temp_db.create_game_role(570, 222, "Dota 2", 5, 1.0)
    temp_db.create_game_role(440, 333, "TF2", 5, 10.0)

    # Get top games - should be sorted by rank
    top_games = temp_db.get_top_games_by_owners()
    
    # Verify behavior: lower rank comes first when owner counts are equal
    assert top_games[0]["appid"] == 570  # Dota with rank 1.0
    assert top_games[1]["appid"] == 730  # CS2 with rank 2.5
    assert top_games[2]["appid"] == 440  # TF2 with rank 10.0


def test_update_game_stats(temp_db):
    """Test that updating stats changes top games ordering"""
    # Create games with initial stats
    temp_db.create_game_role(730, 123, "CS2", 5, 10.0)
    temp_db.create_game_role(570, 456, "Dota 2", 5, 5.0)

    # Initially Dota should rank higher (better rank)
    top_games = temp_db.get_top_games_by_owners(2)
    assert top_games[0]["appid"] == 570

    # Update CS2 to have better rank
    temp_db.update_game_stats(730, 5, 1.0)

    # Now CS2 should rank higher
    top_games = temp_db.get_top_games_by_owners(2)
    assert top_games[0]["appid"] == 730


def test_top_games_sorted_by_avg_rank(temp_db):
    """Test that games with same owner count are sorted by avg playtime rank"""
    # Create games with same owner count but different avg ranks
    temp_db.create_game_role(730, 111, "CS2", 5, 2.0)  # Good rank
    temp_db.create_game_role(570, 222, "Dota 2", 5, 5.0)  # Worse rank
    temp_db.create_game_role(440, 333, "TF2", 5, 1.5)  # Best rank
    temp_db.create_game_role(620, 444, "Portal 2", 3, 1.0)  # Fewer owners

    # Get top games
    top_games = temp_db.get_top_games_by_owners(10)

    # Should be sorted by owner_count DESC, then avg_playtime_rank ASC
    # So: 5 owners (TF2 rank 1.5, CS2 rank 2.0, Dota rank 5.0), then 3 owners (Portal 2)
    assert top_games[0]["appid"] == 440  # TF2 with rank 1.5
    assert top_games[1]["appid"] == 730  # CS2 with rank 2.0
    assert top_games[2]["appid"] == 570  # Dota with rank 5.0
    assert top_games[3]["appid"] == 620  # Portal 2 with 3 owners


def test_avg_rank_empty_owners(temp_db):
    """Test calculating avg rank with no owners returns high value"""
    avg_rank = temp_db.calculate_avg_playtime_rank(999, [])
    assert avg_rank == 999.0


def test_cleanup_removes_all_games(temp_db):
    """Test that cleanup operation removes all game data"""
    # Create multiple games
    temp_db.create_game_role(730, 111, "CS2", 5, 2.0)
    temp_db.create_game_role(570, 222, "Dota 2", 5, 1.0)
    temp_db.create_game_role(440, 333, "TF2", 3, 3.0)

    # Link users and add game ownership
    temp_db.link_user(111111, "76561198000000001")
    temp_db.update_user_games(111111, [{"appid": 730, "playtime_forever": 100}])

    # Verify games exist
    all_roles = temp_db.get_all_game_roles()
    assert len(all_roles) == 3

    # Cleanup: remove all games
    for appid in [730, 570, 440]:
        temp_db.remove_game(appid)

    # Verify all games removed
    all_roles_after = temp_db.get_all_game_roles()
    assert len(all_roles_after) == 0

    # Verify user link still exists (not affected by cleanup)
    steam_id = temp_db.get_steam_id(111111)
    assert steam_id == "76561198000000001"


def test_cleanup_handles_partial_removal(temp_db):
    """Test that cleanup can selectively remove games"""
    # Create multiple games
    temp_db.create_game_role(730, 111, "CS2", 5, 2.0)
    temp_db.create_game_role(570, 222, "Dota 2", 5, 1.0)
    temp_db.create_game_role(440, 333, "TF2", 3, 3.0)

    # Remove only one game
    temp_db.remove_game(730)

    # Verify only CS2 removed
    all_roles = temp_db.get_all_game_roles()
    assert len(all_roles) == 2
    assert 730 not in all_roles
    assert 570 in all_roles
    assert 440 in all_roles


def test_get_all_game_roles_returns_mapping(temp_db):
    """Test getting all game roles returns correct appid to role_id mapping"""
    # Create games
    temp_db.create_game_role(730, 111, "CS2", 5, 2.0)
    temp_db.create_game_role(570, 222, "Dota 2", 3, 1.5)

    # Get all roles
    all_roles = temp_db.get_all_game_roles()

    # Verify mapping
    assert len(all_roles) == 2
    assert all_roles[730] == 111
    assert all_roles[570] == 222
