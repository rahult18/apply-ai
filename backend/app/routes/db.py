from fastapi import APIRouter, HTTPException, Query, Header, Form, File, UploadFile
from typing import Optional
import aiohttp
import logging
import json
import os
from app.services.supabase import Supabase
# initialize supabase
supabase = Supabase()

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
        
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            columns = [desc[0] for desc in cursor.description]
            user_data = cursor.fetchone()
            
            if user_data is None:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            # Convert tuple to dictionary
            result = dict(zip(columns, user_data))
            
            # Generate signed URL for resume if it exists
            if result.get('resume'):
                try:
                    resume_path = result['resume']
                    storage = supabase.client.storage.from_("user-documents")
                    
                    # Create signed URL (valid for 1 hour)
                    # Using create_signed_urls with a single path (returns a list)
                    # Reference: https://supabase.com/docs/reference/python/storage-from-createsignedurls
                    signed_urls_response = storage.create_signed_urls(
                        paths=[resume_path],
                        expires_in=3600  # 1 hour
                    )
                    
                    # Extract the signed URL from the response
                    # The response is a list of dicts with 'signedURL' key
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
    disability_status: Optional[str] = Form(None)
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
                        "cache-control": "3600",
                        "upsert": "false"
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
                    
            except Exception as upload_error:
                logger.error(f"Error uploading resume: {str(upload_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(upload_error)}")

        # Parse desired_location if provided (JSON string from form)
        desired_location_list = None
        if desired_location:
            try:
                desired_location_list = json.loads(desired_location) if isinstance(desired_location, str) else desired_location
            except json.JSONDecodeError:
                # If it's already a list or invalid, use as is
                desired_location_list = desired_location if isinstance(desired_location, list) else None

        # Build dynamic UPDATE query with only provided fields
        update_fields = []
        update_values = []
        
        if full_name is not None:
            update_fields.append("full_name = %s")
            update_values.append(full_name)
        if first_name is not None:
            update_fields.append("first_name = %s")
            update_values.append(first_name)
        if last_name is not None:
            update_fields.append("last_name = %s")
            update_values.append(last_name)
        if email is not None:
            update_fields.append("email = %s")
            update_values.append(email)
        if phone_number is not None:
            update_fields.append("phone_number = %s")
            update_values.append(phone_number)
        if linkedin_url is not None:
            update_fields.append("linkedin_url = %s")
            update_values.append(linkedin_url)
        if github_url is not None:
            update_fields.append("github_url = %s")
            update_values.append(github_url)
        if portfolio_url is not None:
            update_fields.append("portfolio_url = %s")
            update_values.append(portfolio_url)
        if other_url is not None:
            update_fields.append("other_url = %s")
            update_values.append(other_url)
        if resume_url is not None:
            update_fields.append("resume = %s")
            update_values.append(resume_url)
        if address is not None:
            update_fields.append("address = %s")
            update_values.append(address)
        if city is not None:
            update_fields.append("city = %s")
            update_values.append(city)
        if state is not None:
            update_fields.append("state = %s")
            update_values.append(state)
        if zip_code is not None:
            update_fields.append("zip_code = %s")
            update_values.append(zip_code)
        if country is not None:
            update_fields.append("country = %s")
            update_values.append(country)
        if authorized_to_work_in_us is not None:
            update_fields.append("authorized_to_work_in_us = %s")
            update_values.append(authorized_to_work_in_us)
        if visa_sponsorship is not None:
            update_fields.append("visa_sponsorship = %s")
            update_values.append(visa_sponsorship)
        if visa_sponsorship_type is not None:
            update_fields.append("visa_sponsorship_type = %s")
            update_values.append(visa_sponsorship_type)
        if desired_salary is not None:
            update_fields.append("desired_salary = %s")
            update_values.append(desired_salary)
        if desired_location_list is not None:
            update_fields.append("desired_location = %s")
            update_values.append(desired_location_list)
        if gender is not None:
            update_fields.append("gender = %s")
            update_values.append(gender)
        if race is not None:
            update_fields.append("race = %s")
            update_values.append(race)
        if veteran_status is not None:
            update_fields.append("veteran_status = %s")
            update_values.append(veteran_status)
        if disability_status is not None:
            update_fields.append("disability_status = %s")
            update_values.append(disability_status)

        # Only update if there are fields to update
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # Add user_id for WHERE clause
        update_values.append(user_id)
        
        # Execute UPDATE query
        try:
            with supabase.db_connection.cursor() as cursor:
                update_query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = NOW() WHERE id = %s"
                cursor.execute(update_query, update_values)
                supabase.db_connection.commit()
        except Exception as db_error:
            # Rollback: delete uploaded file if DB update fails
            if uploaded_file_path:
                try:
                    supabase.client.storage.from_("user_documents").remove([uploaded_file_path])
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

        