from crewai_tools import SerperDevTool
from groq import Groq
from playwright.async_api import async_playwright
import os
import json
from typing import Dict, List
import asyncio
import time

class JobSearchTools:
    def __init__(self):
        self.serper_tool = SerperDevTool(
            api_key=os.getenv("SERPER_API_KEY"),
            n_results=5,
            search_type="search"
        )
        
        self.groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    async def search_jobs(self, position: str, experience_level: str) -> List[Dict]:
        """Search for jobs using Serper with improved error handling"""
        query = f"site:job-boards.greenhouse.io {position} {experience_level}"
        
        try:
            results = self.serper_tool.run(search_query=query)
            
            jobs = []
            # extract the organic results array from the response
            organic_results = results.get('organic', [])
            
            for result in organic_results:
                jobs.append({
                    "title": result.get("title", "Unknown Position"),
                    "link": result.get("link", ""),
                    "company": result.get("source", "Unknown"), 
                    "posted_date": result.get("date", "Unknown")
                })
            
            if not jobs:
                print("Warning: No jobs found in search results")
                
            return jobs
        except Exception as e:
            print(f"Error in search_jobs: {str(e)}")
            return []

    async def fetch_job_description(self, url: str) -> str:
        """Fetch job description using Playwright with improved error handling and timeout"""
        # Add a timeout for the entire operation
        try:
            async with asyncio.timeout(60):  # 60 second timeout for the entire operation
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()
                    
                    try:
                        await page.goto(url, timeout=20000)  # 20 second timeout for page load
                        
                        # wait for either of the common selectors for job descriptions
                        selector_found = False
                        possible_selectors = [
                            ".job__description.body", 
                            ".job-description",
                        ]
                        
                        for selector in possible_selectors:
                            try:
                                await page.wait_for_selector(selector, timeout=5000)
                                description = await page.inner_text(selector)
                                selector_found = True
                                break
                            except:
                                continue
                        
                        if not selector_found:
                            # if no specific selector works, get the whole page content
                            description = await page.content()
                            # extract text from HTML content
                            description = description.replace("<", " <").replace(">", "> ")
                            
                        return description
                    except Exception as e:
                        print(f"Error fetching job description: {str(e)}")
                        return f"Failed to fetch job description: {str(e)}"
                    finally:
                        await browser.close()
        except asyncio.TimeoutError:
            return "Timeout: Failed to fetch job description within the allowed time."
        except Exception as e:
            print(f"Unexpected error in fetch_job_description: {str(e)}")
            return f"Error: {str(e)}"

    async def tailor_resume(self, resume: Dict, job_description: str) -> Dict:
        """Tailor resume using Groq LLM with robust error handling and timeouts"""
        # start with a copy of the original resume that we can modify
        tailored_resume = resume.copy()
        
        try:
            # create a compact version of the resume with only summary, work experience, and projects
            compact_resume = {
                "summary": resume.get("summary", ""),
                "workExperience": resume.get("workExperience", []),
                "projects": resume.get("projects", [])
            }
            
            # extract key information from job description to reduce tokens
            # keeping only the first 1000 characters of the job description to reduce token count
            job_description_summary = job_description[:1000] + "..." if len(job_description) > 1000 else job_description
            
            prompt = f"""
            Given this job description:
            {job_description_summary}
            
            And these relevant parts of a resume:
            {json.dumps(compact_resume, indent=2)}
            
            Tailor the resume to highlight relevant experience and skills for this job.
            Focus on:
            1. Creating a targeted summary that connects to the job requirements
            2. Highlighting relevant work experience with job-specific wording
            3. Selecting most relevant projects that demonstrate required skills
            
            Return the modified parts in the same JSON structure, modifying ONLY the summary, workExperience, and projects sections.
            """
            
            # set timeout for API call
            start_time = time.time()
            timeout = 30  # 30 seconds timeout
            
            # calling the Groq API with the reduced content and a timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.groq_client.chat.completions.create,
                    messages=[{"role": "user", "content": prompt}],
                    model="mixtral-8x7b-32768",
                    temperature=0.7,
                ),
                timeout=timeout
            )
            
            # successfully got a response, parse it
            content = response.choices[0].message.content
            
            try:
                tailored_content = json.loads(content)
                
                # merge tailored content with original resume
                if "summary" in tailored_content:
                    tailored_resume["summary"] = tailored_content["summary"]
                if "workExperience" in tailored_content:
                    tailored_resume["workExperience"] = tailored_content["workExperience"]
                if "projects" in tailored_content:
                    tailored_resume["projects"] = tailored_content["projects"]
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from Groq API: {str(e)}")
                print(f"Raw content: {content[:200]}...") 
                tailored_resume["summary"] = f"NOTE: An error occurred while tailoring this resume. Original resume used. Error: {str(e)}"
                
            return tailored_resume
            
        except asyncio.TimeoutError:
            print(f"Groq API timed out after {timeout} seconds")
            tailored_resume["summary"] = f"NOTE: The resume tailoring service timed out. Original resume used."
            return tailored_resume
        except Exception as e:
            print(f"Error with Groq API: {str(e)}")
            tailored_resume["summary"] = f"NOTE: {resume.get('summary', '')} (An error occurred during tailoring: {str(e)})"
            return tailored_resume


# Create a singleton instance
tools = JobSearchTools()