from fastapi import APIRouter, HTTPException, Query, Header
import aiohttp
import logging
from app.services.supabase import Supabase

# initialize supabase
supabase = Supabase()

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/get-all-applications")
def get_all_applications(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.split("Bearer ")[1]
        user_response = supabase.client.auth.get_user(jwt=token)
        
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = user_response.user.id
        
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT * FROM job_applications WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            columns = [desc[0] for desc in cursor.description]
            applications = cursor.fetchall()
            # Convert tuples to dictionaries
            result = [dict(zip(columns, row)) for row in applications]
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Error getting all applications")
        raise HTTPException(status_code=500, detail=f"Unable to get all applications: {str(e)}")