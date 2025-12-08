import os
from supabase import create_client, Client
import dotenv

# load the .env variables
dotenv.load_dotenv()

class Supabase():
    def __init__(self) -> None:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        self.client: Client = create_client(url, key)