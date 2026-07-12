"""Statistical trend engine for historical pipeline health samples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from pipeline_health_trend_analyzer.contract import (
    MetricTrend,
    TrendDirection,
    TrendSample,
)


MetricExtractor = Callable[[TrendSample], float | int]


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """Configuration describing how one metric should be analyzed."""

    metric_name: str
    extractor: MetricExtractor
    higher_is_better: bool
    stability_tolerance: float = 0.0

    def validate(self) -> list[str]:
        """Return validation errors for this metric definition."""

        errors: list[str] = []

        if not isinstance(self.metric_name, str):
            errors.append(
                "metric_definition.metric_name must be a string"
            )
        elif not self.metric_name.strip():
            errors.append(
                "metric_definition.metric_name must not be empty"
            )

        if not callable(self.extractor):
            errors.append(
                "metric_definition.extractor must be callable"
            )

        if not isinstance(self.higher_is_better, bool):
            errors.append(
                "metric_definition.higher_is_better "
                "must be a boolean"
            )

        if (
            isinstance(self.stability_tolerance, bool)
            or not isinstance(
                self.stability_tolerance,
                (int, float),
            )
        ):
            errors.append(
                "metric_definition.stability_tolerance "
                "must be numeric"
            )
        elif self.stability_tolerance < 0:
            errors.append(
                "metric_definition.stability_tolerance "
                "must not be negative"
            )

        return errors


DEFAULT_METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        metric_name="health_score",
        extractor=lambda sample: sample.health_score,
        higher_is_better=True,
        stability_tolerance=0.5,
    ),
    MetricDefinition(
        metric_name="warning_count",
        extractor=lambda sample: sample.warning_count,
        higher_is_better=False,
        stability_tolerance=0.0,
    ),
    MetricDefinition(
        metric_name="critical_count",
        extractor=lambda sample: sample.critical_count,
        higher_is_better=False,
        stability_tolerance=0.0,
    ),
    MetricDefinition(
        metric_name="total_findings",
        extractor=lambda sample: sample.total_findings,
        higher_is_better=False,
        stability_tolerance=0.0,
    ),
)


def calculate_linear_slope(
    values: Sequence[float | int],
) -> float:
    """Calculate least-squares slope using sample positions as x values."""

    normalized_values = tuple(float(value) for value in values)
    sample_count = len(normalized_values)

    if sample_count < 2:
        return 0.0

    x_values = tuple(float(index) for index in range(sample_count))

    mean_x = sum(x_values) / sample_count
    mean_y = sum(normalized_values) / sample_count

    numerator = sum(
        (x_value - mean_x) * (y_value - mean_y)
        for x_value, y_value in zip(
            x_values,
            normalized_values,
            strict=True,
        )
    )

    denominator = sum(
        (x_value - mean_x) ** 2
        for x_value in x_values
    )

    if denominator == 0:
        return 0.0

    return round(numerator / denominator, 6)


class TrendEngine:
    """Calculate statistical trends from chronological health samples."""

    def __init__(
        self,
        metric_definitions: tuple[
            MetricDefinition,
            ...,
        ] = DEFAULT_METRIC_DEFINITIONS,
    ) -> None:
        if not isinstance(metric_definitions, tuple):
            raise TypeError(
                "metric_definitions must be a tuple"
            )

        if not metric_definitions:
            raise ValueError(
                "metric_definitions must not be empty"
            )

        errors: list[str] = []
        metric_names: set[str] = set()

        for index, definition in enumerate(metric_definitions):
            if not isinstance(definition, MetricDefinition):
                errors.append(
                    f"metric_definitions[{index}] "
                    "must be a MetricDefinition"
                )
                continue

            for error in definition.validate():
                errors.append(
                    f"metric_definitions[{index}].{error}"
                )

            if definition.metric_name in metric_names:
                errors.append(
                    "metric_definitions must not contain "
                    "duplicate metric names"
                )

            metric_names.add(definition.metric_name)

        if errors:
            raise ValueError("; ".join(errors))

        self._metric_definitions = metric_definitions

    @property
    def metric_definitions(
        self,
    ) -> tuple[MetricDefinition, ...]:
        """Return configured metric definitions."""

        return self._metric_definitions

    def analyze_metric(
        self,
        samples: Sequence[TrendSample],
        definition: MetricDefinition,
    ) -> MetricTrend:
        """Calculate one metric trend across chronological samples."""

        normalized_samples = self._normalize_samples(samples)

        if not isinstance(definition, MetricDefinition):
            raise TypeError(
                "definition must be a MetricDefinition"
            )

        definition_errors = definition.validate()

        if definition_errors:
            raise ValueError("; ".join(definition_errors))

        values = tuple(
            self._extract_numeric_value(
                definition,
                sample,
                index,
            )
            for index, sample in enumerate(normalized_samples)
        )

        first_value = values[0]
        current_value = values[-1]
        average_value = sum(values) / len(values)
        minimum_value = min(values)
        maximum_value = max(values)
        delta = current_value - first_value
        slope = calculate_linear_slope(values)

        direction = self.classify_direction(
            sample_count=len(values),
            delta=delta,
            slope=slope,
            higher_is_better=definition.higher_is_better,
            stability_tolerance=definition.stability_tolerance,
        )

        trend = MetricTrend(
            metric_name=definition.metric_name,
            sample_count=len(values),
            first_value=round(first_value, 6),
            current_value=round(current_value, 6),
            average_value=round(average_value, 6),
            minimum_value=round(minimum_value, 6),
            maximum_value=round(maximum_value, 6),
            delta=round(delta, 6),
            slope=round(slope, 6),
            direction=direction,
        )

        errors = trend.validate()

        if errors:
            raise ValueError("; ".join(errors))

        return trend

    def analyze(
        self,
        samples: Sequence[TrendSample],
    ) -> tuple[MetricTrend, ...]:
        """Calculate all configured metric trends."""

        normalized_samples = self._normalize_samples(samples)

        return tuple(
            self.analyze_metric(
                normalized_samples,
                definition,
            )
            for definition in self._metric_definitions
        )

    def classify_direction(
        self,
        *,
        sample_count: int,
        delta: float,
        slope: float,
        higher_is_better: bool,
        stability_tolerance: float,
    ) -> TrendDirection:
        """Classify a statistical metric direction."""

        if isinstance(sample_count, bool) or not isinstance(
            sample_count,
            int,
        ):
            raise TypeError("sample_count must be an integer")

        if sample_count <= 0:
            raise ValueError(
                "sample_count must be greater than zero"
            )

        for name, value in {
            "delta": delta,
            "slope": slope,
            "stability_tolerance": stability_tolerance,
        }.items():
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(f"{name} must be numeric")

        if stability_tolerance < 0:
            raise ValueError(
                "stability_tolerance must not be negative"
            )

        if not isinstance(higher_is_better, bool):
            raise TypeError(
                "higher_is_better must be a boolean"
            )

        if sample_count < 2:
            return TrendDirection.INSUFFICIENT_DATA

        if (
            abs(float(delta)) <= stability_tolerance
            and abs(float(slope)) <= stability_tolerance
        ):
            return TrendDirection.STABLE

        signal = float(slope)

        if abs(signal) <= stability_tolerance:
            signal = float(delta)

        if abs(signal) <= stability_tolerance:
            return TrendDirection.STABLE

        is_increasing = signal > 0

        if higher_is_better:
            return (
                TrendDirection.IMPROVING
                if is_increasing
                else TrendDirection.DEGRADING
            )

        return (
            TrendDirection.DEGRADING
            if is_increasing
            else TrendDirection.IMPROVING
        )

    def _normalize_samples(
        self,
        samples: Sequence[TrendSample],
    ) -> tuple[TrendSample, ...]:
        """Validate a non-empty chronological sample sequence."""

        normalized_samples = tuple(samples)

        if not normalized_samples:
            raise ValueError("samples must not be empty")

        previous_generated_at: str | None = None

        for index, sample in enumerate(normalized_samples):
            if not isinstance(sample, TrendSample):
                raise TypeError(
                    f"samples[{index}] must be a TrendSample"
                )

            errors = sample.validate()

            if errors:
                raise ValueError(
                    "; ".join(
                        f"samples[{index}].{error}"
                        for error in errors
                    )
                )

            if (
                previous_generated_at is not None
                and sample.generated_at < previous_generated_at
            ):
                raise ValueError(
                    "samples must be ordered chronologically"
                )

            previous_generated_at = sample.generated_at

        return normalized_samples

    def _extract_numeric_value(
        self,
        definition: MetricDefinition,
        sample: TrendSample,
        index: int,
    ) -> float:
        """Extract and normalize one configured metric value."""

        value = definition.extractor(sample)

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise TypeError(
                f"metric '{definition.metric_name}' returned "
                f"a non-numeric value for samples[{index}]"
            )

        return float(value)


__all__ = [
    "DEFAULT_METRIC_DEFINITIONS",
    "MetricDefinition",
    "TrendEngine",
    "calculate_linear_slope",
]
