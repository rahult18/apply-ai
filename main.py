from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import json
import os
from db import db_client
from celery_config import process_search_task

app = FastAPI()

class SearchRequest(BaseModel):
    position: str
    experience_level: str

@app.post("/api/search")
async def create_search(request: SearchRequest):
    try:
        # create search record
        search_id = await db_client.create_search(
            request.position,
            request.experience_level
        )
        
        await db_client.log_event(
            search_id,
            "API",
            "INFO",
            {"message": "Search request received and queued for processing"}
        )
        
        # queue the Celery task - async
        process_search_task.delay(
            search_id,
            request.position,
            request.experience_level
        )
        
        return {"search_id": search_id, "status": "queued"}
        
    except Exception as e:
        print(f"Error creating search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/{search_id}")
async def get_search_status(search_id: str):
    try:
        # get the search status from the database
        status = await db_client.get_search_status(search_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Search not found")
            
        # get the latest events
        events = await db_client.get_latest_events(search_id, limit=20)
        
        # add events to the response
        response = status.copy()
        response["latest_events"] = events
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving search status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)