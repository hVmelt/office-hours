"""
Database connection. Reads the URL from .env so it's not hardcoded.
"""

import os
import psycopg
from pgvector.psycopg import register_vector


def get_connection():
    """
    Returns a Postgres connection with the pgvector adapter registered.
    Caller is responsible for closing it (or use it as a context manager).
    """
    url = os.environ["DATABASE_URL"]
    conn = psycopg.connect(url)
    register_vector(conn)
    return conn