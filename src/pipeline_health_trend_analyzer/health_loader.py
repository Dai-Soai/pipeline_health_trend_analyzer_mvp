"""Load Utility #27 health reports as chronological trend samples."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from pipeline_health_trend_analyzer.contract import TrendSample


REQUIRED_HEALTH_REPORT_FIELDS = (
    "report_version",
    "analyzer_version",
    "run_id",
    "generated_at",
    "status",
    "score",
    "summary",
)


class HealthReportLoadError(Exception):
    """Base exception raised while loading health report artifacts."""


class HealthReportFileNotFoundError(HealthReportLoadError):
    """Raised when a requested health report does not exist."""


class HealthReportJSONError(HealthReportLoadError):
    """Raised when a health report contains malformed JSON."""


class HealthReportValidationError(HealthReportLoadError):
    """Raised when a health report violates the loader contract."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


class DuplicateHealthReportError(HealthReportLoadError):
    """Raised when multiple reports share the same run identifier."""


@dataclass(frozen=True, slots=True)
class LoadedHealthReport:
    """Normalized representation of one Utility #27 health report."""

    report_version: str
    analyzer_version: str
    run_id: str
    generated_at: str
    status: str
    health_score: float
    maximum_score: float
    warning_count: int
    critical_count: int
    total_findings: int
    source_path: str | None = None
    source_metadata: dict[str, Any] = field(default_factory=dict)
    raw_report: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return validation errors for this loaded health report."""

        errors: list[str] = []

        for name, value in {
            "report_version": self.report_version,
            "analyzer_version": self.analyzer_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
        }.items():
            if not isinstance(value, str):
                errors.append(f"{name} must be a string")
            elif not value.strip():
                errors.append(f"{name} must not be empty")

        if isinstance(self.generated_at, str) and self.generated_at.strip():
            try:
                datetime.fromisoformat(
                    self.generated_at.replace("Z", "+00:00")
                )
            except ValueError:
                errors.append(
                    "generated_at must be a valid ISO-8601 datetime"
                )

        for name, value in {
            "health_score": self.health_score,
            "maximum_score": self.maximum_score,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                errors.append(f"{name} must be numeric")

        if isinstance(self.maximum_score, (int, float)) and not isinstance(
            self.maximum_score,
            bool,
        ):
            if self.maximum_score <= 0:
                errors.append(
                    "maximum_score must be greater than zero"
                )

        if (
            isinstance(self.health_score, (int, float))
            and not isinstance(self.health_score, bool)
            and isinstance(self.maximum_score, (int, float))
            and not isinstance(self.maximum_score, bool)
            and self.maximum_score > 0
        ):
            if self.health_score < 0:
                errors.append("health_score must not be negative")

            if self.health_score > self.maximum_score:
                errors.append(
                    "health_score must not exceed maximum_score"
                )

        count_fields = {
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "total_findings": self.total_findings,
        }

        for name, value in count_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"{name} must be an integer")
            elif value < 0:
                errors.append(f"{name} must not be negative")

        if all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in count_fields.values()
        ):
            if (
                self.warning_count + self.critical_count
                > self.total_findings
            ):
                errors.append(
                    "warning_count + critical_count must not exceed "
                    "total_findings"
                )

        if self.source_path is not None:
            if not isinstance(self.source_path, str):
                errors.append(
                    "source_path must be a string or null"
                )
            elif not self.source_path.strip():
                errors.append("source_path must not be empty")

        if not isinstance(self.source_metadata, dict):
            errors.append(
                "source_metadata must be a dictionary"
            )

        if not isinstance(self.raw_report, dict):
            errors.append("raw_report must be a dictionary")

        return errors

    @property
    def normalized_score(self) -> float:
        """Return the health score normalized to a 0–100 scale."""

        if self.maximum_score <= 0:
            return 0.0

        return round(
            (self.health_score / self.maximum_score) * 100.0,
            6,
        )

    def to_trend_sample(self) -> TrendSample:
        """Convert this loaded report into a TrendSample."""

        metadata: dict[str, Any] = {
            "health_report_version": self.report_version,
            "health_analyzer_version": self.analyzer_version,
            "maximum_score": self.maximum_score,
        }

        metadata.update(self.source_metadata)

        sample = TrendSample(
            run_id=self.run_id,
            generated_at=self.generated_at,
            status=self.status,
            health_score=self.normalized_score,
            warning_count=self.warning_count,
            critical_count=self.critical_count,
            total_findings=self.total_findings,
            source_path=self.source_path,
            metadata=metadata,
        )

        errors = sample.validate()

        if errors:
            raise HealthReportValidationError(errors)

        return sample


class HealthReportLoader:
    """Load and normalize Utility #27 health report artifacts."""

    def load(self, path: str | Path) -> LoadedHealthReport:
        """Load one JSON health report file."""

        report_path = Path(path).expanduser()

        if not report_path.exists():
            raise HealthReportFileNotFoundError(
                f"Health report not found: {report_path}"
            )

        if not report_path.is_file():
            raise HealthReportLoadError(
                f"Health report path is not a file: {report_path}"
            )

        try:
            raw_data = json.loads(
                report_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise HealthReportJSONError(
                f"Invalid JSON in health report {report_path}: "
                f"{exc.msg} at line {exc.lineno}, "
                f"column {exc.colno}"
            ) from exc
        except OSError as exc:
            raise HealthReportLoadError(
                f"Unable to read health report {report_path}: {exc}"
            ) from exc

        return self.from_dict(
            raw_data,
            source_path=str(report_path.resolve()),
        )

    def from_dict(
        self,
        data: Mapping[str, Any],
        *,
        source_path: str | None = None,
    ) -> LoadedHealthReport:
        """Normalize one health report dictionary."""

        if not isinstance(data, Mapping):
            raise HealthReportValidationError(
                ["health report root must be a JSON object"]
            )

        raw_report = dict(data)
        errors: list[str] = []

        for field_name in REQUIRED_HEALTH_REPORT_FIELDS:
            if field_name not in raw_report:
                errors.append(
                    f"missing required field: {field_name}"
                )

        for field_name in (
            "report_version",
            "analyzer_version",
            "run_id",
            "generated_at",
            "status",
        ):
            if field_name not in raw_report:
                continue

            value = raw_report[field_name]

            if not isinstance(value, str):
                errors.append(
                    f"{field_name} must be a string"
                )
            elif not value.strip():
                errors.append(
                    f"{field_name} must not be empty"
                )

        generated_at = raw_report.get("generated_at")

        if isinstance(generated_at, str) and generated_at.strip():
            try:
                datetime.fromisoformat(
                    generated_at.replace("Z", "+00:00")
                )
            except ValueError:
                errors.append(
                    "generated_at must be a valid ISO-8601 datetime"
                )

        score_data = raw_report.get("score")

        if score_data is not None and not isinstance(score_data, Mapping):
            errors.append("score must be a JSON object")

        summary_data = raw_report.get("summary")

        if (
            summary_data is not None
            and not isinstance(summary_data, Mapping)
        ):
            errors.append("summary must be a JSON object")

        if isinstance(score_data, Mapping):
            for field_name in ("value", "maximum"):
                if field_name not in score_data:
                    errors.append(
                        f"score missing required field: {field_name}"
                    )
                    continue

                value = score_data[field_name]

                if isinstance(value, bool) or not isinstance(
                    value,
                    (int, float),
                ):
                    errors.append(
                        f"score.{field_name} must be numeric"
                    )

        if isinstance(summary_data, Mapping):
            for field_name in (
                "warning_count",
                "critical_count",
                "total_findings",
            ):
                if field_name not in summary_data:
                    errors.append(
                        f"summary missing required field: {field_name}"
                    )
                    continue

                value = summary_data[field_name]

                if isinstance(value, bool) or not isinstance(value, int):
                    errors.append(
                        f"summary.{field_name} must be an integer"
                    )

        if source_path is not None:
            if not isinstance(source_path, str):
                errors.append(
                    "source_path must be a string or null"
                )
            elif not source_path.strip():
                errors.append("source_path must not be empty")

        if errors:
            raise HealthReportValidationError(errors)

        assert isinstance(score_data, Mapping)
        assert isinstance(summary_data, Mapping)

        source_metadata = raw_report.get(
            "source_metadata",
            {},
        )

        if not isinstance(source_metadata, Mapping):
            raise HealthReportValidationError(
                ["source_metadata must be a JSON object"]
            )

        report = LoadedHealthReport(
            report_version=raw_report["report_version"],
            analyzer_version=raw_report["analyzer_version"],
            run_id=raw_report["run_id"],
            generated_at=raw_report["generated_at"],
            status=raw_report["status"],
            health_score=float(score_data["value"]),
            maximum_score=float(score_data["maximum"]),
            warning_count=summary_data["warning_count"],
            critical_count=summary_data["critical_count"],
            total_findings=summary_data["total_findings"],
            source_path=source_path,
            source_metadata=dict(source_metadata),
            raw_report=raw_report,
        )

        validation_errors = report.validate()

        if validation_errors:
            raise HealthReportValidationError(
                validation_errors
            )

        return report

    def load_many(
        self,
        paths: Sequence[str | Path],
    ) -> tuple[LoadedHealthReport, ...]:
        """Load and chronologically order multiple reports."""

        reports = tuple(
            self.load(path)
            for path in paths
        )

        return self._normalize_collection(reports)

    def load_directory(
        self,
        directory: str | Path,
        *,
        pattern: str = "*.json",
        recursive: bool = False,
    ) -> tuple[LoadedHealthReport, ...]:
        """Load health reports from a directory."""

        directory_path = Path(directory).expanduser()

        if not directory_path.exists():
            raise HealthReportFileNotFoundError(
                f"Health report directory not found: "
                f"{directory_path}"
            )

        if not directory_path.is_dir():
            raise HealthReportLoadError(
                f"Health report path is not a directory: "
                f"{directory_path}"
            )

        candidates = (
            directory_path.rglob(pattern)
            if recursive
            else directory_path.glob(pattern)
        )

        paths = sorted(
            path
            for path in candidates
            if path.is_file()
        )

        if not paths:
            raise HealthReportFileNotFoundError(
                f"No health reports matched '{pattern}' in "
                f"{directory_path}"
            )

        return self.load_many(paths)

    def to_trend_samples(
        self,
        reports: Sequence[LoadedHealthReport],
    ) -> tuple[TrendSample, ...]:
        """Convert loaded reports into chronological trend samples."""

        normalized_reports = self._normalize_collection(
            tuple(reports)
        )

        return tuple(
            report.to_trend_sample()
            for report in normalized_reports
        )

    def _normalize_collection(
        self,
        reports: tuple[LoadedHealthReport, ...],
    ) -> tuple[LoadedHealthReport, ...]:
        """Validate uniqueness and sort reports chronologically."""

        seen_run_ids: set[str] = set()

        for report in reports:
            if not isinstance(report, LoadedHealthReport):
                raise TypeError(
                    "reports must contain LoadedHealthReport objects"
                )

            if report.run_id in seen_run_ids:
                raise DuplicateHealthReportError(
                    "Duplicate health report run_id: "
                    f"{report.run_id}"
                )

            seen_run_ids.add(report.run_id)

        return tuple(
            sorted(
                reports,
                key=lambda report: datetime.fromisoformat(
                    report.generated_at.replace("Z", "+00:00")
                ),
            )
        )


__all__ = [
    "DuplicateHealthReportError",
    "HealthReportFileNotFoundError",
    "HealthReportJSONError",
    "HealthReportLoadError",
    "HealthReportLoader",
    "HealthReportValidationError",
    "LoadedHealthReport",
    "REQUIRED_HEALTH_REPORT_FIELDS",
]
