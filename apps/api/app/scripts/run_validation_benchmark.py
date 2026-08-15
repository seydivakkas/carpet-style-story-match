"""CLI Entrypoint for Validation Benchmark v1.

Usage:
    python -m app.scripts.run_validation_benchmark [--output artifacts/validation/benchmark-report.json]

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import argparse
import sys
from pathlib import Path

from app.domain.validation.benchmark import ValidationBenchmarkRunner
from app.domain.validation.models import OverallBenchmarkStatus
from app.domain.validation.report import (
    export_benchmark_report_json,
    format_benchmark_console_summary,
)


def main():
    parser = argparse.ArgumentParser(description="Run Carpet Style & Story Match Validation Benchmark v1")
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/validation/benchmark-report.json",
        help="Path to save machine-readable benchmark report JSON file."
    )
    args = parser.parse_args()

    # Run Benchmark
    runner = ValidationBenchmarkRunner()
    report = runner.run()

    # Print Console Summary
    summary_text = format_benchmark_console_summary(report)
    print(summary_text)

    # Save JSON Report
    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            # Workspace root relative
            workspace_root = Path(__file__).resolve().parents[3]
            out_path = workspace_root / args.output
        saved_path = export_benchmark_report_json(report, out_path)
        print(f"\n[REPORT SAVED]: {saved_path}")

    # Exit code
    if report.overall_status == OverallBenchmarkStatus.PASS:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
