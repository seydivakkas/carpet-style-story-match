"""Report Exporter & Formatter for Validation Benchmark v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import json
from pathlib import Path
from typing import Optional

from app.domain.validation.models import ValidationBenchmarkReport


def export_benchmark_report_json(report: ValidationBenchmarkReport, output_path: Path) -> Path:
    """Exports ValidationBenchmarkReport to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = report.model_dump()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    return output_path


def format_benchmark_console_summary(report: ValidationBenchmarkReport) -> str:
    """Formats a clean console summary string for the benchmark execution."""
    lines = []
    lines.append("=" * 60)
    lines.append("GÖREV 16 — Validation, Calibration & E2E Benchmark v1")
    lines.append("=" * 60)
    lines.append(f"STATUS: {report.overall_status.value}")
    lines.append(f"Benchmark Version: {report.benchmark_version}")
    lines.append(f"Release Contract Version: {report.release_contract_version}")
    lines.append(f"Started At: {report.started_at}")
    lines.append(f"Completed At: {report.completed_at}")
    lines.append("-" * 60)
    lines.append(f"Total Checks:   {report.total_checks}")
    lines.append(f"Passed Checks:  {report.passed_checks}")
    lines.append(f"Failed Checks:  {report.failed_checks}")
    lines.append(f"Warnings:       {report.warning_checks}")
    lines.append("-" * 60)
    lines.append("Check Groups Breakdown:")
    for g in report.groups:
        status_str = f"[{g.status.value}]"
        lines.append(f"  - {g.group_id:<12} {status_str:<8} (Passed: {g.passed_checks}/{g.total_checks})")
    lines.append("=" * 60)
    return "\n".join(lines)
