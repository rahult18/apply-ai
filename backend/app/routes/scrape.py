from fastapi import APIRouter, HTTPException, Query, Header
import aiohttp
import logging
from app.utils import extract_jd, clean_content, normalize_url
from app.services.llm import LLM
from app.services.supabase import Supabase


# Initialize LLM client
llm = LLM()
# Initialise the supabase
supabase = Supabase()

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/scrape")
async def scrape_job_description(
    job_link: str = Query(..., description="URL of the job posting to scrape"),
    authorization: str = Header(None)
):
    try:
        # Creating a async context manager that creates and manages HTTP client session
        async with aiohttp.ClientSession() as session:
            # Creating a context manager that manages the HTTP response
            async with session.get(job_link) as response:
                if response.status != 200:
                    logger.info(f"Failed to fetch content from the URL: {response.status}")
                    raise HTTPException(status_code=response.status, detail=f"Failed to fetch content from the URL: {response.status}")
                content = await response.text()
                cleaned_content = clean_content(content)
                jd = extract_jd(cleaned_content, llm, job_link)
                logger.info(f"Successfully fetched the content from the URL!")

                # fetch the current user
                if not authorization or not authorization.startswith("Bearer "):
                    raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
                
                token = authorization.split("Bearer ")[1]
                user_response = supabase.client.auth.get_user(jwt=token)
                
                if user_response.user is None:
                    raise HTTPException(status_code=401, detail="Invalid token")
                
                user_id = user_response.user.id

                # Normalize URL to prevent duplicates from tracking params, trailing slashes, etc.
                normalized_url = normalize_url(job_link)

                # write the JD to DB: public.job_applications table
                with supabase.db_connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO job_applications (user_id, job_title, company, job_posted, job_description, url, normalized_url, required_skills, preferred_skills, education_requirements, experience_requirements, keywords, job_site_type, open_to_visa_sponsorship) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (user_id, jd.job_title, jd.company, jd.job_posted, jd.job_description, job_link, normalized_url, jd.required_skills, jd.preferred_skills, jd.education_requirements, jd.experience_requirements, jd.keywords, jd.job_site_type, jd.open_to_visa_sponsorship)
                    )
                    supabase.db_connection.commit()
                logger.info(f"Successfully wrote to the DB!")
                
                return {
                    "url": job_link,
                    **jd.model_dump(),
                    "status_code": response.status
                }
    except aiohttp.ClientError as e:
        logger.info(f"Invalid job_link URL provided: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Internal Error occurred: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

