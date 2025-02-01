import asyncio
from fastapi import FastAPI, HTTPException
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

# Models
class SearchRequest(BaseModel):
    position: str
    experience: str

class JobListing(BaseModel):
    job_title: str
    job_link: str
    job_description: str
    date_posted: Optional[str]
    status: str

class SearchResponse(BaseModel):
    run_id: str
    jobs: List[JobListing]

event_store = EventStore()

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.post("/api/search", response_model=SearchResponse)
async def create_search(request: SearchRequest):
    run_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Insert run record
        cur.execute(
            """
            INSERT INTO runs (run_id, timestamp, position, experience, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (run_id, datetime.now(), request.position, request.experience, "Created")
        )
        
        # Initialize and run the scraper agent
        scraper = JobScraperAgent(run_id, request.position, request.experience, event_store)
        job_listings = scraper.scrape_jobs()
        
        # Insert job listings into the jobs table
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
                    job['job_description'],
                    job['date_posted'] if job['date_posted'] else None,
                    "Created",
                    run_id
                )
            )
            job['status'] = "Created"
            stored_jobs.append(job)
        
        conn.commit()
        return SearchResponse(run_id=run_id, jobs=stored_jobs)
    
    except Exception as e:
        conn.rollback()
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