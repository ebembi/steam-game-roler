"""Pytest configuration and fixtures"""
import pytest
import tempfile
import sqlite3
from pathlib import Path
from bot import database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_path = Path(temp_file.name)
    temp_file.close()
    
    # Store original DB path
    original_db = database.DB_FILE
    
    # Override database path
    database.DB_FILE = temp_path
    
    # Create new database instance
    test_db = database.Database()
    
    yield test_db
    
    # Cleanup
    test_db.conn.close()
    database.DB_FILE = original_db
    temp_path.unlink()


@pytest.fixture
def mock_steam_games():
    """Mock Steam game data"""
    return [
        {'appid': 730, 'playtime_forever': 120, 'name': 'Counter-Strike 2'},
        {'appid': 570, 'playtime_forever': 200, 'name': 'Dota 2'},
        {'appid': 440, 'playtime_forever': 30, 'name': 'Team Fortress 2'},
        {'appid': 620, 'playtime_forever': 150, 'name': 'Portal 2'},
    ]


@pytest.fixture
def mock_game_meta():
    """Mock Steam store metadata"""
    return {
        730: {
            'name': 'Counter-Strike 2',
            'categories': ['Multi-player', 'Co-op']
        },
        570: {
            'name': 'Dota 2',
            'categories': ['Multi-player']
        },
        440: {
            'name': 'Team Fortress 2',
            'categories': ['Multi-player']
        },
        620: {
            'name': 'Portal 2',
            'categories': ['Multi-player', 'Co-op']
        },
    }

