from crewai import Crew
from agents import JobSearchAgent, ResumeTailorAgent, ApplicationAgent
from db import db_client
import json
import asyncio
from typing import Dict, List

class JobApplicationCrew:
    def __init__(self, search_id: str):
        self.search_id = search_id
        
        # initialize agents
        self.searcher = JobSearchAgent(search_id)
        self.tailor = ResumeTailorAgent(search_id)
        self.submitter = ApplicationAgent(search_id)
        
        # create crew with just the searcher and tailor
        self.crew = Crew(
            agents=[self.searcher, self.tailor], 
            tasks=[],  # tasks will be created dynamically
            verbose=True
        )


    async def execute_search(self, position: str, experience_level: str, resume: Dict) -> Dict:
        """Execute the job search with improved error handling for partial failures"""
        # job results storage
        jobs = []
        applications = []
        
        try:
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
            
            # update search status to IN_PROGRESS
            await db_client.update_search_status(self.search_id, "IN_PROGRESS")
            print("\n[DEBUG] updated search status to IN_PROGRESS")
            
            # Step 1: Search for jobs
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {"message": "Starting job search phase"}
            )
            
            try:
                jobs = await self.searcher.execute(position, experience_level)
                
                if not jobs:
                    await db_client.log_event(
                        self.search_id,
                        "CREW",
                        "WARNING",
                        {"message": "No jobs found"}
                    )
                    
                    # Continue with the process, but log that no jobs were found
                    print("\n[WARNING] No jobs found")
                else:
                    await db_client.log_event(
                        self.search_id,
                        "CREW",
                        "SUCCESS",
                        {"message": f"Found {len(jobs)} jobs"}
                    )
            except Exception as e:
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "ERROR",
                    {"message": f"Error during job search phase: {str(e)}"}
                )
                print(f"\n[ERROR] Job search failed: {str(e)}")
            
            # Only proceed with tailoring if we have jobs
            if jobs:
                # Step 2: Tailor resumes
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "INFO",
                    {"message": "Starting resume tailoring phase"}
                )
                
                try:
                    applications = await self.tailor.execute(resume, jobs)
                    print("\n[DEBUG] applications tailored: ", len(applications))
                    
                    await db_client.log_event(
                        self.search_id,
                        "CREW", 
                        "SUCCESS",
                        {"message": f"Successfully tailored {len(applications)} resumes"}
                    )
                except Exception as e:
                    await db_client.log_event(
                        self.search_id,
                        "CREW",
                        "ERROR",
                        {"message": f"Error during resume tailoring phase: {str(e)}"}
                    )
                    print(f"\n[ERROR] Resume tailoring failed: {str(e)}")
            
            # Log that we're skipping the application submission phase
            await db_client.log_event(
                self.search_id,
                "CREW",
                "INFO",
                {"message": "Skipping application submission phase as requested"}
            )
            
            # querying the jobs table to get the final status
            job_records = await db_client.get_jobs_for_search(self.search_id)
            
            # creating results from the jobs table
            application_summaries = []
            for job in job_records:
                application_summaries.append({
                    "job_id": job.get("job_id", "unknown"),
                    "job_title": job.get("title", "Unknown Title"),
                    "company": job.get("company", "Unknown Company"),
                    "link": job.get("link", ""),
                    "posted_date": job.get("posted_date", "Unknown"),
                    "resume_tailored": job.get("status") == "resume_tailored",
                    "status": job.get("status", "unknown")
                })
            
            # update final status
            final_results = {
                "jobs_found": len(jobs),
                "applications_created": len(application_summaries),
                "applications_ready": sum(1 for app in application_summaries if app["resume_tailored"]),
                "details": application_summaries
            }
            
            # determine final status based on results
            if len(jobs) > 0 and len(application_summaries) > 0:
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "SUCCESS",
                    {"message": "Job search and resume tailoring completed with some results"}
                )
                
                await db_client.update_search_status(
                    self.search_id,
                    "COMPLETED",
                    final_results
                )
            else:
                await db_client.log_event(
                    self.search_id,
                    "CREW",
                    "WARNING",
                    {"message": "Job search completed but with limited results"}
                )
                
                await db_client.update_search_status(
                    self.search_id,
                    "COMPLETED_WITH_WARNINGS",
                    final_results
                )
            
            return {
                "status": "completed",
                **final_results
            }
            
        except Exception as e:
            await db_client.log_event(
                self.search_id,
                "CREW",
                "ERROR",
                {"error": str(e)}
            )
            
            # still try to get any job records that may exist
            try:
                job_records = await db_client.get_jobs_for_search(self.search_id)
                
                # creating partial results even in case of error
                partial_results = {
                    "jobs_found": len(jobs),
                    "applications_created": len(applications),
                    "error": str(e),
                    "details": [
                        {
                            "job_id": job.get("job_id", "unknown"),
                            "job_title": job.get("title", "Unknown Title"),
                            "company": job.get("company", "Unknown Company"),
                            "status": job.get("status", "unknown")
                        } 
                        for job in job_records
                    ]
                }
                
                await db_client.update_search_status(
                    self.search_id,
                    "ERROR",
                    partial_results
                )
                
                return {
                    "status": "error",
                    "error": str(e),
                    **partial_results
                }
            
            except Exception as inner_e:
                await db_client.update_search_status(
                    self.search_id,
                    "ERROR",
                    {"error": str(e), "jobs_found": len(jobs)}
                )
                
                return {
                    "status": "error",
                    "error": str(e),
                    "jobs_found": len(jobs)
                }