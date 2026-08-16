"""
Developer Smoke CLI Tool for VLM Visual Motif Detection (V2-03).

Usage:
    python scripts/smoke_motif_vlm.py --image <path_to_image> [--output result.json] [--provider TEST_FIXTURE]

Does NOT commit or alter production DB.
"""
import sys
import os
import argparse
import asyncio
import json
import time
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from app.core.config import Settings
from app.domain.upload_analysis import (
    prepare_image_for_vlm,
    get_vlm_provider,
    validate_upload_analysis_result,
    FORBIDDEN_CULTURAL_FIELDS
)


async def run_smoke_test(image_path: str, provider_override: str = None, output_path: str = None):
    print("=" * 60)
    print("V2-03 VLM MOTIF DETECTION SMOKE TOOL")
    print("=" * 60)

    if not os.path.exists(image_path):
        print(f"ERROR: Image file not found: {image_path}")
        sys.exit(1)

    settings = Settings()
    if provider_override:
        settings.MOTIF_VLM_PROVIDER = provider_override

    print(f"Image Path    : {image_path}")
    print(f"Provider Mode : {settings.MOTIF_VLM_PROVIDER}")
    print(f"Model ID      : {settings.MOTIF_VLM_MODEL}")
    print(f"Base URL      : {settings.MOTIF_VLM_BASE_URL or '(None)'}")

    provider = get_vlm_provider(settings)
    if not provider:
        print("\n[RESULT] VLM Provider is DISABLED in settings. Exiting.")
        sys.exit(0)

    with open(image_path, "rb") as f:
        raw_bytes = f.read()

    ext = Path(image_path).suffix.lower().lstrip(".")
    mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"

    print("\nPreparing and sanitizing image (EXIF strip)...")
    prep = prepare_image_for_vlm(raw_bytes, mime, is_remote=(settings.MOTIF_VLM_PROVIDER.upper() == "REMOTE_OPENAI_COMPATIBLE"))
    print(f"Original SHA-256 : {prep.original_sha256[:16]}... ({prep.original_width}x{prep.original_height})")
    print(f"Prepared SHA-256 : {prep.prepared_sha256[:16]}... ({prep.prepared_width}x{prep.prepared_height})")

    print("\nExecuting visual inference...")
    start_time = time.time()
    result = await provider.analyze(prep)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    print(f"\nInference Complete in {latency_ms} ms!")
    print("-" * 60)
    print(f"Analysis ID       : {result.analysis_id}")
    print(f"Visual Category   : {result.visual_category.category_key} (conf: {result.visual_category.confidence})")
    print(f"Observations      : {len(result.visual_observations)}")
    print(f"Motif Candidates  : {len(result.motif_candidates)}")
    for mc in result.motif_candidates:
        print(f"  - [{mc.status.value}] candidate: '{mc.visual_candidate_key}' -> canonical: '{mc.proposed_canonical_motif_key}' (conf: {mc.confidence})")
    print(f"Abstentions       : {len(result.abstentions)}")
    print(f"Provenance        : provider={result.provenance.provider_type}, model={result.provenance.model_id}, prompt={result.provenance.prompt_version}")

    # Validate Contract & Zero Cultural Fields
    print("\nValidating Contract & Safety Invariants...")
    validate_upload_analysis_result(result)

    result_json_str = result.model_dump_json()
    cultural_violations = sum(1 for field in FORBIDDEN_CULTURAL_FIELDS if field in result_json_str.lower())
    print(f"Contract Validation: PASS")
    print(f"Cultural Violations: {cultural_violations}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        print(f"\nStructured result saved to: {output_path}")

    print("\n[SUCCESS] Smoke test completed successfully with 0 cultural violations.")


def main():
    parser = argparse.ArgumentParser(description="Smoke test VLM Motif Detection")
    parser.add_argument("--image", required=True, help="Path to carpet image")
    parser.add_argument("--provider", choices=["DISABLED", "LOCAL_VLLM", "REMOTE_OPENAI_COMPATIBLE", "TEST_FIXTURE"], help="Override provider mode")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    asyncio.run(run_smoke_test(args.image, args.provider, args.output))


if __name__ == "__main__":
    main()
