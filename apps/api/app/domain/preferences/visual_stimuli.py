import os
import hashlib
import io
import math
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageDraw

VISUAL_PREFERENCE_STIMULI_VERSION = "visual-preference-stimuli-v1"

# Reference 9D Style DNA vectors for stimulus variants (intent vectors)
# Canonical dimensions: D1..D9
# D1: color_energy, D2: color_diversity, D3: contrast, D4: warmth,
# D5: visual_complexity, D6: structural_order, D7: rhythm_repetition,
# D8: focal_strength, D9: form_language

STIMULI_CATALOG: Dict[str, Dict[str, Any]] = {
    "V1_COLOR_ENERGY": {
        "stimulus_key": "V1_COLOR_ENERGY",
        "target_dimension": "color_energy",
        "base_family": "BASE_A",  # Abstract Medallion
        "description": "Calm muted chroma vs vivid energetic chroma",
        "reference_style_dna_a": {
            "color_energy": 0.15, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.85, "rhythm_repetition": 0.50,
            "focal_strength": 0.70, "form_language": 0.50
        },
        "reference_style_dna_b": {
            "color_energy": 0.85, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.85, "rhythm_repetition": 0.50,
            "focal_strength": 0.70, "form_language": 0.50
        }
    },
    "V2_CONTRAST": {
        "stimulus_key": "V2_CONTRAST",
        "target_dimension": "contrast",
        "base_family": "BASE_B",  # Abstract All-Over
        "description": "Soft separation vs strong separation",
        "reference_style_dna_a": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.15, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.70, "rhythm_repetition": 0.60,
            "focal_strength": 0.40, "form_language": 0.50
        },
        "reference_style_dna_b": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.85, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.70, "rhythm_repetition": 0.60,
            "focal_strength": 0.40, "form_language": 0.50
        }
    },
    "V3_VISUAL_COMPLEXITY": {
        "stimulus_key": "V3_VISUAL_COMPLEXITY",
        "target_dimension": "visual_complexity",
        "base_family": "BASE_C",  # Abstract Banded
        "description": "Simple macro geometry vs detailed micro-ornamentation",
        "reference_style_dna_a": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.15, "structural_order": 0.75, "rhythm_repetition": 0.50,
            "focal_strength": 0.50, "form_language": 0.50
        },
        "reference_style_dna_b": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.85, "structural_order": 0.75, "rhythm_repetition": 0.50,
            "focal_strength": 0.50, "form_language": 0.50
        }
    },
    "V4_STRUCTURAL_ORDER": {
        "stimulus_key": "V4_STRUCTURAL_ORDER",
        "target_dimension": "structural_order",
        "base_family": "BASE_A",  # Abstract Medallion
        "description": "Asymmetric free arrangement vs symmetric ordered arrangement",
        "reference_style_dna_a": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.20, "rhythm_repetition": 0.50,
            "focal_strength": 0.40, "form_language": 0.50
        },
        "reference_style_dna_b": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.90, "rhythm_repetition": 0.50,
            "focal_strength": 0.70, "form_language": 0.50
        }
    },
    "V5_RHYTHM_REPETITION": {
        "stimulus_key": "V5_RHYTHM_REPETITION",
        "target_dimension": "rhythm_repetition",
        "base_family": "BASE_B",  # Abstract All-Over
        "description": "4 varied motifs without grid repetition vs 16 grid-positioned identical motifs",
        "reference_style_dna_a": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.75, "rhythm_repetition": 0.15,
            "focal_strength": 0.40, "form_language": 0.50
        },
        "reference_style_dna_b": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.75, "rhythm_repetition": 0.90,
            "focal_strength": 0.40, "form_language": 0.50
        }
    },
    "V6_FORM_LANGUAGE": {
        "stimulus_key": "V6_FORM_LANGUAGE",
        "target_dimension": "form_language",
        "base_family": "BASE_C",  # Abstract Banded
        "description": "Angular polygonal straight-line vs curvilinear flowing organic",
        "reference_style_dna_a": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.70, "rhythm_repetition": 0.50,
            "focal_strength": 0.50, "form_language": 0.10
        },
        "reference_style_dna_b": {
            "color_energy": 0.40, "color_diversity": 0.40, "contrast": 0.50, "warmth": 0.50,
            "visual_complexity": 0.40, "structural_order": 0.70, "rhythm_repetition": 0.50,
            "focal_strength": 0.50, "form_language": 0.90
        }
    }
}

CANONICAL_VISUAL_CARDS = list(STIMULI_CATALOG.keys())

