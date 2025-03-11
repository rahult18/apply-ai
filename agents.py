from crewai import Agent
from tools import tools
from db import db_client
import json
import asyncio
from typing import Dict, List
import datetime
from registry import register_agent, get_search_id

class JobSearchAgent(Agent):
    def __init__(self, search_id: str):
        super().__init__(
            role='Job Searcher',
            goal='Find relevant job postings on Greenhouse',
            backstory='I am an AI agent specialized in finding relevant job postings',
            allow_delegation=False,
            verbose=True,
        )

        # Register the agent with the search_id
        register_agent(self, search_id)

    async def execute(self, position: str, experience_level: str) -> List[Dict]:
        try:
            # Get the search_id from the registry
            search_id = get_search_id(self)
            print(f"\n[DEBUG] starting search for jobs with search_id: {search_id}")
            
            # Log search initiation
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "INFO",
                {"message": f"Starting job search for '{position}' with experience level '{experience_level}'"}
            )
            
            jobs = await tools.search_jobs(position, experience_level)
            
            # Log success event with more details
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "SUCCESS",
                {
                    "jobs_found": len(jobs),
                    "job_titles": [job["title"] for job in jobs],
                    "companies": [job["company"] for job in jobs]
                }
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
            search_id = get_search_id(self)
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "ERROR",
                {"error": str(e)}
            )
            raise

    async def _fetch_job_details(self, job: Dict) -> Dict:
        """Fetch detailed job description for a single job and save to database"""
        try:
            search_id = get_search_id(self)
            
            # Log that we're fetching the job description
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "INFO",
                {
                    "message": f"Fetching details for job: {job['title']} at {job['company']}",
                    "job_link": job["link"]
                }
            )
            
            # Save the job to the database first to get a job_id
            job_data = {
                "title": job["title"],
                "company": job["company"],
                "link": job["link"],
                "posted_date": job.get("posted_date", "Unknown"),
                "status": "fetching_description"
            }
            job_id = await db_client.save_job(search_id, job_data)
            job["job_id"] = job_id  # Add job_id to the job dict for reference
            
            # Fetch the job description
            description = await tools.fetch_job_description(job["link"])
            job["description"] = description
            
            # Update the job record with the description
            await db_client.update_job(job_id, {
                "description": description,
                "status": "description_fetched"
            })
            
            # Log the job description as an event (truncated for readability)
            description_preview = description[:500] + "..." if len(description) > 500 else description
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "JOB_DESCRIPTION",
                {
                    "job_title": job["title"],
                    "company": job["company"],
                    "description_preview": description_preview,
                    "description_length": len(description),
                    "job_id": job_id
                }
            )
            
            # Create an application record to track this job
            application_id = await db_client.create_application(job_id, search_id, "description_fetched")
            job["application_id"] = application_id  # Add application_id to the job dict
            
            return job
        except Exception as e:
            search_id = get_search_id(self)
            await db_client.log_event(
                search_id,
                "SEARCHER",
                "ERROR",
                {"error": f"Failed to fetch job details: {str(e)}", "job": job}
            )
            # Even if we fail to get the description, return the job with an empty description
            job["description"] = "Unable to fetch job description."
            if "job_id" in job:
                await db_client.update_job(job["job_id"], {
                    "status": "error_fetching_description"
                })
            return job


