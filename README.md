Objective: Develop an automated job application system using CrewAI that helps users apply for jobs in the US. The system will leverage various APIs and technologies for job scraping, resume tailoring, and application submission.

Tech Stack:

- Backend: Python Fast API

- Frontend: Next.js

- Database: Supabase

- AI Agent Orchestration: Crew AI


User Flow:

1. User Input:

   - The user enters the desired job title and selects their experience level (entry-level, mid-level, senior).

   - The user submits their personal information (education, projects, work experience, skills, summary) through a form which will be stored as user_resume.json in the project directory. After the user hits the POST `/api/search` endpoint kick off the crew.

2. Job Listing Scraping:

   - An AI agent will use the Serper API to scrape job listings specifically from the Greenhouse job board (job-boards.greenhouse.io). Use SerperDevTool to scrape the job listings `from crewai_tools import SerperDevTool`

   - This is how you can scrape the job listings
   ```python
   self.serper_tool = SerperDevTool(
        n_results=5, #only fetches the first 5 results in the search page
        search_type="search"
    )
   ```

   - The agent will return details of the 5 job postings: job title, link, company name, and posting date. Meanwhile it will fetch the job description of these posting as background tasks in FastAPI

3. Resume Tailoring and Generation:

   - After fetching the job postings, a second AI agent will initiate.

   - From the extracted job description (JD) from each job link and it will tailor the user's resume using Groq's free LLM.

   - The tailored resume will highlight relevant bullet points from the Work Experience, Projects, and Summary sections.

   - The output will be an ATS-compatible resume in PDF format.

4. Automated Job Application:

   - Once the resume is generated, a final AI agent will use Playwright to autofill the job application fields with the tailored resume.

Concurrency Handling:

- Implement multithreading in Python to manage multiple job postings concurrently.

- Each thread will handle fetching the JD, tailoring the resume, and submitting applications for each job posting.

- Return a search_id to the user that corresponds to the job search they searched for, allowing them to track the overall job application process. 

Database Structure:

- Store user information and application status in Supabase for tracking and reference.
Supabase Tables:
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Searches table to track overall search processes
CREATE TABLE searches (
    search_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    position VARCHAR(255) NOT NULL,
    experience_level VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    results JSONB DEFAULT '{}'::jsonb
);

-- Events table for detailed tracking of the entire process
CREATE TABLE events (
    event_id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    search_id UUID REFERENCES searches(search_id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,  -- 'SEARCHER', 'SCRAPER', 'TAILOR'
    event_type VARCHAR(50) NOT NULL,  -- 'INFO', 'ERROR', 'SUCCESS'
    details JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster event retrieval
CREATE INDEX idx_events_search_id ON events(search_id);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_searches_updated_at
    BEFORE UPDATE ON searches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add RLS policies
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust according to your auth setup)
CREATE POLICY "Enable read access for all users" ON searches
    FOR SELECT
    USING (true);

CREATE POLICY "Enable read access for all users" ON events
    FOR SELECT
    USING (true);

-- Optional: Create a view for easier querying of search status with events
CREATE VIEW search_status AS
SELECT 
    s.search_id,
    s.position,
    s.experience_level,
    s.status,
    s.created_at,
    s.updated_at,
    COUNT(e.event_id) as event_count,
    jsonb_agg(e.details ORDER BY e.created_at) as event_history
FROM searches s
LEFT JOIN events e ON s.search_id = e.search_id
GROUP BY s.search_id, s.position, s.experience_level, s.status, s.created_at, s.updated_at;


Output Requirements:

- Ensure that the system efficiently processes user inputs, manages multi-threading for concurrent job applications, and provides real-time updates to the user regarding their application status.

Expected File directory structure:
job_search_system/
├── .env                # Environment variables (API keys)
├── user_resume.json    # User resume details in JSON
├── main.py        # FastAPI app + endpoints (minimal) 
├── agents.py      # All agents (Searcher, Scraper, Tailor)
├── tools.py       # Shared tools (Serper, Playwright, Groq)
├── crew.py        # CrewAI coordination
└── db.py          # Supabase client

Endpoints
1. POST /api/search
Request Body: Position and Experience Level
Response: search_id (uuid)

2. GET /api/search/<search_id>
Response: events related to that search_id
