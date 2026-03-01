"""
User repository for database operations on users table.
"""
from typing import Any
import json
from app.repositories.base import get_cursor, build_update_query


class UserRepository:
    def __init__(self, pool):
        self.pool = pool

    def get_by_id(self, user_id: str) -> dict | None:
        """Get full user profile by ID."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()

    def get_basic_info(self, user_id: str) -> dict | None:
        """Get basic user info (first_name, full_name, avatar_url)."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "SELECT first_name, full_name, avatar_url FROM users WHERE id = %s",
                (user_id,)
            )
            return cursor.fetchone()

    def get_email_from_auth(self, user_id: str) -> str | None:
        """Get email from auth.users table."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("SELECT email FROM auth.users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return row["email"] if row else None

    def get_resume_path(self, user_id: str) -> str | None:
        """Get user's resume storage path."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("SELECT resume FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return row["resume"] if row else None

    def get_resume_profile(self, user_id: str) -> dict | None:
        """Get user's parsed resume profile (JSON)."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("SELECT resume_profile FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if not row or not row["resume_profile"]:
                return None
            profile = row["resume_profile"]
            if isinstance(profile, str):
                try:
                    return json.loads(profile)
                except json.JSONDecodeError:
                    return None
            return profile

    def get_for_autofill(self, user_id: str) -> dict | None:
        """Get all user fields needed for autofill agent."""
        with get_cursor(self.pool) as cursor:
            cursor.execute("""
                SELECT email, full_name, first_name, last_name, phone_number,
                       linkedin_url, github_url, portfolio_url, other_url, resume,
                       resume_profile, address, city, state, zip_code, country,
                       authorized_to_work_in_us, visa_sponsorship, visa_sponsorship_type,
                       desired_salary, desired_location, gender, race, veteran_status,
                       disability_status
                FROM users WHERE id = %s
            """, (user_id,))
            return cursor.fetchone()

    def create(self, user_id: str, email: str) -> None:
        """Create a new user record."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "INSERT INTO users (id, email) VALUES (%s, %s)",
                (user_id, email)
            )
            pass  # commit handled by get_cursor pool context manager

    def update(self, user_id: str, updates: dict[str, Any]) -> None:
        """
        Update user profile with provided fields.

        Args:
            user_id: User ID
            updates: Dict of field names to values (None values are skipped)
        """
        query, params = build_update_query(
            "users",
            updates,
            {"id": user_id},
            extra_sets=["resume_parse_status = 'In progress'", "updated_at = NOW()"]
        )
        if not query:
            return

        with get_cursor(self.pool) as cursor:
            cursor.execute(query, params)
            pass  # commit handled by get_cursor pool context manager

    def update_resume_profile(self, user_id: str, resume_profile: dict) -> None:
        """Update user's parsed resume profile."""
        with get_cursor(self.pool) as cursor:
            cursor.execute(
                "UPDATE users SET resume_profile = %s, resume_parse_status = 'Done', updated_at = NOW() WHERE id = %s",
                (json.dumps(resume_profile), user_id)
            )
            pass  # commit handled by get_cursor pool context manager
