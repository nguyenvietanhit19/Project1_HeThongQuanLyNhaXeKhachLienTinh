from psycopg2 import pool

from app.config import DATABASE_URL

connection_pool = pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)


def get_connection():
    return connection_pool.getconn()


def release_connection(conn):
    connection_pool.putconn(conn)
