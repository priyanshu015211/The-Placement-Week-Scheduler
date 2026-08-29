import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)
