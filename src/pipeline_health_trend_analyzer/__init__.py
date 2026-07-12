"""Pipeline Health Trend Analyzer MVP.

Analyze historical pipeline health reports and produce structured
health trend assessments.
"""

from pipeline_health_trend_analyzer.analyzer import (
    PipelineHealthTrendAnalyzer,
)
from pipeline_health_trend_analyzer.contract import (
    MetricTrend,
    TrendDirection,
    TrendOverview,
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
from pipeline_health_trend_analyzer.report_io import (
    TrendReportContractError,
    TrendReportFileNotFoundError,
    TrendReportInspection,
    TrendReportIOError,
    TrendReportJSONError,
    TrendReportSerializer,
    TrendReportStore,
)
from pipeline_health_trend_analyzer.summary import (
    TrendSummaryBuilder,
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
    "PipelineHealthTrendAnalyzer",
    "TrendDirection",
    "TrendOverview",
    "TrendEngine",
    "TrendReport",
    "TrendReportStore",
    "TrendReportSerializer",
    "TrendReportJSONError",
    "TrendReportIOError",
    "TrendReportInspection",
    "TrendReportFileNotFoundError",
    "TrendReportContractError",
    "TrendSample",
    "TrendSummary",
    "TrendSummaryBuilder",
    "calculate_linear_slope",
    "__version__",
]
