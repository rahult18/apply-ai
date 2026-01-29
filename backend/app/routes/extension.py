from fastapi import APIRouter, HTTPException, Header
from app.models import ExchangeRequestBody, JobsIngestRequestBody, AutofillPlanRequest, AutofillPlanResponse, AutofillAgentInput, AutofillAgentOutput, AutofillEventRequest, AutofillFeedbackRequest, AutofillSubmitRequest, JobStatusRequest, JobStatusResponse
from app.services.supabase import Supabase
from app.services.llm import LLM
from app.services.autofill_agent_dag import DAG
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import dotenv
import os
import json
from jose import JWTError, jwt
from app.utils import clean_content, extract_jd, normalize_url, infer_job_site_type, check_if_job_application_belongs_to_user, check_if_run_id_belongs_to_user, extract_job_url_info
import aiohttp
import uuid

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
        created_at = datetime.now(timezone.utc)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # Store the hashed one-time code in the database with an expiration time
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.extension_connect_codes (user_id, code_hash, expires_at, created_at) VALUES(%s, %s, %s, %s)", (user_response.user.id, one_time_code_hash, expires_at, created_at))
            supabase.db_connection.commit()

        return {
            "one_time_code": one_time_code
        }

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
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT id, user_id FROM public.extension_connect_codes WHERE code_hash=%s AND expires_at > NOW() AND used_at IS NULL", (one_time_code_hash,))
            code_record = cursor.fetchone()

            if code_record is None:
                raise HTTPException(status_code=401, detail="Invalid or expired one-time code")
            
            code_id = code_record[0]
            user_id = code_record[1]

            # Marking the code as used
            cursor.execute("UPDATE public.extension_connect_codes SET used_at=NOW() WHERE id=%s", (code_id,))
            supabase.db_connection.commit()
            
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

        # Return the user's access token
        return {
            "token": token
        }

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

        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT email FROM auth.users WHERE id=%s", (user_id,))
            auth_row = cursor.fetchone()
            if not auth_row:
                raise HTTPException(status_code=401, detail="User not found")
            email = auth_row[0]

            cursor.execute("SELECT full_name FROM public.users WHERE id=%s", (user_id,))
            user_row = cursor.fetchone()
            full_name = user_row[0] if user_row else None

        return {
            "email": email,
            "id": user_id,
            "full_name": full_name
        }

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
        with supabase.db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, job_title, company, url FROM job_applications WHERE user_id = %s AND normalized_url = %s LIMIT 1",
                (user_id, normalized_url)
            )
            existing_job = cursor.fetchone()

            if existing_job:
                # Job application already exists - return existing data without LLM call
                job_application_id = existing_job[0]
                job_title = existing_job[1]
                company = existing_job[2]
                url = existing_job[3]
                logger.info(f"Job application already exists with id={job_application_id}. Returning existing data.")

                return {
                    "job_application_id": job_application_id,
                    "url": url,
                    "job_title": job_title,
                    "company": company
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
        with supabase.db_connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO job_applications (user_id, job_title, company, job_posted, job_description, url, normalized_url, required_skills, preferred_skills, education_requirements, experience_requirements, keywords, job_site_type, open_to_visa_sponsorship, jd_dom_html) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (user_id, jd.job_title, jd.company, jd.job_posted, jd.job_description, body.job_link, normalized_url, jd.required_skills, jd.preferred_skills, jd.education_requirements, jd.experience_requirements, jd.keywords, job_site_type, jd.open_to_visa_sponsorship, jd_dom_html)
            )
            job_application_id = cursor.fetchone()[0]
            supabase.db_connection.commit()
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
        with supabase.db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, job_title, company, status FROM public.job_applications WHERE user_id = %s AND normalized_url = %s LIMIT 1",
                (user_id, normalized_base_url)
            )
            job_record = cursor.fetchone()

            if not job_record:
                # Job not found
                return JobStatusResponse(
                    found=False,
                    page_type=page_type
                )

            job_application_id = str(job_record[0])
            job_title = job_record[1]
            company = job_record[2]
            job_status = job_record[3]

            # Determine application state based on job_applications.status and autofill_runs
            if job_status == "applied":
                state = "applied"
            else:
                # Check if any completed autofill run exists
                cursor.execute(
                    "SELECT COUNT(*) FROM public.autofill_runs WHERE job_application_id = %s AND user_id = %s AND status = 'completed'",
                    (job_application_id, user_id)
                )
                autofill_count = cursor.fetchone()[0]
                if autofill_count > 0:
                    state = "autofill_generated"
                else:
                    state = "jd_extracted"

            logger.info(f"Job status found for job_application_id={job_application_id}, state={state}, page_type={page_type}, job_title={job_title}, company={company}")

            return JobStatusResponse(
                found=True,
                page_type=page_type,
                state=state,
                job_application_id=job_application_id,
                job_title=job_title,
                company=company
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

        # check if job_application_id belongs to the user_id
        if not check_if_job_application_belongs_to_user(user_id, body.job_application_id, supabase):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this job application")
        
        normalized_job_url = normalize_url(body.page_url)
        dom_html_hashed = hashlib.sha256(body.dom_html.encode('utf-8')).hexdigest()

        # Generate signed URL for user's resume (for file upload fields)
        resume_signed_url = None
        try:
            with supabase.db_connection.cursor() as cursor:
                cursor.execute("SELECT resume FROM public.users WHERE id=%s", (user_id,))
                resume_row = cursor.fetchone()
                if resume_row and resume_row[0]:
                    storage = supabase.client.storage.from_("user-documents")
                    signed_urls_response = storage.create_signed_urls(
                        paths=[resume_row[0]],
                        expires_in=3600
                    )
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

        # check if an autofill plan already exists for this job application + page
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT id, status, plan_json, plan_summary FROM public.autofill_runs WHERE job_application_id=%s AND user_id=%s AND page_url=%s AND plan_json IS NOT NULL AND status='completed' ORDER BY created_at DESC LIMIT 1", (body.job_application_id, user_id, normalized_job_url))
            result = cursor.fetchone()
            if result:
                autofill_run_id = result[0]
                status = result[1]
                plan_json = result[2]
                plan_summary = result[3]

                response = AutofillPlanResponse(
                    run_id=autofill_run_id,
                    status=status,
                    plan_json=plan_json,
                    plan_summary=plan_summary,
                    resume_url=resume_signed_url
                )
                logger.info("Autofill plan response: %s", json.dumps(response.model_dump(), ensure_ascii=False))
                return response
        
        # If not, create a new autofill plan
        
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.autofill_runs (user_id, job_application_id, page_url, dom_html, dom_html_hash, dom_captured_at, status, created_at) VALUES(%s, %s, %s, %s, %s, NOW(), %s, NOW()) RETURNING id", (user_id, body.job_application_id, normalized_job_url, body.dom_html, dom_html_hashed, 'running'))
            autofill_run_id = cursor.fetchone()[0]
            supabase.db_connection.commit()

            # building the input for the DAG
            autofill_agent_input = AutofillAgentInput(
                run_id=autofill_run_id,
                job_application_id=body.job_application_id,
                user_id=user_id,
                page_url=normalized_job_url,
                dom_html=body.dom_html,
                extracted_fields=[field.model_dump() for field in body.extracted_fields]
            )
            
            # fetching the extracted JD details from DB
            cursor.execute("SELECT job_title, company, job_posted, job_description, job_site_type, required_skills, preferred_skills, education_requirements, experience_requirements, keywords, open_to_visa_sponsorship FROM public.job_applications WHERE id=%s", (body.job_application_id,))
            jd_record = cursor.fetchone()
            if jd_record:
                autofill_agent_input.job_title = jd_record[0]
                autofill_agent_input.company = jd_record[1]
                autofill_agent_input.job_posted = jd_record[2]
                autofill_agent_input.job_description = jd_record[3]
                autofill_agent_input.job_site_type = jd_record[4]
                autofill_agent_input.required_skills = jd_record[5]
                autofill_agent_input.preferred_skills = jd_record[6]
                autofill_agent_input.education_requirements = jd_record[7]
                autofill_agent_input.experience_requirements = jd_record[8]
                autofill_agent_input.keywords = jd_record[9]
                autofill_agent_input.open_to_visa_sponsorship = jd_record[10]

            # fetching the user details and resume information from DB
            cursor.execute("SELECT email, full_name, first_name, last_name, phone_number, linkedin_url, github_url, portfolio_url, other_url, resume, resume_profile, address, city, state, zip_code, country, authorized_to_work_in_us, visa_sponsorship, visa_sponsorship_type, desired_salary, desired_location, gender, race, veteran_status, disability_status FROM public.users WHERE id=%s", (user_id,))
            user_record = cursor.fetchone()
            if user_record:
                autofill_agent_input.email = user_record[0]
                autofill_agent_input.full_name = user_record[1]
                autofill_agent_input.first_name = user_record[2]
                autofill_agent_input.last_name = user_record[3]
                autofill_agent_input.phone_number = user_record[4]
                autofill_agent_input.linkedin_url = user_record[5]
                autofill_agent_input.github_url = user_record[6]
                autofill_agent_input.portfolio_url = user_record[7]
                autofill_agent_input.other_url = user_record[8]
                autofill_agent_input.resume_file_path = user_record[9]
                resume_profile = user_record[10]
                if isinstance(resume_profile, str):
                    try:
                        resume_profile = json.loads(resume_profile)
                    except json.JSONDecodeError:
                        resume_profile = None
                autofill_agent_input.resume_profile = resume_profile
                autofill_agent_input.address = user_record[11]
                autofill_agent_input.city = user_record[12]
                autofill_agent_input.state = user_record[13]
                autofill_agent_input.zip_code = user_record[14]
                autofill_agent_input.country = user_record[15]
                autofill_agent_input.authorized_to_work_in_us = user_record[16]
                autofill_agent_input.visa_sponsorship = user_record[17]
                autofill_agent_input.visa_sponsorship_type = user_record[18]
                autofill_agent_input.desired_salary = user_record[19]
                autofill_agent_input.desired_location = user_record[20]
                autofill_agent_input.gender = user_record[21]
                autofill_agent_input.race = user_record[22]
                autofill_agent_input.veteran_status = user_record[23]
                autofill_agent_input.disability_status = user_record[24]

        # trigger the autofill agent DAG
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

        if not check_if_run_id_belongs_to_user(body.run_id, user_id, supabase):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")
        
        # Store the event in the database
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.autofill_events (run_id, user_id, event_type, payload, created_at) VALUES(%s, %s, %s, %s, NOW())", (body.run_id, user_id, body.event_type, body.payload))
            supabase.db_connection.commit()

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
        
        if not check_if_run_id_belongs_to_user(body.run_id, user_id, supabase):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")

        # Store the feedback in the database
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO public.autofill_feedback (run_id, job_application_id, user_id, question_signature, correction, created_at) VALUES(%s, %s, %s, %s, %s, NOW())", (body.run_id, body.job_application_id, user_id, body.question_signature, body.correction))
            supabase.db_connection.commit()
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
        
        if not check_if_run_id_belongs_to_user(body.run_id, user_id, supabase):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this autofill run")

        # Store the submission in the database
        with supabase.db_connection.cursor() as cursor:
            # update the public.autofill_runs table to mark the status as 'submitted'
            cursor.execute("UPDATE public.autofill_runs SET status = 'submitted', updated_at = NOW() WHERE id = %s", (body.run_id,))

            # also update the public.job_applications table to mark the application as 'applied'
            cursor.execute("UPDATE public.job_applications SET status = 'applied', updated_at = NOW() WHERE id = (SELECT job_application_id FROM public.autofill_runs WHERE id = %s)", (body.run_id,))
            
            # insert an event in the public.autofill_events table
            cursor.execute("INSERT INTO public.autofill_events (run_id, user_id, event_type, payload, created_at) VALUES(%s, %s, %s, %s, NOW())", (body.run_id, user_id, 'application_submitted', body.payload))

            supabase.db_connection.commit()

        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to submit autofill application: {str(e)}")
        raise HTTPException(status_code=500, detail="Unable to submit autofill application")
