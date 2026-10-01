from psycopg2 import pool

from app.config import DATABASE_URL

_connection_pool = None


def get_pool():
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
    return _connection_pool


def get_connection():
    return get_pool().getconn()


def release_connection(conn):
    p = get_pool()
    if p:
        p.putconn(conn)

