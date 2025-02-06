from crewai_tools import SerperDevTool
from typing import List, Dict
from job_manager import EventStore
from playwright.async_api import async_playwright
import asyncio
import psycopg2
import os
from dotenv import load_dotenv
from groq import Groq
import json

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "dbname": os.getenv("dbname")
}

class JobScraperAgent:
    """
        This agent is responsible for scraping job listings and processing job descriptions
        Handles both initial job search and detailed job description fetching
    """
    
    
    def __init__(self, run_id: str, position: str, experience: str, event_store: EventStore):
        """
            Initialize the scraper agent with search parameters and tracking
            
            Args:
                run_id: Unique identifier for this job search run
                position: Job title/position to search for
                experience: Required experience level
                event_store: EventStore instance for tracking progress
        """
        self.run_id = run_id
        self.position = position
        self.experience = experience
        self.event_store = event_store
        self.serper_tool = SerperDevTool(
            n_results=5, #only fetches the first 5 results in the search page
            search_type="search"
        )
    
    def _build_search_query(self) -> str:
        """
            Constructs the search query based on position and experience level
            Includes appropriate filters for experience level
            
            Returns:
                str: Formatted search query string
        """
        
        # this dictionary maps the experience levels to exclusion terms
        experience_filters = {
            "Entry Level": '-lead -senior -principal -staff -architect',
            "Mid Level": '-principal -lead -staff -architect',
            "Senior": 'senior'
        }
        
        filter_terms = experience_filters.get(self.experience, '')
        return f'site:job-boards.greenhouse.io "{self.position}" AND "united states" {filter_terms}'
    
    def _parse_job_listings(self, search_results: Dict) -> List[Dict]:
        """
            Parses raw search results into structured job listings
            Args:
                search_results: Raw results from search API
                
            Returns:
                List[Dict]: List of formatted job listings
        """
        job_listings = []
        
        for result in search_results.get('organic', [])[:5]:
            job_listing = {
                'job_title': result.get('title', '').split(' - ')[0],
                'company': result.get('title', '').split(' - ')[-1],
                'job_link': result.get('link', ''),
                'date_posted': result.get('date', ''),
            }
            job_listings.append(job_listing)
        
        return job_listings

    def scrape_jobs(self) -> List[Dict]:
        """
            Performs the initial job search and listing collection
            Handles the complete process from search to parsing
            
            Returns:
                List[Dict]: List of job listings
        """
        try:
            self.event_store.add_event(
                self.run_id,
                f"Starting job search for {self.position} - {self.experience}"
            )
            
            search_query = self._build_search_query()
            self.event_store.add_event(
                self.run_id,
                f"Executing search with query: {search_query}"
            )
            
            results = self.serper_tool.run(search_query=search_query)
            
            self.event_store.add_event(
                self.run_id,
                f"Retrieved {len(results.get('organic', []))} results"
            )
            
            job_listings = self._parse_job_listings(results)
            
            self.event_store.add_event(
                self.run_id,
                f"Successfully parsed {len(job_listings)} job listings"
            )
            
            return job_listings
            
        except Exception as e:
            self.event_store.add_event(
                self.run_id,
                f"Error during job scraping: {str(e)}"
            )
            raise
    
    
    async def fetch_job_description(self, job: dict) -> None:
        """
        Fetches and stores the detailed job description for a single job listing
        Uses Playwright for web scraping and updates database with results
        
        Args:
            job: Dictionary containing job information
        """
        try:
            print(f"\n[DEBUG] Starting JD fetch for job_id: {job['job_id']}, title: {job['job_title']}")
            print(f"[DEBUG] Job URL: {job['job_link']}")
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            async with async_playwright() as p:
                # Update status to indicate fetching in progress
                cur.execute(
                    """
                    UPDATE jobs 
                    SET status = 'FETCHING_JD'
                    WHERE job_link = %s AND run_id = %s
                    """,
                    (job['job_link'], self.run_id)
                )
                conn.commit()
                print(f"[DEBUG] Updated status to FETCHING_JD for job_id: {job['job_id']}")
                
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                try:
                    await page.goto(job['job_link'], wait_until='networkidle')
                    description_element = await page.wait_for_selector("div.job__description.body")
                    
                    if description_element:
                        job_description = await description_element.inner_text()
                        print(f"[DEBUG] Extracted description for job_id: {job['job_id']} (length: {len(job_description)})")
                        
                        # Update database with fetched description
                        cur.execute(
                            """
                            UPDATE jobs 
                            SET job_description = %s, status = 'JD_FETCHED'
                            WHERE job_link = %s AND run_id = %s
                            """,
                            (job_description, job['job_link'], self.run_id)
                        )
                        conn.commit()
                        
                        self.event_store.add_event(
                            self.run_id,
                            f"Successfully fetched JD for {job['job_link']}"
                        )
                    
                except Exception as e:
                    print(f"[DEBUG] Error fetching description for job_id: {job['job_id']}: {str(e)}")
                    # handle failures in description fetching
                    cur.execute(
                        """
                        UPDATE jobs 
                        SET status = 'JD_FAILED'
                        WHERE job_link = %s AND run_id = %s
                        """,
                        (job['job_link'], self.run_id)
                    )
                    conn.commit()
                    
                    self.event_store.add_event(
                        self.run_id,
                        f"Failed to fetch JD for {job['job_link']}: {str(e)}"
                    )
                
                finally:
                    await page.close()
                    await browser.close()
                    
        except Exception as e:
            print(f"[DEBUG] Critical error in fetch_job_description for job_id: {job['job_id']}: {str(e)}")
            self.event_store.add_event(
                self.run_id,
                f"Error in fetch_job_description: {str(e)}"
            )
        finally:
            cur.close()
            conn.close()

    async def process_job_descriptions(self, jobs: List[dict]) -> None:
        """
        Processes all job descriptions concurrently
        Creates and manages multiple fetch tasks
        
        Args:
            jobs: List of job listings to process
        """
        print(f"[DEBUG] Starting to process {len(jobs)} job descriptions")
        tasks = [self.fetch_job_description(job) for job in jobs]
        await asyncio.gather(*tasks)
        print("[DEBUG] Completed processing all job descriptions")
        