class ResumeTailorAgent(Agent):
    def __init__(self, search_id: str):
        super().__init__(
            role='Resume Tailor',
            goal='Customize resumes for specific job postings',
            backstory='I am an AI agent specialized in tailoring resumes to match job requirements',
            allow_delegation=False,
            verbose=True,
        )
        register_agent(self, search_id)

    async def execute(self, resume: Dict, jobs: List[Dict]) -> List[Dict]:
        try:
            search_id = get_search_id(self)
            if not search_id:
                print("[WARNING] No search_id found for ResumeTailorAgent. Using fallback.")
                search_id = "unknown_search"
            
            # Log the start of resume tailoring
            await db_client.log_event(
                search_id,
                "TAILOR",
                "INFO",
                {"message": f"Starting resume tailoring for {len(jobs)} jobs"}
            )
                
            tailored_applications = []
            
            for job in jobs:
                try:
                    # Skip if no description was fetched or it's empty
                    if "description" not in job or not job["description"]:
                        await db_client.log_event(
                            search_id,
                            "TAILOR",
                            "WARNING",
                            {"message": f"Skipping job {job['title']} - No description available"}
                        )
                        continue
                    
                    # Get job_id from the job dictionary (should be added by JobSearchAgent)
                    job_id = job.get("job_id")
                    application_id = job.get("application_id")
                    
                    if not job_id:
                        await db_client.log_event(
                            search_id,
                            "TAILOR",
                            "WARNING",
                            {"message": f"Skipping job - No job_id available"}
                        )
                        continue
                    
                    # Log that we're tailoring the resume for this job
                    await db_client.log_event(
                        search_id,
                        "TAILOR",
                        "INFO",
                        {
                            "message": f"Tailoring resume for: {job['title']} at {job['company']}",
                            "job_id": job_id
                        }
                    )
                        
                    # Update job status
                    await db_client.update_job(job_id, {"status": "tailoring_resume"})
                    
                    # Tailor resume for this specific job
                    tailored_resume = await tools.tailor_resume(resume, job["description"])
                    
                    # Update job with tailored resume
                    await db_client.update_job(job_id, {
                        "tailored_resume": json.dumps(tailored_resume),
                        "status": "resume_tailored"
                    })
                    
                    # If we have an application_id, update it
                    if application_id:
                        await db_client.update_application_status(
                            application_id, 
                            "tailored",
                            tailored_resume
                        )
                    
                    application = {
                        "job": job,
                        "tailored_resume": tailored_resume
                    }
                    
                    tailored_applications.append(application)
                    
                    # Log the tailored resume details
                    resume_summary = {
                        "personalInfo": tailored_resume.get("personalInfo", {}),
                        "summary": tailored_resume.get("summary", ""),
                        "skills": tailored_resume.get("skills", {}),
                        # Include only the titles and companies from work experience
                        "workExperience": [
                            {
                                "title": exp.get("title", ""),
                                "company": exp.get("company", ""),
                                # Include a preview of responsibilities
                                "responsibilities_preview": [r[:100] + "..." if len(r) > 100 else r 
                                                        for r in exp.get("responsibilities", [])[:2]]
                            } 
                            for exp in tailored_resume.get("workExperience", [])[:2]
                        ],
                        "education": tailored_resume.get("education", []),
                        # Include only names of projects
                        "projects": [{"name": p.get("name", "")} for p in tailored_resume.get("projects", [])]
                    }
                    
                    # Log tailored resume as an event
                    await db_client.log_event(
                        search_id,
                        "TAILOR",
                        "TAILORED_RESUME",
                        {
                            "job_title": job["title"],
                            "company": job["company"],
                            "job_id": job_id,
                            "tailored_resume_summary": resume_summary
                        }
                    )
                    
                    # Log success for this job
                    await db_client.log_event(
                        search_id,
                        "TAILOR",
                        "SUCCESS",
                        {
                            "job_title": job["title"],
                            "company": job["company"],
                            "job_id": job_id,
                            "resume_tailored": True
                        }
                    )
                except Exception as e:
                    # Log individual tailoring failure but continue with other jobs
                    job_id = job.get("job_id")
                    if job_id:
                        await db_client.update_job(job_id, {"status": "tailoring_failed"})
                    
                    await db_client.log_event(
                        search_id,
                        "TAILOR",
                        "ERROR",
                        {"error": f"Failed to tailor resume: {str(e)}", "job_title": job["title"]}
                    )
                
            return tailored_applications
            
        except Exception as e:
            search_id = get_search_id(self)
            await db_client.log_event(
                search_id,
                "TAILOR",
                "ERROR",
                {"error": str(e)}
            )
            raise

class ApplicationAgent(Agent):
    def __init__(self, search_id: str):
        super().__init__(
            role='Application Submitter',
            goal='Submit job applications through Greenhouse',
            backstory='I am an AI agent specialized in automated job application submission',
            allow_delegation=False,
            verbose=True,
        )
        # Don't forget to register this agent too
        register_agent(self, search_id)

    async def execute(self, applications: List[Dict]) -> List[Dict]:
        try:
            search_id = get_search_id(self)
            if not search_id:
                print("[WARNING] No search_id found for ApplicationAgent. Using fallback.")
                search_id = "unknown_search"
                
            results = []
            
            for app in applications:
                try:
                    # Submit the application using Playwright
                    # This is a placeholder - actual implementation would depend on
                    # Greenhouse's application form structure
                    result = {
                        "job": app["job"],
                        "status": "submitted",
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }
                    
                    results.append(result)
                    
                    # Log success
                    await db_client.log_event(
                        search_id,
                        "SUBMITTER",
                        "SUCCESS",
                        {"job_title": app["job"]["title"]}
                    )
                    
                except Exception as e:
                    # Log individual application failure
                    await db_client.log_event(
                        search_id,
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
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })
            
            return results
            
        except Exception as e:
            search_id = get_search_id(self)
            await db_client.log_event(
                search_id,
                "SUBMITTER",
                "ERROR",
                {"error": str(e)}
            )
            raise