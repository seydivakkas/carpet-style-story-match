"""
Image Preparation and Privacy Sanitization Engine for VLM Inference.

Decodes, validates, strips sensitive EXIF metadata, normalizes orientation/format,
and calculates SHA-256 hashes for original and sanitized inference image payloads.
"""
import io
import hashlib
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict


class PreparedInferenceImage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original_sha256: str
    prepared_sha256: str
    original_width: int
    original_height: int
    prepared_width: int
    prepared_height: int
    mime_type: str
    image_bytes: bytes
    preparation_version: str = "vlm-image-prep-v1.0.0"


class ImageValidationError(ValueError):
    """Raised when uploaded image fails MIME, decode, or dimension validation."""
    pass


ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def prepare_image_for_vlm(
    raw_bytes: bytes,
    mime_type: str,
    max_dimension: int = 2048,
    is_remote: bool = False
) -> PreparedInferenceImage:
    """Validate, decode, sanitize EXIF metadata, and prepare image for VLM inference."""
    if not raw_bytes:
        raise ImageValidationError("Empty image payload provided.")

    if mime_type.lower() not in ALLOWED_MIME_TYPES:
        raise ImageValidationError(f"Unsupported MIME type '{mime_type}'. Allowed: {ALLOWED_MIME_TYPES}")

    # Compute original hash
    original_hash = hashlib.sha256(raw_bytes).hexdigest()

    # Decode image using PIL
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()  # Validate header/structure
    except Exception as e:
        raise ImageValidationError(f"Corrupted or invalid image payload: {e}")

    # Re-open after verify() to process pixels
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        orig_w, orig_h = image.size

        # Fix EXIF orientation if present
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # Convert to RGB (strips alpha channel/palette anomalies)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Bounded resize if image exceeds max_dimension
        w, h = image.size
        if w > max_dimension or h > max_dimension:
            if w >= h:
                new_w = max_dimension
                new_h = max(1, int(h * (max_dimension / w)))
            else:
                new_h = max_dimension
                new_w = max(1, int(w * (max_dimension / h)))
            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        prep_w, prep_h = image.size

        # Re-encode to clean JPEG without EXIF metadata (Privacy strip)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=90, exif=b"")  # Explicitly empty EXIF
        prepared_bytes = buf.getvalue()
        prepared_hash = hashlib.sha256(prepared_bytes).hexdigest()

        return PreparedInferenceImage(
            original_sha256=original_hash,
            prepared_sha256=prepared_hash,
            original_width=orig_w,
            original_height=orig_h,
            prepared_width=prep_w,
            prepared_height=prep_h,
            mime_type="image/jpeg",
            image_bytes=prepared_bytes
        )
    except Exception as e:
        raise ImageValidationError(f"Failed to sanitize and encode image for VLM: {e}")
