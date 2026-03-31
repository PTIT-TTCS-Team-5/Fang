import httpx

from app.core.logging import logger


async def download_cv(url: str) -> bytes:
    """
    Download the CV file from the provided snapshot URL.
    """
    logger.info(f"Downloading CV from {url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.content
