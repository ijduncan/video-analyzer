from fastapi import Header


async def get_api_key(x_api_key: str = Header(default="")) -> str | None:
    """Extract optional API key from X-API-Key header."""
    return x_api_key.strip() or None