class ResumeTailorAgent:
    """
        AI agent responsible for tailoring resumes based on job descriptions
        Uses Mixtral model via Groq for customization
    """
    
    def __init__(self, run_id: str, event_store: EventStore):
        """
            Initialize the tailor agent with tracking and API clients
            
            Args:
                run_id: Unique identifier for this job search run
                event_store: EventStore instance for tracking progress
        """
        self.run_id = run_id
        self.event_store = event_store
        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )
        
    def _load_resume(self) -> dict:
        """
            Loads the user's resume from JSON file
            
            Returns:
                dict: Resume data
        """
        with open('user_resume.json', 'r') as f:
            return json.load(f)
            
    def _create_prompt(self, resume: dict, job_description: str) -> str:
        """
            Creates the prompt for the AI model
            
            Args:
                resume: Original resume data
                job_description: Job description to tailor for
                
            Returns:
                str: Formatted prompt
        """
        return f"""You are an expert ATS resume optimizer and tailoring specialist. Your task is to modify a JSON resume to maximize its match with a specific job description while maintaining authenticity and professional standards.

            Key Instructions:
            1. Analyze the job description first, identifying:
            - Required technical skills and tools
            - Key responsibilities and deliverables
            - Industry-specific terminology and frameworks
            - Soft skills and cultural requirements

            2. Modify ONLY these resume sections to align with the job requirements:
            - summary: Rewrite to emphasize relevant experience and skills that match the job
            - skills: Reorder categories and items to prioritize relevant skills first
            - workExperience[].responsibilities: Adjust language and emphasis to match job requirements
            - projects[].description: Highlight aspects that demonstrate relevant expertise

            3. Follow these optimization rules:
            - Use strong action verbs from the job description
            - Include specific metrics and quantifiable achievements
            - Mirror the job description's key terminology
            - Maintain professional tone and factual accuracy
            - Keep all modifications realistic and truthful
            - Ensure all technical terms are used in proper context
            - Preserve original structure and formatting of the JSON

            4. ATS Optimization Requirements:
            - Use standard industry terms, not abbreviations
            - Include relevant keywords from the job description naturally
            - Maintain proper JSON structure for parsing
            - Keep formatting clean and consistent

            Input Job Description:
            {job_description}

            Resume to Optimize (JSON format):
            {json.dumps(resume, indent=2)}

            Response Requirements:
            1. Return ONLY the modified JSON object
            2. Maintain exact same JSON structure
            3. Ensure output is valid, parseable JSON
            4. No explanations or additional text
            5. No Markdown code block markers"""        
        
    async def tailor_resume(self, job: dict) -> dict:
        """
            Tailors the resume for a specific job
            
            Args:
                job: Dictionary containing job information including description
                
            Returns:
                dict: Tailored resume data
        """
        try:
            self.event_store.add_event(
                self.run_id,
                f"Starting resume tailoring for job: {job['job_title']}"
            )
            
            print(f"\n[DEBUG] Starting resume tailoring for job id: {job['job_id']}")
            
            # Load original resume
            resume = self._load_resume()
            
            # Create prompt for the model
            prompt = self._create_prompt(resume, job['job_description'])
            
            # Get tailored resume from Mixtral
            completion = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ATS resume tailoring assistant. You excel at modifying resumes to match job descriptions while maintaining proper JSON structure."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Lower temperature for more consistent JSON output
                top_p=0.9,
                max_tokens=4000,
                stream=False
            )
            
            # Parse the response
            response_content = completion.choices[0].message.content.strip()
            # Remove any markdown code block markers if present
            if response_content.startswith("```json"):
                response_content = response_content[7:-3]
            elif response_content.startswith("```"):
                response_content = response_content[3:-3]
                
            tailored_resume = json.loads(response_content)
            
            print(f"\n[DEBUG] Successfully tailored resume for job id: {job['job_id']}")
            
            self.event_store.add_event(
                self.run_id,
                f"Successfully tailored resume for job: {job['job_title']}"
            )
            
            return tailored_resume
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}"
            print(f"\n[DEBUG] {error_msg}")
            self.event_store.add_event(
                self.run_id,
                f"Error tailoring resume for {job['job_title']}: {error_msg}"
            )
            raise
            
        except Exception as e:
            error_msg = f"Error during resume tailoring: {str(e)}"
            print(f"\n[DEBUG] {error_msg}")
            self.event_store.add_event(
                self.run_id,
                f"Error tailoring resume: {error_msg}"
            )
            raise       
        
        