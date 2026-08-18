"""
Visual Verifier Input Compositor (visual-verifier-input-v1.0.0).

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import io
import hashlib
from typing import Tuple, List, Dict, Any
from PIL import Image, ImageDraw, ImageOps


COMPOSITOR_VERSION = "visual-verifier-input-v1.0.0"


def compose_verifier_input(
    image: Image.Image,
    bbox: List[float],
    proposal_id: str,
    proposed_key: str,
    padding_ratio: float = 0.20,
    target_canvas_size: Tuple[int, int] = (672, 448)
) -> Tuple[Image.Image, str]:
    """
    Composes a single deterministic verifier image containing:
    - Left panel (336x448): Full carpet image with green proposal bounding box.
    - Right panel (336x448): Padded crop around proposal region.

    Returns:
        (composed_pil_image, sha256_hash_hex)
    """
    # Ensure RGB
    base_img = image.convert("RGB")
    w, h = base_img.size

    x1, y1, x2, y2 = bbox
    # Clamp bounding box
    x1_c = max(0.0, min(float(w), x1))
    y1_c = max(0.0, min(float(h), y1))
    x2_c = max(0.0, min(float(w), x2))
    y2_c = max(0.0, min(float(h), y2))

    # Left Panel: Full image + bounding box overlay
    left_img = base_img.copy()
    draw = ImageDraw.Draw(left_img)
    # Draw green bounding box (width=3)
    draw.rectangle([x1_c, y1_c, x2_c, y2_c], outline=(0, 255, 0), width=3)
    left_panel = ImageOps.fit(left_img, (336, 448), Image.Resampling.BILINEAR)

    # Right Panel: Padded proposal crop
    box_w = max(1.0, x2_c - x1_c)
    box_h = max(1.0, y2_c - y1_c)
    pad_x = box_w * padding_ratio
    pad_y = box_h * padding_ratio

    crop_x1 = max(0, int(x1_c - pad_x))
    crop_y1 = max(0, int(y1_c - pad_y))
    crop_x2 = min(w, int(x2_c + pad_x))
    crop_y2 = min(h, int(y2_c + pad_y))

    if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
        crop_img = base_img.crop((int(x1_c), int(y1_c), max(int(x1_c) + 1, int(x2_c)), max(int(y1_c) + 1, int(y2_c))))
    else:
        crop_img = base_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))

    right_panel = ImageOps.fit(crop_img, (336, 448), Image.Resampling.BILINEAR)

    # Canvas concatenation (672 x 448)
    canvas = Image.new("RGB", (672, 448), (255, 255, 255))
    canvas.paste(left_panel, (0, 0))
    canvas.paste(right_panel, (336, 0))

    # Compute deterministic SHA-256 hash of PNG byte buffer
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf_bytes = buf.getvalue()
    image_hash = hashlib.sha256(buf_bytes).hexdigest()

    return canvas, image_hash
