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
from pipeline_health_trend_analyzer.trend_engine import (
    DEFAULT_METRIC_DEFINITIONS,
    MetricDefinition,
    TrendEngine,
    calculate_linear_slope,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_METRIC_DEFINITIONS",
    "DuplicateHealthReportError",
    "HealthReportFileNotFoundError",
    "HealthReportJSONError",
    "HealthReportLoadError",
    "HealthReportLoader",
    "HealthReportValidationError",
    "LoadedHealthReport",
    "MetricDefinition",
    "MetricTrend",
    "TrendDirection",
    "TrendEngine",
    "TrendReport",
    "TrendSample",
    "TrendSummary",
    "calculate_linear_slope",
    "__version__",
]
