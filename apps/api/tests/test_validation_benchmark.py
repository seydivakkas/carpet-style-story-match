"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""
import pytest
from app.domain.validation.benchmark import ValidationBenchmarkRunner
from app.domain.validation.models import OverallBenchmarkStatus


def test_validation_benchmark_all_checks_pass():
    """Executes the master validation benchmark suite and asserts 100% required check pass rate."""
    runner = ValidationBenchmarkRunner()
    report = runner.run()
    
    assert report.overall_status == OverallBenchmarkStatus.PASS, f"Validation benchmark failed with {report.failed_checks} failures"
    assert report.failed_checks == 0, f"Expected 0 failed checks, got {report.failed_checks}"
    assert report.passed_checks == report.total_checks, "Not all checks passed"
    assert report.total_checks >= 30, f"Expected at least 30 benchmark checks, got {report.total_checks}"
