"""
Shared HTTP client with exponential backoff retry for external API calls.
"""
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 16  # seconds
BACKOFF_MULTIPLIER = 2


class HTTPClientError(Exception):
    """Custom exception for HTTP client errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class HTTPClient:
    """Singleton HTTP client with retry logic"""
    _instance = None
    _session: Optional[aiohttp.ClientSession] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """
        Make HTTP request with exponential backoff retry.

        Retries on: 429 (rate limit), 500, 502, 503, 504, connection errors, timeouts
        Does NOT retry on: 400, 401, 403, 404

        Returns:
            Parsed JSON response (dict or list)

        Raises:
            HTTPClientError: On non-retryable errors or after all retries exhausted
        """
        session = await self._get_session()
        backoff = INITIAL_BACKOFF
        last_error = None

        request_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None

        for attempt in range(max_retries + 1):
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                    params=params,
                    timeout=request_timeout,
                ) as response:
                    if response.status == 200:
                        return await response.json()

                    response_text = await response.text()

                    # Check if retryable
                    if response.status in {429, 500, 502, 503, 504}:
                        last_error = HTTPClientError(
                            f"HTTP {response.status}: {response_text[:200]}",
                            status_code=response.status,
                            retryable=True
                        )
                        if attempt < max_retries:
                            # Handle rate limit with Retry-After header
                            if response.status == 429:
                                retry_after = response.headers.get('Retry-After')
                                if retry_after:
                                    try:
                                        backoff = min(int(retry_after), MAX_BACKOFF)
                                    except ValueError:
                                        pass

                            logger.warning(
                                f"Retryable error {response.status} for {url}, "
                                f"attempt {attempt + 1}/{max_retries + 1}, waiting {backoff}s"
                            )
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                            continue

                    # Non-retryable error
                    raise HTTPClientError(
                        f"HTTP {response.status}: {response_text[:200]}",
                        status_code=response.status,
                        retryable=False
                    )

            except aiohttp.ClientError as e:
                last_error = HTTPClientError(f"Connection error: {str(e)}", retryable=True)
                if attempt < max_retries:
                    logger.warning(
                        f"Connection error for {url}, attempt {attempt + 1}/{max_retries + 1}, waiting {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                raise last_error

            except asyncio.TimeoutError:
                last_error = HTTPClientError("Request timed out", retryable=True)
                if attempt < max_retries:
                    logger.warning(
                        f"Timeout for {url}, attempt {attempt + 1}/{max_retries + 1}, waiting {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                raise last_error

        # All retries exhausted
        if last_error:
            raise last_error
        raise HTTPClientError("Max retries exceeded")


# Singleton instance
http_client = HTTPClient()
