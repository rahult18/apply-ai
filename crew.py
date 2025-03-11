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
        # Initialize but don't use the submitter
        self.submitter = ApplicationAgent(search_id)
        
        # Create crew with just the searcher and tailor
        self.crew = Crew(
            agents=[self.searcher, self.tailor],  # Removed submitter from active agents
            tasks=[],  # Tasks will be created dynamically
            verbose=True
        )


    async def execute_search(self, position: str, experience_level: str, resume: Dict) -> Dict:
        try:
            # Log the start of the search process
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {
                    "message": f"Starting job search and application process",
                    "position": position,
                    "experience_level": experience_level
                }
            )
            
            # Update search status to IN_PROGRESS
            await db_client.update_search_status(self.search_id, "IN_PROGRESS")
            print("\n[DEBUG] updated search status to IN_PROGRESS")
            
            # Step 1: Search for jobs
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {"message": "Starting job search phase"}
            )
            
            jobs = await self.searcher.execute(position, experience_level)
            
            if not jobs:
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "WARNING",
                    {"message": "No jobs found"}
                )
                
                await db_client.update_search_status(
                    self.search_id, 
                    "COMPLETED",
                    {"message": "No jobs found"}
                )
                return {"status": "completed", "jobs_found": 0}
            
            # Step 2: Tailor resumes
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {"message": "Starting resume tailoring phase"}
            )
            
            applications = await self.tailor.execute(resume, jobs)
            print("\n[DEBUG] applications tailored: ", len(applications))
            
            if not applications:
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "WARNING",
                    {"message": "Failed to create applications"}
                )
                
                await db_client.update_search_status(
                    self.search_id,
                    "COMPLETED",
                    {
                        "message": "Failed to create applications",
                        "jobs_found": len(jobs)
                    }
                )
                return {"status": "completed", "jobs_found": len(jobs), "applications_created": 0}
            
            # Log that we're skipping the application submission phase
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {"message": "Skipping application submission phase as requested"}
            )
            
            # Query the jobs table to get the final status
            job_records = await db_client.get_jobs_for_search(self.search_id)
            
            # Create results from the jobs table
            application_summaries = []
            for job in job_records:
                application_summaries.append({
                    "job_id": job["job_id"],
                    "job_title": job["title"],
                    "company": job["company"],
                    "link": job["link"],
                    "posted_date": job.get("posted_date", "Unknown"),
                    "resume_tailored": job["status"] == "resume_tailored",
                    "status": job["status"]
                })
            
            # Update final status
            final_results = {
                "jobs_found": len(jobs),
                "applications_created": len(application_summaries),
                "applications_ready": sum(1 for app in application_summaries if app["resume_tailored"]),
                "details": application_summaries
            }
            
            await db_client.log_event(
                self.search_id,
                "CREW",
                "SUCCESS",
                {"message": "Job search and resume tailoring completed successfully"}
            )
            
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