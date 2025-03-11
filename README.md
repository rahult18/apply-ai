# Apply AI: Automated Job Application System

A sophisticated system that automates the job application process using AI agents, built with CrewAI, FastAPI, Celery, and Supabase.

## Overview

This project is an automated job application system that helps users find and apply for jobs. It leverages AI agents to search for relevant job postings, tailor resumes for each job, and (optionally) submit applications automatically.

The system follows this workflow:
1. User submits job search criteria (position and experience level)
2. System searches for job postings on Greenhouse job boards
3. For each relevant job found, the system tailors the user's resume to match the job requirements
4. (Optional) The system can automatically submit applications

## Project Architecture

The application is built with a modern tech stack:

- **Backend**: Python FastAPI for RESTful API endpoints
- **Frontend**: Next.js (not included in this repository)
- **Database**: Supabase for data persistence and real-time updates
- **AI Agent Orchestration**: CrewAI for coordinating specialized AI agents
- **Background Processing**: Celery with Redis for asynchronous task management
- **External APIs**:
  - Serper API for job listings scraping
  - Groq LLM API for resume tailoring
  - Playwright for web automation

## System Flow

1. When a user creates a search, it is initially set to "QUEUED" status
2. A Celery task is created to process the search asynchronously
3. The Celery worker picks up the task and runs the job search process:
   - JobSearchAgent finds relevant job postings
   - For each job, details and job descriptions are fetched
   - ResumeTailorAgent customizes the resume for each job
   - Results are stored in the database
4. Throughout the process, events are logged to the database
5. The user can check the status at any time through the API

## Concurrency and Performance Considerations

- **Async Operations**: FastAPI and asyncio enable efficient handling of multiple requests
- **Background Processing**: Celery offloads intensive tasks from the web server
- **Task Isolation**: Each search runs as a separate Celery task, ensuring isolation
- **Parallel Job Processing**: Within a search, multiple jobs are processed concurrently using asyncio
- **Error Resilience**: Failures in processing individual jobs don't affect the entire search process

## System Components

### Agents (agents.py)

Three specialized AI agents built with CrewAI:

1. **JobSearchAgent**: Searches for job postings using the Serper API
2. **ResumeTailorAgent**: Tailors resumes to match job requirements using Groq LLM
3. **ApplicationAgent**: Submits applications through web automation

### Crew Orchestration (crew.py)

The `JobApplicationCrew` class orchestrates the agents to:
- Execute job searches
- Manage the resume tailoring process
- Handle error cases and partial failures
- Track progress and results

### Database Integration (db.py)

`DatabaseClient` provides methods to:
- Create and track searches
- Log events during the search process
- Store and update job information
- Manage application records
- Retrieve status and latest events

### API Endpoints (main.py)

FastAPI implementation with two main endpoints:
- `POST /api/search`: Create a new job search
- `GET /api/search/{search_id}`: Get the status and events for a search

### Background Processing (celery_config.py, run_celery.py)

#### Celery Implementation Details

The system uses Celery to handle resource-intensive job search processes in the background:

- **Task Definition**: The main Celery task `process_search_task` is defined in `celery_config.py`
- **Worker Configuration**:
  - Task timeout limit: 30 minutes
  - Worker prefetch multiplier: 1 (one task per worker at a time)
  - Task serialization: JSON
  - Automatic task tracking enabled

- **Error Handling**: The Celery task includes comprehensive error handling to:
  - Log errors to the database
  - Update search status appropriately
  - Provide partial results when possible

#### Redis as Message Broker and Result Backend

Redis serves dual roles in this system:

1. **Message Broker**: Queues the job search tasks for processing by Celery workers
2. **Result Backend**: Stores task results temporarily for retrieval

Redis connection details are configured through environment variables, defaulting to `redis://localhost:6379/0` for local development.

### Tools and Utilities (tools.py)

Specialized tools for the agents:
- `search_jobs`: Uses Serper API to find job listings
- `fetch_job_description`: Uses Playwright to extract job descriptions
- `tailor_resume`: Uses Groq LLM to customize resumes

### Agent Registry (registry.py)

Simple in-memory registry to associate agent instances with search IDs, enabling proper event tracking.

## Database Schema

The Supabase database includes the following tables:

1. **searches**: Tracks overall search processes
2. **events**: Records detailed process events
3. **jobs**: Stores information about discovered jobs
4. **applications**: Tracks the application status for each job

A view called **search_status** provides an aggregated view of searches with their events.

## How to Run the System

### Prerequisites

- Python 3.8+
- Redis server
- Supabase account
- API keys for Serper and Groq

### Running the Services

#### Start Redis
```bash
# Start Redis in the foreground
redis-server

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

#### Start Celery Worker
```bash
# Run the Celery worker
python run_celery.py
```

#### Start FastAPI Application
```bash
# Start the API server
uvicorn main:app --reload
```

### Using the System

1. Prepare a user resume in JSON format (see `user_resume.json` for the expected structure)
2. Create a job search by sending a POST request to `/api/search` with:
   ```json
   {
     "position": "software engineer",
     "experience_level": "entry-level"
   }
   ```
3. Use the returned `search_id` to track the search status by sending GET requests to `/api/search/{search_id}`

## Monitoring and Debugging

The system includes extensive logging throughout the process. All events are stored in the `events` table in Supabase with details including:
- Agent type (SEARCHER, TAILOR, etc.)
- Event type (INFO, SUCCESS, ERROR, etc.)
- Timestamp
- Detailed information specific to the event


## Sample API Responses

1. POST `/api/search`
```json
{
    "search_id": "ff531f74-0d84-435c-a959-4d107eb87421",
    "status": "queued"
}
```

2. GET `api/search/search_id`
```json
{
    "search_id": "ff531f74-0d84-435c-a959-4d107eb87421",
    "position": "software engineer",
    "experience_level": "Mid Level",
    "status": "COMPLETED",
    "created_at": "2025-03-11T22:54:32.204669+00:00",
    "updated_at": "2025-03-11T22:55:54.845406+00:00",
    "event_count": 37,
    "event_history": [..],
    "latest_events": [..]
}
```