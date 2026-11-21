import sqlite3
import os

DB_NAME = "snapfind.db"

class Database:
    def __init__(self, db_path=None):
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, DB_NAME)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_size INTEGER,
                    mtime REAL,
                    ocr_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON images(file_path)")
            conn.commit()

    def is_indexed(self, file_path, file_size, mtime):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM images WHERE file_path = ? AND file_size = ? AND ABS(mtime - ?) < 0.001",
                (file_path, file_size, mtime)
            )
            return cur.fetchone() is not None

    def upsert_image(self, file_path, file_size, mtime, ocr_text):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO images (file_path, file_size, mtime, ocr_text)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    ocr_text = excluded.ocr_text
            """, (file_path, file_size, mtime, ocr_text))
            conn.commit()

    def search(self, query, limit=50):
        if not query.strip():
            return self.get_recent(limit)

        q = f"%{query.strip().lower()}%"
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, file_path, ocr_text, created_at
                FROM images
                WHERE LOWER(ocr_text) LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """, (q, limit))
            return cur.fetchall()

    def get_recent(self, limit=50):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, file_path, ocr_text, created_at
                FROM images
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return cur.fetchall()

    def count(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM images")
            row = cur.fetchone()
            return row[0] if row else 0
