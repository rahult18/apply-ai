from celery import Celery
import os
import json
from typing import Dict
import asyncio

# create celery instance
celery_app = Celery('job_search_system')

# configure celery
celery_app.conf.broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery_app.conf.result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.task_track_started = True
celery_app.conf.task_time_limit = 1800  # 30 minutes max per task
celery_app.conf.worker_prefetch_multiplier = 1  # 1 task per worker at a time


from crew import JobApplicationCrew
from db import db_client

@celery_app.task(bind=True, name='process_search')
def process_search_task(self, search_id: str, position: str, experience_level: str):
    """
    Celery task to process a job search
    """
    # creating event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(
            db_client.log_event(
                search_id,
                "CELERY",
                "INFO",
                {"message": f"Starting job search process in background task"}
            )
        )
        
        # load user resume
        with open("user_resume.json", "r") as f:
            resume = json.load(f)
        
        # create and execute crew
        crew = JobApplicationCrew(search_id)
        loop.run_until_complete(
            crew.execute_search(position, experience_level, resume)
        )
        
        return {"status": "completed", "search_id": search_id}
        
    except Exception as e:
        loop.run_until_complete(
            db_client.log_event(
                search_id,
                "CELERY",
                "ERROR",
                {"error": str(e)}
            )
        )
        
        # update search status to ERROR
        loop.run_until_complete(
            db_client.update_search_status(
                search_id,
                "ERROR",
                {"error": str(e)}
            )
        )
        
        raise
    
    finally:
        # Close the event loop
        loop.close()