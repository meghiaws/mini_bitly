from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...schemas.url import URLShortenRequest, URLShortenResponse, URLStatsResponse
from ...services.url_service import URLService
from ...api.dependencies import get_base_url
from ...decorators.log_stats import log_url_visit

router = APIRouter()


@router.post("/shorten", response_model=URLShortenResponse, status_code=201)
async def shorten_url(
    url_data: URLShortenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a short URL from a long URL.

    Args:
        url_data: Request containing the long URL
        request: FastAPI request object
        db: Database session

    Returns:
        URLShortenResponse: The created short URL information
    """
    # Convert HttpUrl to string
    original_url = str(url_data.long_url)

    # Create short URL
    url = await URLService.create_short_url(db, original_url)

    # Build response
    base_url = get_base_url(request)
    short_url = f"{base_url}/{url.short_code}"

    return URLShortenResponse(
        short_code=url.short_code,
        short_url=short_url,
        original_url=url.original_url,
        created_at=url.created_at
    )


@router.get("/{short_code}/stats", response_model=URLStatsResponse)
async def get_url_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for a short URL.

    Args:
        short_code: The short code to get stats for
        db: Database session

    Returns:
        URLStatsResponse: Statistics for the URL

    Raises:
        HTTPException: If the short code is not found
    """
    stats = await URLService.get_url_stats(db, short_code)

    if not stats:
        raise HTTPException(status_code=404, detail="Short code not found")

    return URLStatsResponse(**stats)


@router.get("/{short_code}")
@log_url_visit
async def redirect_to_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Redirect to the original URL using the short code.

    This endpoint uses the @log_url_visit decorator to automatically
    log the visit before redirecting.

    Args:
        short_code: The short code to redirect
        request: FastAPI request object
        db: Database session

    Returns:
        RedirectResponse: Redirect to the original URL

    Raises:
        HTTPException: If the short code is not found
    """
    url = await URLService.get_url_by_short_code(db, short_code)

    if not url:
        raise HTTPException(status_code=404, detail="Short code not found")

    return RedirectResponse(url=url.original_url, status_code=307)
