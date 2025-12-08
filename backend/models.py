from pydantic import BaseModel

class JD(BaseModel):
    job_title: str
    company: str
    job_posted: str
    job_description: str
    open_to_visa_sponsorship: bool

class RequestBody(BaseModel):
    email: str
    password: str