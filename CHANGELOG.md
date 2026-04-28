# Changelog

## 0.3.0 (2026-04-27)

- Add `Monitor.export_json(path)` to persist the recorded snapshot ring buffer as JSON
- Add `Monitor.snapshots()` returning a defensive copy of the recorded buffer for external analysis
- Replace 7-line import-only test with a comprehensive test suite covering snapshot types, metric lookup, export, and trend math

## 0.2.1 (2026-03-31)

- Standardize README to 3-badge format with emoji Support section
- Update CI checkout action to v5 for Node.js 24 compatibility

## 0.2.0 (2026-03-27)

- Add historical trend tracking with ring buffer recording
- Add `Trend` dataclass for trend analysis results
- Add `Monitor.start_recording()` and `Monitor.stop_recording()` for background snapshot collection
- Add `Monitor.get_trend()` for computing linear metric trends over a time window

## 0.1.8 (2026-03-22)

- Add pytest and mypy configuration to pyproject.toml

## 0.1.5

- Add basic import test

## 0.1.4

- Add Development section to README

## 0.1.1

- Add project URLs to pyproject.toml

## 0.1.0 (2026-03-10)

- Initial release
