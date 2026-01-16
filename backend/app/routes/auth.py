from fastapi import APIRouter, HTTPException, Header
from app.models import RequestBody
from app.services.supabase import Supabase
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = Supabase()

router = APIRouter()

@router.post("/signup")
def signup(body: RequestBody):
    try:
        data = supabase.client.auth.sign_up(body.model_dump())
        
        if data.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        
        #insert row into DB: public.users table
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (id, email) VALUES (%s, %s)", (data.user.id, data.user.email))
            supabase.db_connection.commit()

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


@router.post("/login")
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


@router.get("/me")
def get_current_user(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

        token = authorization.split("Bearer ")[1]

        # Get user from Supabase using the token
        user_response = supabase.client.auth.get_user(jwt=token)

        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = user_response.user.id

        # Fetch user's name from the users table
        first_name = None
        full_name = None
        try:
            with supabase.db_connection.cursor() as cursor:
                cursor.execute("SELECT first_name, full_name FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone()
                if row:
                    first_name = row[0]
                    full_name = row[1]
        except Exception as db_error:
            logger.warning(f"Could not fetch user name: {str(db_error)}")

        # Return user info as expected by frontend
        return {
            "email": user_response.user.email,
            "id": user_id,
            "first_name": first_name,
            "full_name": full_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Unable to get user: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
