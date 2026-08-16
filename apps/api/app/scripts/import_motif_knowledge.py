"""CLI script to import curated motif story knowledge JSON datasets."""
import argparse
import asyncio
import json
import os
import sys
from app.db.session import AsyncSessionLocal
from app.domain.motif_knowledge.importer import MotifKnowledgeImporter
from app.domain.motif_knowledge.schemas import CurationImportSchema


async def main_async(filepath: str, dry_run: bool, allow_overwrite: bool):
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    schema = CurationImportSchema.model_validate(raw_data)

    async with AsyncSessionLocal() as session:
        importer = MotifKnowledgeImporter(session)
        result = await importer.import_data(schema, dry_run=dry_run, allow_overwrite=allow_overwrite)

    mode = "DRY RUN" if dry_run else "IMPORTED"
    print(f"[{mode} SUCCESS]")
    print(f"  Sources created: {result.sources_created}")
    print(f"  Motifs created: {result.motifs_created}")
    print(f"  Claims created: {result.claims_created}")
    print(f"  Claim Sources created: {result.claim_sources_created}")
    print(f"  Claim Themes created: {result.claim_themes_created}")


def main():
    parser = argparse.ArgumentParser(description="Import curated motif knowledge JSON dataset.")
    parser.add_argument("filepath", help="Path to JSON dataset file")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation without persisting to database")
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow updating existing DB records")

    args = parser.parse_args()
    asyncio.run(main_async(args.filepath, args.dry_run, args.allow_overwrite))


if __name__ == "__main__":
    main()
