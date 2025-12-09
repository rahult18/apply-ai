import os
from pathlib import Path
from sqlalchemy.sql.functions import user
from supabase import create_client, Client
import dotenv
import psycopg2
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
        self.db_connection = psycopg2.connect(
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            dbname=db_name
        )
        self.client: Client = create_client(url, key)

