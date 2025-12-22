import logging
import re
import html
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from app.services.llm import LLM
from app.services.supabase import Supabase
from app.models import JD, ExtractedResumeModel
import fitz

logger = logging.getLogger(__name__)

# initiate supabase client
supabase = Supabase()

def extract_jd(content: str, llm: LLM, url: str = None) -> JD:
    logger.info(f"Extracting JD from the given content: {len(content)} chars")
    url_context = f"\n    Job Posting URL: {url}\n" if url else ""
    prompt = f"""
    You are an expert job description scraper. Below attached is the raw HTML content of a job posting link, now I need you to synthesize the raw content and give me a structured JSON output without any extra text and codefences. 
    {url_context}
    Raw HTML Content:
    {content}

    Expected JSON Output:
    ```json
    {{
        "job_title": Title of the job, return as a string,
        "company": Title of the company, return as a string,
        "job_posted": Date of the job posting, return as a string,
        "job_description": Job Description of the given job posting, return as a string,
        "required_skills": List of required skills for the job, return as a list of strings,
        "preferred_skills": List of preferred skills for the job, return as a list of strings,
        "education_requirements": List of education requirements for the job, return as a list of strings,
        "experience_requirements": List of experience requirements for the job, return as a list of strings,
        "keywords": List of keywords for the job, return as a list of strings,
        "job_site_type": Hostname of the job posting URL, return as a string, for example: boards.greenhouse.io, jobs.ashbyhq.com, jobs.lever.co,
        "open_to_visa_sponsorship": true/false - check if the company is open to US Work visa sponsorship, return as a boolean
    }}
    ```
    """

    response = llm.client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": JD.model_json_schema(),
        }
    )
    extracted_jd = JD.model_validate_json(response.text)
    # logger.info(f"LLM response: {extracted_jd}")
    return extracted_jd


def clean_content(content: str) -> str:
    # Remove script tags and their content (multiline)
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags and their content (multiline)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove JavaScript code patterns (window.*, function definitions, etc.)
    cleaned = re.sub(r"window\.\w+\s*=\s*\{[^}]*\}", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"window\.__\w+\s*=\s*\{[^}]*\}", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\(\([^)]*\)\s*=>\s*\{[^}]*\}\)\([^)]*\)", "", cleaned, flags=re.DOTALL)
    
    # Remove HTML tags using regex
    cleaned = re.sub(r"<[^>]*>", "", cleaned)
    
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    
    # Normalize whitespace (multiple spaces/newlines → single space/newline)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    cleaned = cleaned.strip()
    
    logger.info(f"Cleaned content length: {len(cleaned)} chars (original: {len(content)} chars)")
    return cleaned


def normalize_url(url: str) -> str:
    """
    Normalize a URL by:
    - Removing tracking parameters (utm_*, gh_src, source, ref, etc.)
    - Normalizing trailing slashes
    - Removing fragments
    - Lowercasing the scheme and netloc
    - Sorting query parameters
    
    This helps prevent duplicate entries from URLs that differ only by tracking params.
    """
    try:
        parsed = urlparse(url)
        
        # Normalize scheme and netloc (lowercase)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove fragment
        fragment = ""
        
        # Normalize path (remove trailing slash unless it's root)
        path = parsed.path.rstrip('/') or '/'
        
        # Filter out tracking parameters from query string
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'utm_id', 'utm_source_platform', 'utm_creative_format',
            'gh_src', 'source', 'ref', 'referrer', 'referer',
            'fbclid', 'gclid', 'msclkid', 'twclid',
            'li_fat_id', 'trackingId', 'trk', 'trkInfo',
            '_ga', '_gid', 'mc_cid', 'mc_eid',
            'icid', 'ncid', 'ncid', 'ncid',
            'campaign_id', 'ad_id', 'adgroup_id'
        }
        
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=False)
            # Remove tracking parameters
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in tracking_params
            }
            # Sort parameters for consistency
            query = urlencode(sorted(filtered_params.items()), doseq=True)
        else:
            query = ""
        
        # Reconstruct URL
        normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
        
        logger.debug(f"Normalized URL: {url} -> {normalized}")
        return normalized
        
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {str(e)}, returning original")
        return url

