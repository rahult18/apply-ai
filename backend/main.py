import uvicorn
import fastapi
from fastapi import HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiohttp
import logging
from llm import LLM
from models import RequestBody
from supabase_client import Supabase
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#initialising the LLM client
logger.info(f"Initialising the LLM client")
llm = LLM()

#initialising the Supbase Client
logger.info(f"Initialising the Supabase Client")
supabase = Supabase()

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

# Supabase Sign Up endpoint
@app.post("/auth/signup")
def signup(body: RequestBody):
    try:
        data = supabase.client.auth.sign_up(body.model_dump())
        
        if data.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        
        # If session is None, email confirmation is required
        if data.session is None:
            return {
                "token": None,
                "user": {
                    "email": data.user.email,
                    "id": data.user.id
                },
                "message": "Please check your email to confirm your account"
            }
        
        # Return token and user info as expected by frontend
        return {
            "token": data.session.access_token,
            "user": {
                "email": data.user.email,
                "id": data.user.id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to signup user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unable to signup user: {str(e)}")


# Supabase email-password login endpoint
@app.post("/auth/login")
def login(body: RequestBody):
    try:
        data = supabase.client.auth.sign_in_with_password(body.model_dump())
        
        if data.user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if data.session is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Return token and user info as expected by frontend
        return {
            "token": data.session.access_token,
            "user": {
                "email": data.user.email,
                "id": data.user.id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to login user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid email or password")


# Get current user endpoint
@app.get("/auth/me")
def get_current_user(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.split("Bearer ")[1]
        
        # Get user from Supabase using the token
        # The get_user method validates the token and returns user info
        user_response = supabase.client.auth.get_user(jwt=token)
        
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Return user info as expected by frontend
        return {
            "email": user_response.user.email,
            "id": user_response.user.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to get user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)