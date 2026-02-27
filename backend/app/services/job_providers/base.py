"""
Abstract base class for job board provider API clients.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class NormalizedJob:
    """Normalized job structure from any provider API"""
    external_id: str
    title: str
    apply_url: str
    location: Optional[str] = None
    is_remote: bool = False
    department: Optional[str] = None
    team: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw_data: dict = None

    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}


class BaseJobProvider(ABC):
    """Abstract base for job provider API clients"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier (ashby, lever, greenhouse)"""
        pass

    @property
    @abstractmethod
    def api_base_url(self) -> str:
        """Return base URL for the provider's API"""
        pass

    @abstractmethod
    async def fetch_jobs(self, board_identifier: str) -> List[NormalizedJob]:
        """
        Fetch all jobs from a board and return normalized job objects.

        Args:
            board_identifier: The board name/site/token for this provider

        Returns:
            List of NormalizedJob objects

        Raises:
            HTTPClientError: On API errors
        """
        pass

    @abstractmethod
    def build_api_url(self, board_identifier: str) -> str:
        """Build the full API URL for fetching jobs"""
        pass

    def extract_company_name(self, board_identifier: str, raw_response: dict) -> Optional[str]:
        """
        Extract company name from API response or infer from board identifier.
        Override in subclasses for provider-specific logic.
        """
        return None
