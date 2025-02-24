from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import json
import os
from db import db_client
from crew import JobApplicationCrew

app = FastAPI()

class SearchRequest(BaseModel):
    position: str
    experience_level: str

async def process_search(search_id: str, position: str, experience_level: str):
    try:
        # Load user resume
        with open("user_resume.json", "r") as f:
            resume = json.load(f)
        
        # Create and execute crew
        crew = JobApplicationCrew(search_id)
        await crew.execute_search(position, experience_level, resume)
        
    except Exception as e:
        # Error handling is done within the crew
        print(f"Error processing search {search_id}: {str(e)}")

@app.post("/api/search")
async def create_search(request: SearchRequest, background_tasks: BackgroundTasks):
    try:
        # Create search record
        search_id = await db_client.create_search(
            request.position,
            request.experience_level
        )
        
        # Start background processing
        background_tasks.add_task(
            process_search,
            search_id,
            request.position,
            request.experience_level
        )
        
        return {"search_id": search_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}")
async def get_search_status(search_id: str):
    try:
        status = await db_client.get_search_status(search_id)
        if not status:
            raise HTTPException(status_code=404, detail="Search not found")
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)