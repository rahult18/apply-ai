from supabase import create_client
import os
from typing import Dict, Any, List
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
            "status": "QUEUED" 
        }
        
        result = self.supabase.table("searches").insert(data).execute()
        return result.data[0]["search_id"]

    async def log_event(self, search_id: str, agent_type: str, event_type: str, details: Dict[str, Any]):
        """Log an event for a specific search with timestamp"""
        details["timestamp"] = datetime.utcnow().isoformat()
        
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
    
    async def get_latest_events(self, search_id: str, limit: int = 20) -> List[Dict]:
        """Get the latest events for a search with a specified limit"""
        events = self.supabase.table("events") \
            .select("*") \
            .eq("search_id", search_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        # Parse JSON details for each event
        result = []
        for event in events.data:
            try:
                event["details"] = json.loads(event["details"])
            except:
                pass
            result.append(event)
            
        return result
    
    async def save_job(self, search_id: str, job_data: Dict) -> str:
        """Save a job to the jobs table and return the job_id"""
        job_data["search_id"] = search_id
        result = self.supabase.table("jobs").insert(job_data).execute()
        return result.data[0]["job_id"]

    async def update_job(self, job_id: str, data: Dict):
        """Update job data"""
        self.supabase.table("jobs").update(data).eq("job_id", job_id).execute()

    async def create_application(self, job_id: str, search_id: str, status: str, tailored_resume: Dict = None) -> str:
        """Create a new application record"""
        data = {
            "job_id": job_id,
            "search_id": search_id,
            "status": status
        }
        if tailored_resume:
            data["tailored_resume"] = json.dumps(tailored_resume)
        
        result = self.supabase.table("applications").insert(data).execute()
        return result.data[0]["application_id"]

    async def update_application_status(self, application_id: str, status: str, tailored_resume: Dict = None):
        """Update application status and optional tailored resume"""
        data = {"status": status}
        if tailored_resume:
            data["tailored_resume"] = json.dumps(tailored_resume)
        
        self.supabase.table("applications").update(data).eq("application_id", application_id).execute()

    async def get_jobs_for_search(self, search_id: str) -> List[Dict]:
        """Get all jobs for a specific search"""
        result = self.supabase.table("jobs").select("*").eq("search_id", search_id).execute()
        return result.data

# Create a singleton instance
db_client = DatabaseClient()