from pydantic import BaseModel

class JD(BaseModel):
    job_title: str
    company: str
    job_posted: str
    job_description: str
    required_skills: list[str]
    preferred_skills: list[str]
    education_requirements: list[str]
    experience_requirements: list[str]
    keywords: list[str]
    job_site_type: str
    open_to_visa_sponsorship: bool

class RequestBody(BaseModel):
    email: str
    password: str

