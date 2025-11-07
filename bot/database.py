import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
DB_FILE = DATA_DIR / 'bot_data.db'

DATA_DIR.mkdir(exist_ok=True)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """Initialize database tables"""
        cur = self.conn.cursor()
        
        # Discord user to Steam ID mapping
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_links (
                discord_id INTEGER PRIMARY KEY,
                steam_id TEXT NOT NULL UNIQUE,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Store user's game library (appid -> playtime in minutes)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_games (
                discord_id INTEGER,
                appid INTEGER,
                playtime_minutes INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (discord_id, appid),
                FOREIGN KEY (discord_id) REFERENCES user_links(discord_id)
            )
        ''')
        
        # Track which games have roles created
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_roles (
                appid INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL,
                game_name TEXT NOT NULL,
                owner_count INTEGER DEFAULT 0,
                avg_playtime_rank REAL DEFAULT 999.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add owner_count column if it doesn't exist (migration)
        try:
            cur.execute('ALTER TABLE game_roles ADD COLUMN owner_count INTEGER DEFAULT 0')
            self.conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add avg_playtime_rank column if it doesn't exist (migration)
        try:
            cur.execute('ALTER TABLE game_roles ADD COLUMN avg_playtime_rank REAL DEFAULT 999.0')
            self.conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Track last scan time
        cur.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                scan_type TEXT PRIMARY KEY,
                last_scan TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Blacklisted games
        cur.execute('''
            CREATE TABLE IF NOT EXISTS blacklisted_games (
                appid INTEGER PRIMARY KEY,
                blacklisted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def link_user(self, discord_id: int, steam_id: str) -> bool:
        """Link a Discord user to a Steam ID. Returns True if new link, False if updated."""
        cur = self.conn.cursor()
        try:
            cur.execute('''
                INSERT OR REPLACE INTO user_links (discord_id, steam_id)
                VALUES (?, ?)
            ''', (discord_id, steam_id))
            self.conn.commit()
            return True
        except sqlite3.Error:
            self.conn.rollback()
            return False
    
    def get_steam_id(self, discord_id: int) -> Optional[str]:
        """Get Steam ID for a Discord user"""
        cur = self.conn.cursor()
        cur.execute('SELECT steam_id FROM user_links WHERE discord_id = ?', (discord_id,))
        row = cur.fetchone()
        return row['steam_id'] if row else None
    
    def get_all_links(self) -> List[Dict]:
        """Get all Discord user to Steam ID links"""
        cur = self.conn.cursor()
        cur.execute('SELECT discord_id, steam_id FROM user_links')
        return [dict(row) for row in cur.fetchall()]
    
    def update_user_games(self, discord_id: int, games: List[Dict]):
        """Update a user's game library. games is list of {appid, playtime_forever}"""
        cur = self.conn.cursor()
        # Delete old games for this user
        cur.execute('DELETE FROM user_games WHERE discord_id = ?', (discord_id,))
        # Insert new games
        for game in games:
            playtime = game.get('playtime_forever', 0)  # in minutes
            appid = game.get('appid')
            if appid:
                cur.execute('''
                    INSERT OR REPLACE INTO user_games (discord_id, appid, playtime_minutes)
                    VALUES (?, ?, ?)
                ''', (discord_id, appid, playtime))
        self.conn.commit()
    
    def get_user_games(self, discord_id: int) -> Set[int]:
        """Get set of appids owned by a user"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid FROM user_games WHERE discord_id = ?', (discord_id,))
        return {row['appid'] for row in cur.fetchall()}
    
    def get_game_owners(self, appid: int) -> List[int]:
        """Get list of Discord IDs who own a game"""
        cur = self.conn.cursor()
        cur.execute('SELECT discord_id FROM user_games WHERE appid = ?', (appid,))
        return [row['discord_id'] for row in cur.fetchall()]
    
    def get_all_games_with_owners(self) -> Dict[int, List[int]]:
        """Get all games with their owners. Returns {appid: [discord_ids]}"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid, discord_id FROM user_games')
        result = {}
        for row in cur.fetchall():
            appid = row['appid']
            if appid not in result:
                result[appid] = []
            result[appid].append(row['discord_id'])
        return result
    
    def get_game_playtime(self, discord_id: int, appid: int) -> int:
        """Get playtime in minutes for a user's game"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT playtime_minutes FROM user_games
            WHERE discord_id = ? AND appid = ?
        ''', (discord_id, appid))
        row = cur.fetchone()
        return row['playtime_minutes'] if row else 0
    
    def create_game_role(self, appid: int, role_id: int, game_name: str, owner_count: int = 0, avg_playtime_rank: float = 999.0):
        """Record that a role was created for a game"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO game_roles (appid, role_id, game_name, owner_count, avg_playtime_rank)
            VALUES (?, ?, ?, ?, ?)
        ''', (appid, role_id, game_name, owner_count, avg_playtime_rank))
        self.conn.commit()
    
    def update_game_owner_count(self, appid: int, owner_count: int):
        """Update the owner count for a game"""
        cur = self.conn.cursor()
        cur.execute('''
            UPDATE game_roles SET owner_count = ? WHERE appid = ?
        ''', (owner_count, appid))
        self.conn.commit()
    
    def update_game_stats(self, appid: int, owner_count: int, avg_playtime_rank: float):
        """Update the owner count and avg playtime rank for a game"""
        cur = self.conn.cursor()
        cur.execute('''
            UPDATE game_roles SET owner_count = ?, avg_playtime_rank = ? WHERE appid = ?
        ''', (owner_count, avg_playtime_rank, appid))
        self.conn.commit()
    
    def get_game_owner_count(self, appid: int) -> int:
        """Get the owner count for a game"""
        cur = self.conn.cursor()
        cur.execute('SELECT owner_count FROM game_roles WHERE appid = ?', (appid,))
        row = cur.fetchone()
        return row['owner_count'] if row else 0
    
    def get_game_role(self, appid: int) -> Optional[int]:
        """Get role ID for a game, if it exists"""
        cur = self.conn.cursor()
        cur.execute('SELECT role_id FROM game_roles WHERE appid = ?', (appid,))
        row = cur.fetchone()
        return row['role_id'] if row else None
    
    def get_all_game_roles(self) -> Dict[int, int]:
        """Get all game roles. Returns {appid: role_id}"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid, role_id FROM game_roles')
        return {row['appid']: row['role_id'] for row in cur.fetchall()}
    
    def update_scan_time(self, scan_type: str):
        """Update last scan time for a scan type"""
        cur = self.conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO scan_history (scan_type, last_scan)
            VALUES (?, CURRENT_TIMESTAMP)
        ''', (scan_type,))
        self.conn.commit()
    
    def get_last_scan_time(self, scan_type: str) -> Optional[str]:
        """Get last scan time for a scan type"""
        cur = self.conn.cursor()
        cur.execute('SELECT last_scan FROM scan_history WHERE scan_type = ?', (scan_type,))
        row = cur.fetchone()
        return row['last_scan'] if row else None
    
    def is_blacklisted(self, appid: int) -> bool:
        """Check if a game is blacklisted"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid FROM blacklisted_games WHERE appid = ?', (appid,))
        return cur.fetchone() is not None
    
    def toggle_blacklist(self, appid: int) -> bool:
        """
        Toggle blacklist status for a game.
        Returns True if blacklisted, False if unblacklisted.
        """
        cur = self.conn.cursor()
        if self.is_blacklisted(appid):
            cur.execute('DELETE FROM blacklisted_games WHERE appid = ?', (appid,))
            self.conn.commit()
            return False
        else:
            cur.execute('INSERT INTO blacklisted_games (appid) VALUES (?)', (appid,))
            self.conn.commit()
            return True
    
    def get_blacklisted_games(self) -> Set[int]:
        """Get all blacklisted appids"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid FROM blacklisted_games')
        return {row['appid'] for row in cur.fetchall()}
    
    def remove_game(self, appid: int):
        """Remove a game from the database (user_games and game_roles)"""
        cur = self.conn.cursor()
        # Remove from user_games
        cur.execute('DELETE FROM user_games WHERE appid = ?', (appid,))
        # Remove from game_roles
        cur.execute('DELETE FROM game_roles WHERE appid = ?', (appid,))
        self.conn.commit()
    
    def get_game_name(self, appid: int) -> Optional[str]:
        """Get game name from game_roles table"""
        cur = self.conn.cursor()
        cur.execute('SELECT game_name FROM game_roles WHERE appid = ?', (appid,))
        row = cur.fetchone()
        return row['game_name'] if row else None
    
    def calculate_avg_playtime_rank(self, appid: int, discord_ids: List[int]) -> float:
        """
        Calculate the average playtime rank for a game across its owners.
        Lower rank = more played (rank 1 = most played game).
        """
        if not discord_ids:
            return 999.0
        
        cur = self.conn.cursor()
        ranks = []
        
        for discord_id in discord_ids:
            # Get all games for this user, ordered by playtime DESC
            cur.execute('''
                SELECT appid FROM user_games
                WHERE discord_id = ?
                ORDER BY playtime_minutes DESC, appid ASC
            ''', (discord_id,))
            
            user_games = [row['appid'] for row in cur.fetchall()]
            
            # Find the rank of this game (1-indexed)
            try:
                rank = user_games.index(appid) + 1
                ranks.append(rank)
            except ValueError:
                # Game not found in user's library (shouldn't happen)
                ranks.append(999)
        
        # Return average rank
        return sum(ranks) / len(ranks) if ranks else 999.0
    
    def get_top_games_by_owners(self, limit: int = None) -> List[Dict]:
        """
        Get games ordered by number of owners (descending), then by avg playtime rank (ascending).
        Returns list of dicts with appid, game_name, role_id, owner_count, avg_playtime_rank
        """
        cur = self.conn.cursor()
        if limit:
            cur.execute('''
                SELECT appid, game_name, role_id, owner_count, avg_playtime_rank 
                FROM game_roles 
                ORDER BY owner_count DESC, avg_playtime_rank ASC, game_name ASC 
                LIMIT ?
            ''', (limit,))
        else:
            cur.execute('''
                SELECT appid, game_name, role_id, owner_count, avg_playtime_rank 
                FROM game_roles 
                ORDER BY owner_count DESC, avg_playtime_rank ASC, game_name ASC
            ''')
        return [dict(row) for row in cur.fetchall()]
    
    def get_all_games_owner_counts(self) -> Dict[int, int]:
        """Get owner counts for all games. Returns {appid: owner_count}"""
        cur = self.conn.cursor()
        cur.execute('SELECT appid, owner_count FROM game_roles')
        return {row['appid']: row['owner_count'] for row in cur.fetchall()}

# Global database instance
db = Database()

