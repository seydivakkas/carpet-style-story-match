import io
import cv2
import numpy as np
from PIL import Image

def encode_png(img_bgr: np.ndarray) -> bytes:
    success, buf = cv2.imencode(".png", img_bgr)
    if not success:
        raise ValueError("Could not encode synthetic image to PNG")
    return buf.tobytes()

def create_d1_pair() -> tuple[bytes, bytes]:
    # Low Chroma vs High Chroma
    base = np.zeros((300, 300, 3), dtype=np.uint8)
    base[:, :] = (128, 128, 128)
    
    # Low chroma: pastel pale blue (140, 130, 125 in BGR)
    low_c = base.copy()
    cv2.rectangle(low_c, (50, 50), (250, 250), (140, 130, 125), -1)
    
    # High chroma: vivid intense red/yellow (0, 0, 255 BGR)
    high_c = base.copy()
    cv2.rectangle(high_c, (50, 50), (250, 250), (0, 0, 255), -1)
    cv2.circle(high_c, (150, 150), 60, (0, 255, 255), -1)

    return encode_png(low_c), encode_png(high_c)

def create_d2_pair() -> tuple[bytes, bytes]:
    # 2 Colors vs 8 Colors
    # 2 colors
    img2 = np.zeros((300, 300, 3), dtype=np.uint8)
    img2[:, :] = (50, 50, 50)
    cv2.rectangle(img2, (50, 50), (250, 250), (200, 200, 200), -1)

    # 8 distinct quantized colors
    img8 = np.zeros((300, 300, 3), dtype=np.uint8)
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (100, 100, 255), (255, 100, 100)
    ]
    h, w = 300, 300
    grid = 3
    dw, dh = w // grid, h // grid
    for idx, col in enumerate(colors):
        r = idx // grid
        c = idx % grid
        cv2.rectangle(img8, (c*dw, r*dh), ((c+1)*dw, (r+1)*dh), col, -1)

    return encode_png(img2), encode_png(img8)

def create_d3_pair() -> tuple[bytes, bytes]:
    # Low contrast vs High contrast
    low_cnt = np.full((300, 300, 3), 120, dtype=np.uint8)
    cv2.rectangle(low_cnt, (50, 50), (250, 250), (135, 135, 135), -1)

    high_cnt = np.full((300, 300, 3), 10, dtype=np.uint8)
    cv2.rectangle(high_cnt, (50, 50), (250, 250), (245, 245, 245), -1)

    return encode_png(low_cnt), encode_png(high_cnt)

def create_d4_pair() -> tuple[bytes, bytes]:
    # Cool (Blue/Cyan) vs Warm (Red/Orange/Yellow)
    cool_img = np.zeros((300, 300, 3), dtype=np.uint8)
    cool_img[:, :] = (200, 120, 20)  # BGR Cyan/Blue

    warm_img = np.zeros((300, 300, 3), dtype=np.uint8)
    warm_img[:, :] = (20, 80, 230)  # BGR Red/Orange

    return encode_png(cool_img), encode_png(warm_img)

def create_d5_pair() -> tuple[bytes, bytes]:
    # Simple vs Detailed micro-texture
    simple_img = np.full((300, 300, 3), 150, dtype=np.uint8)
    cv2.rectangle(simple_img, (50, 50), (250, 250), (50, 50, 50), -1)

    detailed_img = simple_img.copy()
    # Add dense high-frequency grid noise/texture
    for r in range(50, 250, 4):
        for c in range(50, 250, 4):
            val = (r * c * 37) % 255
            cv2.rectangle(detailed_img, (c, r), (c+2, r+2), (val, val, val), -1)

    return encode_png(simple_img), encode_png(detailed_img)

