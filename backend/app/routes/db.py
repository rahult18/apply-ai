from fastapi import APIRouter, HTTPException, Query, Header, Form, File, UploadFile, BackgroundTasks
from typing import Optional
import aiohttp
import logging
import json
import os
from app.services.supabase import Supabase
from app.services.llm import LLM
from app.repositories import UserRepository, JobApplicationRepository
from app.utils import parse_resume

# initialize LLM client
llm = LLM()

# initialize supabase
supabase = Supabase()
user_repo = UserRepository(supabase.db_connection)
job_app_repo = JobApplicationRepository(supabase.db_connection)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/get-profile")
def get_profile(authorization: str = Header(None)):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.split("Bearer ")[1]
        user_response = supabase.client.auth.get_user(jwt=token)
        
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = user_response.user.id

        result = user_repo.get_by_id(user_id)
        if result is None:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Convert RealDictRow to regular dict for modification
        result = dict(result)

        # Generate signed URL for resume if it exists
        if result.get('resume'):
            try:
                resume_path = result['resume']
                storage = supabase.client.storage.from_("user-documents")

                # Create signed URL (valid for 1 hour)
                signed_urls_response = storage.create_signed_urls(
                    paths=[resume_path],
                    expires_in=3600
                )

                # Extract the signed URL from the response
                if isinstance(signed_urls_response, list) and len(signed_urls_response) > 0:
                    first_result = signed_urls_response[0]
                    if isinstance(first_result, dict):
                        result['resume_url'] = first_result.get('signedURL') or first_result.get('signed_url')
                    elif hasattr(first_result, 'signedURL'):
                        result['resume_url'] = first_result.signedURL
                    elif hasattr(first_result, 'signed_url'):
                        result['resume_url'] = first_result.signed_url
                    else:
                        logger.warning(f"Unexpected signed URL response format: {type(first_result)}")
                        result['resume_url'] = None
                else:
                    logger.warning(f"Unexpected signed URLs response: {type(signed_urls_response)}")
                    result['resume_url'] = None
            except Exception as e:
                logger.error(f"Error generating signed URL for resume: {str(e)}")
                result['resume_url'] = None

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unable to get profile: {str(e)}")

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

        return job_app_repo.get_all_for_user(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Error getting all applications")
        raise HTTPException(status_code=500, detail=f"Unable to get all applications: {str(e)}")

@router.post("/update-profile")
async def update_profile(
    authorization: str = Header(None),
    full_name: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    portfolio_url: Optional[str] = Form(None),
    other_url: Optional[str] = Form(None),
    resume: Optional[UploadFile] = File(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    zip_code: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    authorized_to_work_in_us: Optional[bool] = Form(None),
    visa_sponsorship: Optional[bool] = Form(None),
    visa_sponsorship_type: Optional[str] = Form(None),
    desired_salary: Optional[float] = Form(None),
    desired_location: Optional[str] = Form(None),  # Will be JSON string from frontend
    gender: Optional[str] = Form(None),
    race: Optional[str] = Form(None),
    veteran_status: Optional[str] = Form(None),
    disability_status: Optional[str] = Form(None),
    open_to_relocation: Optional[bool] = Form(None),
    resume_profile: Optional[str] = Form(None),  # JSON string from frontend
    background_tasks: BackgroundTasks = None
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.split("Bearer ")[1]
        user_response = supabase.client.auth.get_user(jwt=token)
        
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_id = user_response.user.id
        resume_url = None
        uploaded_file_path = None

        # Handle optional resume upload
        if resume is not None:
            try:
                # Read file contents
                file_contents = await resume.read()
                
                # Sanitize filename
                filename = os.path.basename(resume.filename) if resume.filename else "resume.pdf"
                
                # Construct file path
                file_path = f"resumes/{user_id}/{filename}"
                uploaded_file_path = file_path
                
                # Upload to Supabase storage
                resume_upload_response = supabase.client.storage.from_("user-documents").upload(
                    file=file_contents,
                    path=file_path,
                    file_options={
                        "content-type": resume.content_type or "application/pdf",
                        "cache-control": "3600",
                        "upsert": "true"
                    }
                )
                
                # Supabase Python client returns response with 'path' attribute
                if hasattr(resume_upload_response, 'path'):
                    resume_url = resume_upload_response.path
                elif hasattr(resume_upload_response, 'data') and hasattr(resume_upload_response.data, 'path'):
                    resume_url = resume_upload_response.data.path
                else:
                    # Fallback: construct path manually
                    resume_url = file_path
                
                # If resume was updated, trigger background task to parse it
                if resume_url is not None:
                    background_tasks.add_task(parse_resume, user_id, resume_url, llm)
                    
            except Exception as upload_error:
                logger.error(f"Error uploading resume: {str(upload_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(upload_error)}")

        # Parse desired_location if provided (JSON string from form)
        desired_location_parsed = None
        if desired_location:
            try:
                desired_location_parsed = json.loads(desired_location) if isinstance(desired_location, str) else desired_location
            except json.JSONDecodeError:
                desired_location_parsed = desired_location if isinstance(desired_location, list) else None

        # Parse resume_profile if provided (JSON string from form)
        resume_profile_parsed = None
        if resume_profile is not None:
            try:
                resume_profile_parsed = json.dumps(json.loads(resume_profile))
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for resume_profile, skipping")

        # Build updates dict (None values are skipped by repository)
        updates = {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone_number,
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "portfolio_url": portfolio_url,
            "other_url": other_url,
            "resume": resume_url,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "authorized_to_work_in_us": authorized_to_work_in_us,
            "visa_sponsorship": visa_sponsorship,
            "visa_sponsorship_type": visa_sponsorship_type,
            "desired_salary": desired_salary,
            "desired_location": desired_location_parsed,
            "gender": gender,
            "race": race,
            "veteran_status": veteran_status,
            "disability_status": disability_status,
            "open_to_relocation": open_to_relocation,
            "resume_profile": resume_profile_parsed,
        }

        # Filter out None values
        updates = {k: v for k, v in updates.items() if v is not None}

        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # Execute UPDATE query
        try:
            user_repo.update(user_id, updates)
        except Exception as db_error:
            # Rollback: delete uploaded file if DB update fails
            if uploaded_file_path:
                try:
                    supabase.client.storage.from_("user-documents").remove([uploaded_file_path])
                except Exception as delete_error:
                    logger.error(f"Failed to delete uploaded file after DB error: {str(delete_error)}")
            logger.error(f"Database update error: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(db_error)}")

        return {"message": "Profile updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unable to update profile: {str(e)}")

