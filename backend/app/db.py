import threading

from psycopg2 import pool

from app.config import DATABASE_URL

# Tạo pool ở lần gọi get_connection() đầu tiên, không phải lúc import module:
# unit test chỉ mock repository nên import app.* không được đòi Postgres
# đang chạy (CI chỉ chạy `pytest backend/tests/unit`, không có DB).
_pool: pool.SimpleConnectionPool | None = None
_khoa_tao_pool = threading.Lock()


def _lay_pool() -> pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        with _khoa_tao_pool:
            if _pool is None:
                _pool = pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
    return _pool


def get_connection():
    return _lay_pool().getconn()


def release_connection(conn):
    _lay_pool().putconn(conn)
