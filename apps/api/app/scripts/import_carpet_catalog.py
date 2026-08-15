"""CLI script to import carpet catalog curation JSON datasets."""
import argparse
import asyncio
import json
import os
import sys
from app.db.session import AsyncSessionLocal
from app.domain.carpet_catalog.importer import CarpetCatalogImporter
from app.domain.carpet_catalog.schemas import CatalogImportDataset


async def main_async(filepath: str, dry_run: bool):
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    dataset = CatalogImportDataset.model_validate(raw_data)

    async with AsyncSessionLocal() as session:
        importer = CarpetCatalogImporter(session)
        result = await importer.import_dataset(dataset, dry_run=dry_run)

    mode = "DRY RUN" if dry_run else "IMPORTED"
    print(f"[{mode} SUCCESS]")
    print(f"  Carpets created/updated: {result.carpets_created}")
    print(f"  Motif associations created: {result.motif_associations_created}")
    print(f"  Presence sources created: {result.presence_sources_created}")
    print(f"  Story associations created: {result.story_associations_created}")


def main():
    parser = argparse.ArgumentParser(description="Import carpet catalog curation JSON dataset.")
    parser.add_argument("filepath", help="Path to JSON dataset file")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation without persisting to database")

    args = parser.parse_args()
    asyncio.run(main_async(args.filepath, args.dry_run))


if __name__ == "__main__":
    main()
