"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

V2-04 Developer CLI Script for Carpet Analysis Pipeline.
Usage:
  python -m app.scripts.analyze_carpet --image <path_to_image> [--stages visual motif research] [--subject-motif star] [--output result.json]
"""
import sys
import json
import asyncio
import argparse
from pathlib import Path

from app.core.config import settings
from app.domain.orchestrator import CarpetAnalysisOrchestrator
from app.domain.upload_analysis.service import get_vlm_provider


async def main():
    parser = argparse.ArgumentParser(description="V2-04 Carpet Analysis Pipeline Developer CLI")
    parser.add_argument("--image", required=True, help="Path to carpet image file")
    parser.add_argument("--stages", nargs="+", default=["visual"], choices=["visual", "motif", "research"], help="Analysis stages to execute")
    parser.add_argument("--subject-motif", default=None, help="Verified subject motif key for research stage")
    parser.add_argument("--output", default=None, help="Optional output JSON file path")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Error: Image file '{img_path}' not found.", file=sys.stderr)
        sys.exit(1)

    raw_bytes = img_path.read_bytes()
    mime_type = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"

    # Instantiate VLM provider using factory
    try:
        vlm_prov = get_vlm_provider(settings)
    except Exception:
        vlm_prov = None

    orchestrator = CarpetAnalysisOrchestrator(vlm_provider=vlm_prov)
    results = await orchestrator.run_pipeline(
        raw_bytes=raw_bytes,
        mime_type=mime_type,
        stages=args.stages,
        verified_subject_motif=args.subject_motif
    )

    out_str = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(out_str, encoding="utf-8")
        print(f"Results written to: {out_p}")
    else:
        print(out_str)


if __name__ == "__main__":
    asyncio.run(main())
