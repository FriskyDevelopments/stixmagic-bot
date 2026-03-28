"""OpenAI integration helpers — only called for premium users."""
import os
import io
import logging
import requests as http_requests
from openai import OpenAI

logger = logging.getLogger(__name__)

IMAGE_DOWNLOAD_USER_AGENT = "ChatGPT-Telegram-Bot/1.0"

_client = None


def get_client():
    """Return a cached OpenAI client, or None if the API key is not configured."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        _client = OpenAI(api_key=api_key)
    return _client


def generate_sticker_image(prompt: str) -> io.BytesIO | None:
    """Call DALL-E 3 to generate a sticker image from *prompt*.

    Returns the image as a BytesIO object (PNG bytes), or None on failure.
    Only call this function after confirming the user is premium.

    NOTE: DALL-E 3 does not support transparent backgrounds. This function requests
    a solid white background. To achieve transparency, consider:
    - Post-processing with a background removal library (e.g., rembg)
    - TODO: Migrate to GPT Image models when they support the transparent parameter
    """
    client = get_client()
    if client is None:
        logger.error("OPENAI_API_KEY is not set — cannot generate image.")
        return None

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=(
                f"{prompt}. "
                "Style: clean, simple, cartoon sticker with solid white background, "
                "no text, white outline, vibrant colors."
            ),
            size="1024x1024",
            quality="standard",
            n=1,
        )
        data = getattr(response, "data", None)
        if not data:
            logger.error("DALL-E API error: empty image data in response.")
            return None
        image_url = getattr(data[0], "url", None)
        if not image_url:
            logger.error("DALL-E API error: missing image URL in response.")
            return None
    except Exception:
        logger.exception("DALL-E API error")
        return None

    try:
        img_response = http_requests.get(
            image_url,
            headers={"User-Agent": IMAGE_DOWNLOAD_USER_AGENT},
            timeout=30
        )
        img_response.raise_for_status()
        return io.BytesIO(img_response.content)
    except Exception:
        logger.exception("DALL-E image download error")
        return None