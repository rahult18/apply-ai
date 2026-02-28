from fastapi import File
from pydantic import BaseModel
from typing import Optional, Any

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
    location: Optional[str] = None
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

class ExtractedFormField(BaseModel):
    """Field extracted by browser extension's DOMParser"""
    type: str  # "input", "textarea", "select", "combobox", etc.
    inputType: str  # "text", "email", "tel", "file", etc.
    name: Optional[str] = None
    id: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False
    value: Optional[Any] = None  # Can be string or boolean
    selector: str
    autocomplete: Optional[str] = None
    isCombobox: Optional[bool] = False
    options: list[dict[str, Any]] = []  # [{value: str, label: str, checked?: bool}]
    maxLength: Optional[int] = None

class AutofillPlanRequest(BaseModel):
    job_application_id: str
    page_url: str
    dom_html: str  # Keep for storage/debugging
    extracted_fields: list[ExtractedFormField]  # REQUIRED - extracted by browser

class AutofillPlanResponse(BaseModel):
    run_id: str
    status: str
    plan_json: Optional[dict] = None
    plan_summary: Optional[dict] = None
    resume_url: Optional[str] = None

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
    dom_html: str  # Keep for storage/debugging
    extracted_fields: Optional[list[ExtractedFormField]] = None  # Extracted by browser
    
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


class JobStatusRequest(BaseModel):
    url: str


class JobStatusResponse(BaseModel):
    found: bool
    page_type: str = "unknown"  # "jd" | "application" | "combined" | "unknown"
    state: Optional[str] = None  # "jd_extracted" | "autofill_generated" | "applied"
    job_application_id: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    run_id: Optional[str] = None  # Most recent completed autofill run_id (for mark-as-applied)
    current_page_autofilled: bool = False  # Whether THIS specific page has been autofilled
    plan_summary: Optional[dict] = None  # { total_fields, autofilled_fields, suggested_fields, skipped_fields }


class ResumeMatchRequest(BaseModel):
    job_application_id: str


class ResumeMatchResponse(BaseModel):
    score: int  # 0-100
    matched_keywords: list[str]
    missing_keywords: list[str]


class AutofillEventResponse(BaseModel):
    id: str
    run_id: str
    event_type: str
    payload: Optional[dict] = None
    created_at: str  # ISO format datetime string


class AutofillEventsListResponse(BaseModel):
    events: list[AutofillEventResponse]
    total_count: int


# ===== Job Discovery and Ingestion Models =====

from enum import Enum
from datetime import datetime
from pydantic import Field


class JobBoardProvider(str, Enum):
    """Supported job board providers"""
    ASHBY = "ashby"
    LEVER = "lever"
    GREENHOUSE = "greenhouse"


# --- Discovery Endpoint Models ---

class DiscoveryRunRequest(BaseModel):
    """Request body for POST /discovery/run"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query for job boards")
    providers: list[JobBoardProvider] = Field(
        default=[JobBoardProvider.ASHBY, JobBoardProvider.LEVER, JobBoardProvider.GREENHOUSE],
        description="Providers to search"
    )
    max_results: int = Field(default=50, ge=1, le=200, description="Max SERP results per provider")


class DiscoveredBoard(BaseModel):
    """A single discovered job board"""
    provider: JobBoardProvider
    board_identifier: str
    canonical_url: str
    company_name: Optional[str] = None
    is_new: bool  # True if newly discovered, False if already existed


class DiscoveryRunResponse(BaseModel):
    """Response from POST /discovery/run"""
    total_urls_found: int
    valid_boards_parsed: int
    new_boards_created: int
    existing_boards_updated: int
    boards: list[DiscoveredBoard]
    errors: list[str] = []


# --- Sync Endpoint Models ---

class SyncRunRequest(BaseModel):
    """Request body for POST /sync/run"""
    providers: Optional[list[JobBoardProvider]] = Field(
        default=None,
        description="Providers to sync (None = all)"
    )
    limit_boards: int = Field(default=100, ge=1, le=1000, description="Max boards to sync")


class BoardSyncResult(BaseModel):
    """Result of syncing a single board"""
    board_id: str
    provider: JobBoardProvider
    board_identifier: str
    jobs_fetched: int
    jobs_created: int
    jobs_updated: int
    success: bool
    error: Optional[str] = None


class SyncRunResponse(BaseModel):
    """Response from POST /sync/run"""
    boards_processed: int
    total_jobs_fetched: int
    total_jobs_created: int
    total_jobs_updated: int
    failed_boards: int
    results: list[BoardSyncResult]


# --- Jobs Public Endpoint Models ---

class DiscoveredJobResponse(BaseModel):
    """A single job from discovered_jobs table"""
    id: str
    board_id: str
    provider: JobBoardProvider
    company_name: Optional[str]
    external_id: str
    title: str
    location: Optional[str]
    is_remote: bool
    department: Optional[str]
    team: Optional[str]
    apply_url: str
    description: Optional[str]
    posted_at: Optional[datetime]


class JobsListResponse(BaseModel):
    """Response from GET /jobs"""
    jobs: list[DiscoveredJobResponse]
    total_count: int
    limit: int
    offset: int
    has_more: bool
