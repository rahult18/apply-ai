import uvicorn
import asyncio
import fastapi
from fastapi import HTTPException, Query
import aiohttp
import logging
from llm import LLM
from utils import extract_jd, clean_content
import dotenv

#loading the env variables
dotenv.load_dotenv()

#setting up the basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

#creating the fastapi backend
app = fastapi.FastAPI()
#initialising the LLM client
logger.info(f"Initialising the LLM client")
llm = LLM()

# health check endpoint
@app.get("/")
def health_check():
    return {"status": "ok"}

# scrape job description endpoint
@app.post("/scrape")
#adding a query parameter for this endpoint, so /scrape?job_link:apple.careers.com/1234, it will pull the job_link from here
# ... in the Query mean that it's a required field
async def scrape_job_description(job_link: str = Query(..., description="URL of the job posting to scrape")):
    try:
        # creating a async context manager that creates and manages HTTP client session
        async with aiohttp.ClientSession() as session:
            # creating a context manager that manages the HTTP response
            async with session.get(job_link) as response:
                if response.status != 200:
                    logger.info(f"Failed to fetch content from the URL: {response.status}")
                    raise HTTPException(status_code=response.status, detail=f"Failed to fetch content from the URL: {response.status}")
                content = await response.text()
                cleaned_content = clean_content(content)
                jd = extract_jd(cleaned_content, llm)
                logger.info(f"Successfully fetched the content from the URL!")
                return {"url": job_link, "job_title": jd.job_title, "company": jd.company, "job_posted": jd.job_posted, "job_description": jd.job_description, "status_code": response.status}
    except aiohttp.ClientError as e:
        logger.info(f"Invalid job_link URL provided")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except Exception as e:
        logger.info(f"Internal Error occurred")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)