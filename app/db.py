import os
import threading

import psycopg2
from dotenv import load_dotenv

load_dotenv()

_local = threading.local()


def get_conn():
    """Return a per-thread database connection, creating one if needed."""
    conn = getattr(_local, "conn", None)
    if conn is None or conn.closed:
        _local.conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "smart_student_assessment"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            port=os.getenv("DB_PORT", "5432"),
        )
        _local.conn.autocommit = False
    return _local.conn


class _ThreadLocalConnection:
    """Proxy that delegates attribute access to the current thread's connection."""

    def __getattr__(self, name):
        return getattr(get_conn(), name)


conn = _ThreadLocalConnection()
