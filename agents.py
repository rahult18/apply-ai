from crewai_tools import SerperDevTool
from typing import List, Dict
from job_manager import EventStore

class JobScraperAgent:
    def __init__(self, run_id: str, position: str, experience: str, event_store: EventStore):
        self.run_id = run_id
        self.position = position
        self.experience = experience
        self.event_store = event_store
        # Initialize with search parameters
        self.serper_tool = SerperDevTool(
            n_results=5,
            search_type="search"  # Explicitly specify search type
        )
    
    def _build_search_query(self) -> str:
        # Map experience levels to exclusion terms
        experience_filters = {
            "Entry Level": '-lead -senior -principal -staff -architect',
            "Mid Level": '-principal -lead -staff -architect',
            "Senior": 'senior'
        }
        
        filter_terms = experience_filters.get(self.experience, '')
        return f'site:job-boards.greenhouse.io "{self.position}" AND "united states" {filter_terms}'
    
    def _parse_job_listings(self, search_results: Dict) -> List[Dict]:
        job_listings = []
        
        for result in search_results.get('organic', [])[:5]:
            job_listing = {
                'job_title': result.get('title', '').split(' - ')[0],
                'company': result.get('title', '').split(' - ')[-1],
                'job_link': result.get('link', ''),
                'date_posted': result.get('date', ''),
                'job_description': result.get('snippet', '')
            }
            job_listings.append(job_listing)
        
        return job_listings

    def scrape_jobs(self) -> List[Dict]:
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
            
            # Pass as keyword argument explicitly
            results = self.serper_tool.run(search_query=search_query)
            print("\n\nResults: ", results)
            
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