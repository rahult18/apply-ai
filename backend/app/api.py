import fastapi
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
import dotenv

# Loading the env variables from backend directory
BASE_DIR = Path(__file__).parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

# Setting up the basic logging configuration (fallback if main.py did not configure it)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

# Creating the FastAPI backend
app = fastapi.FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.routes import auth, db, extension, discovery, sync, jobs

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(db.router, prefix="/db", tags=["db"])
app.include_router(extension.router, prefix="/extension", tags=["extension"])

# Job discovery and ingestion routers
app.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

# Health check endpoint
@app.get("/")
def health_check():
    return {"status": "ok"}
