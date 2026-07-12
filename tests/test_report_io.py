import json
from pathlib import Path

import pytest

from pipeline_health_trend_analyzer import (
    PipelineHealthTrendAnalyzer,
    TrendReportContractError,
    TrendReportFileNotFoundError,
    TrendReportJSONError,
    TrendReportSerializer,
    TrendReportStore,
)


def build_report():
    return (
        PipelineHealthTrendAnalyzer()
        .analyze_directory(
            "examples/health_reports",
            run_id="report-io-test",
            generated_at="2026-07-12T13:00:00Z",
        )
    )


def test_serializer_dumps_trend_report() -> None:
    content = TrendReportSerializer().dumps(
        build_report()
    )
    data = json.loads(content)

    assert data["status"] == "completed"
    assert data["analyzer_version"] == "0.1.0"
    assert (
        data["summary"]["overall_direction"]
        == "improving"
    )
    assert len(data["metric_trends"]) == 4


def test_serializer_round_trip() -> None:
    serializer = TrendReportSerializer()
    report = build_report()

    restored = serializer.loads(
        serializer.dumps(report)
    )

    assert restored == report
    assert restored.validate() == []


def test_serializer_rejects_invalid_json() -> None:
    with pytest.raises(TrendReportJSONError):
        TrendReportSerializer().loads(
            "{invalid-json"
        )


def test_serializer_rejects_non_object_root() -> None:
    with pytest.raises(
        TrendReportContractError
    ) as exc_info:
        TrendReportSerializer().loads(
            '["not", "an", "object"]'
        )

    assert (
        "trend report root must be a JSON object"
        in exc_info.value.errors
    )


def test_store_writes_and_reads_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trend-report.json"
    store = TrendReportStore()
    report = build_report()

    resolved_path = store.write(report, path)
    restored = store.read(path)

    assert resolved_path == path.resolve()
    assert restored == report
    assert path.exists()


def test_store_creates_parent_directories(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "nested"
        / "reports"
        / "trend.json"
    )

    TrendReportStore().write(
        build_report(),
        path,
    )

    assert path.exists()


def test_store_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        TrendReportFileNotFoundError
    ):
        TrendReportStore().read(
            tmp_path / "missing.json"
        )


def test_validate_file_returns_no_errors_for_valid_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trend.json"
    store = TrendReportStore()

    store.write(
        build_report(),
        path,
    )

    assert store.validate_file(path) == ()


def test_validate_file_returns_errors_for_invalid_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "invalid.json"

    path.write_text(
        json.dumps(
            {
                "report_version": "1.0",
                "analyzer_version": "",
            }
        ),
        encoding="utf-8",
    )

    errors = TrendReportStore().validate_file(path)

    assert errors


def test_store_inspects_trend_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trend.json"
    store = TrendReportStore()

    store.write(
        build_report(),
        path,
    )

    inspection = store.inspect(path)

    assert inspection.status == "completed"
    assert inspection.overall_direction == "improving"
    assert inspection.sample_count == 3
    assert inspection.metric_count == 4
    assert inspection.improving_count == 4
    assert inspection.stable_count == 0
    assert inspection.degrading_count == 0
    assert inspection.dominant_direction == "improving"
    assert len(inspection.highlighted_metrics) == 4


def test_inspection_serialization(
    tmp_path: Path,
) -> None:
    path = tmp_path / "trend.json"
    store = TrendReportStore()

    store.write(
        build_report(),
        path,
    )

    data = store.inspect(path).to_dict()

    assert data["status"] == "completed"
    assert data["overall_direction"] == "improving"
    assert (
        data["headline"]
        == "Pipeline health is improving"
    )
    assert isinstance(
        data["highlighted_metrics"],
        list,
    )
