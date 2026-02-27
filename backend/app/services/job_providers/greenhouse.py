"""
Greenhouse job board API client.
API: https://boards-api.greenhouse.io/v1/boards/{token}/jobs
"""
from typing import List, Optional
from datetime import datetime
from app.services.job_providers.base import BaseJobProvider, NormalizedJob
from app.services.http_client import http_client
import logging

logger = logging.getLogger(__name__)


class GreenhouseProvider(BaseJobProvider):

    @property
    def provider_name(self) -> str:
        return "greenhouse"

    @property
    def api_base_url(self) -> str:
        return "https://boards-api.greenhouse.io/v1/boards"

    def build_api_url(self, board_identifier: str) -> str:
        return f"{self.api_base_url}/{board_identifier}/jobs"

    async def fetch_jobs(self, board_identifier: str) -> List[NormalizedJob]:
        url = self.build_api_url(board_identifier)
        # Greenhouse requires content=true for job descriptions
        params = {"content": "true"}
        logger.info(f"Fetching Greenhouse jobs from {url}")

        response = await http_client.request("GET", url, params=params)

        jobs = []
        # Greenhouse returns { jobs: [...], ... }
        raw_jobs = response.get("jobs", [])

        for raw_job in raw_jobs:
            try:
                job = self._normalize_job(raw_job, board_identifier)
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to normalize Greenhouse job {raw_job.get('id')}: {e}")
                continue

        logger.info(f"Fetched {len(jobs)} jobs from Greenhouse board {board_identifier}")
        return jobs

    def _normalize_job(self, raw: dict, board_identifier: str) -> NormalizedJob:
        """Convert Greenhouse API response to NormalizedJob"""
        # Greenhouse job structure:
        # { id, title, location: {name}, departments: [{name}], offices: [{name}],
        #   content, absolute_url, updated_at, ... }

        location_obj = raw.get("location") or {}
        location = None
        if isinstance(location_obj, dict):
            location = location_obj.get("name")

        # Check remote from location or offices
        is_remote = False
        if location and "remote" in location.lower():
            is_remote = True
        offices = raw.get("offices") or []
        for office in offices:
            if isinstance(office, dict) and "remote" in office.get("name", "").lower():
                is_remote = True
                break

        # Department (first one)
        departments = raw.get("departments") or []
        department = None
        if departments and isinstance(departments[0], dict):
            department = departments[0].get("name")

        # Posted/updated date
        posted_at = None
        if raw.get("updated_at"):
            try:
                posted_at = datetime.fromisoformat(raw["updated_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        return NormalizedJob(
            external_id=str(raw.get("id")),
            title=raw.get("title", "Unknown"),
            location=location,
            is_remote=is_remote,
            department=department,
            team=None,  # Greenhouse doesn't have teams in the same way
            apply_url=raw.get("absolute_url"),
            description=raw.get("content"),
            posted_at=posted_at,
            raw_data=raw,
        )

    def extract_company_name(self, board_identifier: str, raw_response: dict) -> Optional[str]:
        # Greenhouse may include company name at board level
        return raw_response.get("name") or board_identifier.replace("-", " ").replace("_", " ").title()
