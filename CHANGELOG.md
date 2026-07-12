# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-07-12

### Added

#### Project bootstrap

- Initial project structure.
- Python package bootstrap.
- Test directory.
- Historical report examples directory.
- Runtime report output directory.
- File-first snapshot artifact directory.
- Packaging configuration.

#### Trend contract

- Trend direction enumeration.
- Historical trend sample contract.
- Numeric metric trend contract.
- Aggregate trend summary contract.
- Human-readable trend overview contract.
- Complete trend report contract.
- Contract serialization and deserialization.
- Contract validation.
- Chronological sample validation.
- Analyzer version metadata field.
- Optional overview enrichment for backward compatibility.

#### Health report loading

- Utility #27 health report loader.
- Loaded health report contract.
- Health report metadata validation.
- JSON file and directory loading.
- Recursive report discovery.
- Chronological report ordering.
- Duplicate run identifier detection.
- Health score normalization.
- Health report to trend sample conversion.
- Example historical health reports.

#### Trend engine

- Configurable metric definition contract.
- Default pipeline health trend metrics.
- Least-squares linear slope calculation.
- First and current value calculation.
- Average, minimum, maximum, and delta calculation.
- Metric-aware improving and degrading classification.
- Stable classification with configurable tolerance.
- Insufficient-data classification.
- Unified trend engine.

#### Pipeline trend analysis

- Pipeline health trend analyzer orchestration.
- Overall trend direction aggregation.
- Analysis from samples.
- Analysis from loaded reports.
- Analysis from explicit files.
- Analysis from directories.
- Complete trend summary generation.
- Complete trend report generation.
- Automatic trend run identifier generation.
- Source report metadata preservation.

#### Trend summary

- Human-readable trend overview.
- Trend summary builder.
- Direction-specific headlines.
- Historical sample summary messages.
- Dominant trend direction output.
- Highlighted metric selection.
- Delta-based highlighted metric ordering.
- Direction-specific operational recommendations.
- Trend overview integration with generated reports.

#### Command-line interface

- Installed `pipeline-health-trend` console command.
- Trend analysis CLI command.
- Human-readable trend report output.
- Detailed metric trend output.
- Quiet direction-only output.
- Custom health report glob patterns.
- Recursive report discovery.
- Configurable trend failure thresholds.
- Automation-friendly CLI exit codes.

#### JSON report artifacts

- JSON trend report serializer.
- JSON trend report deserializer.
- Atomic trend report artifact writer.
- Trend report artifact reader.
- Trend report validation API.
- Trend report inspection contract.
- CLI `--output` report generation.
- CLI `validate` command.
- CLI `inspect` command.

#### Quality and packaging

- Complete automated regression suite.
- Wheel package build.
- Source distribution build.
- Wheel metadata verification.
- Clean wheel installation verification.
- Installed CLI smoke verification.
- JSON generation verification.
- JSON validation verification.
- JSON inspection verification.
