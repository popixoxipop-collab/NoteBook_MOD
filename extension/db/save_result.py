import json
import sqlite3
from db.init_db import DB_PATH


def save_result(review: str, items: list) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO results (review, items) VALUES (?, ?)",
        (review, json.dumps(items, ensure_ascii=False))
    )
    row_id = c.lastrowid
    conn.commit()
    conn.close()
    return row_id
