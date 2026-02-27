"""
Ashby job board API client.
API: https://api.ashbyhq.com/posting-api/job-board/{boardName}
"""
from typing import List, Optional
from datetime import datetime
from app.services.job_providers.base import BaseJobProvider, NormalizedJob
from app.services.http_client import http_client
import logging

logger = logging.getLogger(__name__)


class AshbyProvider(BaseJobProvider):

    @property
    def provider_name(self) -> str:
        return "ashby"

    @property
    def api_base_url(self) -> str:
        return "https://api.ashbyhq.com/posting-api/job-board"

    def build_api_url(self, board_identifier: str) -> str:
        return f"{self.api_base_url}/{board_identifier}"

    async def fetch_jobs(self, board_identifier: str) -> List[NormalizedJob]:
        url = self.build_api_url(board_identifier)
        logger.info(f"Fetching Ashby jobs from {url}")

        response = await http_client.request("GET", url)

        jobs = []
        # Ashby returns { jobs: [...], ... }
        raw_jobs = response.get("jobs", [])

        for raw_job in raw_jobs:
            try:
                job = self._normalize_job(raw_job, board_identifier)
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to normalize Ashby job {raw_job.get('id')}: {e}")
                continue

        logger.info(f"Fetched {len(jobs)} jobs from Ashby board {board_identifier}")
        return jobs

    def _normalize_job(self, raw: dict, board_identifier: str) -> NormalizedJob:
        """Convert Ashby API response to NormalizedJob"""
        # Ashby job structure:
        # { id, title, location: {name, ...}, department, team, employmentType, ... }

        location_obj = raw.get("location") or {}
        location = None
        if isinstance(location_obj, dict):
            location = location_obj.get("name")
        elif location_obj:
            location = str(location_obj)

        # Check remote from location or employmentType
        is_remote = False
        if location and "remote" in location.lower():
            is_remote = True
        if raw.get("isRemote"):
            is_remote = True
        employment_type = raw.get("employmentType", "")
        if employment_type and "remote" in str(employment_type).lower():
            is_remote = True

        # Posted date
        posted_at = None
        if raw.get("publishedAt"):
            try:
                posted_at = datetime.fromisoformat(raw["publishedAt"].replace("Z", "+00:00"))
            except Exception:
                pass

        # Apply URL: construct from board identifier and job ID
        job_id = raw.get("id")
        apply_url = f"https://jobs.ashbyhq.com/{board_identifier}/{job_id}"

        return NormalizedJob(
            external_id=str(job_id),
            title=raw.get("title", "Unknown"),
            location=location,
            is_remote=is_remote,
            department=raw.get("department"),
            team=raw.get("team"),
            apply_url=apply_url,
            description=raw.get("descriptionHtml") or raw.get("descriptionPlain"),
            posted_at=posted_at,
            raw_data=raw,
        )

    def extract_company_name(self, board_identifier: str, raw_response: dict) -> Optional[str]:
        # Ashby includes company info in response
        return raw_response.get("organizationName") or raw_response.get("companyName")
