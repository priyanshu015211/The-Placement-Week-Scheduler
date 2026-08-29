import os
<<<<<<< HEAD
import mysql.connector
=======
import psycopg2
from psycopg2.extras import RealDictCursor
>>>>>>> 570756796cf9b8d1a793db9a58128c18abce722c
from dotenv import load_dotenv

load_dotenv()

<<<<<<< HEAD

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def get_cursor(conn):
    return conn.cursor(dictionary=True)
=======
def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)
>>>>>>> 570756796cf9b8d1a793db9a58128c18abce722c