def parse_resume(user_id: str, resume_url: str, llm: LLM):
    """
    This functions parses the resume located at resume_url and updates the user's profile with resume extracted information
    
    :param user_id: User ID of the user whose resume is to be parsed
    :type user_id: str
    :param resume_url: URL of the resume to be parsed
    :type resume_url: str
    """
    try:
        # fetch the resume from supabase storage
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT resume FROM public.users WHERE id = %s", (user_id,))
            resume_path = cursor.fetchone()[0]
            resume_file = supabase.client.storage.from_("user-documents").download(resume_path)
            # read the resume file using fitz
            doc = fitz.open(stream=resume_file, filetype="pdf")
            extracted_resume_text = ""
            for page in doc:
                extracted_resume_text += page.get_text()
            doc.close()

            # Use LLM to parse the resume text
            prompt = f"""
            You are an expert resume parser. Below is the extracted text from a user's resume. Please extract the following information and return it in a structured JSON format without any extra text or codefences.

            Resume Text:
            {extracted_resume_text}

            Expected JSON Output:
            ```json
            {{
                "summary": "Summary of the user's professional background, return as a string",
                "skills": ["List of skills mentioned in the resume, return as a list of strings"],
                "experience": [
                    {{
                        "company": "Company Name",
                        "position": "Job Title",
                        "start_date": "YYYY-MM-DD",
                        "end_date": "YYYY-MM-DD or null if current",
                        "description": "Job responsibilities and achievements as a string"
                    }}
                ],
                "education": [
                    {{
                        "institution": "Institution Name",
                        "degree": "Degree Name",
                        "field_of_study": "Field of Study",
                        "start_date": "YYYY-MM-DD",
                        "end_date": "YYYY-MM-DD or null if current",
                        "description": "Description of academic achievements or coursework as a string"
                    }}
                ],
                "certifications": [
                    {{
                        "name": "Certification Name",
                        "issuing_organization": "Organization Name",
                        "issue_date": "YYYY-MM-DD",
                        "expiration_date": "YYYY-MM-DD or null if no expiration",
                        "credential_id": "Credential ID or null",
                        "credential_url": "URL to credential or null"
                    }}
                ],
                "projects": [
                    {{
                        "name": "Project Name",
                        "description": "Project description as a string",
                        "link": "URL to project or null"
                    }}
                ]
            }}
            ```
            """

            response = llm.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ExtractedResumeModel.model_json_schema(),
                }
            )
            resume_data = response.text

            # Update user's profile in the database with parsed resume data
            update_query = "UPDATE public.users SET resume_text = %s, resume_profile = %s, resume_parse_status = 'Completed', resume_parsed_at = NOW() WHERE id = %s"
            cursor.execute(update_query, (extracted_resume_text, resume_data, user_id))
            supabase.db_connection.commit()
            logger.info(f"Successfully parsed and updated resume for user {user_id}")

    except Exception as e:
        logger.error(f"Error parsing resume for user {user_id} from {resume_url}: {str(e)}")
    

def check_if_job_application_belongs_to_user(user_id: str, job_application_id: str, supabase: Supabase) -> bool:
    """
    Check if the given job application ID belongs to the specified user ID.

    :param user_id: User ID to check ownership against
    :type user_id: str
    :param job_application_id: Job Application ID to verify
    :type job_application_id: str
    :param supabase: Supabase client instance for database access
    :type supabase: Supabase
    :return: True if the job application belongs to the user, False otherwise
    :rtype: bool
    """
    try:
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM public.job_applications WHERE id = %s AND user_id = %s", (job_application_id, user_id))
            count = cursor.fetchone()[0]
            if count > 0:
                return True
            else:
                return False
    except Exception as e:
        logger.error(f"Error checking job application ownership for user_id {user_id} and job_application_id {job_application_id}: {str(e)}")
        return False

def check_if_run_id_belongs_to_user(run_id: str, user_id: str, supabase: Supabase) -> bool:
    """
    Check if the given autofill run ID belongs to the specified user ID.

    :param run_id: Autofill Run ID to verify
    :type run_id: str
    :param user_id: User ID to check ownership against
    :type user_id: str
    :param supabase: Supabase client instance for database access
    :type supabase: Supabase
    :return: True if the autofill run belongs to the user, False otherwise
    :rtype: bool
    """
    try:
        with supabase.db_connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM public.autofill_runs WHERE id = %s AND user_id = %s", (run_id, user_id))
            count = cursor.fetchone()[0]
            if count > 0:
                return True
            else:
                return False
    except Exception as e:
        logger.error(f"Error checking autofill run ownership for run_id {run_id} and user_id {user_id}: {str(e)}")
        return False