"""
Serper.dev Google SERP API client for job board discovery.
"""
import os
from typing import List
from app.services.http_client import http_client, HTTPClientError
import logging

logger = logging.getLogger(__name__)

SERPER_API_URL = "https://google.serper.dev/search"

# Provider-specific site filters for SERP queries
PROVIDER_SITE_FILTERS = {
    "ashby": "site:jobs.ashbyhq.com",
    "lever": "site:jobs.lever.co",
    "greenhouse": "site:boards.greenhouse.io",
}


class SerperClient:
    """Serper.dev SERP API client for discovering job boards"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._api_key = None

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            self._api_key = os.getenv("SERPER_API_KEY")
        return self._api_key

    async def search(
        self,
        query: str,
        provider: str,
        max_results: int = 50,
    ) -> List[str]:
        """
        Search for job board URLs using Serper.dev.

        Args:
            query: Search query (e.g., "software engineer jobs")
            provider: Job board provider to filter ('ashby', 'lever', 'greenhouse')
            max_results: Maximum results to return (Serper max is 100)

        Returns:
            List of discovered URLs

        Raises:
            ValueError: If SERPER_API_KEY not configured
            HTTPClientError: On API errors
        """
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured in environment variables")

        if provider not in PROVIDER_SITE_FILTERS:
            raise ValueError(f"Unknown provider: {provider}. Valid options: {list(PROVIDER_SITE_FILTERS.keys())}")

        site_filter = PROVIDER_SITE_FILTERS[provider]
        full_query = f"{query} {site_filter}"

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "q": full_query,
            "num": min(max_results, 100),  # Serper max is 100
        }

        logger.info(f"Searching Serper for: {full_query}")

        try:
            response = await http_client.request(
                "POST",
                SERPER_API_URL,
                headers=headers,
                json_data=payload,
            )

            # Extract URLs from organic results
            urls = []
            organic = response.get("organic", [])
            for result in organic:
                link = result.get("link")
                if link:
                    urls.append(link)

            logger.info(f"Found {len(urls)} URLs from Serper for {provider}")
            return urls

        except HTTPClientError as e:
            logger.error(f"Serper API error for {provider}: {e}")
            raise


# Singleton instance
serper_client = SerperClient()
