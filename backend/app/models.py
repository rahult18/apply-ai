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