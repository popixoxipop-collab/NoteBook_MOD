import sqlite3

DB_PATH = "reviews.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            review    TEXT NOT NULL,
            items     TEXT NOT NULL,
            created   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
