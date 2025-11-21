from fastapi import Request


def get_base_url(request: Request) -> str:
    """
    Get the base URL from the request.

    Args:
        request: FastAPI request object

    Returns:
        str: Base URL (e.g., "http://localhost:8000")
    """
    return f"{request.url.scheme}://{request.url.netloc}"
