"""
Job applications repository for database operations.
"""
from typing import Any
from app.repositories.base import get_cursor


class JobApplicationRepository:
    def __init__(self, pool):
        self.pool = pool

    def get_all_for_user(self, user_id: str) -> list[dict]:
        """Get all job applications for a user, ordered by created_at DESC."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT * FROM job_applications WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            return cursor.fetchall()

    def get_by_normalized_url(self, user_id: str, normalized_url: str) -> dict | None:
        """Find job application by normalized URL for a user."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT id, job_title, company, url FROM job_applications WHERE user_id = %s AND normalized_url = %s LIMIT 1",
                (user_id, normalized_url)
            )
            return cursor.fetchone()

    def get_status_by_normalized_url(self, user_id: str, normalized_url: str) -> dict | None:
        """Get job application status info by normalized URL."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT id, job_title, company, status FROM job_applications WHERE user_id = %s AND normalized_url = %s LIMIT 1",
                (user_id, normalized_url)
            )
            return cursor.fetchone()

    def get_for_autofill(self, job_application_id: str) -> dict | None:
        """Get job details needed for autofill agent."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("""
                SELECT job_title, company, job_posted, job_description, job_site_type,
                       required_skills, preferred_skills, education_requirements,
                       experience_requirements, keywords, open_to_visa_sponsorship
                FROM job_applications WHERE id = %s
            """, (job_application_id,))
            return cursor.fetchone()

    def get_keywords_and_skills(self, job_application_id: str) -> dict | None:
        """Get keywords and skills for resume matching."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT required_skills, preferred_skills, keywords FROM job_applications WHERE id = %s",
                (job_application_id,)
            )
            return cursor.fetchone()

    def create(
        self,
        user_id: str,
        job_title: str,
        company: str,
        url: str,
        normalized_url: str,
        jd_dom_html: str,
        job_posted: str | None = None,
        job_description: str | None = None,
        required_skills: list | None = None,
        preferred_skills: list | None = None,
        education_requirements: str | None = None,
        experience_requirements: str | None = None,
        keywords: list | None = None,
        job_site_type: str | None = None,
        open_to_visa_sponsorship: bool | None = None,
    ) -> str:
        """Create a new job application. Returns the new ID."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("""
                INSERT INTO job_applications (
                    user_id, job_title, company, job_posted, job_description, url,
                    normalized_url, required_skills, preferred_skills, education_requirements,
                    experience_requirements, keywords, job_site_type, open_to_visa_sponsorship,
                    jd_dom_html
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id, job_title, company, job_posted, job_description, url,
                normalized_url, required_skills, preferred_skills, education_requirements,
                experience_requirements, keywords, job_site_type, open_to_visa_sponsorship,
                jd_dom_html
            ))
            result = cursor.fetchone()
            pass  # commit handled by get_cursor pool context manager
            return str(result["id"])

    def mark_as_applied(self, job_application_id: str) -> None:
        """Mark a job application as applied."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "UPDATE job_applications SET status = 'applied', updated_at = NOW() WHERE id = %s",
                (job_application_id,)
            )
            pass  # commit handled by get_cursor pool context manager

    def belongs_to_user(self, job_application_id: str, user_id: str) -> bool:
        """Check if a job application belongs to a user."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT 1 FROM job_applications WHERE id = %s AND user_id = %s",
                (job_application_id, user_id)
            )
            return cursor.fetchone() is not None
