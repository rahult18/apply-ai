from crewai_tools import SerperDevTool
from typing import List, Dict
from job_manager import EventStore
from playwright.async_api import async_playwright
import asyncio
import psycopg2
import os
from dotenv import load_dotenv

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
            print(f"\n[DEBUG] Starting to fetch JD for job: {job['job_title']}")
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
                
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                try:
                    await page.goto(job['job_link'], wait_until='networkidle')
                    description_element = await page.wait_for_selector("div.job__description.body")
                    
                    if description_element:
                        job_description = await description_element.inner_text()
                        
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
        tasks = [self.fetch_job_description(job) for job in jobs]
        await asyncio.gather(*tasks)