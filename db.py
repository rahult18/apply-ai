from supabase import create_client
import os
from typing import Dict, Any
import json
from datetime import datetime

class DatabaseClient:
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    async def create_search(self, position: str, experience_level: str) -> str:
        """Create a new search record and return the search_id"""
        data = {
            "position": position,
            "experience_level": experience_level,
            "status": "CREATED"
        }
        
        result = self.supabase.table("searches").insert(data).execute()
        return result.data[0]["search_id"]

    async def log_event(self, search_id: str, agent_type: str, event_type: str, details: Dict[str, Any]):
        """Log an event for a specific search"""
        event_data = {
            "search_id": search_id,
            "agent_type": agent_type,
            "event_type": event_type,
            "details": json.dumps(details)
        }
        
        self.supabase.table("events").insert(event_data).execute()

    async def update_search_status(self, search_id: str, status: str, results: Dict[str, Any] = None):
        """Update the status and optional results of a search"""
        data = {"status": status}
        if results:
            data["results"] = json.dumps(results)
            
        self.supabase.table("searches").update(data).eq("search_id", search_id).execute()

    async def get_search_status(self, search_id: str) -> Dict[str, Any]:
        """Get the current status and events for a search"""
        search = self.supabase.table("search_status").select("*").eq("search_id", search_id).single().execute()
        return search.data

# Create a singleton instance
db_client = DatabaseClient()