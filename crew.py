from crewai import Crew
from agents import JobSearchAgent, ResumeTailorAgent, ApplicationAgent
from db import db_client
import json
import asyncio
from typing import Dict

class JobApplicationCrew:
    def __init__(self, search_id: str):
        self.search_id = search_id
        
        # Initialize agents
        self.searcher = JobSearchAgent(search_id)
        self.tailor = ResumeTailorAgent(search_id)
        self.submitter = ApplicationAgent(search_id)
        
        # Create crew
        self.crew = Crew(
            agents=[self.searcher, self.tailor, self.submitter],
            tasks=[],  # Tasks will be created dynamically
            verbose=True
        )

    async def execute_search(self, position: str, experience_level: str, resume: Dict) -> Dict:
        try:
            # Update search status to IN_PROGRESS
            await db_client.update_search_status(self.search_id, "IN_PROGRESS")
            print("\n[DEBUG] updated search status to IN_PROGRESS")
            
            # Step 1: Search for jobs
            jobs = await self.searcher.execute(position, experience_level)
            print("\n[DEBUG] jobs: ", jobs)
            
            if not jobs:
                await db_client.update_search_status(
                    self.search_id, 
                    "COMPLETED",
                    {"message": "No jobs found"}
                )
                return {"status": "completed", "jobs_found": 0}
            
            # Step 2: Tailor resumes
            applications = await self.tailor.execute(resume, jobs)
            print("\n[DEBUG] applications: ", applications)
            
            if not applications:
                await db_client.update_search_status(
                    self.search_id,
                    "COMPLETED",
                    {
                        "message": "Failed to create applications",
                        "jobs_found": len(jobs)
                    }
                )
                return {"status": "completed", "jobs_found": len(jobs), "applications_created": 0}
            
            # Step 3: Submit applications
            results = await self.submitter.execute(applications)
            print("\n[DEBUG] results: ", results)
            
            # Update final status
            final_results = {
                "jobs_found": len(jobs),
                "applications_created": len(applications),
                "applications_submitted": len([r for r in results if r["status"] == "submitted"]),
                "applications_failed": len([r for r in results if r["status"] == "failed"]),
                "details": results
            }
            
            await db_client.update_search_status(
                self.search_id,
                "COMPLETED",
                final_results
            )
            
            return {
                "status": "completed",
                **final_results
            }
            
        except Exception as e:
            # Log error and update status
            await db_client.log_event(
                self.search_id,
                "CREW",
                "ERROR",
                {"error": str(e)}
            )
            
            await db_client.update_search_status(
                self.search_id,
                "ERROR",
                {"error": str(e)}
            )
            
            raise