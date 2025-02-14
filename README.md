Tables:
1. User
    - user_id
    - First name
    - Last name
    - Email
    - Phone
    - Resume
    - Cover Letter
    - Gender
    - Disability Status
    - Veteran Status
    - isHispanic
    - Ethinic Status
    - LinkedIn 
    - Github
    - Portfolio
    - needSponsorship
    - isLegally authorised
    - open to relocation

2. Education
    - id (auto increment)
    - school
    - degree
    - discipline
    - end date
    - start date
    - user_id (fk)

3. Jobs
    - job id
    - job link
    - job title
    - date posted
    - job description
    - status
    - tailored resume
    - run id (fk)

4. Runs
    - run id (pk)
    - timestamp
    - position
    - status

user enters position and exp level -> run id, return (async DB push) -> job positing UI (async db)


Endpoints
1. POST /api/search
Request Body: Position and Experience Level
Response: run_id (uuid)

2. GET /api/search/<run_id>
Request body: run_id
Response: events

3. GET /api/job/<job_id>
Request body: job_id
Response: events

backend file command: uvicorn api:app --reload --host 0.0.0.0 --port 8000


Objective: Develop an automated job application system using CrewAI that helps users apply for jobs in the US. The system will leverage various APIs and technologies for job scraping, resume tailoring, and application submission.

Tech Stack:

- Backend: Python Flask

- Frontend: Next.js

- Database: PostgreSQL

User Flow:

1. User Input:

   - The user enters the desired job title and selects their experience level (entry-level, mid-level, senior).

   - The user submits their personal information (education, projects, work experience, skills, summary) through a form.

2. Job Listing Scraping:

   - An AI agent will use the Serper API to scrape job listings specifically from the Greenhouse job board (job-boards.greenhouse.io).

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

- Return a run_id to the user that corresponds to the job position they searched for, allowing them to track the overall job application process. Additionally, return a job_id for each job posting to check the status of its application.

Database Structure:

- Store user information and application status in PostgreSQL for tracking and reference.

Output Requirements:

- Ensure that the system efficiently processes user inputs, manages multi-threading for concurrent job applications, and provides real-time updates to the user regarding their application status.