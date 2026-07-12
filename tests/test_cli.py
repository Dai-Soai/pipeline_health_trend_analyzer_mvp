from pathlib import Path

import pytest

from pipeline_health_trend_analyzer import (
    PipelineHealthTrendAnalyzer,
    TrendDirection,
)
from pipeline_health_trend_analyzer.cli import (
    EXIT_ERROR,
    EXIT_SUCCESS,
    EXIT_TREND_THRESHOLD,
    _format_number,
    build_parser,
    format_report,
    main,
    threshold_reached,
)


EXAMPLE_DIRECTORY = Path("examples/health_reports")


def test_parser_accepts_analyze_command() -> None:
    args = build_parser().parse_args(
        [
            "analyze",
            str(EXAMPLE_DIRECTORY),
            "--pattern",
            "health_report_*.json",
            "--recursive",
            "--show-metrics",
            "--fail-on",
            "degrading",
        ]
    )

    assert args.command == "analyze"
    assert args.health_reports == str(EXAMPLE_DIRECTORY)
    assert args.pattern == "health_report_*.json"
    assert args.recursive is True
    assert args.show_metrics is True
    assert args.fail_on == "degrading"


def test_format_number_removes_trailing_zeroes() -> None:
    assert _format_number(25.0) == "25"
    assert _format_number(73.333333) == "73.333333"
    assert _format_number(-1.5) == "-1.5"


def test_format_report_contains_summary() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            EXAMPLE_DIRECTORY,
            run_id="cli-summary-test",
            generated_at="2026-07-12T12:00:00Z",
        )
    )

    output = format_report(report)

    assert "Pipeline Health Trend Analysis" in output
    assert "Overall direction: improving" in output
    assert "Samples: 3" in output
    assert "Metrics: 4" in output
    assert "Improving: 4" in output
    assert "Headline: Pipeline health is improving" in output


def test_format_report_can_show_metric_details() -> None:
    report = (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            EXAMPLE_DIRECTORY,
            run_id="cli-metrics-test",
            generated_at="2026-07-12T12:00:00Z",
        )
    )

    output = format_report(
        report,
        show_metrics=True,
    )

    assert "Metric Trends" in output
    assert "[improving] health_score" in output
    assert "[improving] warning_count" in output
    assert "[improving] critical_count" in output
    assert "[improving] total_findings" in output
    assert "Delta: 50" in output
    assert "Slope: 25" in output


@pytest.mark.parametrize(
    ("observed", "threshold", "expected"),
    [
        (
            TrendDirection.IMPROVING,
            TrendDirection.STABLE,
            False,
        ),
        (
            TrendDirection.STABLE,
            TrendDirection.STABLE,
            True,
        ),
        (
            TrendDirection.DEGRADING,
            TrendDirection.STABLE,
            True,
        ),
        (
            TrendDirection.STABLE,
            TrendDirection.DEGRADING,
            False,
        ),
        (
            TrendDirection.INSUFFICIENT_DATA,
            TrendDirection.DEGRADING,
            True,
        ),
        (
            TrendDirection.DEGRADING,
            TrendDirection.INSUFFICIENT_DATA,
            False,
        ),
    ],
)
def test_threshold_reached(
    observed: TrendDirection,
    threshold: TrendDirection,
    expected: bool,
) -> None:
    assert threshold_reached(observed, threshold) is expected


def test_main_analyze_prints_report(capsys) -> None:
    exit_code = main(
        [
            "analyze",
            str(EXAMPLE_DIRECTORY),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert "Overall direction: improving" in captured.out
    assert "Samples: 3" in captured.out
    assert captured.err == ""


def test_main_quiet_prints_only_direction(capsys) -> None:
    exit_code = main(
        [
            "analyze",
            str(EXAMPLE_DIRECTORY),
            "--quiet",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert captured.out.strip() == "improving"
    assert captured.err == ""


def test_main_does_not_fail_below_stable_threshold(
    capsys,
) -> None:
    exit_code = main(
        [
            "analyze",
            str(EXAMPLE_DIRECTORY),
            "--quiet",
            "--fail-on",
            "stable",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert captured.out.strip() == "improving"


def test_main_reports_missing_directory(
    capsys,
    tmp_path: Path,
) -> None:
    missing_directory = tmp_path / "missing"

    exit_code = main(
        [
            "analyze",
            str(missing_directory),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_ERROR
    assert captured.out == ""
    assert "Health report directory not found" in captured.err


def test_main_reports_empty_directory(
    capsys,
    tmp_path: Path,
) -> None:
    exit_code = main(
        [
            "analyze",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_ERROR
    assert captured.out == ""
    assert "No health reports matched" in captured.err


def test_main_analyze_writes_json_report(
    capsys,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "trend-report.json"

    exit_code = main(
        [
            "analyze",
            str(EXAMPLE_DIRECTORY),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert output_path.exists()
    assert "Report written:" in captured.out


def test_main_validates_trend_report(
    capsys,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "trend-report.json"

    assert (
        main(
            [
                "analyze",
                str(EXAMPLE_DIRECTORY),
                "--output",
                str(output_path),
                "--quiet",
            ]
        )
        == EXIT_SUCCESS
    )

    capsys.readouterr()

    exit_code = main(
        [
            "validate",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert (
        captured.out.strip()
        == "Trend report is valid."
    )
    assert captured.err == ""


def test_main_inspects_trend_report(
    capsys,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "trend-report.json"

    assert (
        main(
            [
                "analyze",
                str(EXAMPLE_DIRECTORY),
                "--output",
                str(output_path),
                "--quiet",
            ]
        )
        == EXIT_SUCCESS
    )

    capsys.readouterr()

    exit_code = main(
        [
            "inspect",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == EXIT_SUCCESS
    assert "Trend Report Inspection" in captured.out
    assert (
        "Overall direction: improving"
        in captured.out
    )
    assert "Samples: 3" in captured.out
    assert "Metrics: 4" in captured.out