class ProceduralStimulusGenerator:
    WIDTH = 600
    HEIGHT = 800

    @staticmethod
    def hex_color(rgb: Tuple[int, int, int]) -> str:
        return "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])

    @classmethod
    def render_stimulus(cls, stimulus_key: str, variant: str) -> Tuple[bytes, bytes, str]:
        """
        Renders stimulus pair variant ('A' or 'B').
        Returns (svg_bytes, png_bytes, sha256_hash_of_svg).
        """
        assert variant in ("A", "B")

        if stimulus_key == "V1_COLOR_ENERGY":
            svg, img = cls._render_v1(variant)
        elif stimulus_key == "V2_CONTRAST":
            svg, img = cls._render_v2(variant)
        elif stimulus_key == "V3_VISUAL_COMPLEXITY":
            svg, img = cls._render_v3(variant)
        elif stimulus_key == "V4_STRUCTURAL_ORDER":
            svg, img = cls._render_v4(variant)
        elif stimulus_key == "V5_RHYTHM_REPETITION":
            svg, img = cls._render_v5(variant)
        elif stimulus_key == "V6_FORM_LANGUAGE":
            svg, img = cls._render_v6(variant)
        else:
            raise ValueError(f"Unknown stimulus key: {stimulus_key}")

        svg_bytes = svg.encode("utf-8")
        
        png_io = io.BytesIO()
        img.save(png_io, format="PNG")
        png_bytes = png_io.getvalue()

        sha256 = hashlib.sha256(svg_bytes).hexdigest()
        return svg_bytes, png_bytes, sha256

    # -----------------------------------------------------------------
    # V1: Color Energy (BASE_A Medallion)
    # A = desaturated calm chroma, B = vivid energetic chroma (matching L* structure)
    # -----------------------------------------------------------------
    @classmethod
    def _render_v1(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        if variant == "A":
            # Desaturated muted tones matching L* lightness of Variant B
            bg = (120, 110, 105)
            border = (60, 55, 70)
            inner = (215, 210, 200)
            med = (105, 95, 110)
            accent = (135, 145, 135)
        else:
            # Saturated vivid energetic tones
            bg = (215, 45, 30)       # Crimson
            border = (30, 50, 195)    # Cobalt
            inner = (245, 205, 35)    # Gold
            med = (175, 35, 185)     # Magenta
            accent = (25, 175, 75)    # Emerald

        draw.rectangle([0, 0, W, H], fill=bg)
        draw.rectangle([40, 40, W-40, H-40], fill=border, outline=inner, width=8)
        draw.rectangle([80, 80, W-80, H-80], fill=inner)

        cx, cy = W//2, H//2
        draw.ellipse([cx-150, cy-200, cx+150, cy+200], fill=med, outline=accent, width=6)
        draw.polygon([(cx, cy-120), (cx+100, cy), (cx, cy+120), (cx-100, cy)], fill=accent)

        bg_h = cls.hex_color(bg)
        border_h = cls.hex_color(border)
        inner_h = cls.hex_color(inner)
        med_h = cls.hex_color(med)
        accent_h = cls.hex_color(accent)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  <rect x="40" y="40" width="{W-80}" height="{H-80}" fill="{border_h}" stroke="{inner_h}" stroke-width="8"/>
  <rect x="80" y="80" width="{W-160}" height="{H-160}" fill="{inner_h}"/>
  <ellipse cx="{cx}" cy="{cy}" rx="150" ry="200" fill="{med_h}" stroke="{accent_h}" stroke-width="6"/>
  <polygon points="{cx},{cy-120} {cx+100},{cy} {cx},{cy+120} {cx-100},{cy}" fill="{accent_h}"/>
</svg>'''
        return svg, img

    # -----------------------------------------------------------------
    # V2: Contrast (BASE_B All-Over)
    # A = soft separation, B = strong separation (exact same warm hue family)
    # -----------------------------------------------------------------
    @classmethod
    def _render_v2(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        if variant == "A":
            # Soft luminance contrast (warm terracotta theme with edge definition)
            bg = (140, 100, 60)
            motif_c = (205, 165, 125)
            border = (175, 135, 95)
        else:
            # High luminance contrast (same warm amber/terracotta theme)
            bg = (35, 18, 8)
            motif_c = (245, 205, 150)
            border = (210, 170, 120)

        draw.rectangle([0, 0, W, H], fill=bg)
        draw.rectangle([30, 30, W-30, H-30], fill=bg, outline=border, width=6)

        rows, cols = 6, 4
        dx = (W - 120) // cols
        dy = (H - 120) // rows

        motifs_svg = []
        motif_h = cls.hex_color(motif_c)
        for r in range(rows):
            for c in range(cols):
                cx = 60 + c * dx + dx // 2
                cy = 60 + r * dy + dy // 2
                draw.polygon([(cx, cy-25), (cx+25, cy), (cx, cy+25), (cx-25, cy)], fill=motif_c)
                motifs_svg.append(f'<polygon points="{cx},{cy-25} {cx+25},{cy} {cx},{cy+25} {cx-25},{cy}" fill="{motif_h}"/>')

        bg_h = cls.hex_color(bg)
        border_h = cls.hex_color(border)
        motifs_str = "\n  ".join(svg_motifs if 'svg_motifs' in locals() else motifs_svg)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  <rect x="30" y="30" width="{W-60}" height="{H-60}" fill="{bg_h}" stroke="{border_h}" stroke-width="6"/>
  {motifs_str}
</svg>'''
        return svg, img

    # -----------------------------------------------------------------
    # V3: Visual Complexity (BASE_C Banded)
    # A = simple macro bands, B = micro-ornaments, nested geometry and internal hatching
    # -----------------------------------------------------------------
    @classmethod
    def _render_v3(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        bg = (40, 60, 90)
        band_c = (200, 160, 80)
        line_c = (235, 205, 135)
        detail_c = (150, 115, 45)

        draw.rectangle([0, 0, W, H], fill=bg)

        band_height = H // 7
        svg_bands = []
        band_h = cls.hex_color(band_c)
        line_h = cls.hex_color(line_c)
        detail_h = cls.hex_color(detail_c)

        cx = W // 2

        for i in range(1, 6):
            y1 = i * band_height + 5
            y2 = y1 + band_height - 30
            cy_mid = (y1 + y2) // 2

            draw.rectangle([60, y1, W-60, y2], fill=band_c)
            svg_bands.append(f'<rect x="60" y="{y1}" width="{W-120}" height="{y2-y1}" fill="{band_h}"/>')

            if variant == "B":
                # Concentric inner borders (tone-on-tone)
                draw.rectangle([66, y1+3, W-66, y2-3], outline=line_c, width=2)
                draw.rectangle([72, y1+6, W-72, y2-6], outline=detail_c, width=2)
                draw.line([(72, cy_mid), (W-72, cy_mid)], fill=line_c, width=1)
                svg_bands.append(f'<rect x="66" y="{y1+3}" width="{W-132}" height="{y2-y1-6}" fill="none" stroke="{line_h}" stroke-width="2"/>')
                svg_bands.append(f'<rect x="72" y="{y1+6}" width="{W-144}" height="{y2-y1-12}" fill="none" stroke="{detail_h}" stroke-width="2"/>')
                svg_bands.append(f'<line x1="72" y1="{cy_mid}" x2="{W-72}" y2="{cy_mid}" stroke="{line_h}" stroke-width="1"/>')

                # Strictly symmetric vertical hatching & micro-diamonds
                max_offset = (W // 2) - 80
                for offset in range(0, max_offset + 1, 6):
                    x1_pos = cx - offset
                    x2_pos = cx + offset

                    # Left line & micro-element
                    draw.line([(x1_pos, y1+8), (x1_pos, y2-8)], fill=line_c, width=1)
                    draw.polygon([(x1_pos, cy_mid-2), (x1_pos+2, cy_mid), (x1_pos, cy_mid+2), (x1_pos-2, cy_mid)], fill=detail_c)
                    svg_bands.append(f'<line x1="{x1_pos}" y1="{y1+8}" x2="{x1_pos}" y2="{y2-8}" stroke="{line_h}" stroke-width="1"/>')
                    svg_bands.append(f'<polygon points="{x1_pos},{cy_mid-2} {x1_pos+2},{cy_mid} {x1_pos},{cy_mid+2} {x1_pos-2},{cy_mid}" fill="{detail_h}"/>')

                    if offset > 0:
                        # Right line & micro-element
                        draw.line([(x2_pos, y1+8), (x2_pos, y2-8)], fill=line_c, width=1)
                        draw.polygon([(x2_pos, cy_mid-2), (x2_pos+2, cy_mid), (x2_pos, cy_mid+2), (x2_pos-2, cy_mid)], fill=detail_c)
                        svg_bands.append(f'<line x1="{x2_pos}" y1="{y1+8}" x2="{x2_pos}" y2="{y2-8}" stroke="{line_h}" stroke-width="1"/>')
                        svg_bands.append(f'<polygon points="{x2_pos},{cy_mid-2} {x2_pos+2},{cy_mid} {x2_pos},{cy_mid+2} {x2_pos-2},{cy_mid}" fill="{detail_h}"/>')

        bg_h = cls.hex_color(bg)
        bands_str = "\n  ".join(svg_bands)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  {bands_str}
</svg>'''
        return svg, img

    # -----------------------------------------------------------------
    # V4: Structural Order (BASE_A Medallion)
    # A = perturbed/asymmetric, B = 4-way bilateral symmetric
    # -----------------------------------------------------------------
    @classmethod
    def _render_v4(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        bg = (180, 50, 40)
        border = (30, 30, 30)
        med = (220, 190, 100)
        acc = (20, 100, 160)

        draw.rectangle([0, 0, W, H], fill=bg)
        draw.rectangle([40, 40, W-40, H-40], fill=bg, outline=border, width=8)

        cx, cy = W//2, H//2
        med_h = cls.hex_color(med)
        acc_h = cls.hex_color(acc)

        if variant == "A":
            # Strongly asymmetric / perturbed spatial arrangement
            med_cx, med_cy = cx - 110, cy + 120
            draw.ellipse([med_cx-120, med_cy-140, med_cx+120, med_cy+140], fill=med)

            # 4 corner motifs placed asymmetrically (3 concentrated on upper-right/top, 1 small on bottom-left)
            draw.rectangle([W-220, 60, W-70, 210], fill=acc)
            draw.rectangle([W-180, 230, W-80, 330], fill=acc)
            draw.rectangle([220, 80, 320, 180], fill=acc)
            draw.rectangle([50, H-120, 120, H-50], fill=acc)

            svg_shapes = f'''
  <ellipse cx="{med_cx}" cy="{med_cy}" rx="120" ry="140" fill="{med_h}"/>
  <rect x="{W-220}" y="60" width="150" height="150" fill="{acc_h}"/>
  <rect x="{W-180}" y="230" width="100" height="100" fill="{acc_h}"/>
  <rect x="220" y="80" width="100" height="100" fill="{acc_h}"/>
  <rect x="50" y="{H-120}" width="70" height="70" fill="{acc_h}"/>
'''
        else:
            # Perfect 4-way bilateral reflection symmetry
            med_cx, med_cy = cx, cy
            draw.ellipse([med_cx-130, med_cy-160, med_cx+130, med_cy+160], fill=med)

            draw.rectangle([70, 70, 170, 170], fill=acc)
            draw.rectangle([W-170, 70, W-70, 170], fill=acc)
            draw.rectangle([70, H-170, 170, H-70], fill=acc)
            draw.rectangle([W-170, H-170, W-70, H-70], fill=acc)

            svg_shapes = f'''
  <ellipse cx="{med_cx}" cy="{med_cy}" rx="130" ry="160" fill="{med_h}"/>
  <rect x="70" y="70" width="100" height="100" fill="{acc_h}"/>
  <rect x="{W-170}" y="70" width="100" height="100" fill="{acc_h}"/>
  <rect x="70" y="{H-170}" width="100" height="100" fill="{acc_h}"/>
  <rect x="{W-170}" y="{H-170}" width="100" height="100" fill="{acc_h}"/>
'''

        bg_h = cls.hex_color(bg)
        border_h = cls.hex_color(border)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  <rect x="40" y="40" width="{W-80}" height="{H-80}" fill="{bg_h}" stroke="{border_h}" stroke-width="8"/>
  {svg_shapes}
</svg>'''
        return svg, img

    # -----------------------------------------------------------------
    # V5: Rhythm & Repetition (BASE_B All-Over)
    # A = 4 symmetric varied motifs without grid repetition
    # B = 16 grid-positioned identical motifs
    # -----------------------------------------------------------------
    @classmethod
    def _render_v5(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        
        # Subtle texture background
        np.random.seed(42)
        noise = np.random.randint(-20, 20, (H, W, 3), dtype=np.int32)
        bg_base = np.array([30, 80, 60], dtype=np.int32)
        bg = np.clip(bg_base + noise, 0, 255).astype(np.uint8)

        img = Image.fromarray(bg)
        draw = ImageDraw.Draw(img)

        motif_c = (230, 210, 160)
        border = (20, 50, 40)
        motif_h = cls.hex_color(motif_c)
        border_h = cls.hex_color(border)

        draw.rectangle([30, 30, W-30, H-30], outline=border, width=6)

        motifs_svg = []

        if variant == "A":
            # 4 symmetric positions (top-left, top-right, bottom-left, bottom-right) with 4 DIFFERENT shapes
            draw.ellipse([100-15, 150-15, 100+15, 150+15], fill=motif_c) # circle top-left
            draw.rectangle([500-14, 150-14, 500+14, 150+14], fill=motif_c) # rect top-right
            draw.polygon([(100, 650-16), (100+16, 650+16), (100-16, 650+16)], fill=motif_c) # tri bottom-left
            draw.polygon([(500, 650-16), (500+16, 650), (500, 650+16), (500-16, 650)], fill=motif_c) # diamond bottom-right

            motifs_svg.append(f'<circle cx="100" cy="150" r="15" fill="{motif_h}"/>')
            motifs_svg.append(f'<rect x="486" y="136" width="28" height="28" fill="{motif_h}"/>')
            motifs_svg.append(f'<polygon points="100,634 116,666 84,666" fill="{motif_h}"/>')
            motifs_svg.append(f'<polygon points="500,634 516,650 500,666 484,650" fill="{motif_h}"/>')
        else:
            # 16 grid-positioned identical motifs (4x4)
            rows, cols = 4, 4
            dx = (W - 120) // cols
            dy = (H - 120) // rows

            for r in range(rows):
                for c in range(cols):
                    cx = 60 + c * dx + dx // 2
                    cy = 60 + r * dy + dy // 2
                    draw.ellipse([cx-15, cy-15, cx+15, cy+15], fill=motif_c)
                    motifs_svg.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{motif_h}"/>')

        bg_h = "#1e503c"
        motifs_str = "\n  ".join(motifs_svg)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  <rect x="30" y="30" width="{W-60}" height="{H-60}" fill="{bg_h}" stroke="{border_h}" stroke-width="6"/>
  {motifs_str}
</svg>'''
        return svg, img

    # -----------------------------------------------------------------
    # V6: Form Language (BASE_C Banded)
    # A = Angular straight-line geometric vs B = Curvilinear organic flowing
    # -----------------------------------------------------------------
    @classmethod
    def _render_v6(cls, variant: str) -> Tuple[str, Image.Image]:
        W, H = cls.WIDTH, cls.HEIGHT
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        bg = (50, 40, 70)
        motif_c = (220, 170, 90)
        accent = (180, 70, 110)

        draw.rectangle([0, 0, W, H], fill=bg)

        band_w = W // 3
        motifs_svg = []
        motif_h = cls.hex_color(motif_c)
        acc_h = cls.hex_color(accent)

        for col in range(3):
            cx = col * band_w + band_w // 2
            for row in range(4):
                cy = 100 + row * 180

                if variant == "A":
                    pts = [(cx, cy-60), (cx+50, cy), (cx, cy+60), (cx-50, cy)]
                    draw.polygon(pts, fill=motif_c, outline=accent, width=4)
                    pts_str = f"{cx},{cy-60} {cx+50},{cy} {cx},{cy+60} {cx-50},{cy}"
                    motifs_svg.append(f'<polygon points="{pts_str}" fill="{motif_h}" stroke="{acc_h}" stroke-width="4"/>')
                else:
                    draw.ellipse([cx-50, cy-60, cx+50, cy+60], fill=motif_c, outline=accent, width=4)
                    motifs_svg.append(f'<ellipse cx="{cx}" cy="{cy}" rx="50" ry="60" fill="{motif_h}" stroke="{acc_h}" stroke-width="4"/>')

        bg_h = cls.hex_color(bg)
        motifs_str = "\n  ".join(motifs_svg)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{bg_h}"/>
  {motifs_str}
</svg>'''
        return svg, img

def generate_and_save_all_stimuli(target_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Generates all 12 stimulus assets (6 cards x 2 variants) and writes .svg and .png files.
    Returns asset hash mapping: { 'V1_COLOR_ENERGY_A': sha256, ... }
    """
    abs_target_dir = os.path.abspath(target_dir)
    os.makedirs(abs_target_dir, exist_ok=True)
    hashes = {}

    for key in CANONICAL_VISUAL_CARDS:
        for variant in ["A", "B"]:
            asset_key = f"{key}_{variant}"
            svg_bytes, png_bytes, sha256 = ProceduralStimulusGenerator.render_stimulus(key, variant)
            
            svg_path = os.path.join(abs_target_dir, f"{asset_key.lower()}.svg")
            png_path = os.path.join(abs_target_dir, f"{asset_key.lower()}.png")

            try:
                if not os.path.exists(svg_path) or os.path.getsize(svg_path) == 0:
                    with open(svg_path, "wb") as f:
                        f.write(svg_bytes)
            except OSError:
                pass

            try:
                if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
                    with open(png_path, "wb") as f:
                        f.write(png_bytes)
            except OSError:
                pass

            hashes[asset_key] = sha256

    return hashes
