"""
Lever job board API client.
API: https://api.lever.co/v0/postings/{site}
"""
from typing import List, Optional
from datetime import datetime
from app.services.job_providers.base import BaseJobProvider, NormalizedJob
from app.services.http_client import http_client
import logging

logger = logging.getLogger(__name__)


class LeverProvider(BaseJobProvider):

    @property
    def provider_name(self) -> str:
        return "lever"

    @property
    def api_base_url(self) -> str:
        return "https://api.lever.co/v0/postings"

    def build_api_url(self, board_identifier: str) -> str:
        return f"{self.api_base_url}/{board_identifier}"

    async def fetch_jobs(self, board_identifier: str) -> List[NormalizedJob]:
        url = self.build_api_url(board_identifier)
        logger.info(f"Fetching Lever jobs from {url}")

        # Lever returns array directly
        response = await http_client.request("GET", url)

        jobs = []
        raw_jobs = response if isinstance(response, list) else []

        for raw_job in raw_jobs:
            try:
                job = self._normalize_job(raw_job, board_identifier)
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to normalize Lever job {raw_job.get('id')}: {e}")
                continue

        logger.info(f"Fetched {len(jobs)} jobs from Lever site {board_identifier}")
        return jobs

    def _normalize_job(self, raw: dict, board_identifier: str) -> NormalizedJob:
        """Convert Lever API response to NormalizedJob"""
        # Lever job structure:
        # { id, text (title), categories: {location, team, department, commitment},
        #   hostedUrl, applyUrl, createdAt, ... }

        categories = raw.get("categories") or {}
        location = categories.get("location")

        # Check remote
        is_remote = False
        if location and "remote" in location.lower():
            is_remote = True
        commitment = categories.get("commitment", "")
        if commitment and "remote" in commitment.lower():
            is_remote = True
        # Also check workplaceType if available
        workplace_type = raw.get("workplaceType", "")
        if workplace_type and "remote" in str(workplace_type).lower():
            is_remote = True

        # Posted date (Lever uses createdAt as Unix timestamp ms)
        posted_at = None
        if raw.get("createdAt"):
            try:
                posted_at = datetime.utcfromtimestamp(raw["createdAt"] / 1000)
            except Exception:
                pass

        return NormalizedJob(
            external_id=str(raw.get("id")),
            title=raw.get("text", "Unknown"),
            location=location,
            is_remote=is_remote,
            department=categories.get("department"),
            team=categories.get("team"),
            apply_url=raw.get("applyUrl") or raw.get("hostedUrl"),
            description=raw.get("descriptionPlain") or raw.get("description"),
            posted_at=posted_at,
            raw_data=raw,
        )

    def extract_company_name(self, board_identifier: str, raw_response: dict) -> Optional[str]:
        # Lever doesn't include company name in API, infer from site identifier
        # e.g., "stripe" -> "Stripe"
        return board_identifier.replace("-", " ").replace("_", " ").title()
