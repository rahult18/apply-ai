from fastapi import File
from pydantic import BaseModel
from typing import Optional

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

class UpdateProfileBody(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    other_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    authorized_to_work_in_us: Optional[bool] = None
    visa_sponsorship: Optional[bool] = None
    visa_sponsorship_type: Optional[str] = None
    desired_salary: Optional[float] = None
    desired_location: Optional[list[str]] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None

class ExchangeRequestBody(BaseModel):
    one_time_code: str
    install_id: str
class EducationEntry(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class ExperienceEntry(BaseModel):
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class ProjectEntry(BaseModel):
    name: str
    description: Optional[str] = None
    link: Optional[str] = None

class CertificationEntry(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
class ExtractedResumeModel(BaseModel):
    summary: Optional[str] = None
    skills: Optional[list[str]] = None
    experience: Optional[list[ExperienceEntry]] = None
    education: Optional[list[EducationEntry]] = None
    certifications: Optional[list[CertificationEntry]] = None
    projects: Optional[list[ProjectEntry]] = None

class JobsIngestRequestBody(BaseModel):
    job_link: str
    dom_html: Optional[str] = None

class AutofillPlanRequest(BaseModel):
    job_application_id: str
    page_url: str
    dom_html: str

class AutofillPlanResponse(BaseModel):
    run_id: str
    status: str
    plan_json: Optional[dict] = None
    plan_summary: Optional[dict] = None

class AutofillEventRequest(BaseModel):
    run_id: str
    event_type: str
    payload: Optional[dict] = None

class AutofillFeedbackRequest(BaseModel):
    run_id: str
    job_application_id: str
    question_signature: Optional[str] = None
    correction: Optional[dict] = None

class AutofillSubmitRequest(BaseModel):
    run_id: str
    payload: Optional[dict] = None

class AutofillAgentInput(BaseModel):
    run_id: str
    job_application_id: str
    user_id: str

    #application page details
    page_url: str
    dom_html: str
    
    #job details
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_posted: Optional[str] = None
    job_description: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    education_requirements: Optional[list[str]] = None
    experience_requirements: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    open_to_visa_sponsorship: Optional[bool] = None
    job_site_type: Optional[str] = None

    #user details
    email: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    other_url: Optional[str] = None
    resume_file_path: Optional[str] = None
    resume_profile: Optional[ExtractedResumeModel] = None 
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    authorized_to_work_in_us: Optional[bool] = None
    visa_sponsorship: Optional[bool] = None
    visa_sponsorship_type: Optional[str] = None
    desired_salary: Optional[float] = None
    desired_location: Optional[list[str]] = None
    gender: Optional[str] = None
    race: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None


class AutofillAgentOutput(BaseModel):
    status: str
    plan_json: Optional[dict] = None
    plan_summary: Optional[dict] = None
