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