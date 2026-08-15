import io
import hashlib
from typing import Tuple, Dict, Any
import numpy as np
import cv2
from PIL import Image, ImageOps

from app.core.config import settings
from app.domain.images.exceptions import (
    ImageTooLargeError,
    ImageUnsupportedMediaTypeError,
    ImageDecodeFailedError,
    ImageDimensionsTooSmallError,
    ImageDimensionsTooLargeError
)

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

class ImageValidationService:
    def validate_and_process_upload(
        self,
        file_bytes: bytes,
        content_type: str
    ) -> Tuple[bytes, str, str, int, int, int, int, str]:
        """
        Validates raw image bytes and returns processed tuple:
        (canonical_bytes, mime_type, extension, byte_size, width_px, height_px, channels, sha256)
        """
        # 1. Bounded Byte Size Check
        byte_size = len(file_bytes)
        if byte_size > settings.MAX_IMAGE_UPLOAD_BYTES:
            raise ImageTooLargeError(byte_size, settings.MAX_IMAGE_UPLOAD_BYTES)

        # 2. Content Type Check
        clean_mime = (content_type or "").lower().strip()
        if clean_mime not in ALLOWED_MIME_TYPES:
            raise ImageUnsupportedMediaTypeError(clean_mime)

        extension = ALLOWED_MIME_TYPES[clean_mime]

        # 3. Compute SHA-256 Hash of original input bytes
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # 4. Image Decoding (OpenCV primary, Pillow fallback)
        nparr = np.frombuffer(file_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        width_px = 0
        height_px = 0
        channels = 3

        if img_np is not None:
            if len(img_np.shape) == 2:
                height_px, width_px = img_np.shape
                channels = 1
            elif len(img_np.shape) == 3:
                height_px, width_px, channels = img_np.shape
            else:
                raise ImageDecodeFailedError("Invalid image array shape")
        else:
            # Fallback to Pillow
            try:
                pil_img = Image.open(io.BytesIO(file_bytes))
                pil_img = ImageOps.exif_transpose(pil_img)
                width_px, height_px = pil_img.size
                channels = len(pil_img.getbands())
            except Exception as e:
                raise ImageDecodeFailedError(f"Failed to decode image content: {e}") from e

        # 5. Dimension & Pixel Bounds Validation
        if width_px < settings.MIN_IMAGE_WIDTH or height_px < settings.MIN_IMAGE_HEIGHT:
            raise ImageDimensionsTooSmallError(
                width_px, height_px, settings.MIN_IMAGE_WIDTH, settings.MIN_IMAGE_HEIGHT
            )

        if width_px > settings.MAX_IMAGE_WIDTH or height_px > settings.MAX_IMAGE_HEIGHT:
            raise ImageDimensionsTooLargeError(
                width_px, height_px, settings.MAX_IMAGE_WIDTH, settings.MAX_IMAGE_HEIGHT
            )

        total_pixels = width_px * height_px
        if total_pixels > settings.MAX_IMAGE_PIXELS:
            raise ImageDimensionsTooLargeError(
                width_px, height_px, settings.MAX_IMAGE_WIDTH, settings.MAX_IMAGE_HEIGHT
            )

        # 6. EXIF Privacy Stripping & Normalization
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            pil_img = ImageOps.exif_transpose(pil_img)
            
            # Re-encode clean image without EXIF metadata
            output_buffer = io.BytesIO()
            save_format = "JPEG" if clean_mime in ["image/jpeg", "image/jpg"] else clean_mime.split("/")[-1].upper()
            
            if pil_img.mode in ("RGBA", "P") and save_format == "JPEG":
                pil_img = pil_img.convert("RGB")

            pil_img.save(output_buffer, format=save_format)
            canonical_bytes = output_buffer.getvalue()
        except Exception:
            # Fallback to raw file_bytes if re-encoding fails
            canonical_bytes = file_bytes

        return (
            canonical_bytes,
            clean_mime,
            extension,
            len(canonical_bytes),
            width_px,
            height_px,
            channels,
            sha256
        )
