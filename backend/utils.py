import logging
import re
import html
from llm import LLM
from models import JD

logger = logging.getLogger(__name__)

def extract_jd(content: str, llm: LLM) -> JD:
    logger.info(f"Extracting JD from the given content: {len(content)} chars")
    prompt = f"""
    You are an expert job description scraper. Below attached is the raw HTML content of a job posting link, now I need you to synthesize the raw content and give me a structured JSON output without any extra text and codefences. 

    Raw HTML Content:
    {content}

    Expected JSON Output:
    ```json
    {{
        "job_title": Title of the job,
        "company": Title of the company,
        "job_posted": Date of the job posting,
        "job_description": Job Description of the given job posting,
        "open_to_visa_sponsorship": true/false - check if the company is open to US Work visa sponsorship
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
