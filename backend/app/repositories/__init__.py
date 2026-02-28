"""
Repository layer for database operations.

Provides organized data access with RealDictCursor for automatic dict conversion.
"""
from app.repositories.base import get_cursor
from app.repositories.users import UserRepository
from app.repositories.job_applications import JobApplicationRepository
from app.repositories.autofill import AutofillRepository

__all__ = [
    "get_cursor",
    "UserRepository",
    "JobApplicationRepository",
    "AutofillRepository",
]
