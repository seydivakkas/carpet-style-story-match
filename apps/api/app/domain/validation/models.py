"""Validation Domain Pydantic Models for Carpet Style & Story Match v1.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.validation.constants import (
    RELEASE_CONTRACT_VERSION,
    VALIDATION_BENCHMARK_VERSION,
    VERSION_INVENTORY,
)


class BenchmarkCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


class OverallBenchmarkStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class BenchmarkCheckResult(BaseModel):
    check_id: str
    group_id: str
    title: str
    status: BenchmarkCheckStatus
    is_required: bool = True
    message: str
    details: Optional[Dict[str, Any]] = None


class BenchmarkGroupResult(BaseModel):
    group_id: str
    title: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    status: OverallBenchmarkStatus
    checks: List[BenchmarkCheckResult] = Field(default_factory=list)


class ValidationBenchmarkReport(BaseModel):
    benchmark_version: str = VALIDATION_BENCHMARK_VERSION
    release_contract_version: str = RELEASE_CONTRACT_VERSION
    algorithm_versions: Dict[str, str] = Field(default_factory=lambda: VERSION_INVENTORY)
    started_at: str
    completed_at: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    overall_status: OverallBenchmarkStatus
    groups: List[BenchmarkGroupResult] = Field(default_factory=list)
    checks: List[BenchmarkCheckResult] = Field(default_factory=list)
