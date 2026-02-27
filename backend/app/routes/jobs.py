"""
Public jobs endpoint for searching discovered jobs.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import logging

from app.models import (
    JobBoardProvider,
    DiscoveredJobResponse,
    JobsListResponse,
)
from app.services.supabase import Supabase

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = Supabase()


@router.get("", response_model=JobsListResponse)
def search_jobs(
    keyword: Optional[str] = Query(None, max_length=200, description="Full-text search keyword"),
    provider: Optional[JobBoardProvider] = Query(None, description="Filter by provider"),
    location: Optional[str] = Query(None, max_length=100, description="Location substring filter"),
    remote: Optional[bool] = Query(None, description="Filter remote jobs"),
    posted_after: Optional[datetime] = Query(None, description="Filter by posted date"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    Search discovered jobs with filtering and full-text search.

    - keyword: Full-text search on title, description, location, department
    - provider: Filter by job board provider (ashby, lever, greenhouse)
    - location: Case-insensitive substring match on location
    - remote: Filter for remote jobs only
    - posted_after: Filter jobs posted after this date
    """
    try:
        # Build query dynamically
        conditions = ["dj.is_active = true", "cb.is_active = true"]
        params = []

        # Full-text search
        if keyword:
            conditions.append("dj.search_vector @@ plainto_tsquery('english', %s)")
            params.append(keyword)

        # Provider filter
        if provider:
            conditions.append("cb.provider = %s")
            params.append(provider.value)

        # Location filter (case-insensitive substring)
        if location:
            conditions.append("LOWER(dj.location) LIKE LOWER(%s)")
            params.append(f"%{location}%")

        # Remote filter
        if remote is not None:
            conditions.append("dj.is_remote = %s")
            params.append(remote)

        # Posted after filter
        if posted_after:
            conditions.append("dj.posted_at >= %s")
            params.append(posted_after)

        where_clause = " AND ".join(conditions)

        # Count query
        count_query = f"""
            SELECT COUNT(*)
            FROM discovered_jobs dj
            JOIN company_boards cb ON dj.board_id = cb.id
            WHERE {where_clause}
        """

        # Main query with ordering and pagination
        # Order by relevance if keyword search, otherwise by posted_at
        if keyword:
            order_clause = "ts_rank(dj.search_vector, plainto_tsquery('english', %s)) DESC, dj.posted_at DESC NULLS LAST"
            order_params = [keyword]
        else:
            order_clause = "dj.posted_at DESC NULLS LAST"
            order_params = []

        main_query = f"""
            SELECT
                dj.id,
                dj.board_id,
                cb.provider,
                cb.company_name,
                dj.external_id,
                dj.title,
                dj.location,
                dj.is_remote,
                dj.department,
                dj.team,
                dj.apply_url,
                dj.description,
                dj.posted_at
            FROM discovered_jobs dj
            JOIN company_boards cb ON dj.board_id = cb.id
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """

        with supabase.db_connection.cursor() as cursor:
            # Get total count
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]

            # Get jobs
            cursor.execute(main_query, params + order_params + [limit, offset])
            rows = cursor.fetchall()

        jobs = []
        for row in rows:
            jobs.append(DiscoveredJobResponse(
                id=str(row[0]),
                board_id=str(row[1]),
                provider=JobBoardProvider(row[2]),
                company_name=row[3],
                external_id=row[4],
                title=row[5],
                location=row[6],
                is_remote=row[7] if row[7] is not None else False,
                department=row[8],
                team=row[9],
                apply_url=row[10],
                description=row[11],
                posted_at=row[12],
            ))

        return JobsListResponse(
            jobs=jobs,
            total_count=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + len(jobs)) < total_count,
        )

    except Exception as e:
        logger.error(f"Job search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Job search failed")
