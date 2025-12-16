import logging
import re
import html
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from app.services.llm import LLM
from app.models import JD

logger = logging.getLogger(__name__)

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
        "job_site_type": Type of the job posting source/platform - determine from the URL or content, must be one of: "linkedin", "job-board" (for platforms like greenhouse, askbyhq), "y-combinator", or "careers page" (company's own careers page), return as a string,
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

