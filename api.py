from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import uuid
import psycopg2
from dotenv import load_dotenv
import os
from typing import List, Optional
from job_manager import Event, EventStore
from agents import JobScraperAgent


# Load environment variables
load_dotenv()

app = FastAPI()

# Database configuration
DB_CONFIG = {
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "dbname": os.getenv("dbname")
}

# Pydantic models for request/response validation
class SearchRequest(BaseModel):
    """
        Model for job search request parameters
        position: Job title or role to search for
        experience: Experience level (Entry Level, Mid Level, Senior)
    """
    position: str
    experience: str

class JobListing(BaseModel):
    """
        Model representing a single job listing
    """
    job_title: str
    job_link: str
    job_description: str
    date_posted: Optional[str]
    status: str

class SearchResponse(BaseModel):
    """
        Model for the search response containing run_id and job listings
    """
    run_id: str
    jobs: List[JobListing]
    
class EventResponse(BaseModel):
    """
        Model for individual event responses
    """
    timestamp: datetime
    data: str

class JobEvent(BaseModel):
    """
        Model for job-specific events and status
    """
    job_id: str
    job_title: str
    status: str
    job_link: str

class RunEvents(BaseModel):
    """
        Model for aggregating all events and status for a specific run
    """
    run_id: str
    status: str
    jobs: List[JobEvent]
    # storing events at run level
    events: List[EventResponse]  

# Initialize event store for tracking job processing events
event_store = EventStore()

def get_db_connection():
    """
    Creates and returns a new database connection using the configured parameters
    """
    return psycopg2.connect(**DB_CONFIG)


"""
    Endpoint to initiate a new job search
    - Creates a new run with unique ID
    - Initializes job scraping
    - Triggers background job description fetching
"""
@app.post("/api/search", response_model=SearchResponse)
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create new run record and insert into runs table
        cur.execute(
            """
            INSERT INTO runs (run_id, timestamp, position, experience, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (run_id, datetime.now(), request.position, request.experience, "Created")
        )
        
        # Initialize scraper and get job listings
        scraper = JobScraperAgent(run_id, request.position, request.experience, event_store)
        job_listings = scraper.scrape_jobs()
        
        # Store job listings and prepare to fetch JDs in the background
        stored_jobs = []
        for job in job_listings:
            cur.execute(
                """
                INSERT INTO jobs (job_title, job_link, job_description, date_posted, status, run_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING job_id
                """,
                (
                    job['job_title'],
                    job['job_link'],
                    None, 
                    job['date_posted'] if job['date_posted'] else None,
                    "PENDING_JD",  # Initial status for this job
                    run_id
                )
            )
            job['job_description'] = "" 
            job['status'] = "PENDING_JD"
            stored_jobs.append(job)
        
        # Adding background task for fetching job descriptions
        background_tasks.add_task(scraper.process_job_descriptions, stored_jobs)
        
        conn.commit()
        return SearchResponse(run_id=run_id, jobs=stored_jobs)
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

"""
    Endpoint to retrieve all events and status for a specific run
    - Returns job statuses
    - Returns event history
    - Calculates overall run status
"""
@app.get("/api/run/{run_id}/events", response_model=RunEvents)
async def get_run_events(run_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First check if run exists
        cur.execute(
            """
            SELECT status FROM runs 
            WHERE run_id = %s
            """,
            (run_id,)
        )
        run = cur.fetchone()
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
            
        # Fetch all jobs for this run
        cur.execute(
            """
            SELECT 
                job_id,
                job_title,
                status,
                job_link
            FROM jobs
            WHERE run_id = %s
            """,
            (run_id,)
        )
        jobs = cur.fetchall()
        
        # Process jobs
        job_events = []
        all_statuses = set()
        
        for job in jobs:
            job_id, job_title, status, job_link = job
            all_statuses.add(status)
            
            job_events.append(JobEvent(
                job_id=job_id,
                job_title=job_title,
                status=status,
                job_link=job_link
            ))
        
        # Get events from event store for this run
        run_events = event_store.get_events(run_id)
        
        # Convert Event objects to EventResponse
        event_responses = [
            EventResponse(timestamp=event.timestamp, data=event.data)
            for event in run_events
        ]
        
        # Determine overall status
        overall_status = "IN_PROGRESS"
        if all(status == "JD_FETCHED" for status in all_statuses):
            overall_status = "COMPLETED"
        elif any(status == "JD_FAILED" for status in all_statuses):
            overall_status = "FAILED"
        
        return RunEvents(
            run_id=run_id,
            status=overall_status,
            jobs=job_events,
            events=event_responses
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


@app.get("/api/job/{job_id}")
async def get_job_events(job_id: str) -> List[Event]:
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
       pass
    except Exception as e:
        pass
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)