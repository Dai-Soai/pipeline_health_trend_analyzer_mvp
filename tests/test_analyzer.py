from pathlib import Path

import pytest

from pipeline_health_trend_analyzer import (
    MetricTrend,
    PipelineHealthTrendAnalyzer,
    TrendDirection,
    TrendSample,
)


EXAMPLE_DIRECTORY = Path("examples/health_reports")


def metric_trend(
    *,
    metric_name: str,
    direction: TrendDirection,
) -> MetricTrend:
    return MetricTrend(
        metric_name=metric_name,
        sample_count=2,
        first_value=10.0,
        current_value=20.0,
        average_value=15.0,
        minimum_value=10.0,
        maximum_value=20.0,
        delta=10.0,
        slope=10.0,
        direction=direction,
    )


def sample(
    *,
    run_id: str,
    generated_at: str,
    health_score: float,
    warning_count: int = 0,
    critical_count: int = 0,
    total_findings: int = 0,
) -> TrendSample:
    return TrendSample(
        run_id=run_id,
        generated_at=generated_at,
        status="healthy",
        health_score=health_score,
        warning_count=warning_count,
        critical_count=critical_count,
        total_findings=total_findings,
    )


def test_analyzer_metadata_properties() -> None:
    analyzer = PipelineHealthTrendAnalyzer()

    assert analyzer.report_version == "1.0"
    assert analyzer.analyzer_version == "0.1.0"


def test_analyzer_rejects_empty_version_metadata() -> None:
    with pytest.raises(
        ValueError,
        match="report_version must not be empty",
    ):
        PipelineHealthTrendAnalyzer(
            report_version="",
        )


def test_overall_direction_is_improving() -> None:
    trends = (
        metric_trend(
            metric_name="health_score",
            direction=TrendDirection.IMPROVING,
        ),
        metric_trend(
            metric_name="warning_count",
            direction=TrendDirection.IMPROVING,
        ),
        metric_trend(
            metric_name="critical_count",
            direction=TrendDirection.STABLE,
        ),
    )

    direction = (
        PipelineHealthTrendAnalyzer()
        .determine_overall_direction(trends)
    )

    assert direction is TrendDirection.IMPROVING


def test_overall_direction_is_degrading() -> None:
    trends = (
        metric_trend(
            metric_name="health_score",
            direction=TrendDirection.DEGRADING,
        ),
        metric_trend(
            metric_name="warning_count",
            direction=TrendDirection.DEGRADING,
        ),
        metric_trend(
            metric_name="critical_count",
            direction=TrendDirection.STABLE,
        ),
    )

    direction = (
        PipelineHealthTrendAnalyzer()
        .determine_overall_direction(trends)
    )

    assert direction is TrendDirection.DEGRADING


def test_overall_direction_is_stable_when_counts_tie() -> None:
    trends = (
        metric_trend(
            metric_name="health_score",
            direction=TrendDirection.IMPROVING,
        ),
        metric_trend(
            metric_name="warning_count",
            direction=TrendDirection.DEGRADING,
        ),
    )

    direction = (
        PipelineHealthTrendAnalyzer()
        .determine_overall_direction(trends)
    )

    assert direction is TrendDirection.STABLE


def test_overall_direction_is_insufficient_data() -> None:
    trends = (
        metric_trend(
            metric_name="health_score",
            direction=TrendDirection.INSUFFICIENT_DATA,
        ),
        metric_trend(
            metric_name="warning_count",
            direction=TrendDirection.INSUFFICIENT_DATA,
        ),
    )

    direction = (
        PipelineHealthTrendAnalyzer()
        .determine_overall_direction(trends)
    )

    assert direction is TrendDirection.INSUFFICIENT_DATA


def test_analyze_samples_builds_valid_report() -> None:
    samples = (
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
        ),
    )

    report = PipelineHealthTrendAnalyzer().analyze_samples(
        samples,
        run_id="trend-test-001",
        generated_at="2026-07-12T10:00:00Z",
    )

    assert report.validate() == []
    assert report.run_id == "trend-test-001"
    assert report.status == "completed"
    assert report.summary.sample_count == 3
    assert report.summary.metric_count == 4
    assert (
        report.summary.overall_direction
        is TrendDirection.IMPROVING
    )


def test_analyze_one_sample_marks_insufficient_data() -> None:
    report = PipelineHealthTrendAnalyzer().analyze_samples(
        (
            sample(
                run_id="run-001",
                generated_at="2026-07-11T10:00:00Z",
                health_score=80.0,
                warning_count=1,
                total_findings=1,
            ),
        ),
        run_id="trend-single",
        generated_at="2026-07-12T10:00:00Z",
    )

    assert report.status == "insufficient_data"
    assert (
        report.summary.overall_direction
        is TrendDirection.INSUFFICIENT_DATA
    )
    assert report.summary.insufficient_data_count == 4


def test_analyze_directory_builds_improving_report() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            EXAMPLE_DIRECTORY,
            run_id="trend-directory-test",
            generated_at="2026-07-12T10:00:00Z",
        )
    )

    assert report.validate() == []
    assert report.run_id == "trend-directory-test"
    assert report.status == "completed"
    assert len(report.samples) == 3
    assert len(report.metric_trends) == 4
    assert (
        report.summary.overall_direction
        is TrendDirection.IMPROVING
    )


def test_analyze_directory_preserves_source_metadata() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            EXAMPLE_DIRECTORY,
            run_id="trend-metadata-test",
            generated_at="2026-07-12T10:00:00Z",
        )
    )

    metadata = report.source_metadata

    assert metadata["source_report_count"] == 3
    assert metadata["metric_definition_count"] == 4
    assert metadata["source_health_report_versions"] == ["1.0"]
    assert metadata["source_health_analyzer_versions"] == ["0.1.0"]
    assert len(metadata["source_paths"]) == 3


def test_analyze_files_accepts_unsorted_paths() -> None:
    paths = (
        EXAMPLE_DIRECTORY / "health_report_003.json",
        EXAMPLE_DIRECTORY / "health_report_001.json",
        EXAMPLE_DIRECTORY / "health_report_002.json",
    )

    report = PipelineHealthTrendAnalyzer().analyze_files(
        paths,
        run_id="trend-files-test",
        generated_at="2026-07-12T10:00:00Z",
    )

    assert report.samples[0].run_id == "health-run-001"
    assert report.samples[-1].run_id == "health-run-003"
    assert (
        report.summary.overall_direction
        is TrendDirection.IMPROVING
    )


def test_generated_run_id_has_trend_prefix() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            EXAMPLE_DIRECTORY,
            generated_at="2026-07-12T10:00:00Z",
        )
    )

    assert report.run_id.startswith("trend-")
