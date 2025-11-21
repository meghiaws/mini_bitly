import secrets
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.url import URL, URLVisit


class URLService:
    """Service for URL shortening operations"""

    @staticmethod
    def generate_short_code(length: int = None) -> str:
        """
        Generate a random short code.

        Args:
            length: Length of the short code (defaults to settings.SHORT_CODE_LENGTH)

        Returns:
            str: Random short code
        """
        if length is None:
            length = settings.SHORT_CODE_LENGTH

        charset = settings.SHORT_CODE_CHARSET
        return ''.join(secrets.choice(charset) for _ in range(length))

    @staticmethod
    async def create_short_url(db: AsyncSession, original_url: str) -> URL:
        """
        Create a new short URL.

        Args:
            db: Database session
            original_url: The original URL to shorten

        Returns:
            URL: The created URL object
        """
        # Check if URL already exists
        result = await db.execute(
            select(URL).where(URL.original_url == original_url).limit(1)
        )
        existing_url = result.scalar_one_or_none()

        if existing_url:
            return existing_url

        # Generate unique short code
        max_attempts = 10
        for _ in range(max_attempts):
            short_code = URLService.generate_short_code()

            # Check if short code already exists
            result = await db.execute(
                select(URL).where(URL.short_code == short_code).limit(1)
            )
            if not result.scalar_one_or_none():
                break
        else:
            # If we couldn't find a unique code, try with longer length
            short_code = URLService.generate_short_code(length=8)

        # Create new URL
        url = URL(
            original_url=original_url,
            short_code=short_code
        )
        db.add(url)
        await db.commit()
        await db.refresh(url)

        return url

    @staticmethod
    async def get_url_by_short_code(db: AsyncSession, short_code: str) -> URL | None:
        """
        Get URL by short code.

        Args:
            db: Database session
            short_code: The short code to look up

        Returns:
            URL | None: The URL object or None if not found
        """
        result = await db.execute(
            select(URL).where(URL.short_code == short_code).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def log_visit(db: AsyncSession, url_id: int, visitor_ip: str) -> None:
        """
        Log a visit to a short URL.

        Args:
            db: Database session
            url_id: The ID of the URL that was visited
            visitor_ip: IP address of the visitor
        """
        visit = URLVisit(
            url_id=url_id,
            visitor_ip=visitor_ip
        )
        db.add(visit)
        await db.commit()

    @staticmethod
    async def get_url_stats(db: AsyncSession, short_code: str) -> dict:
        """
        Get statistics for a short URL.

        Args:
            db: Database session
            short_code: The short code to get stats for

        Returns:
            dict: Statistics including URL info and visit count
        """
        # Get URL info with visit count in single query
        url = await URLService.get_url_by_short_code(db=db, short_code=short_code)

        if not url:
            return None

        result = await db.execute(
            select(func.count(URLVisit.id))
            .where(URLVisit.url_id == url.id)
        )
        total_visits = result.scalar() or 0

        return {
            "short_code": url.short_code,
            "original_url": url.original_url,
            "total_visits": total_visits,
            "created_at": url.created_at
        }