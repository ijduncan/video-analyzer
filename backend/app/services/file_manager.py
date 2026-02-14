import asyncio
import time
from pathlib import Path

from google.genai import types

from app.services.gemini_client import get_client


async def upload_video(file_path: str, mime_type: str, api_key: str | None = None):
    """Upload a video to Google's File API and return the file object."""
    client = get_client(api_key)
    uploaded = await asyncio.to_thread(
        client.files.upload, file=Path(file_path), config={"mime_type": mime_type}
    )
    return uploaded


async def poll_until_active(file_name: str, timeout: int = 300, interval: int = 5, api_key: str | None = None):
    """Poll the File API until the file reaches ACTIVE state."""
    client = get_client(api_key)
    start = time.time()

    while True:
        file_obj = await asyncio.to_thread(client.files.get, name=file_name)
        if file_obj.state == "ACTIVE":
            return file_obj
        if file_obj.state == "FAILED":
            raise RuntimeError(f"File processing failed: {file_name}")
        if time.time() - start > timeout:
            raise TimeoutError(
                f"File {file_name} did not become ACTIVE within {timeout}s"
            )
        await asyncio.sleep(interval)


async def delete_file(file_name: str):
    """Delete a file from Google's File API."""
    client = get_client()
    await asyncio.to_thread(client.files.delete, name=file_name)
