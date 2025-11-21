from functools import wraps
from fastapi import Request

from ..services.url_service import URLService


def get_client_ip(request: Request) -> str:
    """
    Extract real client IP address from request.
    Handles various proxy scenarios and forwarding headers.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Priority order for IP extraction:
    # 1. CF-Connecting-IP (Cloudflare)
    # 2. True-Client-IP (Akamai, Cloudflare)
    # 3. X-Real-IP (Nginx proxy)
    # 4. X-Forwarded-For (Standard proxy header)
    # 5. Direct client IP

    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # Akamai and other CDNs
    true_client_ip = request.headers.get("True-Client-IP")
    if true_client_ip:
        return true_client_ip

    # Nginx and other proxies
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Standard proxy header (can contain multiple IPs)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be: "client, proxy1, proxy2"
        # We want the leftmost (original client) IP
        ips = [ip.strip() for ip in forwarded.split(",")]
        if ips:
            return ips[0]

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def log_url_visit(func):
    """
    Decorator to log URL visits.

    Usage:
        @log_url_visit
        async def redirect_endpoint(short_code: str, request: Request, db: AsyncSession):
            # Your endpoint logic must return the URL object
            pass
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        db = kwargs.get('db')

        if not all([request, db]):
            # If required parameters are missing, just call the function
            return await func(*args, **kwargs)

        client_ip = get_client_ip(request)

        result = await func(*args, **kwargs)

        # Log the visit asynchronously (don't block the response)
        # Extract url_id from the result if it's a RedirectResponse
        # We need to get the URL object from the endpoint
        short_code = kwargs.get('short_code')
        if short_code:
            try:
                url = await URLService.get_url_by_short_code(db, short_code)
                if url:
                    await URLService.log_visit(db, url.id, client_ip)
            except Exception:
                # Don't fail the request if logging fails
                pass

        return result

    return wrapper
