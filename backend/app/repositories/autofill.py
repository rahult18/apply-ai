"""
Autofill repository for autofill_runs, autofill_events, autofill_feedback,
and extension_connect_codes tables.
"""
from typing import Any
from datetime import datetime, timezone, timedelta
import json
from app.repositories.base import get_cursor


class AutofillRepository:
    def __init__(self, connection):
        self.connection = connection

    # -----------------
    # Extension Connect Codes
    # -----------------

    def create_connect_code(self, user_id: str, code_hash: str, expires_at: datetime) -> None:
        """Create a new extension connect code."""
        created_at = datetime.now(timezone.utc)
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "INSERT INTO extension_connect_codes (user_id, code_hash, expires_at, created_at) VALUES (%s, %s, %s, %s)",
                (user_id, code_hash, expires_at, created_at)
            )
            self.connection.commit()

    def get_valid_connect_code(self, code_hash: str) -> dict | None:
        """Get a valid (not expired, not used) connect code by hash."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "SELECT id, user_id FROM extension_connect_codes WHERE code_hash = %s AND expires_at > NOW() AND used_at IS NULL",
                (code_hash,)
            )
            return cursor.fetchone()

    def mark_connect_code_used(self, code_id: str) -> None:
        """Mark a connect code as used."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "UPDATE extension_connect_codes SET used_at = NOW() WHERE id = %s",
                (code_id,)
            )
            self.connection.commit()

    # -----------------
    # Autofill Runs
    # -----------------

    def get_completed_plan(self, job_application_id: str, user_id: str, page_url: str) -> dict | None:
        """Get a completed autofill plan for a job application + page."""
        with get_cursor(self.connection) as cursor:
            cursor.execute("""
                SELECT id, status, plan_json, plan_summary
                FROM autofill_runs
                WHERE job_application_id = %s AND user_id = %s AND page_url = %s
                  AND plan_json IS NOT NULL AND status = 'completed'
                ORDER BY created_at DESC LIMIT 1
            """, (job_application_id, user_id, page_url))
            return cursor.fetchone()

    def get_latest_completed_run_id(self, job_application_id: str, user_id: str) -> str | None:
        """Get the most recent completed run ID for a job application."""
        with get_cursor(self.connection) as cursor:
            cursor.execute("""
                SELECT id FROM autofill_runs
                WHERE job_application_id = %s AND user_id = %s AND status = 'completed'
                ORDER BY created_at DESC LIMIT 1
            """, (job_application_id, user_id))
            row = cursor.fetchone()
            return str(row["id"]) if row else None

    def create_run(
        self,
        user_id: str,
        job_application_id: str,
        page_url: str,
        dom_html: str,
        dom_html_hash: str,
    ) -> str:
        """Create a new autofill run. Returns the new ID."""
        with get_cursor(self.connection) as cursor:
            cursor.execute("""
                INSERT INTO autofill_runs
                (user_id, job_application_id, page_url, dom_html, dom_html_hash, dom_captured_at, status, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), 'running', NOW())
                RETURNING id
            """, (user_id, job_application_id, page_url, dom_html, dom_html_hash))
            result = cursor.fetchone()
            self.connection.commit()
            return str(result["id"])

    def run_belongs_to_user(self, run_id: str, user_id: str) -> bool:
        """Check if an autofill run belongs to a user."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "SELECT 1 FROM autofill_runs WHERE id = %s AND user_id = %s",
                (run_id, user_id)
            )
            return cursor.fetchone() is not None

    def mark_run_submitted(self, run_id: str) -> None:
        """Mark an autofill run as submitted."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "UPDATE autofill_runs SET status = 'submitted', updated_at = NOW() WHERE id = %s",
                (run_id,)
            )
            self.connection.commit()

    def mark_job_as_applied_from_run(self, run_id: str) -> None:
        """Mark the job application associated with a run as applied."""
        with get_cursor(self.connection) as cursor:
            cursor.execute("""
                UPDATE job_applications SET status = 'applied', updated_at = NOW()
                WHERE id = (SELECT job_application_id FROM autofill_runs WHERE id = %s)
            """, (run_id,))
            self.connection.commit()

    # -----------------
    # Autofill Events
    # -----------------

    def create_event(
        self,
        run_id: str,
        user_id: str,
        event_type: str,
        payload: dict | None = None,
    ) -> None:
        """Log an autofill event."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "INSERT INTO autofill_events (run_id, user_id, event_type, payload, created_at) VALUES (%s, %s, %s, %s, NOW())",
                (run_id, user_id, event_type, json.dumps(payload) if payload else None)
            )
            self.connection.commit()

    def get_events_for_job_application(self, job_application_id: str, user_id: str, limit: int = 100) -> list[dict]:
        """Get autofill events for a job application."""
        with get_cursor(self.connection) as cursor:
            cursor.execute("""
                SELECT e.id, e.run_id, e.event_type, e.payload, e.created_at
                FROM autofill_events e
                JOIN autofill_runs r ON e.run_id = r.id
                WHERE r.job_application_id = %s AND r.user_id = %s
                ORDER BY e.created_at DESC
                LIMIT %s
            """, (job_application_id, user_id, limit))
            return cursor.fetchall()

    # -----------------
    # Autofill Feedback
    # -----------------

    def create_feedback(
        self,
        run_id: str,
        job_application_id: str,
        user_id: str,
        question_signature: str,
        correction: str,
    ) -> None:
        """Submit feedback/correction for an autofill answer."""
        with get_cursor(self.connection) as cursor:
            cursor.execute(
                "INSERT INTO autofill_feedback (run_id, job_application_id, user_id, question_signature, correction, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                (run_id, job_application_id, user_id, question_signature, correction)
            )
            self.connection.commit()
