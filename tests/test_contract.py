from pipeline_health_trend_analyzer import (
    MetricTrend,
    TrendDirection,
    TrendReport,
    TrendSample,
    TrendSummary,
)


def build_sample(
    *,
    run_id: str = "health-run-001",
    generated_at: str = "2026-07-10T10:00:00Z",
    health_score: float = 80.0,
) -> TrendSample:
    return TrendSample(
        run_id=run_id,
        generated_at=generated_at,
        status="warning",
        health_score=health_score,
        warning_count=2,
        critical_count=0,
        total_findings=2,
        source_path=f"/tmp/{run_id}.json",
        metadata={"analyzer_version": "0.1.0"},
    )


def build_metric_trend() -> MetricTrend:
    return MetricTrend(
        metric_name="health_score",
        sample_count=3,
        first_value=70.0,
        current_value=80.0,
        average_value=75.0,
        minimum_value=70.0,
        maximum_value=80.0,
        delta=10.0,
        slope=5.0,
        direction=TrendDirection.IMPROVING,
    )


def test_trend_direction_values() -> None:
    assert TrendDirection.IMPROVING.value == "improving"
    assert TrendDirection.STABLE.value == "stable"
    assert TrendDirection.DEGRADING.value == "degrading"
    assert (
        TrendDirection.INSUFFICIENT_DATA.value
        == "insufficient_data"
    )


def test_trend_sample_round_trip() -> None:
    sample = build_sample()

    restored = TrendSample.from_dict(sample.to_dict())

    assert restored == sample
    assert restored.validate() == []


def test_trend_sample_rejects_invalid_score() -> None:
    sample = build_sample(health_score=101.0)

    assert (
        "trend_sample.health_score must not exceed 100"
        in sample.validate()
    )


def test_trend_sample_rejects_inconsistent_counts() -> None:
    sample = TrendSample(
        run_id="run-invalid",
        generated_at="2026-07-10T10:00:00Z",
        status="critical",
        health_score=40.0,
        warning_count=3,
        critical_count=2,
        total_findings=4,
    )

    assert (
        "trend_sample.warning_count + critical_count "
        "must not exceed total_findings"
        in sample.validate()
    )


def test_metric_trend_round_trip() -> None:
    metric_trend = build_metric_trend()

    restored = MetricTrend.from_dict(metric_trend.to_dict())

    assert restored == metric_trend
    assert restored.validate() == []


def test_metric_trend_rejects_invalid_delta() -> None:
    metric_trend = MetricTrend(
        metric_name="health_score",
        sample_count=2,
        first_value=70.0,
        current_value=80.0,
        average_value=75.0,
        minimum_value=70.0,
        maximum_value=80.0,
        delta=5.0,
        slope=10.0,
        direction=TrendDirection.IMPROVING,
    )

    assert (
        "metric_trend.delta must equal "
        "current_value - first_value"
        in metric_trend.validate()
    )


def test_trend_summary_from_metric_trends() -> None:
    metric_trends = (
        build_metric_trend(),
        MetricTrend(
            metric_name="warning_count",
            sample_count=3,
            first_value=4.0,
            current_value=2.0,
            average_value=3.0,
            minimum_value=2.0,
            maximum_value=4.0,
            delta=-2.0,
            slope=-1.0,
            direction=TrendDirection.IMPROVING,
        ),
        MetricTrend(
            metric_name="critical_count",
            sample_count=3,
            first_value=0.0,
            current_value=0.0,
            average_value=0.0,
            minimum_value=0.0,
            maximum_value=0.0,
            delta=0.0,
            slope=0.0,
            direction=TrendDirection.STABLE,
        ),
    )

    summary = TrendSummary.from_metric_trends(
        sample_count=3,
        metric_trends=metric_trends,
        overall_direction=TrendDirection.IMPROVING,
    )

    assert summary.sample_count == 3
    assert summary.metric_count == 3
    assert summary.improving_count == 2
    assert summary.stable_count == 1
    assert summary.degrading_count == 0
    assert summary.validate() == []


def test_trend_summary_rejects_count_mismatch() -> None:
    summary = TrendSummary(
        sample_count=3,
        metric_count=4,
        improving_count=1,
        stable_count=1,
        degrading_count=1,
        insufficient_data_count=0,
        overall_direction=TrendDirection.STABLE,
    )

    assert (
        "trend_summary.metric_count must equal the sum "
        "of all direction counts"
        in summary.validate()
    )


def test_trend_report_round_trip() -> None:
    samples = (
        build_sample(
            run_id="run-001",
            generated_at="2026-07-10T10:00:00Z",
            health_score=70.0,
        ),
        build_sample(
            run_id="run-002",
            generated_at="2026-07-11T10:00:00Z",
            health_score=80.0,
        ),
    )

    metric_trends = (build_metric_trend(),)

    summary = TrendSummary.from_metric_trends(
        sample_count=2,
        metric_trends=metric_trends,
        overall_direction=TrendDirection.IMPROVING,
    )

    report = TrendReport(
        report_version="1.0",
        analyzer_version="0.1.0",
        run_id="trend-run-001",
        generated_at="2026-07-12T10:00:00Z",
        status="completed",
        summary=summary,
        samples=samples,
        metric_trends=metric_trends,
        source_metadata={
            "source_report_count": 2,
        },
    )

    restored = TrendReport.from_dict(report.to_dict())

    assert restored == report
    assert restored.validate() == []


def test_trend_report_requires_chronological_samples() -> None:
    samples = (
        build_sample(
            run_id="run-new",
            generated_at="2026-07-11T10:00:00Z",
        ),
        build_sample(
            run_id="run-old",
            generated_at="2026-07-10T10:00:00Z",
        ),
    )

    metric_trends = (build_metric_trend(),)

    report = TrendReport(
        report_version="1.0",
        analyzer_version="0.1.0",
        run_id="trend-run-002",
        generated_at="2026-07-12T10:00:00Z",
        status="completed",
        summary=TrendSummary.from_metric_trends(
            sample_count=2,
            metric_trends=metric_trends,
            overall_direction=TrendDirection.STABLE,
        ),
        samples=samples,
        metric_trends=metric_trends,
    )

    assert (
        "samples must be ordered chronologically"
        in report.validate()
    )


def test_trend_report_detects_summary_sample_mismatch() -> None:
    samples = (build_sample(),)
    metric_trends = (build_metric_trend(),)

    report = TrendReport(
        report_version="1.0",
        analyzer_version="0.1.0",
        run_id="trend-run-003",
        generated_at="2026-07-12T10:00:00Z",
        status="completed",
        summary=TrendSummary.from_metric_trends(
            sample_count=2,
            metric_trends=metric_trends,
            overall_direction=TrendDirection.STABLE,
        ),
        samples=samples,
        metric_trends=metric_trends,
    )

    assert (
        "summary.sample_count must match samples length"
        in report.validate()
    )


def test_trend_report_detects_duplicate_metric_names() -> None:
    metric_trend = build_metric_trend()
    metric_trends = (
        metric_trend,
        metric_trend,
    )

    report = TrendReport(
        report_version="1.0",
        analyzer_version="0.1.0",
        run_id="trend-run-004",
        generated_at="2026-07-12T10:00:00Z",
        status="completed",
        summary=TrendSummary.from_metric_trends(
            sample_count=1,
            metric_trends=metric_trends,
            overall_direction=TrendDirection.STABLE,
        ),
        samples=(build_sample(),),
        metric_trends=metric_trends,
    )

    assert (
        "metric_trends must not contain duplicate metric names"
        in report.validate()
    )
