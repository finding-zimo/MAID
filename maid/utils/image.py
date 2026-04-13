"""Frame preprocessing: resize and JPEG-encode captured screenshots."""

from __future__ import annotations

import base64
import io

from PIL import Image

# Maximum dimension (width or height). Claude's vision works well at 720p,
# and keeping frames small directly reduces token count and API latency.
MAX_DIMENSION = 1280


def encode_frame(png_bytes: bytes, quality: int = 80) -> str:
    """Resize a raw PNG screenshot and return a base64-encoded JPEG string.

    Args:
        png_bytes: Raw PNG image data from mss.
        quality: JPEG compression quality (0-100). 80 is a good balance.

    Returns:
        Base64 string suitable for the Anthropic vision API.
    """
    img = Image.open(io.BytesIO(png_bytes))

    # Convert RGBA (mss default) to RGB for JPEG encoding.
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize if larger than MAX_DIMENSION on either axis, preserving aspect ratio.
    w, h = img.size
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")
