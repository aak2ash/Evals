# app/services/evals_service.py
from asyncio.log import logger
import json
from typing import Any, Dict,Optional
from app.core.config import settings

import httpx

class FeedbackService:
    def __init__(self,
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: Optional[int] = None):
        self.base_url = base_url or getattr(settings, "openai_base_url", "https://api.openai.com/v1")
        self.api_key = api_key or getattr(settings, "openai_api_key", None)
        self.model = model or getattr(settings, "openai_model", "gpt-4o-mini")
        self.timeout = timeout or getattr(settings, "request_timeout", 60)
        self._client = httpx.AsyncClient(timeout=self.timeout)

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set in settings; FeedbackService will fail if used.")

    async def score(self,
                    expected: str,
                    predicted: str,
                    transcript: Optional[str] = None,
                    extra_instructions: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = (
            "You are an evaluator. Compare a predicted assistant response to an expected reference. "
            "Return a single valid JSON object (no surrounding text) with keys:\n"
            "  - accuracy: number (0.0-1.0)\n"
            "  - completeness: number (0.0-1.0)\n"
            "  - relevance: number (0.0-1.0)\n"
            "  - overall: number (0.0-1.0)\n"
            "  - reasoning: string (brief explanation)\n"
            "  - differences: list of strings (what differs)\n"
            "  - pass_fail: string ('pass' or 'fail')\n"
            "Be concise and output only JSON.\n"
        )

        user_parts = []
        if transcript:
            user_parts.append(f"Transcript:\n{transcript}\n")
        user_parts.append(f"Expected Response:\n{expected}\n")
        user_parts.append(f"Predicted Response:\n{predicted}\n")
        if extra_instructions:
            user_parts.append(extra_instructions)
        user_prompt = "\n".join(user_parts)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 512
        }
        url = f"{self.base_url}/chat/completions"

        try:
            resp = await self._client.post(url, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return {"error": "no_choices", "raw": data}
            content = choices[0].get("message", {}).get("content") or choices[0].get("text") or ""
            try:
                parsed = json.loads(content)
                for k in ["accuracy", "completeness", "relevance", "overall"]:
                    if k in parsed:
                        try:
                            parsed[k] = float(parsed[k])
                        except Exception:
                            pass
                return parsed
            except Exception:
                return {"error": "invalid_json", "raw_text": content}
        except httpx.TimeoutException:
            logger.exception("OpenAI judge timed out")
            return {"error": "timeout"}
        except httpx.HTTPStatusError as e:
            logger.exception("OpenAI judge HTTP error: %s", e)
            try:
                body = e.response.text
            except Exception:
                body = None
            return {"error": "http_error", "status_code": e.response.status_code, "body": body}
        except Exception as e:
            logger.exception("Unexpected error calling OpenAI judge: %s", e)
            return {"error": "unexpected", "detail": str(e)}

    async def close(self):
        try:
            await self._client.aclose()
        except Exception:
            pass