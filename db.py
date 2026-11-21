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
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_hash TEXT,
                    ocr_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON images(file_hash)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON images(file_path)")
            conn.commit()

    def is_indexed(self, file_path, file_hash):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM images WHERE file_path = ? AND file_hash = ?", (file_path, file_hash))
            return cur.fetchone() is not None

    def upsert_image(self, file_path, file_hash, ocr_text):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO images (file_path, file_hash, ocr_text)
                VALUES (?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    ocr_text = excluded.ocr_text
            """, (file_path, file_hash, ocr_text))
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

    def cleanup_missing(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, file_path FROM images")
            rows = cur.fetchall()
            to_delete = [r[0] for r in rows if not os.path.exists(r[1])]
            if to_delete:
                cur.executemany("DELETE FROM images WHERE id = ?", [(i,) for i in to_delete])
                conn.commit()
            return len(to_delete)
