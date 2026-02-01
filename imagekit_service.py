import logging
from datetime import datetime
from typing import Optional

from config import IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT

logger = logging.getLogger(__name__)

# Cache for the ImageKit client
_client = None


def get_imagekit_client():
    """Get ImageKit client instance."""
    global _client

    if _client is not None:
        return _client

    if not IMAGEKIT_PRIVATE_KEY:
        logger.warning("IMAGEKIT_PRIVATE_KEY not configured")
        return None

    try:
        from imagekitio import ImageKit
        _client = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)
        logger.info("ImageKit client initialized successfully")
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize ImageKit: {e}")
        return None


def upload_food_image(image_bytes: bytes, user_id: int, food_name: str = "food") -> Optional[str]:
    """
    Upload a food image to ImageKit and return the URL.

    Args:
        image_bytes: The image data as bytes
        user_id: Telegram user ID
        food_name: Name of the food for the filename

    Returns:
        ImageKit URL, or None if upload failed
    """
    client = get_imagekit_client()
    if not client:
        return None

    try:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean food name for filename
        clean_name = "".join(c for c in food_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_')[:30]
        filename = f"{timestamp}_{user_id}_{clean_name}.jpg"

        # Upload to ImageKit using the SDK
        response = client.files.upload(
            file=image_bytes,
            file_name=filename,
            folder="/food-tracker-ihsan",
            tags=["food", f"user_{user_id}"]
        )

        if response and response.url:
            logger.info(f"Uploaded food image to ImageKit: {response.url}")
            return response.url
        else:
            logger.error(f"ImageKit upload failed: no URL in response")
            return None

    except Exception as e:
        logger.error(f"Failed to upload image to ImageKit: {e}")
        return None


def is_imagekit_configured() -> bool:
    """Check if ImageKit is properly configured."""
    return bool(IMAGEKIT_PRIVATE_KEY)
