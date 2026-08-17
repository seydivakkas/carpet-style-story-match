"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Perceptual Color Palette Centroids & Labeling.
Maps CIELAB / HSV / RGB colors to controlled perceptual labels.
NOTE: Perceptual labels (e.g. indigo_like) describe visual appearance ONLY,
NOT dye material identification.
"""
import math
from typing import List, Tuple, Dict

PERCEPTUAL_COLOR_SWATCHES: Dict[str, Tuple[float, float, float]] = {
    # Label: (Lab_L, Lab_a, Lab_b) in OpenCV 0..255 scale (L*2.55, a+128, b+128)
    "deep_red": (75.0, 185.0, 155.0),
    "warm_red": (110.0, 195.0, 165.0),
    "orange_red": (130.0, 180.0, 175.0),
    "orange": (150.0, 160.0, 185.0),
    "ochre": (140.0, 140.0, 170.0),
    "mustard": (160.0, 130.0, 180.0),
    "yellow": (200.0, 120.0, 200.0),
    "yellow_green": (170.0, 100.0, 180.0),
    "green": (130.0, 85.0, 160.0),
    "blue_green": (130.0, 80.0, 130.0),
    "cyan": (170.0, 75.0, 110.0),
    "blue": (110.0, 135.0, 80.0),
    "deep_blue": (60.0, 145.0, 70.0),
    "indigo_like": (45.0, 140.0, 75.0),  # Visual appearance label ONLY
    "violet": (90.0, 165.0, 80.0),
    "magenta": (130.0, 190.0, 110.0),
    "brown": (80.0, 145.0, 150.0),
    "tan": (130.0, 140.0, 150.0),
    "beige": (170.0, 132.0, 142.0),
    "cream": (220.0, 126.0, 135.0),
    "gray": (128.0, 128.0, 128.0),
    "charcoal": (50.0, 128.0, 128.0),
    "black": (20.0, 128.0, 128.0),
    "off_white": (235.0, 127.0, 129.0),
    "white": (250.0, 128.0, 128.0)
}


def get_nearest_perceptual_label(lab_tuple: Tuple[float, float, float]) -> str:
    """Finds the nearest perceptual color label using CIELAB Euclidean distance."""
    l_val, a_val, b_val = lab_tuple
    best_label = "unresolved"
    min_dist = float("inf")

    for label, centroid in PERCEPTUAL_COLOR_SWATCHES.items():
        dist = math.sqrt(
            (l_val - centroid[0]) ** 2 +
            (a_val - centroid[1]) ** 2 +
            (b_val - centroid[2]) ** 2
        )
        if dist < min_dist:
            min_dist = dist
            best_label = label

    return best_label
