import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def _ensure_operational_columns(conn):
    """Add resource operational-state columns when upgrading an older DB."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'rooms'
              AND column_name = 'status'
            """
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                ALTER TABLE rooms
                ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'available'
                """
            )

        cursor.execute(
            """
            UPDATE rooms
            SET status = 'available'
            WHERE status IS NULL OR status = ''
            """
        )

        conn.commit()
    finally:
        cursor.close()


def get_connection():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
    _ensure_operational_columns(conn)
    return conn
