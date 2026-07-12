import json
from pathlib import Path

import pytest

from pipeline_health_trend_analyzer import (
    DuplicateHealthReportError,
    HealthReportFileNotFoundError,
    HealthReportJSONError,
    HealthReportLoader,
    HealthReportValidationError,
    LoadedHealthReport,
)


EXAMPLE_DIRECTORY = Path("examples/health_reports")


def valid_health_report(
    *,
    run_id: str = "health-run-test",
    generated_at: str = "2026-07-10T10:00:00Z",
    status: str = "warning",
    score: float = 70.0,
    maximum: float = 100.0,
    warning_count: int = 3,
    critical_count: int = 0,
    total_findings: int = 3,
) -> dict:
    return {
        "report_version": "1.0",
        "analyzer_version": "0.1.0",
        "run_id": run_id,
        "generated_at": generated_at,
        "status": status,
        "score": {
            "value": score,
            "maximum": maximum,
            "percentage": score,
        },
        "summary": {
            "total_findings": total_findings,
            "info_count": 0,
            "warning_count": warning_count,
            "critical_count": critical_count,
        },
        "overview": None,
        "findings": [],
        "source_metadata": {
            "collector_version": "0.1.0",
        },
    }


def test_loader_normalizes_dictionary() -> None:
    report = HealthReportLoader().from_dict(
        valid_health_report()
    )

    assert isinstance(report, LoadedHealthReport)
    assert report.report_version == "1.0"
    assert report.analyzer_version == "0.1.0"
    assert report.run_id == "health-run-test"
    assert report.health_score == 70.0
    assert report.maximum_score == 100.0
    assert report.validate() == []


def test_loaded_report_normalizes_score() -> None:
    report = HealthReportLoader().from_dict(
        valid_health_report(
            score=4.0,
            maximum=5.0,
        )
    )

    assert report.normalized_score == 80.0


def test_loaded_report_converts_to_trend_sample() -> None:
    report = HealthReportLoader().from_dict(
        valid_health_report()
    )

    sample = report.to_trend_sample()

    assert sample.run_id == "health-run-test"
    assert sample.health_score == 70.0
    assert sample.warning_count == 3
    assert sample.critical_count == 0
    assert sample.metadata["health_report_version"] == "1.0"
    assert sample.metadata["health_analyzer_version"] == "0.1.0"
    assert sample.metadata["collector_version"] == "0.1.0"
    assert sample.validate() == []


def test_loader_reads_health_report_file() -> None:
    path = EXAMPLE_DIRECTORY / "health_report_002.json"

    report = HealthReportLoader().load(path)

    assert report.run_id == "health-run-002"
    assert report.status == "warning"
    assert report.source_path == str(path.resolve())


def test_loader_preserves_raw_report() -> None:
    data = valid_health_report()

    report = HealthReportLoader().from_dict(data)

    assert report.raw_report == data


def test_loader_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(HealthReportFileNotFoundError):
        HealthReportLoader().load(
            tmp_path / "missing.json"
        )


def test_loader_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{invalid-json", encoding="utf-8")

    with pytest.raises(HealthReportJSONError):
        HealthReportLoader().load(path)


def test_loader_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text(
        json.dumps(["not", "an", "object"]),
        encoding="utf-8",
    )

    with pytest.raises(
        HealthReportValidationError
    ) as exc_info:
        HealthReportLoader().load(path)

    assert (
        "health report root must be a JSON object"
        in exc_info.value.errors
    )


def test_loader_rejects_missing_metadata() -> None:
    data = valid_health_report()
    del data["analyzer_version"]
    del data["run_id"]

    with pytest.raises(
        HealthReportValidationError
    ) as exc_info:
        HealthReportLoader().from_dict(data)

    assert (
        "missing required field: analyzer_version"
        in exc_info.value.errors
    )
    assert (
        "missing required field: run_id"
        in exc_info.value.errors
    )


def test_loader_rejects_invalid_generated_at() -> None:
    data = valid_health_report(
        generated_at="not-a-datetime"
    )

    with pytest.raises(
        HealthReportValidationError
    ) as exc_info:
        HealthReportLoader().from_dict(data)

    assert (
        "generated_at must be a valid ISO-8601 datetime"
        in exc_info.value.errors
    )


def test_load_directory_orders_reports_chronologically() -> None:
    reports = HealthReportLoader().load_directory(
        EXAMPLE_DIRECTORY
    )

    assert tuple(
        report.run_id
        for report in reports
    ) == (
        "health-run-001",
        "health-run-002",
        "health-run-003",
    )


def test_to_trend_samples_preserves_chronology() -> None:
    loader = HealthReportLoader()
    reports = loader.load_directory(EXAMPLE_DIRECTORY)

    samples = loader.to_trend_samples(reports)

    assert tuple(
        sample.health_score
        for sample in samples
    ) == (
        50.0,
        70.0,
        100.0,
    )


def test_load_many_sorts_unsorted_paths() -> None:
    paths = (
        EXAMPLE_DIRECTORY / "health_report_003.json",
        EXAMPLE_DIRECTORY / "health_report_001.json",
        EXAMPLE_DIRECTORY / "health_report_002.json",
    )

    reports = HealthReportLoader().load_many(paths)

    assert reports[0].run_id == "health-run-001"
    assert reports[-1].run_id == "health-run-003"


def test_loader_rejects_duplicate_run_ids(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    data = valid_health_report(
        run_id="duplicate-run"
    )

    first_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    data["generated_at"] = "2026-07-11T10:00:00Z"

    second_path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    with pytest.raises(DuplicateHealthReportError):
        HealthReportLoader().load_many(
            (first_path, second_path)
        )


def test_load_directory_rejects_empty_directory(
    tmp_path: Path,
) -> None:
    with pytest.raises(HealthReportFileNotFoundError):
        HealthReportLoader().load_directory(tmp_path)
