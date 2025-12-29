"""Gemini AI client wrapper for text and vision capabilities."""

import asyncio
import base64
import logging
from typing import Optional

from google import genai
from google.genai import types

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Google Gemini API with text and vision support."""

    def __init__(self):
        """Initialize the Gemini client with API key."""
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = "gemini-flash-latest"  # More quota-friendly
        self.max_retries = 2
        self.retry_delay = 5  # seconds

    async def send_text(self, prompt: str) -> Optional[str]:
        """
        Send a text prompt to Gemini and get a response.

        Args:
            prompt: The text prompt to send.

        Returns:
            The generated text response, or None if failed.
        """
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                logger.warning(f"Gemini text request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error("Gemini text request failed after all retries")
        return None

    async def send_image(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Send an image with a prompt to Gemini for vision analysis.

        Args:
            image_bytes: Raw bytes of the image.
            prompt: The prompt describing what to extract/analyze.
            mime_type: MIME type of the image (default: image/jpeg).

        Returns:
            The generated text response, or None if failed.
        """
        for attempt in range(self.max_retries):
            try:
                # Create image part for multimodal input
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=[prompt, image_part]
                )
                return response.text
            except Exception as e:
                logger.warning(f"Gemini vision request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)

        logger.error("Gemini vision request failed after all retries")
        return None

    async def send_image_with_json(
        self,
        image_bytes: bytes,
        prompt: str,
        mime_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Send an image with a prompt expecting JSON response.

        Adds JSON formatting instructions to the prompt.

        Args:
            image_bytes: Raw bytes of the image.
            prompt: The prompt describing what to extract.
            mime_type: MIME type of the image.

        Returns:
            The generated JSON string, or None if failed.
        """
        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown code blocks, no explanations.
Just the raw JSON array or object."""

        return await self.send_image(image_bytes, json_prompt, mime_type)


# Singleton instance - lazy initialization
_gemini_client = None


def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


# For backward compatibility
gemini_client = None


def _init_client():
    global gemini_client
    if gemini_client is None and config.GEMINI_API_KEY:
        gemini_client = GeminiClient()


# Try to initialize on import, but don't fail if API key not set
try:
    _init_client()
except Exception:
    pass
