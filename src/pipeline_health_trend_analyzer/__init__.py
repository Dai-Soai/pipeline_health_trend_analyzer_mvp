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

__version__ = "0.1.0"

__all__ = [
    "MetricTrend",
    "TrendDirection",
    "TrendReport",
    "TrendSample",
    "TrendSummary",
    "__version__",
]
