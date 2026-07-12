"""Core contracts for Pipeline Health Trend Analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence


class TrendDirection(str, Enum):
    """Direction of change observed across historical samples."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class TrendSample:
    """Normalized point-in-time pipeline health sample."""

    run_id: str
    generated_at: str
    status: str
    health_score: float
    warning_count: int
    critical_count: int
    total_findings: int
    source_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return validation errors for this trend sample."""

        errors: list[str] = []

        for name, value in {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
        }.items():
            if not isinstance(value, str):
                errors.append(f"trend_sample.{name} must be a string")
            elif not value.strip():
                errors.append(
                    f"trend_sample.{name} must not be empty"
                )

        if isinstance(self.generated_at, str) and self.generated_at.strip():
            try:
                datetime.fromisoformat(
                    self.generated_at.replace("Z", "+00:00")
                )
            except ValueError:
                errors.append(
                    "trend_sample.generated_at must be a valid "
                    "ISO-8601 datetime"
                )

        if (
            isinstance(self.health_score, bool)
            or not isinstance(self.health_score, (int, float))
        ):
            errors.append(
                "trend_sample.health_score must be numeric"
            )
        else:
            if self.health_score < 0:
                errors.append(
                    "trend_sample.health_score must not be negative"
                )

            if self.health_score > 100:
                errors.append(
                    "trend_sample.health_score must not exceed 100"
                )

        count_fields = {
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "total_findings": self.total_findings,
        }

        for name, value in count_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(
                    f"trend_sample.{name} must be an integer"
                )
            elif value < 0:
                errors.append(
                    f"trend_sample.{name} must not be negative"
                )

        if all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in count_fields.values()
        ):
            if (
                self.warning_count + self.critical_count
                > self.total_findings
            ):
                errors.append(
                    "trend_sample.warning_count + critical_count "
                    "must not exceed total_findings"
                )

        if self.source_path is not None:
            if not isinstance(self.source_path, str):
                errors.append(
                    "trend_sample.source_path must be a string or null"
                )
            elif not self.source_path.strip():
                errors.append(
                    "trend_sample.source_path must not be empty"
                )

        if not isinstance(self.metadata, dict):
            errors.append(
                "trend_sample.metadata must be a dictionary"
            )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize this sample to a JSON-compatible dictionary."""

        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "health_score": float(self.health_score),
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "total_findings": self.total_findings,
            "source_path": self.source_path,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> TrendSample:
        """Deserialize a trend sample."""

        return cls(
            run_id=data["run_id"],
            generated_at=data["generated_at"],
            status=data["status"],
            health_score=float(data["health_score"]),
            warning_count=data["warning_count"],
            critical_count=data["critical_count"],
            total_findings=data["total_findings"],
            source_path=data.get("source_path"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class MetricTrend:
    """Statistical trend assessment for one numeric metric."""

    metric_name: str
    sample_count: int
    first_value: float
    current_value: float
    average_value: float
    minimum_value: float
    maximum_value: float
    delta: float
    slope: float
    direction: TrendDirection

    def validate(self) -> list[str]:
        """Return validation errors for this metric trend."""

        errors: list[str] = []

        if not isinstance(self.metric_name, str):
            errors.append(
                "metric_trend.metric_name must be a string"
            )
        elif not self.metric_name.strip():
            errors.append(
                "metric_trend.metric_name must not be empty"
            )

        if (
            isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
        ):
            errors.append(
                "metric_trend.sample_count must be an integer"
            )
        elif self.sample_count <= 0:
            errors.append(
                "metric_trend.sample_count must be greater than zero"
            )

        numeric_fields = {
            "first_value": self.first_value,
            "current_value": self.current_value,
            "average_value": self.average_value,
            "minimum_value": self.minimum_value,
            "maximum_value": self.maximum_value,
            "delta": self.delta,
            "slope": self.slope,
        }

        for name, value in numeric_fields.items():
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                errors.append(
                    f"metric_trend.{name} must be numeric"
                )

        if all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            for value in numeric_fields.values()
        ):
            if self.minimum_value > self.maximum_value:
                errors.append(
                    "metric_trend.minimum_value must not exceed "
                    "maximum_value"
                )

            if not (
                self.minimum_value
                <= self.first_value
                <= self.maximum_value
            ):
                errors.append(
                    "metric_trend.first_value must be within "
                    "minimum_value and maximum_value"
                )

            if not (
                self.minimum_value
                <= self.current_value
                <= self.maximum_value
            ):
                errors.append(
                    "metric_trend.current_value must be within "
                    "minimum_value and maximum_value"
                )

            if not (
                self.minimum_value
                <= self.average_value
                <= self.maximum_value
            ):
                errors.append(
                    "metric_trend.average_value must be within "
                    "minimum_value and maximum_value"
                )

            expected_delta = round(
                self.current_value - self.first_value,
                6,
            )

            if round(float(self.delta), 6) != expected_delta:
                errors.append(
                    "metric_trend.delta must equal "
                    "current_value - first_value"
                )

        if not isinstance(self.direction, TrendDirection):
            errors.append(
                "metric_trend.direction must be a TrendDirection"
            )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize this metric trend."""

        return {
            "metric_name": self.metric_name,
            "sample_count": self.sample_count,
            "first_value": float(self.first_value),
            "current_value": float(self.current_value),
            "average_value": float(self.average_value),
            "minimum_value": float(self.minimum_value),
            "maximum_value": float(self.maximum_value),
            "delta": float(self.delta),
            "slope": float(self.slope),
            "direction": self.direction.value,
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> MetricTrend:
        """Deserialize a metric trend."""

        return cls(
            metric_name=data["metric_name"],
            sample_count=data["sample_count"],
            first_value=float(data["first_value"]),
            current_value=float(data["current_value"]),
            average_value=float(data["average_value"]),
            minimum_value=float(data["minimum_value"]),
            maximum_value=float(data["maximum_value"]),
            delta=float(data["delta"]),
            slope=float(data["slope"]),
            direction=TrendDirection(data["direction"]),
        )


@dataclass(frozen=True, slots=True)
class TrendSummary:
    """Aggregate summary of all generated metric trends."""

    sample_count: int
    metric_count: int
    improving_count: int
    stable_count: int
    degrading_count: int
    insufficient_data_count: int
    overall_direction: TrendDirection

    def validate(self) -> list[str]:
        """Return validation errors for this trend summary."""

        errors: list[str] = []

        count_fields = {
            "sample_count": self.sample_count,
            "metric_count": self.metric_count,
            "improving_count": self.improving_count,
            "stable_count": self.stable_count,
            "degrading_count": self.degrading_count,
            "insufficient_data_count": (
                self.insufficient_data_count
            ),
        }

        for name, value in count_fields.items():
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(
                    f"trend_summary.{name} must be an integer"
                )
            elif value < 0:
                errors.append(
                    f"trend_summary.{name} must not be negative"
                )

        if isinstance(self.sample_count, int) and not isinstance(
            self.sample_count,
            bool,
        ):
            if self.sample_count <= 0:
                errors.append(
                    "trend_summary.sample_count must be "
                    "greater than zero"
                )

        if all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in count_fields.values()
        ):
            calculated_metric_count = (
                self.improving_count
                + self.stable_count
                + self.degrading_count
                + self.insufficient_data_count
            )

            if self.metric_count != calculated_metric_count:
                errors.append(
                    "trend_summary.metric_count must equal the sum "
                    "of all direction counts"
                )

        if not isinstance(
            self.overall_direction,
            TrendDirection,
        ):
            errors.append(
                "trend_summary.overall_direction must be "
                "a TrendDirection"
            )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize this trend summary."""

        return {
            "sample_count": self.sample_count,
            "metric_count": self.metric_count,
            "improving_count": self.improving_count,
            "stable_count": self.stable_count,
            "degrading_count": self.degrading_count,
            "insufficient_data_count": (
                self.insufficient_data_count
            ),
            "overall_direction": self.overall_direction.value,
        }

    @classmethod
    def from_metric_trends(
        cls,
        *,
        sample_count: int,
        metric_trends: Sequence[MetricTrend],
        overall_direction: TrendDirection,
    ) -> TrendSummary:
        """Build a summary from metric trends."""

        normalized_trends = tuple(metric_trends)

        return cls(
            sample_count=sample_count,
            metric_count=len(normalized_trends),
            improving_count=sum(
                trend.direction is TrendDirection.IMPROVING
                for trend in normalized_trends
            ),
            stable_count=sum(
                trend.direction is TrendDirection.STABLE
                for trend in normalized_trends
            ),
            degrading_count=sum(
                trend.direction is TrendDirection.DEGRADING
                for trend in normalized_trends
            ),
            insufficient_data_count=sum(
                trend.direction
                is TrendDirection.INSUFFICIENT_DATA
                for trend in normalized_trends
            ),
            overall_direction=overall_direction,
        )

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> TrendSummary:
        """Deserialize a trend summary."""

        return cls(
            sample_count=data["sample_count"],
            metric_count=data["metric_count"],
            improving_count=data["improving_count"],
            stable_count=data["stable_count"],
            degrading_count=data["degrading_count"],
            insufficient_data_count=(
                data["insufficient_data_count"]
            ),
            overall_direction=TrendDirection(
                data["overall_direction"]
            ),
        )


@dataclass(frozen=True, slots=True)
class TrendReport:
    """Complete pipeline health trend report."""

    report_version: str
    analyzer_version: str
    run_id: str
    generated_at: str
    status: str
    summary: TrendSummary
    samples: tuple[TrendSample, ...]
    metric_trends: tuple[MetricTrend, ...]
    source_metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return validation errors for this trend report."""

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

        if not isinstance(self.summary, TrendSummary):
            errors.append(
                "summary must be a TrendSummary"
            )
        else:
            errors.extend(self.summary.validate())

        if not isinstance(self.samples, tuple):
            errors.append("samples must be a tuple")
        else:
            previous_timestamp: datetime | None = None

            for index, sample in enumerate(self.samples):
                if not isinstance(sample, TrendSample):
                    errors.append(
                        f"samples[{index}] must be a TrendSample"
                    )
                    continue

                for error in sample.validate():
                    errors.append(f"samples[{index}].{error}")

                try:
                    current_timestamp = datetime.fromisoformat(
                        sample.generated_at.replace("Z", "+00:00")
                    )
                except (AttributeError, ValueError):
                    continue

                if (
                    previous_timestamp is not None
                    and current_timestamp < previous_timestamp
                ):
                    errors.append(
                        "samples must be ordered chronologically"
                    )

                previous_timestamp = current_timestamp

        if not isinstance(self.metric_trends, tuple):
            errors.append(
                "metric_trends must be a tuple"
            )
        else:
            metric_names: set[str] = set()

            for index, trend in enumerate(self.metric_trends):
                if not isinstance(trend, MetricTrend):
                    errors.append(
                        f"metric_trends[{index}] "
                        "must be a MetricTrend"
                    )
                    continue

                for error in trend.validate():
                    errors.append(
                        f"metric_trends[{index}].{error}"
                    )

                if trend.metric_name in metric_names:
                    errors.append(
                        "metric_trends must not contain duplicate "
                        "metric names"
                    )

                metric_names.add(trend.metric_name)

        if (
            isinstance(self.summary, TrendSummary)
            and isinstance(self.samples, tuple)
            and self.summary.sample_count != len(self.samples)
        ):
            errors.append(
                "summary.sample_count must match samples length"
            )

        if (
            isinstance(self.summary, TrendSummary)
            and isinstance(self.metric_trends, tuple)
            and self.summary.metric_count != len(self.metric_trends)
        ):
            errors.append(
                "summary.metric_count must match metric_trends length"
            )

        if not isinstance(self.source_metadata, dict):
            errors.append(
                "source_metadata must be a dictionary"
            )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize this trend report."""

        return {
            "report_version": self.report_version,
            "analyzer_version": self.analyzer_version,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "status": self.status,
            "summary": self.summary.to_dict(),
            "samples": [
                sample.to_dict()
                for sample in self.samples
            ],
            "metric_trends": [
                trend.to_dict()
                for trend in self.metric_trends
            ],
            "source_metadata": dict(self.source_metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> TrendReport:
        """Deserialize a complete trend report."""

        return cls(
            report_version=data["report_version"],
            analyzer_version=data["analyzer_version"],
            run_id=data["run_id"],
            generated_at=data["generated_at"],
            status=data["status"],
            summary=TrendSummary.from_dict(data["summary"]),
            samples=tuple(
                TrendSample.from_dict(item)
                for item in data.get("samples", [])
            ),
            metric_trends=tuple(
                MetricTrend.from_dict(item)
                for item in data.get("metric_trends", [])
            ),
            source_metadata=dict(
                data.get("source_metadata", {})
            ),
        )


__all__ = [
    "MetricTrend",
    "TrendDirection",
    "TrendReport",
    "TrendSample",
    "TrendSummary",
]
