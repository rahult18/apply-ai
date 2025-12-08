from fastapi import APIRouter, HTTPException, Query
import aiohttp
import logging
from app.utils import extract_jd, clean_content
from app.services.llm import LLM

# Initialize LLM client
llm = LLM()

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/scrape")
async def scrape_job_description(job_link: str = Query(..., description="URL of the job posting to scrape")):
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
                return {
                    "url": job_link,
                    **jd.model_dump(),
                    "status_code": response.status
                }
    except aiohttp.ClientError as e:
        logger.info(f"Invalid job_link URL provided")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except Exception as e:
        logger.info(f"Internal Error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

