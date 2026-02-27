"""
Sync endpoint for fetching jobs from discovered boards via provider APIs.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging
import json

from app.models import (
    SyncRunRequest,
    SyncRunResponse,
    BoardSyncResult,
    JobBoardProvider,
)
from app.services.job_providers import get_provider, NormalizedJob
from app.services.http_client import HTTPClientError
from app.services.supabase import Supabase
from app.utils import verify_internal_api_key

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = Supabase()

# Deactivate board after this many consecutive failures
MAX_FAILURE_COUNT = 5


@router.post("/run", response_model=SyncRunResponse)
async def run_sync(
    body: SyncRunRequest,
    _: bool = Depends(verify_internal_api_key),
):
    """
    Sync jobs from active company boards.

    - Fetches jobs from provider APIs for active boards
    - Upserts jobs to discovered_jobs table
    - Updates last_synced_at and failure tracking per board
    - Deactivates boards after MAX_FAILURE_COUNT consecutive failures

    Requires: X-Internal-API-Key header
    """
    try:
        # Build provider filter
        filter_params = []

        if body.providers:
            placeholders = ",".join(["%s"] * len(body.providers))
            provider_filter = f"AND provider IN ({placeholders})"
            filter_params = [p.value for p in body.providers]
        else:
            provider_filter = ""

        # Fetch active boards to sync (ordered by least recently synced)
        with supabase.db_connection.cursor() as cursor:
            query = f"""
                SELECT id, provider, board_identifier, company_name, failure_count
                FROM company_boards
                WHERE is_active = true {provider_filter}
                ORDER BY last_synced_at ASC NULLS FIRST
                LIMIT %s
            """
            cursor.execute(query, filter_params + [body.limit_boards])
            boards = cursor.fetchall()

        logger.info(f"Syncing {len(boards)} boards")

        results: List[BoardSyncResult] = []
        total_jobs_fetched = 0
        total_jobs_created = 0
        total_jobs_updated = 0
        failed_boards = 0

        # Process boards sequentially (to avoid rate limits)
        for board_row in boards:
            board_id, provider_str, board_identifier, company_name, failure_count = board_row
            provider = JobBoardProvider(provider_str)

            result = await sync_single_board(
                board_id=str(board_id),
                provider=provider,
                board_identifier=board_identifier,
                company_name=company_name,
                current_failure_count=failure_count,
            )

            results.append(result)

            if result.success:
                total_jobs_fetched += result.jobs_fetched
                total_jobs_created += result.jobs_created
                total_jobs_updated += result.jobs_updated
            else:
                failed_boards += 1

        logger.info(f"Sync complete: {len(results)} boards, {total_jobs_fetched} jobs fetched, {failed_boards} failed")

        return SyncRunResponse(
            boards_processed=len(results),
            total_jobs_fetched=total_jobs_fetched,
            total_jobs_created=total_jobs_created,
            total_jobs_updated=total_jobs_updated,
            failed_boards=failed_boards,
            results=results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync run failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


async def sync_single_board(
    board_id: str,
    provider: JobBoardProvider,
    board_identifier: str,
    company_name: Optional[str],
    current_failure_count: int,
) -> BoardSyncResult:
    """Sync a single board and return result"""
    try:
        # Fetch jobs from provider API
        provider_client = get_provider(provider.value)
        jobs: List[NormalizedJob] = await provider_client.fetch_jobs(board_identifier)

        jobs_created = 0
        jobs_updated = 0

        with supabase.db_connection.cursor() as cursor:
            # Get existing job external_ids for this board
            cursor.execute(
                "SELECT external_id FROM discovered_jobs WHERE board_id = %s",
                (board_id,)
            )
            existing_ids = {row[0] for row in cursor.fetchall()}

            # Track which jobs are still active
            seen_ids = set()

            for job in jobs:
                seen_ids.add(job.external_id)

                if job.external_id in existing_ids:
                    # Update existing job
                    cursor.execute(
                        """
                        UPDATE discovered_jobs SET
                            title = %s,
                            location = %s,
                            is_remote = %s,
                            department = %s,
                            team = %s,
                            apply_url = %s,
                            description = %s,
                            posted_at = %s,
                            raw_data = %s,
                            last_seen_at = NOW(),
                            is_active = true,
                            updated_at = NOW()
                        WHERE board_id = %s AND external_id = %s
                        """,
                        (
                            job.title,
                            job.location,
                            job.is_remote,
                            job.department,
                            job.team,
                            job.apply_url,
                            job.description,
                            job.posted_at,
                            json.dumps(job.raw_data) if job.raw_data else None,
                            board_id,
                            job.external_id,
                        )
                    )
                    jobs_updated += 1
                else:
                    # Insert new job
                    cursor.execute(
                        """
                        INSERT INTO discovered_jobs
                        (board_id, external_id, title, location, is_remote, department, team,
                         apply_url, description, posted_at, raw_data, first_seen_at, last_seen_at, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), true)
                        """,
                        (
                            board_id,
                            job.external_id,
                            job.title,
                            job.location,
                            job.is_remote,
                            job.department,
                            job.team,
                            job.apply_url,
                            job.description,
                            job.posted_at,
                            json.dumps(job.raw_data) if job.raw_data else None,
                        )
                    )
                    jobs_created += 1

            # Mark jobs no longer in API response as inactive
            stale_ids = existing_ids - seen_ids
            if stale_ids:
                placeholders = ",".join(["%s"] * len(stale_ids))
                cursor.execute(
                    f"""
                    UPDATE discovered_jobs
                    SET is_active = false, updated_at = NOW()
                    WHERE board_id = %s AND external_id IN ({placeholders})
                    """,
                    [board_id] + list(stale_ids)
                )
                logger.info(f"Marked {len(stale_ids)} stale jobs as inactive for board {board_identifier}")

            # Update board sync status (success)
            cursor.execute(
                """
                UPDATE company_boards SET
                    last_synced_at = NOW(),
                    failure_count = 0,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (board_id,)
            )

            supabase.db_connection.commit()

        return BoardSyncResult(
            board_id=board_id,
            provider=provider,
            board_identifier=board_identifier,
            jobs_fetched=len(jobs),
            jobs_created=jobs_created,
            jobs_updated=jobs_updated,
            success=True,
        )

    except HTTPClientError as e:
        # Handle API error with failure tracking
        return await handle_board_failure(
            board_id, provider, board_identifier, current_failure_count, str(e)
        )
    except Exception as e:
        logger.error(f"Error syncing board {board_identifier}: {str(e)}", exc_info=True)
        return await handle_board_failure(
            board_id, provider, board_identifier, current_failure_count, str(e)
        )


async def handle_board_failure(
    board_id: str,
    provider: JobBoardProvider,
    board_identifier: str,
    current_failure_count: int,
    error_message: str,
) -> BoardSyncResult:
    """Handle board sync failure with failure tracking and deactivation"""
    new_failure_count = current_failure_count + 1
    should_deactivate = new_failure_count >= MAX_FAILURE_COUNT

    try:
        with supabase.db_connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE company_boards SET
                    failure_count = %s,
                    last_error = %s,
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (new_failure_count, error_message[:500], not should_deactivate, board_id)
            )
            supabase.db_connection.commit()

        if should_deactivate:
            logger.warning(f"Deactivated board {board_identifier} after {MAX_FAILURE_COUNT} consecutive failures")

    except Exception as db_error:
        logger.error(f"Failed to update failure count for {board_identifier}: {db_error}")

    return BoardSyncResult(
        board_id=board_id,
        provider=provider,
        board_identifier=board_identifier,
        jobs_fetched=0,
        jobs_created=0,
        jobs_updated=0,
        success=False,
        error=error_message[:200],
    )
