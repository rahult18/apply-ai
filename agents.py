from crewai import Agent
from tools import tools
from db import db_client
import json
import asyncio
from typing import Dict, List
import datetime

class JobSearchAgent(Agent):
    def __init__(self, search_id: str):
        self.search_id = search_id
        print("\n[DEBUG] search_id: ", search_id)
        super().__init__(
            role='Job Searcher',
            goal='Find relevant job postings on Greenhouse',
            backstory='I am an AI agent specialized in finding relevant job postings',
            allow_delegation=False,
            verbose=True,
            # Add search_id as a metadata property
            metadata={"search_id": search_id}
        )

    async def execute(self, position: str, experience_level: str) -> List[Dict]:
        try:
            # Search for jobs
            print("\n[DEBUG] starting search for jobs")
            jobs = await tools.search_jobs(position, experience_level)
            
            # Log success event
            await db_client.log_event(
                self.search_id,
                "SEARCHER",
                "SUCCESS",
                {"jobs_found": len(jobs)}
            )
            
            # Start background tasks to fetch job descriptions
            tasks = []
            for job in jobs:
                task = asyncio.create_task(self._fetch_job_details(job))
                tasks.append(task)
            
            # Wait for all job descriptions to be fetched
            detailed_jobs = await asyncio.gather(*tasks)
            return detailed_jobs
            
        except Exception as e:
            await db_client.log_event(
                self.search_id,
                "SEARCHER",
                "ERROR",
                {"error": str(e)}
            )
            raise

    async def _fetch_job_details(self, job: Dict) -> Dict:
        """Fetch detailed job description for a single job"""
        try:
            description = await tools.fetch_job_description(job["link"])
            job["description"] = description
            return job
        except Exception as e:
            await db_client.log_event(
                self.search_id,
                "SEARCHER",
                "ERROR",
                {"error": f"Failed to fetch job details: {str(e)}", "job": job}
            )
            return job

class ResumeTailorAgent(Agent):
    def __init__(self, search_id: str):
        self.search_id = search_id
        super().__init__(
            role='Resume Tailor',
            goal='Customize resumes for specific job postings',
            backstory='I am an AI agent specialized in tailoring resumes to match job requirements',
            allow_delegation=False,
            verbose=True,
            # Add search_id as a metadata property
            metadata={"search_id": search_id}
        )


    async def execute(self, resume: Dict, jobs: List[Dict]) -> List[Dict]:
        try:
            tailored_applications = []
            
            for job in jobs:
                # Skip if no description was fetched
                if "description" not in job:
                    continue
                    
                # Tailor resume for this specific job
                tailored_resume = await tools.tailor_resume(resume, job["description"])
                
                # Generate PDF
                pdf_bytes = await tools.generate_pdf_resume(tailored_resume)
                
                application = {
                    "job": job,
                    "tailored_resume": tailored_resume,
                    "pdf_resume": pdf_bytes
                }
                
                tailored_applications.append(application)
                
                # Log success for this job
                await db_client.log_event(
                    self.search_id,
                    "TAILOR",
                    "SUCCESS",
                    {"job_title": job["title"]}
                )
                
            return tailored_applications
            
        except Exception as e:
            await db_client.log_event(
                self.search_id,
                "TAILOR",
                "ERROR",
                {"error": str(e)}
            )
            raise

class ApplicationAgent(Agent):
    def __init__(self, search_id: str):
        self.search_id = search_id
        super().__init__(
            role='Application Submitter',
            goal='Submit job applications through Greenhouse',
            backstory='I am an AI agent specialized in automated job application submission',
            allow_delegation=False,
            verbose=True,
            # Add search_id as a metadata property
            metadata={"search_id": search_id}
        )

    async def execute(self, applications: List[Dict]) -> List[Dict]:
        try:
            results = []
            
            for app in applications:
                try:
                    # Submit the application using Playwright
                    # This is a placeholder - actual implementation would depend on
                    # Greenhouse's application form structure
                    result = {
                        "job": app["job"],
                        "status": "submitted",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    results.append(result)
                    
                    # Log success
                    await db_client.log_event(
                        self.search_id,
                        "SUBMITTER",
                        "SUCCESS",
                        {"job_title": app["job"]["title"]}
                    )
                    
                except Exception as e:
                    # Log individual application failure
                    await db_client.log_event(
                        self.search_id,
                        "SUBMITTER",
                        "ERROR",
                        {
                            "error": str(e),
                            "job_title": app["job"]["title"]
                        }
                    )
                    
                    results.append({
                        "job": app["job"],
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            return results
            
        except Exception as e:
            await db_client.log_event(
                self.search_id,
                "SUBMITTER",
                "ERROR",
                {"error": str(e)}
            )
            raise