import pytest

from pipeline_health_trend_analyzer import (
    MetricDefinition,
    TrendDirection,
    TrendEngine,
    TrendSample,
    calculate_linear_slope,
)


def sample(
    *,
    run_id: str,
    generated_at: str,
    health_score: float,
    warning_count: int,
    critical_count: int,
    total_findings: int,
) -> TrendSample:
    return TrendSample(
        run_id=run_id,
        generated_at=generated_at,
        status="warning",
        health_score=health_score,
        warning_count=warning_count,
        critical_count=critical_count,
        total_findings=total_findings,
    )


def improving_samples() -> tuple[TrendSample, ...]:
    return (
        sample(
            run_id="run-001",
            generated_at="2026-07-09T10:00:00Z",
            health_score=50.0,
            warning_count=3,
            critical_count=2,
            total_findings=5,
        ),
        sample(
            run_id="run-002",
            generated_at="2026-07-10T10:00:00Z",
            health_score=70.0,
            warning_count=3,
            critical_count=0,
            total_findings=3,
        ),
        sample(
            run_id="run-003",
            generated_at="2026-07-11T10:00:00Z",
            health_score=100.0,
            warning_count=0,
            critical_count=0,
            total_findings=0,
        ),
    )


def test_calculate_linear_slope_for_increasing_values() -> None:
    assert calculate_linear_slope((10, 20, 30)) == 10.0


def test_calculate_linear_slope_for_decreasing_values() -> None:
    assert calculate_linear_slope((6, 4, 2)) == -2.0


def test_calculate_linear_slope_for_one_value() -> None:
    assert calculate_linear_slope((10,)) == 0.0


def test_metric_definition_validation() -> None:
    definition = MetricDefinition(
        metric_name="health_score",
        extractor=lambda item: item.health_score,
        higher_is_better=True,
        stability_tolerance=0.5,
    )

    assert definition.validate() == []


def test_metric_definition_rejects_negative_tolerance() -> None:
    definition = MetricDefinition(
        metric_name="health_score",
        extractor=lambda item: item.health_score,
        higher_is_better=True,
        stability_tolerance=-1.0,
    )

    assert (
        "metric_definition.stability_tolerance "
        "must not be negative"
        in definition.validate()
    )


def test_engine_analyzes_health_score() -> None:
    engine = TrendEngine()

    trend = engine.analyze_metric(
        improving_samples(),
        engine.metric_definitions[0],
    )

    assert trend.metric_name == "health_score"
    assert trend.sample_count == 3
    assert trend.first_value == 50.0
    assert trend.current_value == 100.0
    assert trend.average_value == pytest.approx(73.333333)
    assert trend.minimum_value == 50.0
    assert trend.maximum_value == 100.0
    assert trend.delta == 50.0
    assert trend.slope == 25.0
    assert trend.direction is TrendDirection.IMPROVING
    assert trend.validate() == []


def test_engine_treats_decreasing_warning_count_as_improving() -> None:
    trends = TrendEngine().analyze(improving_samples())

    warning_trend = next(
        trend
        for trend in trends
        if trend.metric_name == "warning_count"
    )

    assert warning_trend.first_value == 3.0
    assert warning_trend.current_value == 0.0
    assert warning_trend.delta == -3.0
    assert warning_trend.direction is TrendDirection.IMPROVING


def test_engine_treats_increasing_critical_count_as_degrading() -> None:
    samples = (
        sample(
            run_id="run-001",
            generated_at="2026-07-09T10:00:00Z",
            health_score=100.0,
            warning_count=0,
            critical_count=0,
            total_findings=0,
        ),
        sample(
            run_id="run-002",
            generated_at="2026-07-10T10:00:00Z",
            health_score=75.0,
            warning_count=0,
            critical_count=1,
            total_findings=1,
        ),
    )

    trends = TrendEngine().analyze(samples)

    critical_trend = next(
        trend
        for trend in trends
        if trend.metric_name == "critical_count"
    )

    assert critical_trend.delta == 1.0
    assert critical_trend.direction is TrendDirection.DEGRADING


def test_engine_classifies_constant_values_as_stable() -> None:
    samples = (
        sample(
            run_id="run-001",
            generated_at="2026-07-09T10:00:00Z",
            health_score=80.0,
            warning_count=1,
            critical_count=0,
            total_findings=1,
        ),
        sample(
            run_id="run-002",
            generated_at="2026-07-10T10:00:00Z",
            health_score=80.0,
            warning_count=1,
            critical_count=0,
            total_findings=1,
        ),
    )

    trends = TrendEngine().analyze(samples)

    assert all(
        trend.direction is TrendDirection.STABLE
        for trend in trends
    )


def test_engine_classifies_one_sample_as_insufficient_data() -> None:
    samples = (
        sample(
            run_id="run-001",
            generated_at="2026-07-09T10:00:00Z",
            health_score=80.0,
            warning_count=1,
            critical_count=0,
            total_findings=1,
        ),
    )

    trends = TrendEngine().analyze(samples)

    assert all(
        trend.direction
        is TrendDirection.INSUFFICIENT_DATA
        for trend in trends
    )


def test_default_engine_returns_four_metric_trends() -> None:
    trends = TrendEngine().analyze(improving_samples())

    assert tuple(
        trend.metric_name
        for trend in trends
    ) == (
        "health_score",
        "warning_count",
        "critical_count",
        "total_findings",
    )


def test_engine_rejects_empty_samples() -> None:
    with pytest.raises(
        ValueError,
        match="samples must not be empty",
    ):
        TrendEngine().analyze(())


def test_engine_rejects_unsorted_samples() -> None:
    samples = tuple(reversed(improving_samples()))

    with pytest.raises(
        ValueError,
        match="samples must be ordered chronologically",
    ):
        TrendEngine().analyze(samples)


def test_engine_rejects_duplicate_metric_names() -> None:
    definition = MetricDefinition(
        metric_name="duplicate",
        extractor=lambda item: item.health_score,
        higher_is_better=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicate metric names",
    ):
        TrendEngine((definition, definition))
