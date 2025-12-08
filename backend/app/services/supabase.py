import os
from pathlib import Path
from supabase import create_client, Client
import dotenv

# Load the .env variables from backend directory
BASE_DIR = Path(__file__).parent.parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

class Supabase():
    def __init__(self) -> None:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(url, key)

