"""CLI Script for Historical Reference Curation Import v1."""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from app.db.session import AsyncSessionLocal
from app.domain.historical_reference.importer import HistoricalReferenceImporter
from app.domain.historical_reference.schemas import HistoricalReferenceImportDataset


async def run_import(file_path: str, dry_run: bool) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Import dataset file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    dataset = HistoricalReferenceImportDataset.model_validate(raw_data)

    async with AsyncSessionLocal() as session:
        importer = HistoricalReferenceImporter(session)
        result = await importer.import_dataset(dataset, dry_run=dry_run)
        return result


def main():
    parser = argparse.ArgumentParser(description="Import Historical Reference Curation Dataset v1")
    parser.add_argument("file_path", help="Path to historical reference curation JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset and source references without writing to DB")

    args = parser.parse_args()

    try:
        res = asyncio.run(run_import(args.file_path, args.dry_run))
        print("IMPORT SUCCESSFUL")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"IMPORT FAILED: {type(e).__name__}: {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
