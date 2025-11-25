from asyncio.log import logger
import httpx
from typing import Any, Dict, Optional
from app.core.config import settings
class TranscriptAnalyzerClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = base_url or settings.transcript_analyzer_url
        self.timeout = timeout or settings.request_timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def analyze_transcript(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = await self._client.post(self.base_url, headers={"Content-Type": "application/json"}, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            logger.exception("Transcript analyzer timed out")
            return {"error": "timeout"}
        except httpx.HTTPStatusError as e:
            logger.exception("Transcript analyzer HTTP error: %s", e)
            return {"error": "http_error", "status_code": e.response.status_code, "body": e.response.text}
        except Exception as e:
            logger.exception("Unexpected error calling transcript analyzer: %s", e)
            return {"error": "unexpected", "detail": str(e)}

    async def close(self):
        try:
            await self._client.aclose()
        except Exception:
            pass
