"""Validation Benchmark Runner for Carpet Style & Story Match v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from datetime import datetime, timezone
from typing import Dict, List

from app.domain.validation.checks import run_all_checks
from app.domain.validation.constants import (
    RELEASE_CONTRACT_VERSION,
    VALIDATION_BENCHMARK_VERSION,
    VERSION_INVENTORY,
)
from app.domain.validation.models import (
    BenchmarkCheckResult,
    BenchmarkCheckStatus,
    BenchmarkGroupResult,
    OverallBenchmarkStatus,
    ValidationBenchmarkReport,
)


class ValidationBenchmarkRunner:
    """Executes all validation check suites and generates machine-readable reports."""

    def __init__(self):
        self.version_inventory = VERSION_INVENTORY

    def run(self) -> ValidationBenchmarkReport:
        started_at = datetime.now(timezone.utc).isoformat()

        # Run check suite
        all_checks: List[BenchmarkCheckResult] = run_all_checks()

        # Group checks by group_id
        grouped: Dict[str, List[BenchmarkCheckResult]] = {}
        for c in all_checks:
            grouped.setdefault(c.group_id, []).append(c)

        group_results: List[BenchmarkGroupResult] = []
        total_failed = 0
        total_passed = 0
        total_warnings = 0

        for group_id, checks in grouped.items():
            g_total = len(checks)
            g_passed = sum(1 for c in checks if c.status == BenchmarkCheckStatus.PASS)
            g_failed = sum(1 for c in checks if c.status == BenchmarkCheckStatus.FAIL)
            g_warnings = sum(1 for c in checks if c.status == BenchmarkCheckStatus.WARN)

            total_passed += g_passed
            total_failed += g_failed
            total_warnings += g_warnings

            g_status = (
                OverallBenchmarkStatus.FAIL
                if g_failed > 0
                else OverallBenchmarkStatus.PASS
            )

            group_results.append(
                BenchmarkGroupResult(
                    group_id=group_id,
                    title=f"Benchmark Group {group_id}",
                    total_checks=g_total,
                    passed_checks=g_passed,
                    failed_checks=g_failed,
                    warning_checks=g_warnings,
                    status=g_status,
                    checks=checks,
                )
            )

        completed_at = datetime.now(timezone.utc).isoformat()

        # Rule 7: NO HIDDEN FAILURES - If any required check fails, overall_status MUST be FAIL
        overall_status = (
            OverallBenchmarkStatus.FAIL
            if total_failed > 0
            else OverallBenchmarkStatus.PASS
        )

        return ValidationBenchmarkReport(
            benchmark_version=VALIDATION_BENCHMARK_VERSION,
            release_contract_version=RELEASE_CONTRACT_VERSION,
            algorithm_versions=self.version_inventory,
            started_at=started_at,
            completed_at=completed_at,
            total_checks=len(all_checks),
            passed_checks=total_passed,
            failed_checks=total_failed,
            warning_checks=total_warnings,
            overall_status=overall_status,
            groups=group_results,
            checks=all_checks,
        )
