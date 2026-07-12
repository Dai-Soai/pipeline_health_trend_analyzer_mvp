"""Pipeline Health Trend Analyzer MVP.

Analyze historical pipeline health reports and produce structured
health trend assessments.
"""

from pipeline_health_trend_analyzer.contract import (
    MetricTrend,
    TrendDirection,
    TrendReport,
    TrendSample,
    TrendSummary,
)
from pipeline_health_trend_analyzer.health_loader import (
    DuplicateHealthReportError,
    HealthReportFileNotFoundError,
    HealthReportJSONError,
    HealthReportLoadError,
    HealthReportLoader,
    HealthReportValidationError,
    LoadedHealthReport,
)

__version__ = "0.1.0"

__all__ = [
    "DuplicateHealthReportError",
    "HealthReportFileNotFoundError",
    "HealthReportJSONError",
    "HealthReportLoadError",
    "HealthReportLoader",
    "HealthReportValidationError",
    "LoadedHealthReport",
    "MetricTrend",
    "TrendDirection",
    "TrendReport",
    "TrendSample",
    "TrendSummary",
    "__version__",
]
