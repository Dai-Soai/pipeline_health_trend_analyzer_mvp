"""JSON trend report serialization, validation, and inspection."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline_health_trend_analyzer.contract import TrendReport


class TrendReportIOError(Exception):
    """Base exception raised for trend report artifact errors."""


class TrendReportFileNotFoundError(TrendReportIOError):
    """Raised when a trend report file does not exist."""


class TrendReportJSONError(TrendReportIOError):
    """Raised when a trend report contains malformed JSON."""


class TrendReportContractError(TrendReportIOError):
    """Raised when a trend report violates the report contract."""

    def __init__(
        self,
        errors: list[str] | tuple[str, ...],
    ) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True, slots=True)
class TrendReportInspection:
    """Concise inspection result for a trend report artifact."""

    report_version: str
    analyzer_version: str
    run_id: str
    generated_at: str
    status: str
    overall_direction: str
    sample_count: int
    metric_count: int
    improving_count: int
    stable_count: int
    degrading_count: int
    insufficient_data_count: int
    headline: str | None
    dominant_direction: str | None
    highlighted_metrics: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this inspection result."""

        return {
            "report_version": self.report_version,
            "analyzer_version": self.analyzer_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "overall_direction": self.overall_direction,
            "sample_count": self.sample_count,
            "metric_count": self.metric_count,
            "improving_count": self.improving_count,
            "stable_count": self.stable_count,
            "degrading_count": self.degrading_count,
            "insufficient_data_count": (
                self.insufficient_data_count
            ),
            "headline": self.headline,
            "dominant_direction": self.dominant_direction,
            "highlighted_metrics": list(
                self.highlighted_metrics
            ),
        }


class TrendReportSerializer:
    """Serialize and deserialize JSON trend report artifacts."""

    def dumps(
        self,
        report: TrendReport,
        *,
        indent: int = 2,
    ) -> str:
        """Serialize a TrendReport to JSON text."""

        self._validate_report(report)

        return json.dumps(
            report.to_dict(),
            indent=indent,
            sort_keys=True,
            ensure_ascii=False,
        )

    def loads(self, content: str) -> TrendReport:
        """Deserialize a TrendReport from JSON text."""

        if not isinstance(content, str):
            raise TypeError("content must be a string")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise TrendReportJSONError(
                "Invalid trend report JSON: "
                f"{exc.msg} at line {exc.lineno}, "
                f"column {exc.colno}"
            ) from exc

        return self.from_dict(data)

    def from_dict(
        self,
        data: Mapping[str, Any],
    ) -> TrendReport:
        """Deserialize a TrendReport from a dictionary."""

        if not isinstance(data, Mapping):
            raise TrendReportContractError(
                ["trend report root must be a JSON object"]
            )

        try:
            report = TrendReport.from_dict(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise TrendReportContractError(
                [
                    "unable to deserialize trend report: "
                    f"{exc}"
                ]
            ) from exc

        self._validate_report(report)

        return report

    def _validate_report(
        self,
        report: TrendReport,
    ) -> None:
        """Validate a TrendReport before use."""

        if not isinstance(report, TrendReport):
            raise TypeError("report must be a TrendReport")

        errors = report.validate()

        if errors:
            raise TrendReportContractError(errors)


class TrendReportStore:
    """Read and write TrendReport JSON artifacts."""

    def __init__(
        self,
        serializer: TrendReportSerializer | None = None,
    ) -> None:
        self._serializer = (
            serializer or TrendReportSerializer()
        )

    def write(
        self,
        report: TrendReport,
        path: str | Path,
    ) -> Path:
        """Atomically write a trend report JSON artifact."""

        output_path = Path(path).expanduser()
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = self._serializer.dumps(report) + "\n"

        temporary_path = output_path.with_name(
            f".{output_path.name}.tmp"
        )

        try:
            temporary_path.write_text(
                content,
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                output_path,
            )
        except OSError as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

            raise TrendReportIOError(
                "Unable to write trend report "
                f"{output_path}: {exc}"
            ) from exc

        return output_path.resolve()

    def read(
        self,
        path: str | Path,
    ) -> TrendReport:
        """Read and validate a trend report JSON artifact."""

        report_path = Path(path).expanduser()

        if not report_path.exists():
            raise TrendReportFileNotFoundError(
                f"Trend report not found: {report_path}"
            )

        if not report_path.is_file():
            raise TrendReportIOError(
                "Trend report path is not a file: "
                f"{report_path}"
            )

        try:
            content = report_path.read_text(
                encoding="utf-8",
            )
        except OSError as exc:
            raise TrendReportIOError(
                "Unable to read trend report "
                f"{report_path}: {exc}"
            ) from exc

        return self._serializer.loads(content)

    def validate_file(
        self,
        path: str | Path,
    ) -> tuple[str, ...]:
        """Return validation errors for a trend report file."""

        try:
            self.read(path)
        except TrendReportContractError as exc:
            return exc.errors
        except TrendReportIOError as exc:
            return (str(exc),)

        return ()

    def inspect(
        self,
        path: str | Path,
    ) -> TrendReportInspection:
        """Inspect a trend report artifact."""

        report = self.read(path)

        headline: str | None = None
        dominant_direction: str | None = None
        highlighted_metrics: tuple[str, ...] = ()

        if report.overview is not None:
            headline = report.overview.headline
            dominant_direction = (
                report.overview.dominant_direction.value
            )
            highlighted_metrics = (
                report.overview.highlighted_metrics
            )

        return TrendReportInspection(
            report_version=report.report_version,
            analyzer_version=report.analyzer_version,
            run_id=report.run_id,
            generated_at=report.generated_at,
            status=report.status,
            overall_direction=(
                report.summary.overall_direction.value
            ),
            sample_count=report.summary.sample_count,
            metric_count=report.summary.metric_count,
            improving_count=report.summary.improving_count,
            stable_count=report.summary.stable_count,
            degrading_count=report.summary.degrading_count,
            insufficient_data_count=(
                report.summary.insufficient_data_count
            ),
            headline=headline,
            dominant_direction=dominant_direction,
            highlighted_metrics=highlighted_metrics,
        )


__all__ = [
    "TrendReportContractError",
    "TrendReportFileNotFoundError",
    "TrendReportInspection",
    "TrendReportIOError",
    "TrendReportJSONError",
    "TrendReportSerializer",
    "TrendReportStore",
]
