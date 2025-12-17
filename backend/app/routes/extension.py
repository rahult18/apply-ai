from fastapi import APIRouter, HTTPException, Header
from app.models import ExchangeRequestBody
from app.services.supabase import Supabase
import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import dotenv
import os
from jose import JWTError, jwt

# Loading the env variables from backend directory
BASE_DIR = Path(__file__).parent.parent
dotenv.load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = Supabase()

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
