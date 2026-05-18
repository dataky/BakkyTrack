import sqlite3
import os
import time
from config import BASE_DIR

class DatabaseService:
    def __init__(self):
        self.db_path = os.path.join(BASE_DIR, "historique.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
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
        conn.commit()
        conn.close()

    def add_match(self, playlist: str, result: str, my_score: int, opp_score: int,
                  mmr_start: int, mmr_end: int, mmr_change: int):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO match_history (timestamp, playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (time.time(), playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change))
        conn.commit()
        conn.close()

    def get_history(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT timestamp, playlist, result, my_score, opp_score, mmr_start, mmr_end, mmr_change 
            FROM match_history 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()
        
        history = []
        for r in rows:
            history.append({
                "timestamp": r[0],
                "playlist": r[1],
                "result": r[2],
                "my_score": r[3],
                "opp_score": r[4],
                "mmr_start": r[5],
                "mmr_end": r[6],
                "mmr_change": r[7]
            })
        return history
