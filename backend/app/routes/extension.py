from fastapi import APIRouter, HTTPException, Header
from app.models import ExchangeRequestBody, JobsIngestRequestBody, AutofillPlanRequest, AutofillPlanResponse, AutofillAgentInput, AutofillAgentOutput, AutofillEventRequest, AutofillFeedbackRequest, AutofillSubmitRequest, JobStatusRequest, JobStatusResponse, ResumeMatchRequest, ResumeMatchResponse, AutofillEventResponse, AutofillEventsListResponse
from app.services.supabase import Supabase
from app.services.llm import LLM
from app.services.autofill_agent_dag import DAG
from app.repositories import UserRepository, JobApplicationRepository, AutofillRepository
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import dotenv
import os
import json
from jose import JWTError, jwt
from app.utils import clean_content, extract_jd, normalize_url, infer_job_site_type, extract_job_url_info
import aiohttp

# Loading the env variables from backend directory
BASE_DIR = Path(__file__).parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

# Initialize LLM client
llm = LLM()
# Initialize Supabase client
supabase = Supabase()
# Initialize Autofill Agent DAG
dag = DAG()
# Initialize repositories
user_repo = UserRepository(supabase.db_connection)
job_app_repo = JobApplicationRepository(supabase.db_connection)
autofill_repo = AutofillRepository(supabase.db_connection)

router = APIRouter()

@router.post("/connect/start")
def get_one_time_code_for_extension(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]

        # Get user from Supabase using the token
        user_response = supabase.client.auth.get_user(jwt=token)

        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        one_time_code = secrets.token_urlsafe(32)
        one_time_code_hash = hashlib.sha256(one_time_code.encode('utf-8')).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        autofill_repo.create_connect_code(user_response.user.id, one_time_code_hash, expires_at)

        return {"one_time_code": one_time_code}

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to generate one-time code: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    

@router.post("/connect/exchange")
def exchange_one_time_code_for_token(body: ExchangeRequestBody):
    try:
        one_time_code_hash = hashlib.sha256(body.one_time_code.encode('utf-8')).hexdigest()

        # Verify the one-time code and get user_id
        code_record = autofill_repo.get_valid_connect_code(one_time_code_hash)
        if code_record is None:
            raise HTTPException(status_code=401, detail="Invalid or expired one-time code")

        code_id = code_record["id"]
        user_id = code_record["user_id"]

        # Mark the code as used
        autofill_repo.mark_connect_code_used(code_id)

        # Generate JWT token
        data = {
            'sub': user_id,
            'exp': datetime.utcnow() + timedelta(minutes=180),
            'iss': 'applyai-api',
            'aud': 'applyai-extension',
            'install_id': body.install_id
        }
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")
        token = jwt.encode(data, secret_key, algorithm=algorithm)

        return {"token": token}

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to exchange one-time code: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    

