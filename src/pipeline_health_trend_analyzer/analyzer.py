"""Pipeline health trend analysis orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from pipeline_health_trend_analyzer.contract import (
    MetricTrend,
    TrendDirection,
    TrendReport,
    TrendSample,
    TrendSummary,
)
from pipeline_health_trend_analyzer.health_loader import (
    HealthReportLoader,
    LoadedHealthReport,
)
from pipeline_health_trend_analyzer.trend_engine import TrendEngine


DEFAULT_REPORT_VERSION = "1.0"
DEFAULT_ANALYZER_VERSION = "0.1.0"


class PipelineHealthTrendAnalyzer:
    """Analyze historical pipeline health reports."""

    def __init__(
        self,
        *,
        loader: HealthReportLoader | None = None,
        trend_engine: TrendEngine | None = None,
        report_version: str = DEFAULT_REPORT_VERSION,
        analyzer_version: str = DEFAULT_ANALYZER_VERSION,
    ) -> None:
        self._loader = loader or HealthReportLoader()
        self._trend_engine = trend_engine or TrendEngine()
        self._report_version = report_version
        self._analyzer_version = analyzer_version

        errors: list[str] = []

        for name, value in {
            "report_version": self._report_version,
            "analyzer_version": self._analyzer_version,
        }.items():
            if not isinstance(value, str):
                errors.append(f"{name} must be a string")
            elif not value.strip():
                errors.append(f"{name} must not be empty")

        if errors:
            raise ValueError("; ".join(errors))

    @property
    def report_version(self) -> str:
        """Return the generated trend report version."""

        return self._report_version

    @property
    def analyzer_version(self) -> str:
        """Return the trend analyzer implementation version."""

        return self._analyzer_version

    @property
    def loader(self) -> HealthReportLoader:
        """Return the configured health report loader."""

        return self._loader

    @property
    def trend_engine(self) -> TrendEngine:
        """Return the configured statistical trend engine."""

        return self._trend_engine

    def determine_overall_direction(
        self,
        metric_trends: Sequence[MetricTrend],
    ) -> TrendDirection:
        """Determine the aggregate trend direction."""

        normalized_trends = tuple(metric_trends)

        if not normalized_trends:
            raise ValueError("metric_trends must not be empty")

        for index, trend in enumerate(normalized_trends):
            if not isinstance(trend, MetricTrend):
                raise TypeError(
                    f"metric_trends[{index}] must be a MetricTrend"
                )

            errors = trend.validate()

            if errors:
                raise ValueError(
                    "; ".join(
                        f"metric_trends[{index}].{error}"
                        for error in errors
                    )
                )

        improving_count = sum(
            trend.direction is TrendDirection.IMPROVING
            for trend in normalized_trends
        )
        degrading_count = sum(
            trend.direction is TrendDirection.DEGRADING
            for trend in normalized_trends
        )
        insufficient_count = sum(
            trend.direction is TrendDirection.INSUFFICIENT_DATA
            for trend in normalized_trends
        )

        if insufficient_count == len(normalized_trends):
            return TrendDirection.INSUFFICIENT_DATA

        if improving_count > degrading_count:
            return TrendDirection.IMPROVING

        if degrading_count > improving_count:
            return TrendDirection.DEGRADING

        return TrendDirection.STABLE

    def analyze_samples(
        self,
        samples: Sequence[TrendSample],
        *,
        run_id: str | None = None,
        generated_at: str | None = None,
        source_metadata: dict[str, object] | None = None,
    ) -> TrendReport:
        """Analyze normalized historical trend samples."""

        normalized_samples = tuple(samples)

        metric_trends = self._trend_engine.analyze(
            normalized_samples
        )

        overall_direction = self.determine_overall_direction(
            metric_trends
        )

        summary = TrendSummary.from_metric_trends(
            sample_count=len(normalized_samples),
            metric_trends=metric_trends,
            overall_direction=overall_direction,
        )

        report_status = (
            "insufficient_data"
            if overall_direction
            is TrendDirection.INSUFFICIENT_DATA
            else "completed"
        )

        normalized_run_id = run_id or (
            f"trend-{uuid4().hex}"
        )

        normalized_generated_at = (
            generated_at
            or datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        metadata: dict[str, object] = {
            "source_report_count": len(normalized_samples),
            "metric_definition_count": len(
                self._trend_engine.metric_definitions
            ),
        }

        metadata.update(source_metadata or {})

        report = TrendReport(
            report_version=self._report_version,
            analyzer_version=self._analyzer_version,
            run_id=normalized_run_id,
            generated_at=normalized_generated_at,
            status=report_status,
            summary=summary,
            samples=normalized_samples,
            metric_trends=metric_trends,
            source_metadata=metadata,
        )

        errors = report.validate()

        if errors:
            raise ValueError("; ".join(errors))

        return report

    def analyze_loaded_reports(
        self,
        reports: Sequence[LoadedHealthReport],
        *,
        run_id: str | None = None,
        generated_at: str | None = None,
    ) -> TrendReport:
        """Analyze already-loaded health reports."""

        normalized_reports = tuple(reports)

        samples = self._loader.to_trend_samples(
            normalized_reports
        )

        source_paths = tuple(
            report.source_path
            for report in normalized_reports
            if report.source_path is not None
        )

        analyzer_versions = sorted(
            {
                report.analyzer_version
                for report in normalized_reports
            }
        )

        report_versions = sorted(
            {
                report.report_version
                for report in normalized_reports
            }
        )

        return self.analyze_samples(
            samples,
            run_id=run_id,
            generated_at=generated_at,
            source_metadata={
                "source_paths": list(source_paths),
                "source_health_report_versions": report_versions,
                "source_health_analyzer_versions": analyzer_versions,
            },
        )

    def analyze_files(
        self,
        paths: Sequence[str | Path],
        *,
        run_id: str | None = None,
        generated_at: str | None = None,
    ) -> TrendReport:
        """Load and analyze multiple health report files."""

        reports = self._loader.load_many(paths)

        return self.analyze_loaded_reports(
            reports,
            run_id=run_id,
            generated_at=generated_at,
        )

    def analyze_directory(
        self,
        directory: str | Path,
        *,
        pattern: str = "*.json",
        recursive: bool = False,
        run_id: str | None = None,
        generated_at: str | None = None,
    ) -> TrendReport:
        """Load and analyze a directory of health reports."""

        reports = self._loader.load_directory(
            directory,
            pattern=pattern,
            recursive=recursive,
        )

        return self.analyze_loaded_reports(
            reports,
            run_id=run_id,
            generated_at=generated_at,
        )


__all__ = [
    "DEFAULT_ANALYZER_VERSION",
    "DEFAULT_REPORT_VERSION",
    "PipelineHealthTrendAnalyzer",
]
