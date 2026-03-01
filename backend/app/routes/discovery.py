"""
Discovery endpoint for finding job boards via Serper.dev SERP API.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging
import asyncio

from app.models import (
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    DiscoveredBoard,
    JobBoardProvider,
)
from app.services.serper import serper_client
from app.services.supabase import Supabase
from app.utils import parse_job_board_url, verify_internal_api_key, infer_company_name_from_identifier

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = Supabase()


@router.post("/run", response_model=DiscoveryRunResponse)
async def run_discovery(
    body: DiscoveryRunRequest,
    _: bool = Depends(verify_internal_api_key),
):
    """
    Run job board discovery using Serper.dev SERP API.

    - Searches Google for job board URLs matching the query
    - Parses URLs to extract board identifiers
    - Validates only canonical board root URLs (rejects deep links)
    - Upserts discovered boards to company_boards table

    Requires: X-Internal-API-Key header
    """
    try:
        all_urls: List[str] = []
        errors: List[str] = []

        # Search each provider in parallel
        async def search_provider(provider: JobBoardProvider) -> List[str]:
            try:
                return await serper_client.search(body.query, provider.value, body.max_results)
            except Exception as e:
                error_msg = f"Serper search failed for {provider.value}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                return []

        results = await asyncio.gather(*[
            search_provider(p) for p in body.providers
        ])

        for urls in results:
            all_urls.extend(urls)

        logger.info(f"Total URLs found from SERP: {len(all_urls)}")

        # Parse and validate URLs
        parsed_boards: List[DiscoveredBoard] = []
        seen_identifiers = set()  # Dedupe within this run

        for url in all_urls:
            parsed = parse_job_board_url(url)

            if not parsed.is_valid:
                logger.debug(f"Rejected URL {url}: {parsed.rejection_reason}")
                continue

            # Dedupe by (provider, board_identifier)
            key = (parsed.provider, parsed.board_identifier)
            if key in seen_identifiers:
                continue
            seen_identifiers.add(key)

            parsed_boards.append(DiscoveredBoard(
                provider=JobBoardProvider(parsed.provider),
                board_identifier=parsed.board_identifier,
                canonical_url=parsed.canonical_url,
                company_name=infer_company_name_from_identifier(parsed.board_identifier),
                is_new=False,  # Will be updated after upsert
            ))

        logger.info(f"Valid boards parsed: {len(parsed_boards)}")

        # Upsert to database
        new_count = 0
        updated_count = 0

        with supabase.get_raw_cursor() as cursor:
            for board in parsed_boards:
                # Check if exists
                cursor.execute(
                    "SELECT id FROM company_boards WHERE provider = %s AND board_identifier = %s",
                    (board.provider.value, board.board_identifier)
                )
                existing = cursor.fetchone()

                if existing:
                    # Update updated_at timestamp
                    cursor.execute(
                        """
                        UPDATE company_boards
                        SET updated_at = NOW()
                        WHERE provider = %s AND board_identifier = %s
                        """,
                        (board.provider.value, board.board_identifier)
                    )
                    updated_count += 1
                    board.is_new = False
                else:
                    # Insert new board
                    cursor.execute(
                        """
                        INSERT INTO company_boards
                        (provider, board_identifier, canonical_url, company_name, discovered_at, is_active)
                        VALUES (%s, %s, %s, %s, NOW(), true)
                        """,
                        (board.provider.value, board.board_identifier, board.canonical_url, board.company_name)
                    )
                    new_count += 1
                    board.is_new = True

            pass  # commit handled by get_raw_cursor context manager

        logger.info(f"Discovery complete: {new_count} new, {updated_count} updated")

        return DiscoveryRunResponse(
            total_urls_found=len(all_urls),
            valid_boards_parsed=len(parsed_boards),
            new_boards_created=new_count,
            existing_boards_updated=updated_count,
            boards=parsed_boards,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Discovery run failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
