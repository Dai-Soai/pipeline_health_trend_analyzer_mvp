"""Command-line interface for Pipeline Health Trend Analyzer."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pipeline_health_trend_analyzer import __version__
from pipeline_health_trend_analyzer.analyzer import (
    PipelineHealthTrendAnalyzer,
)
from pipeline_health_trend_analyzer.contract import (
    TrendDirection,
    TrendReport,
)
from pipeline_health_trend_analyzer.health_loader import (
    HealthReportLoadError,
)


EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_TREND_THRESHOLD = 2


_DIRECTION_RANK = {
    TrendDirection.IMPROVING: 0,
    TrendDirection.STABLE: 1,
    TrendDirection.DEGRADING: 2,
    TrendDirection.INSUFFICIENT_DATA: 3,
}


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        prog="pipeline-health-trend",
        description=(
            "Analyze historical RADAR_SERVICE health reports and "
            "evaluate pipeline health trends."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a directory of historical health reports.",
    )

    analyze_parser.add_argument(
        "health_reports",
        help="Directory containing Utility #27 health report JSON files.",
    )

    analyze_parser.add_argument(
        "--pattern",
        default="*.json",
        help=(
            "Glob pattern used to discover health reports. "
            "Default: %(default)s"
        ),
    )

    analyze_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Discover matching reports recursively.",
    )

    analyze_parser.add_argument(
        "--show-metrics",
        action="store_true",
        help="Print detailed statistical information for each metric.",
    )

    analyze_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the overall trend direction.",
    )

    analyze_parser.add_argument(
        "--fail-on",
        choices=(
            TrendDirection.STABLE.value,
            TrendDirection.DEGRADING.value,
            TrendDirection.INSUFFICIENT_DATA.value,
        ),
        help=(
            "Return exit code 2 when the observed trend reaches or "
            "exceeds this operational threshold."
        ),
    )

    return parser


def format_report(
    report: TrendReport,
    *,
    show_metrics: bool = False,
) -> str:
    """Format a trend report for terminal output."""

    lines = [
        "Pipeline Health Trend Analysis",
        "==============================",
        f"Run ID: {report.run_id}",
        f"Status: {report.status}",
        (
            "Overall direction: "
            f"{report.summary.overall_direction.value}"
        ),
        f"Samples: {report.summary.sample_count}",
        f"Metrics: {report.summary.metric_count}",
        f"Improving: {report.summary.improving_count}",
        f"Stable: {report.summary.stable_count}",
        f"Degrading: {report.summary.degrading_count}",
        (
            "Insufficient data: "
            f"{report.summary.insufficient_data_count}"
        ),
        f"Report version: {report.report_version}",
        f"Analyzer version: {report.analyzer_version}",
    ]

    if report.overview is not None:
        lines.extend(
            [
                "",
                f"Headline: {report.overview.headline}",
                f"Message: {report.overview.message}",
                (
                    "Dominant direction: "
                    f"{report.overview.dominant_direction.value}"
                ),
                (
                    "Highlighted metrics: "
                    + (
                        ", ".join(
                            report.overview.highlighted_metrics
                        )
                        if report.overview.highlighted_metrics
                        else "none"
                    )
                ),
                (
                    "Recommendation: "
                    f"{report.overview.recommendation}"
                ),
            ]
        )

    if show_metrics:
        lines.extend(
            [
                "",
                "Metric Trends",
                "-------------",
            ]
        )

        for index, trend in enumerate(
            report.metric_trends,
            start=1,
        ):
            lines.extend(
                [
                    (
                        f"{index}. [{trend.direction.value}] "
                        f"{trend.metric_name}"
                    ),
                    f"   Samples: {trend.sample_count}",
                    f"   First: {_format_number(trend.first_value)}",
                    (
                        "   Current: "
                        f"{_format_number(trend.current_value)}"
                    ),
                    (
                        "   Average: "
                        f"{_format_number(trend.average_value)}"
                    ),
                    (
                        "   Minimum: "
                        f"{_format_number(trend.minimum_value)}"
                    ),
                    (
                        "   Maximum: "
                        f"{_format_number(trend.maximum_value)}"
                    ),
                    f"   Delta: {_format_number(trend.delta)}",
                    f"   Slope: {_format_number(trend.slope)}",
                ]
            )

    return "\n".join(lines)


def _format_number(value: float) -> str:
    """Format a numeric metric value consistently."""

    return f"{value:.6f}".rstrip("0").rstrip(".")


def threshold_reached(
    observed: TrendDirection,
    threshold: TrendDirection,
) -> bool:
    """Return whether the observed trend reaches a fail threshold."""

    return (
        _DIRECTION_RANK[observed]
        >= _DIRECTION_RANK[threshold]
    )


def run_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command."""

    analyzer = PipelineHealthTrendAnalyzer()

    try:
        report = analyzer.analyze_directory(
            args.health_reports,
            pattern=args.pattern,
            recursive=args.recursive,
        )
    except HealthReportLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except (TypeError, ValueError) as exc:
        print(
            f"error: trend analysis failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    direction = report.summary.overall_direction

    if args.quiet:
        print(direction.value)
    else:
        print(
            format_report(
                report,
                show_metrics=args.show_metrics,
            )
        )

    if args.fail_on is not None:
        threshold = TrendDirection(args.fail_on)

        if threshold_reached(direction, threshold):
            return EXIT_TREND_THRESHOLD

    return EXIT_SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Pipeline Health Trend Analyzer CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args)

    parser.error(f"unsupported command: {args.command}")
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
