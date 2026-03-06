import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class OpenRouterClient:
    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model

    def chat(self, messages: list[dict], temperature: float = 0.1) -> dict:
        """
        Call OpenRouter /chat/completions and return the parsed JSON object
        from the model response content.

        Retries up to 3 times on timeout or 5xx errors.
        Raises LLMError on unrecoverable failure.
        """
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=30.0, verify=False) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(content)
            except httpx.TimeoutException as exc:
                logger.warning("LLM request timeout (attempt %d/3)", attempt + 1)
                last_exc = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise LLMError(f"LLM client error: {exc.response.status_code} {exc.response.text}") from exc
                logger.warning("LLM server error %d (attempt %d/3)", exc.response.status_code, attempt + 1)
                last_exc = exc
            except (json.JSONDecodeError, KeyError) as exc:
                raise LLMError(f"Unexpected LLM response format: {exc}") from exc

        raise LLMError(f"LLM request failed after 3 attempts: {last_exc}") from last_exc
