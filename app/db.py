# app/db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from flask import current_app

_db_pool = None

def get_db_pool():
    global _db_pool
    if _db_pool is None:
        database_url = current_app.config.get('DATABASE_URL')
        if database_url:
            # Render provides PostgreSQL as a standard connection URL.
            _db_pool = pool.ThreadedConnectionPool(1, 10, dsn=database_url)
        else:
            _db_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=current_app.config['DB_HOST'],
                port=current_app.config['DB_PORT'],
                dbname=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD']
            )
    return _db_pool

def get_db_connection():
    db_pool = get_db_pool()
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool = get_db_pool()
    db_pool.putconn(conn)

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Executes parameterized SQL queries safely to prevent SQL injection.
    Returns results as dictionary objects.
    """
    conn = get_db_connection()
    result = None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if commit:
                conn.commit()
            if fetchone:
                result = cur.fetchone()
            elif fetchall:
                result = cur.fetchall()
    finally:
        release_db_connection(conn)
    return result
