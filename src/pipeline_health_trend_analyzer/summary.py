"""Human-readable pipeline health trend summary generation."""

from __future__ import annotations

from collections.abc import Sequence

from pipeline_health_trend_analyzer.contract import (
    MetricTrend,
    TrendDirection,
    TrendOverview,
    TrendSummary,
)


class TrendSummaryBuilder:
    """Build human-readable overviews from metric trends."""

    def __init__(
        self,
        *,
        max_highlighted_metrics: int = 4,
    ) -> None:
        if isinstance(
            max_highlighted_metrics,
            bool,
        ) or not isinstance(
            max_highlighted_metrics,
            int,
        ):
            raise TypeError(
                "max_highlighted_metrics must be an integer"
            )

        if max_highlighted_metrics <= 0:
            raise ValueError(
                "max_highlighted_metrics must be "
                "greater than zero"
            )

        self._max_highlighted_metrics = (
            max_highlighted_metrics
        )

    @property
    def max_highlighted_metrics(self) -> int:
        """Return the maximum highlighted metric count."""

        return self._max_highlighted_metrics

    def build(
        self,
        *,
        summary: TrendSummary,
        metric_trends: Sequence[MetricTrend],
    ) -> TrendOverview:
        """Build a high-level trend overview."""

        if not isinstance(summary, TrendSummary):
            raise TypeError(
                "summary must be a TrendSummary"
            )

        summary_errors = summary.validate()

        if summary_errors:
            raise ValueError("; ".join(summary_errors))

        normalized_trends = tuple(metric_trends)

        if len(normalized_trends) != summary.metric_count:
            raise ValueError(
                "metric_trends length must match "
                "summary.metric_count"
            )

        for index, trend in enumerate(normalized_trends):
            if not isinstance(trend, MetricTrend):
                raise TypeError(
                    f"metric_trends[{index}] "
                    "must be a MetricTrend"
                )

            errors = trend.validate()

            if errors:
                raise ValueError(
                    "; ".join(
                        f"metric_trends[{index}].{error}"
                        for error in errors
                    )
                )

        direction = summary.overall_direction

        overview = TrendOverview(
            headline=self._headline(direction),
            message=self._message(summary),
            dominant_direction=direction,
            highlighted_metrics=self._highlighted_metrics(
                normalized_trends,
                direction,
            ),
            recommendation=self._recommendation(direction),
        )

        errors = overview.validate()

        if errors:
            raise ValueError("; ".join(errors))

        return overview

    def _headline(
        self,
        direction: TrendDirection,
    ) -> str:
        """Return a concise trend headline."""

        headlines = {
            TrendDirection.IMPROVING: (
                "Pipeline health is improving"
            ),
            TrendDirection.STABLE: (
                "Pipeline health trend is stable"
            ),
            TrendDirection.DEGRADING: (
                "Pipeline health is degrading"
            ),
            TrendDirection.INSUFFICIENT_DATA: (
                "Insufficient health history"
            ),
        }

        return headlines[direction]

    def _message(
        self,
        summary: TrendSummary,
    ) -> str:
        """Return a human-readable statistical summary."""

        if (
            summary.overall_direction
            is TrendDirection.INSUFFICIENT_DATA
        ):
            return (
                f"Only {summary.sample_count} historical sample is "
                "available. At least two samples are required to "
                "determine pipeline health movement."
            )

        return (
            f"Analyzed {summary.sample_count} historical samples "
            f"across {summary.metric_count} metrics: "
            f"{summary.improving_count} improving, "
            f"{summary.stable_count} stable, "
            f"{summary.degrading_count} degrading, and "
            f"{summary.insufficient_data_count} with insufficient "
            "data."
        )

    def _highlighted_metrics(
        self,
        metric_trends: tuple[MetricTrend, ...],
        direction: TrendDirection,
    ) -> tuple[str, ...]:
        """Select the most relevant metrics for the overview."""

        if direction is TrendDirection.DEGRADING:
            priority = (
                TrendDirection.DEGRADING,
                TrendDirection.STABLE,
                TrendDirection.IMPROVING,
                TrendDirection.INSUFFICIENT_DATA,
            )
        elif direction is TrendDirection.IMPROVING:
            priority = (
                TrendDirection.IMPROVING,
                TrendDirection.STABLE,
                TrendDirection.DEGRADING,
                TrendDirection.INSUFFICIENT_DATA,
            )
        elif direction is TrendDirection.STABLE:
            priority = (
                TrendDirection.DEGRADING,
                TrendDirection.IMPROVING,
                TrendDirection.STABLE,
                TrendDirection.INSUFFICIENT_DATA,
            )
        else:
            priority = (
                TrendDirection.INSUFFICIENT_DATA,
                TrendDirection.DEGRADING,
                TrendDirection.IMPROVING,
                TrendDirection.STABLE,
            )

        highlighted: list[str] = []
        seen: set[str] = set()

        for target_direction in priority:
            candidates = sorted(
                (
                    trend
                    for trend in metric_trends
                    if trend.direction is target_direction
                ),
                key=lambda trend: abs(trend.delta),
                reverse=True,
            )

            for trend in candidates:
                if trend.metric_name in seen:
                    continue

                highlighted.append(trend.metric_name)
                seen.add(trend.metric_name)

                if (
                    len(highlighted)
                    >= self._max_highlighted_metrics
                ):
                    return tuple(highlighted)

        return tuple(highlighted)

    def _recommendation(
        self,
        direction: TrendDirection,
    ) -> str:
        """Return an operational recommendation."""

        recommendations = {
            TrendDirection.IMPROVING: (
                "Continue monitoring the current runtime "
                "configuration and confirm that the improvement "
                "persists across future executions."
            ),
            TrendDirection.STABLE: (
                "Maintain normal monitoring and review individual "
                "metrics for hidden degradation that may be offset "
                "by improvements elsewhere."
            ),
            TrendDirection.DEGRADING: (
                "Investigate degrading metrics promptly, compare "
                "recent runtime changes, and prevent dependent "
                "automation from reaching a critical state."
            ),
            TrendDirection.INSUFFICIENT_DATA: (
                "Collect at least one additional health report "
                "before making an operational trend decision."
            ),
        }

        return recommendations[direction]


__all__ = [
    "TrendSummaryBuilder",
]
