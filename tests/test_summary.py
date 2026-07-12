from pipeline_health_trend_analyzer import (
    MetricTrend,
    PipelineHealthTrendAnalyzer,
    TrendDirection,
    TrendOverview,
    TrendSummary,
    TrendSummaryBuilder,
)


def build_metric_trend(
    metric_name: str,
    direction: TrendDirection,
    *,
    first_value: float = 10.0,
    current_value: float = 20.0,
) -> MetricTrend:
    delta = current_value - first_value

    return MetricTrend(
        metric_name=metric_name,
        sample_count=3,
        first_value=first_value,
        current_value=current_value,
        average_value=(
            first_value + current_value
        ) / 2,
        minimum_value=min(first_value, current_value),
        maximum_value=max(first_value, current_value),
        delta=delta,
        slope=delta / 2,
        direction=direction,
    )


def build_summary(
    metric_trends: tuple[MetricTrend, ...],
    direction: TrendDirection,
    *,
    sample_count: int = 3,
) -> TrendSummary:
    return TrendSummary.from_metric_trends(
        sample_count=sample_count,
        metric_trends=metric_trends,
        overall_direction=direction,
    )


def test_trend_overview_round_trip() -> None:
    overview = TrendOverview(
        headline="Pipeline health is improving",
        message="Historical health metrics improved.",
        dominant_direction=TrendDirection.IMPROVING,
        highlighted_metrics=(
            "health_score",
            "critical_count",
        ),
        recommendation=(
            "Continue monitoring the current configuration."
        ),
    )

    restored = TrendOverview.from_dict(
        overview.to_dict()
    )

    assert restored == overview
    assert restored.validate() == []


def test_trend_overview_rejects_empty_fields() -> None:
    overview = TrendOverview(
        headline="",
        message="",
        dominant_direction=TrendDirection.STABLE,
        highlighted_metrics=(),
        recommendation="",
    )

    errors = overview.validate()

    assert (
        "trend_overview.headline must not be empty"
        in errors
    )
    assert (
        "trend_overview.message must not be empty"
        in errors
    )
    assert (
        "trend_overview.recommendation must not be empty"
        in errors
    )


def test_builder_creates_improving_overview() -> None:
    trends = (
        build_metric_trend(
            "health_score",
            TrendDirection.IMPROVING,
            first_value=50.0,
            current_value=100.0,
        ),
        build_metric_trend(
            "warning_count",
            TrendDirection.IMPROVING,
            first_value=3.0,
            current_value=0.0,
        ),
    )

    overview = TrendSummaryBuilder().build(
        summary=build_summary(
            trends,
            TrendDirection.IMPROVING,
        ),
        metric_trends=trends,
    )

    assert (
        overview.headline
        == "Pipeline health is improving"
    )
    assert (
        overview.dominant_direction
        is TrendDirection.IMPROVING
    )
    assert overview.highlighted_metrics[0] == "health_score"
    assert "persists" in overview.recommendation


def test_builder_creates_degrading_overview() -> None:
    trends = (
        build_metric_trend(
            "critical_count",
            TrendDirection.DEGRADING,
            first_value=0.0,
            current_value=3.0,
        ),
        build_metric_trend(
            "health_score",
            TrendDirection.DEGRADING,
            first_value=100.0,
            current_value=50.0,
        ),
    )

    overview = TrendSummaryBuilder().build(
        summary=build_summary(
            trends,
            TrendDirection.DEGRADING,
        ),
        metric_trends=trends,
    )

    assert (
        overview.headline
        == "Pipeline health is degrading"
    )
    assert (
        overview.dominant_direction
        is TrendDirection.DEGRADING
    )
    assert "Investigate" in overview.recommendation


def test_builder_creates_stable_overview() -> None:
    trends = (
        build_metric_trend(
            "health_score",
            TrendDirection.STABLE,
            first_value=80.0,
            current_value=80.0,
        ),
    )

    overview = TrendSummaryBuilder().build(
        summary=build_summary(
            trends,
            TrendDirection.STABLE,
        ),
        metric_trends=trends,
    )

    assert (
        overview.headline
        == "Pipeline health trend is stable"
    )
    assert (
        overview.dominant_direction
        is TrendDirection.STABLE
    )


def test_builder_creates_insufficient_data_overview() -> None:
    trends = (
        build_metric_trend(
            "health_score",
            TrendDirection.INSUFFICIENT_DATA,
            first_value=80.0,
            current_value=80.0,
        ),
    )

    overview = TrendSummaryBuilder().build(
        summary=build_summary(
            trends,
            TrendDirection.INSUFFICIENT_DATA,
            sample_count=1,
        ),
        metric_trends=trends,
    )

    assert (
        overview.headline
        == "Insufficient health history"
    )
    assert "At least two samples" in overview.message
    assert (
        overview.dominant_direction
        is TrendDirection.INSUFFICIENT_DATA
    )


def test_builder_limits_highlighted_metrics() -> None:
    trends = tuple(
        build_metric_trend(
            f"metric_{index}",
            TrendDirection.IMPROVING,
            first_value=0.0,
            current_value=float(index + 1),
        )
        for index in range(5)
    )

    overview = TrendSummaryBuilder(
        max_highlighted_metrics=2
    ).build(
        summary=build_summary(
            trends,
            TrendDirection.IMPROVING,
        ),
        metric_trends=trends,
    )

    assert len(overview.highlighted_metrics) == 2
    assert overview.highlighted_metrics == (
        "metric_4",
        "metric_3",
    )


def test_analyzer_adds_overview_to_report() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            "examples/health_reports",
            run_id="m6-overview-test",
            generated_at="2026-07-12T11:00:00Z",
        )
    )

    assert report.overview is not None
    assert report.overview.validate() == []
    assert (
        report.overview.headline
        == "Pipeline health is improving"
    )
    assert (
        report.overview.dominant_direction
        is TrendDirection.IMPROVING
    )
    assert len(report.overview.highlighted_metrics) == 4


def test_trend_report_round_trip_preserves_overview() -> None:
    from pipeline_health_trend_analyzer import TrendReport

    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            "examples/health_reports",
            run_id="m6-round-trip-test",
            generated_at="2026-07-12T11:00:00Z",
        )
    )

    restored = TrendReport.from_dict(
        report.to_dict()
    )

    assert restored == report
    assert restored.overview == report.overview
    assert restored.validate() == []
