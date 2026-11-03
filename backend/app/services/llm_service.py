import asyncio
import json
import logging

import httpx
from pydantic import BaseModel

from app.config.settings import settings

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ConnectTimeout,
)


class LLMService:
    """
    Service responsible for communicating with
    the locally running Qwen3 model through Ollama.

    Supports:

    1. Normal text generation
    2. JSON generation
    3. Schema-constrained JSON generation
    4. Lightweight health checks
    5. Bounded retries for transient connection errors
    """

    def __init__(self) -> None:

        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def check_health(self) -> bool:
        """
        Perform a lightweight ping against Ollama's /api/version endpoint.
        Returns True if reachable and responding with HTTP 200, False otherwise.
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=2.0,
                    read=2.0,
                    write=2.0,
                    pool=2.0,
                )
            ) as client:
                response = await client.get(f"{self.base_url}/api/version")
                return response.status_code == 200
        except Exception:
            return False

    async def _send_request(self, payload: dict) -> dict:
        """
        Send a request payload to Ollama with bounded exponential backoff
        for transient connection failures and sanitized logging of HTTP status errors.
        """
        max_retries = getattr(settings, "OLLAMA_MAX_RETRIES", 2)
        connect_timeout = getattr(settings, "OLLAMA_TIMEOUT_CONNECT", 10.0)
        read_timeout = getattr(settings, "OLLAMA_TIMEOUT_READ", 300.0)

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=connect_timeout,
                        read=read_timeout,
                        write=30.0,
                        pool=30.0,
                    )
                ) as client:

                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )

                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        error_body = ""
                        try:
                            error_body = exc.response.text
                            if len(error_body) > 1000:
                                error_body = error_body[:1000] + "... [truncated]"
                        except Exception:
                            error_body = "<failed to read response body>"

                        logger.error(
                            "Ollama HTTP error %s for model '%s': %s (response body: %s)",
                            exc.response.status_code,
                            self.model,
                            type(exc).__name__,
                            error_body,
                        )
                        raise

                    return response.json()

            except TRANSIENT_EXCEPTIONS as exc:
                if attempt < max_retries:
                    backoff = (2 ** attempt) * 1.0
                    logger.warning(
                        "Transient Ollama connection error (%s): %s. Retrying in %.1fs (attempt %d/%d)...",
                        type(exc).__name__,
                        str(exc),
                        backoff,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Ollama connection failed after %d retries: %s: %s",
                        max_retries,
                        type(exc).__name__,
                        str(exc),
                    )
                    raise

    # --------------------------------------------------
    # Normal generation
    # --------------------------------------------------

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """
        Send a prompt to Ollama and return
        the generated text.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Qwen3 thinking is enabled by default in Ollama.
            # For TalentAI extraction we need direct JSON/text
            # output; thinking tokens otherwise exhaust the
            # read timeout on the same resume that previously
            # worked.
            "think": False,
            "options": {
                "temperature": temperature,
                "num_ctx": getattr(settings, "OLLAMA_NUM_CTX", 4096),
                "num_predict": getattr(settings, "OLLAMA_NUM_PREDICT", 1024),
            },
        }

        data = await self._send_request(payload)

        generated_text = data.get(
            "response",
            "",
        )

        if not generated_text:

            raise ValueError(
                "Ollama returned an empty response."
            )

        return generated_text

    # --------------------------------------------------
    # JSON generation
    # --------------------------------------------------

    async def generate_json(
        self,
        prompt: str,
        schema: type[BaseModel] | None = None,
    ) -> dict:
        """
        Generate a JSON response from Ollama.

        When a Pydantic schema is supplied, the
        schema JSON is passed directly to Ollama.

        This constrains the LLM response to the
        expected structure.
        """

        # --------------------------------------------------
        # Determine output format
        # --------------------------------------------------

        if schema is not None:

            output_format = (
                schema.model_json_schema()
            )

        else:

            output_format = "json"

        # --------------------------------------------------
        # Build payload
        # --------------------------------------------------

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": output_format,
            # Qwen3 thinking is enabled by default in Ollama.
            # Disable it so structured extraction returns JSON
            # instead of spending the full read window on
            # thinking tokens.
            "think": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": getattr(settings, "OLLAMA_NUM_CTX", 4096),
                "num_predict": getattr(settings, "OLLAMA_NUM_PREDICT", 1024),
            },
        }

        # --------------------------------------------------
        # Call Ollama
        # --------------------------------------------------

        data = await self._send_request(payload)

        # --------------------------------------------------
        # Extract response
        # --------------------------------------------------

        generated_text = data.get(
            "response",
            "",
        )

        if not generated_text:

            raise ValueError(
                "Ollama returned an empty JSON response."
            )

        # --------------------------------------------------
        # Parse JSON
        # --------------------------------------------------

        try:

            parsed_json = json.loads(
                generated_text
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Ollama returned invalid JSON."
            ) from exc

        # --------------------------------------------------
        # Verify dictionary
        # --------------------------------------------------

        if not isinstance(
            parsed_json,
            dict,
        ):

            raise ValueError(
                "Ollama JSON response must be an object."
            )

        return parsed_json


llm_service = LLMService()