@router.get("/me")
def fetch_user_using_extension_token(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        email = user_repo.get_email_from_auth(user_id)
        if not email:
            raise HTTPException(status_code=401, detail="User not found")

        user_info = user_repo.get_basic_info(user_id)
        full_name = user_info.get("full_name") if user_info else None

        return {"email": email, "id": user_id, "full_name": full_name}

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to fetch user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    

@router.post("/jobs/ingest")
async def ingest_job_via_extension(body: JobsIngestRequestBody, authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Normalize URL to prevent duplicates from tracking params, trailing slashes, etc.
        normalized_url = normalize_url(body.job_link)

        # Check if job application already exists for this user and normalized URL
        # Do this BEFORE the expensive LLM extraction call
        existing_job = job_app_repo.get_by_normalized_url(user_id, normalized_url)
        if existing_job:
            logger.info(f"Job application already exists with id={existing_job['id']}. Returning existing data.")
            return {
                "job_application_id": existing_job["id"],
                "url": existing_job["url"],
                "job_title": existing_job["job_title"],
                "company": existing_job["company"],
            }

        # Job doesn't exist - proceed with extraction
        if body.dom_html:
            logger.info(f"Successfully fetched the content from the DOM!")
            cleaned_content = clean_content(body.dom_html)
            jd_dom_html = body.dom_html
        else:
            # Creating a async context manager that creates and manages HTTP client session
            async with aiohttp.ClientSession() as session:
                # Creating a context manager that manages the HTTP response
                async with session.get(body.job_link) as response:
                    if response.status != 200:
                        logger.info(f"Failed to fetch content from the URL: {response.status}")
                        raise HTTPException(status_code=response.status, detail=f"Failed to fetch content from the URL: {response.status}")
                    content = await response.text()
                    jd_dom_html = content
                    logger.info(f"Successfully fetched the content from the URL!")
                    cleaned_content = clean_content(content)

        # Extract JD using LLM
        jd = extract_jd(cleaned_content, llm, body.job_link)
        logger.info(f"Successfully extracted the job description!")

        job_site_type = infer_job_site_type(body.job_link)

        # Create new job application
        job_application_id = job_app_repo.create(
            user_id=user_id,
            job_title=jd.job_title,
            company=jd.company,
            url=body.job_link,
            normalized_url=normalized_url,
            jd_dom_html=jd_dom_html,
            job_posted=jd.job_posted,
            job_description=jd.job_description,
            required_skills=jd.required_skills,
            preferred_skills=jd.preferred_skills,
            education_requirements=jd.education_requirements,
            experience_requirements=jd.experience_requirements,
            keywords=jd.keywords,
            job_site_type=job_site_type,
            open_to_visa_sponsorship=jd.open_to_visa_sponsorship,
        )
        logger.info(f"Successfully created new job application in DB!")

        return {
            "job_application_id": job_application_id,
            "url": body.job_link,
            "job_title": jd.job_title,
            "company": jd.company
        }
    except aiohttp.ClientError as e:
        logger.info(f"Invalid job_link URL provided: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to ingest job: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to ingest job")


@router.post("/jobs/status")
def get_job_status(body: JobStatusRequest, authorization: str = Header(None)):
    """
    Get the status of a job application based on URL.

    Handles Lever (/apply suffix) and Ashby (/application suffix) URL patterns
    by stripping the suffix to match against the base JD URL.
    Greenhouse is treated as combined (single page with both JD and form).
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Extract job board info and base URL
        url_info = extract_job_url_info(body.url)
        base_url = url_info["base_url"]
        page_type = url_info["page_type"]

        # Normalize the base URL for matching
        normalized_base_url = normalize_url(base_url)

        # Look up job application by normalized URL
        job_record = job_app_repo.get_status_by_normalized_url(user_id, normalized_base_url)
        if not job_record:
            return JobStatusResponse(found=False, page_type=page_type)

        job_application_id = str(job_record["id"])
        job_title = job_record["job_title"]
        company = job_record["company"]
        job_status = job_record["status"]

        # Determine application state based on job_applications.status and autofill_runs
        run_id = autofill_repo.get_latest_completed_run_id(job_application_id, user_id)

        if job_status == "applied":
            state = "applied"
        elif run_id:
            state = "autofill_generated"
        else:
            state = "jd_extracted"

        logger.info(f"Job status found for job_application_id={job_application_id}, state={state}, page_type={page_type}")

        return JobStatusResponse(
            found=True,
            page_type=page_type,
            state=state,
            job_application_id=job_application_id,
            job_title=job_title,
            company=company,
            run_id=run_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to get job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to get job status")


@router.post("/autofill/plan")
def get_autofill_plan(body: AutofillPlanRequest, authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail='Missing or invalid authorization header')
        
        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if job_application_id belongs to the user_id
        if not job_app_repo.belongs_to_user(body.job_application_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this job application")

        normalized_job_url = normalize_url(body.page_url)
        dom_html_hashed = hashlib.sha256(body.dom_html.encode('utf-8')).hexdigest()

        # Generate signed URL for user's resume (for file upload fields)
        resume_signed_url = None
        try:
            resume_path = user_repo.get_resume_path(user_id)
            if resume_path:
                storage = supabase.client.storage.from_("user-documents")
                signed_urls_response = storage.create_signed_urls(paths=[resume_path], expires_in=3600)
                if isinstance(signed_urls_response, list) and len(signed_urls_response) > 0:
                    first_result = signed_urls_response[0]
                    if isinstance(first_result, dict):
                        resume_signed_url = first_result.get('signedURL') or first_result.get('signed_url')
                    elif hasattr(first_result, 'signedURL'):
                        resume_signed_url = first_result.signedURL
                    elif hasattr(first_result, 'signed_url'):
                        resume_signed_url = first_result.signed_url
        except Exception as e:
            logger.warning(f"Could not generate resume signed URL: {e}")

        # Check if an autofill plan already exists for this job application + page
        existing_plan = autofill_repo.get_completed_plan(body.job_application_id, user_id, normalized_job_url)
        if existing_plan:
            response = AutofillPlanResponse(
                run_id=existing_plan["id"],
                status=existing_plan["status"],
                plan_json=existing_plan["plan_json"],
                plan_summary=existing_plan["plan_summary"],
                resume_url=resume_signed_url,
            )
            logger.info("Autofill plan response: %s", json.dumps(response.model_dump(), ensure_ascii=False))
            return response
        
        # Create a new autofill run
        autofill_run_id = autofill_repo.create_run(
            user_id=user_id,
            job_application_id=body.job_application_id,
            page_url=normalized_job_url,
            dom_html=body.dom_html,
            dom_html_hash=dom_html_hashed,
        )

        # Build the input for the DAG
        autofill_agent_input = AutofillAgentInput(
            run_id=autofill_run_id,
            job_application_id=body.job_application_id,
            user_id=user_id,
            page_url=normalized_job_url,
            dom_html=body.dom_html,
            extracted_fields=[field.model_dump() for field in body.extracted_fields],
        )

        # Fetch the extracted JD details
        jd_record = job_app_repo.get_for_autofill(body.job_application_id)
        if jd_record:
            autofill_agent_input.job_title = jd_record["job_title"]
            autofill_agent_input.company = jd_record["company"]
            autofill_agent_input.job_posted = jd_record["job_posted"]
            autofill_agent_input.job_description = jd_record["job_description"]
            autofill_agent_input.job_site_type = jd_record["job_site_type"]
            autofill_agent_input.required_skills = jd_record["required_skills"]
            autofill_agent_input.preferred_skills = jd_record["preferred_skills"]
            autofill_agent_input.education_requirements = jd_record["education_requirements"]
            autofill_agent_input.experience_requirements = jd_record["experience_requirements"]
            autofill_agent_input.keywords = jd_record["keywords"]
            autofill_agent_input.open_to_visa_sponsorship = jd_record["open_to_visa_sponsorship"]

        # Fetch user details and resume information
        user_record = user_repo.get_for_autofill(user_id)
        if user_record:
            autofill_agent_input.email = user_record["email"]
            autofill_agent_input.full_name = user_record["full_name"]
            autofill_agent_input.first_name = user_record["first_name"]
            autofill_agent_input.last_name = user_record["last_name"]
            autofill_agent_input.phone_number = user_record["phone_number"]
            autofill_agent_input.linkedin_url = user_record["linkedin_url"]
            autofill_agent_input.github_url = user_record["github_url"]
            autofill_agent_input.portfolio_url = user_record["portfolio_url"]
            autofill_agent_input.other_url = user_record["other_url"]
            autofill_agent_input.resume_file_path = user_record["resume"]
            resume_profile = user_record["resume_profile"]
            if isinstance(resume_profile, str):
                try:
                    resume_profile = json.loads(resume_profile)
                except json.JSONDecodeError:
                    resume_profile = None
            autofill_agent_input.resume_profile = resume_profile
            autofill_agent_input.address = user_record["address"]
            autofill_agent_input.city = user_record["city"]
            autofill_agent_input.state = user_record["state"]
            autofill_agent_input.zip_code = user_record["zip_code"]
            autofill_agent_input.country = user_record["country"]
            autofill_agent_input.authorized_to_work_in_us = user_record["authorized_to_work_in_us"]
            autofill_agent_input.visa_sponsorship = user_record["visa_sponsorship"]
            autofill_agent_input.visa_sponsorship_type = user_record["visa_sponsorship_type"]
            autofill_agent_input.desired_salary = user_record["desired_salary"]
            autofill_agent_input.desired_location = user_record["desired_location"]
            autofill_agent_input.gender = user_record["gender"]
            autofill_agent_input.race = user_record["race"]
            autofill_agent_input.veteran_status = user_record["veteran_status"]
            autofill_agent_input.disability_status = user_record["disability_status"]

        # Trigger the autofill agent DAG
        dag_result = dag.app.invoke({"input_data": autofill_agent_input.model_dump()})
        autofill_agent_output = AutofillAgentOutput(
            status=dag_result.get("status"),
            plan_json=dag_result.get("plan_json"),
            plan_summary=dag_result.get("plan_summary"),
        )
        
        # return the autofill plan response
        response = AutofillPlanResponse(
            run_id=autofill_agent_input.run_id,
            status=autofill_agent_output.status,
            plan_json=autofill_agent_output.plan_json,
            plan_summary=autofill_agent_output.plan_summary,
            resume_url=resume_signed_url
        )
        logger.info("Autofill plan response: %s", json.dumps(response.model_dump(), ensure_ascii=False))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to generate autofill plan for run_id {autofill_agent_input.run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to generate autofill plan")
    

@router.post("/autofill/event")
def push_autofill_event(body: AutofillEventRequest, authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail='Missing or invalid authorization header')
        
        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        if not autofill_repo.run_belongs_to_user(body.run_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")

        autofill_repo.create_event(body.run_id, user_id, body.event_type, body.payload)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to log autofill event: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to log autofill event")
    

@router.post("/autofill/feedback")
def submit_autofill_feedback(body: AutofillFeedbackRequest, authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail='Missing or invalid authorization header')
        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")
        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token") 
        
        if not autofill_repo.run_belongs_to_user(body.run_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")

        autofill_repo.create_feedback(
            body.run_id, body.job_application_id, user_id, body.question_signature, body.correction
        )

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to submit autofill feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to submit autofill feedback")
    

@router.post("/autofill/submit")
def submit_autofill_application(body: AutofillSubmitRequest, authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail='Missing or invalid authorization header')
        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        # Decode and verify the JWT token
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if not autofill_repo.run_belongs_to_user(body.run_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")

        # Mark run as submitted and job as applied
        autofill_repo.mark_run_submitted(body.run_id)
        autofill_repo.mark_job_as_applied_from_run(body.run_id)
        autofill_repo.create_event(body.run_id, user_id, 'application_submitted', body.payload)

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to submit autofill application: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to submit autofill application")


@router.post("/resume-match")
def get_resume_match(body: ResumeMatchRequest, authorization: str = Header(None)):
    """
    Compare user's resume against a job description and return match score with keywords.
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM")

        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm], audience='applyai-extension', issuer='applyai-api')
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        if not job_app_repo.belongs_to_user(body.job_application_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this job application")

        # Get JD keywords and skills
        jd_row = job_app_repo.get_keywords_and_skills(body.job_application_id)
        if not jd_row:
            raise HTTPException(status_code=404, detail="Job application not found")

        required_skills = jd_row["required_skills"] or []
        preferred_skills = jd_row["preferred_skills"] or []
        keywords = jd_row["keywords"] or []

        # Get user's resume profile
        resume_profile = user_repo.get_resume_profile(user_id)

        # Extract resume skills and text
        resume_skills = []
        resume_text = ""
        if resume_profile:
            resume_skills = resume_profile.get("skills") or []
            # Build searchable text from experience and projects
            for exp in resume_profile.get("experience") or []:
                resume_text += f" {exp.get('position', '')} {exp.get('description', '')}"
            for proj in resume_profile.get("projects") or []:
                resume_text += f" {proj.get('name', '')} {proj.get('description', '')}"
            resume_text = resume_text.lower()

        # Combine all JD keywords (deduplicated)
        jd_keywords = list(set(
            [s.lower().strip() for s in required_skills] +
            [s.lower().strip() for s in preferred_skills] +
            [k.lower().strip() for k in keywords]
        ))

        # Normalize resume skills for matching
        resume_skills_lower = [s.lower().strip() for s in resume_skills]

        matched = []
        missing = []

        for kw in jd_keywords:
            if not kw:
                continue
            # Check if keyword is in resume skills or text
            if kw in resume_skills_lower or kw in resume_text:
                matched.append(kw)
            else:
                missing.append(kw)

        # Calculate score
        total = len(matched) + len(missing)
        score = round((len(matched) / total) * 100) if total > 0 else 0

        return ResumeMatchResponse(
            score=score,
            matched_keywords=matched,
            missing_keywords=missing
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to get resume match: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to get resume match")


@router.get("/autofill/events/{job_application_id}")
def get_autofill_events(job_application_id: str, authorization: str = Header(None)):
    """
    Get all autofill events for a job application.
    Returns events in reverse chronological order (newest first).
    Called from the web frontend dashboard using a Supabase JWT token.
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]

        # Use Supabase auth (same as /db endpoints) since this is called from the web frontend
        user_response = supabase.client.auth.get_user(jwt=token)
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = user_response.user.id

        if not job_app_repo.belongs_to_user(job_application_id, user_id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this job application")

        rows = autofill_repo.get_events_for_job_application(job_application_id, user_id)

        events = [
            AutofillEventResponse(
                id=str(row["id"]),
                run_id=str(row["run_id"]),
                event_type=row["event_type"],
                payload=row["payload"] if row["payload"] else None,
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
            )
            for row in rows
        ]

        return AutofillEventsListResponse(events=events, total_count=len(events))

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to get autofill events: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to get autofill events")
