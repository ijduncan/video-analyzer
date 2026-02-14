import asyncio
from typing import AsyncIterator

from google import genai

from app.config import settings

_clients: dict[str, genai.Client] = {}


def get_client(api_key: str | None = None) -> genai.Client:
    key = api_key or settings.google_api_key
    if not key:
        raise RuntimeError("No Google API key configured. Provide one via the Settings menu or set GOOGLE_API_KEY in .env")
    if key not in _clients:
        _clients[key] = genai.Client(api_key=key)
    return _clients[key]


async def async_stream_wrapper(sync_iterator) -> AsyncIterator:
    """Convert a synchronous streaming iterator to an async one."""
    loop = asyncio.get_event_loop()
    iterator = iter(sync_iterator)
    while True:
        try:
            chunk = await loop.run_in_executor(None, next, iterator)
            yield chunk
        except StopIteration:
            break
