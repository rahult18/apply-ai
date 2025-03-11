from crewai_tools import SerperDevTool
from groq import Groq
from playwright.async_api import async_playwright
import os
import json
from typing import Dict, List
import asyncio

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
        """Search for jobs using Serper"""
        query = f"site:job-boards.greenhouse.io {position} {experience_level}"
        
        # Pass search_query as a named parameter, not positional
        results = self.serper_tool.run(search_query=query)
        
        jobs = []
        # Extract the organic results array from the response
        organic_results = results.get('organic', [])
        
        for result in organic_results:
            jobs.append({
                "title": result.get("title"),
                "link": result.get("link"),
                "company": result.get("source", "Unknown"),  # 'source' is used instead of 'company' in the response
                "posted_date": result.get("date", "Unknown")
            })
        return jobs

    async def fetch_job_description(self, url: str) -> str:
        """Fetch job description using Playwright"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                await page.goto(url, timeout=30000)  # Increased timeout for page load
                
                # Wait for either of the common selectors for job descriptions
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
                    # If no specific selector works, get the whole page content
                    description = await page.content()
                    # Extract text from HTML content (simplified approach)
                    description = description.replace("<", " <").replace(">", "> ")
                    
                return description
            except Exception as e:
                print(f"Error fetching job description: {str(e)}")
                return f"Failed to fetch job description: {str(e)}"
            finally:
                await browser.close()

    async def tailor_resume(self, resume: Dict, job_description: str) -> Dict:
        """Tailor resume using Groq LLM, processing in chunks to avoid token limits"""
        try:
            # Create a compact version of the resume with only summary, work experience, and projects
            compact_resume = {
                "summary": resume.get("summary", ""),
                "workExperience": resume.get("workExperience", []),
                "projects": resume.get("projects", [])
            }
            
            # Extract key information from job description to reduce tokens
            # Keep only the first 1000 characters of the job description to reduce token count
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
            
            # Call the Groq API with the reduced content
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="mixtral-8x7b-32768",
                temperature=0.7,
            )
            
            tailored_content = json.loads(response.choices[0].message.content)
            
            # Merge tailored content with original resume
            tailored_resume = resume.copy()
            if "summary" in tailored_content:
                tailored_resume["summary"] = tailored_content["summary"]
            if "workExperience" in tailored_content:
                tailored_resume["workExperience"] = tailored_content["workExperience"]
            if "projects" in tailored_content:
                tailored_resume["projects"] = tailored_content["projects"]
            
            return tailored_resume
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from Groq API: {str(e)}")
            # In case of JSON parsing error, still return something useful
            return resume
        except Exception as e:
            print(f"Error with Groq API: {str(e)}")
            # Return the original resume if there's an API error
            return resume


# Create a singleton instance
tools = JobSearchTools()