def create_d6_pair() -> tuple[bytes, bytes]:
    # Asymmetric/free vs Bilaterally symmetric/balanced
    asym_img = np.full((300, 300, 3), 40, dtype=np.uint8)
    cv2.circle(asym_img, (70, 80), 40, (220, 220, 220), -1)
    cv2.rectangle(asym_img, (180, 200), (280, 250), (180, 180, 180), -1)

    sym_img = np.full((300, 300, 3), 40, dtype=np.uint8)
    cv2.circle(sym_img, (70, 150), 40, (220, 220, 220), -1)
    cv2.circle(sym_img, (230, 150), 40, (220, 220, 220), -1)
    cv2.rectangle(sym_img, (120, 50), (180, 250), (180, 180, 180), -1)

    return encode_png(asym_img), encode_png(sym_img)

def create_d7_pair() -> tuple[bytes, bytes]:
    # Single motif vs Repeated grid motif
    single_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.circle(single_img, (150, 150), 30, (200, 200, 200), -1)

    repeated_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    for r in range(45, 300, 60):
        for c in range(45, 300, 60):
            cv2.circle(repeated_img, (c, r), 15, (200, 200, 200), -1)

    return encode_png(single_img), encode_png(repeated_img)

def create_d6_d7_quadrants() -> dict[str, bytes]:
    # Q1: HIGH ORDER / LOW REPETITION (Single centered symmetric medallion)
    q1 = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.circle(q1, (150, 150), 60, (220, 220, 220), -1)
    cv2.rectangle(q1, (120, 120), (180, 180), (100, 100, 100), -1)

    # Q2: LOW ORDER / HIGH REPETITION (Grid of identical motifs placed asymmetrically/scattered)
    q2 = np.full((300, 300, 3), 30, dtype=np.uint8)
    # Repeated small motif at non-symmetric grid positions
    for r in [40, 90, 140, 190, 240]:
        for c in [30, 80, 130, 180, 230]:
            cv2.rectangle(q2, (c, r), (c+12, r+12), (200, 200, 200), -1)
    # Add asymmetric heavy block on right side
    cv2.rectangle(q2, (220, 10), (290, 80), (250, 250, 250), -1)

    # Q3: HIGH ORDER / HIGH REPETITION (Symmetric grid of identical motifs)
    q3 = np.full((300, 300, 3), 30, dtype=np.uint8)
    for r in range(50, 300, 50):
        for c in range(50, 300, 50):
            cv2.circle(q3, (c, r), 12, (220, 220, 220), -1)

    # Q4: LOW ORDER / LOW REPETITION (Random non-repeating asymmetric shapes)
    q4 = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.ellipse(q4, (80, 100), (40, 20), 30, 0, 360, (180, 180, 180), -1)
    cv2.rectangle(q4, (160, 180), (270, 220), (120, 120, 120), -1)

    return {
        "Q1": encode_png(q1),
        "Q2": encode_png(q2),
        "Q3": encode_png(q3),
        "Q4": encode_png(q4),
    }

def create_d8_triplet() -> tuple[bytes, bytes, bytes]:
    # Uniform vs Central vs Off-center focus
    uniform_img = np.full((300, 300, 3), 100, dtype=np.uint8)

    central_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.circle(central_img, (150, 150), 50, (250, 250, 250), -1)

    offcenter_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.circle(offcenter_img, (70, 70), 50, (250, 250, 250), -1)

    return encode_png(uniform_img), encode_png(central_img), encode_png(offcenter_img)

def create_d9_pair() -> tuple[bytes, bytes]:
    # Geometric (straight lines / sharp polygons) vs Organic (smooth curves / circles)
    geom_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.rectangle(geom_img, (40, 40), (260, 260), (220, 220, 220), 3)
    cv2.line(geom_img, (40, 40), (260, 260), (220, 220, 220), 3)
    cv2.line(geom_img, (260, 40), (40, 260), (220, 220, 220), 3)

    organic_img = np.full((300, 300, 3), 30, dtype=np.uint8)
    cv2.circle(organic_img, (150, 150), 100, (220, 220, 220), 3)
    cv2.ellipse(organic_img, (150, 150), (80, 50), 45, 0, 360, (220, 220, 220), 3)

    return encode_png(geom_img), encode_png(organic_img)

def create_blank_image() -> bytes:
    blank = np.full((300, 300, 3), 128, dtype=np.uint8)
    return encode_png(blank)
