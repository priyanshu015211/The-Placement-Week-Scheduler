import sqlite3
import os
from contextlib import contextmanager

DATABASE_FILE = "placement.db"

def get_connection():
    """Return a SQLite connection (for Render deployment)."""
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

@contextmanager
def get_cursor():
    """Context manager for cursor (handles commit/rollback)."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
