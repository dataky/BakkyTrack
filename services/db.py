import sqlite3
import os
import time
import threading
from config import BASE_DIR

class DatabaseService:
    """Service SQLite avec connexion persistante (check_same_thread=False + lock)."""

    def __init__(self):
        db_dir = os.path.join(os.environ.get('LOCALAPPDATA', BASE_DIR), "BakkyTrack")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, "historique.db")
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_db()

    def _init_db(self):
        with self._lock:
            c = self._conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    playlist TEXT,
                    result TEXT,
                    my_score INTEGER,
                    opp_score INTEGER,
                    mmr_start INTEGER,
                    mmr_end INTEGER,
                    mmr_change INTEGER
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS player_encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    player_name TEXT,
                    platform TEXT,
                    match_result TEXT,
                    team TEXT
                )
            ''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_player_name ON player_encounters (player_name)')
            self._conn.commit()

    def add_match(self, playlist: str, result: str, my_score: int, opp_score: int,
                  mmr_start: int, mmr_end: int, mmr_change: int):
        with self._lock:
            self._conn.execute('''
                INSERT INTO match_history (timestamp, playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (time.time(), playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change))
            self._conn.commit()

    def get_history(self, limit=50):
        with self._lock:
            c = self._conn.execute('''
                SELECT timestamp, playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change 
                FROM match_history 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            rows = c.fetchall()
        return [
            {
                "timestamp": r[0], "playlist": r[1], "result": r[2],
                "my_score": r[3], "opp_score": r[4],
                "mmr_start": r[5], "mmr_end": r[6], "mmr_change": r[7],
            }
            for r in rows
        ]

    def record_encounter(self, player_name: str, platform: str, match_result: str, team: str):
        try:
            with self._lock:
                self._conn.execute('''
                    INSERT INTO player_encounters (timestamp, player_name, platform, match_result, team)
                    VALUES (?, ?, ?, ?, ?)
                ''', (time.time(), player_name, platform, match_result, team))
                self._conn.commit()
            self.invalidate_encounter_cache(player_name)  # évite les données obsolètes en cache
        except Exception as e:
            print(f"[DB] Error recording encounter: {e}")

    _encounter_cache: dict = {}
    _encounter_cache_lock = threading.Lock()

    def invalidate_encounter_cache(self, player_name: str):
        with self._encounter_cache_lock:
            self._encounter_cache.pop(player_name, None)

    def get_encounter_record(self, player_name: str) -> dict:
        with self._encounter_cache_lock:
            if player_name in self._encounter_cache:
                return self._encounter_cache[player_name]
        stats = {"vs_wins": 0, "vs_losses": 0, "with_wins": 0, "with_losses": 0}
        try:
            with self._lock:
                c = self._conn.execute(
                    'SELECT match_result, team FROM player_encounters WHERE player_name = ?',
                    (player_name,))
                rows = c.fetchall()
            for res, team in rows:
                if team == "opponent":
                    if res == "win": stats["vs_wins"] += 1
                    else: stats["vs_losses"] += 1
                elif team == "teammate":
                    if res == "win": stats["with_wins"] += 1
                    else: stats["with_losses"] += 1
        except Exception as e:
            print(f"[DB] Error querying encounter: {e}")
        with self._encounter_cache_lock:
            self._encounter_cache[player_name] = stats
        return stats