import os
from pathlib import Path
from contextlib import contextmanager
from supabase import create_client, Client
import dotenv
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import logging

logger = logging.getLogger(__name__)

# Load the .env variables from backend directory
BASE_DIR = Path(__file__).parent.parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

class Supabase():
    def __init__(self) -> None:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        db_name: str = os.environ.get("DB_NAME")
        db_user: str = os.environ.get("DB_USER")
        db_password: str = os.environ.get("DB_PASSWORD")
        db_host: str = os.environ.get("DB_HOST")
        db_port: str = os.environ.get("DB_PORT")

        # ThreadedConnectionPool gives each thread its own connection,
        # preventing thread-safety issues from sharing a single psycopg2 connection.
        self.db_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            dbname=db_name,
        )
        self.client: Client = create_client(url, key)

    @contextmanager
    def get_cursor(self):
        """Thread-safe context manager: gets a dedicated connection from the pool,
        yields a RealDictCursor, commits on success, rolls back on error,
        and returns the connection to the pool."""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
        finally:
            self.db_pool.putconn(conn)

    @contextmanager
    def get_raw_cursor(self):
        """Same as get_cursor but yields a standard tuple cursor (not RealDictCursor).
        Use for queries that access rows by positional index."""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
        finally:
            self.db_pool.putconn(conn)
