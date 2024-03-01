# philiprehberger-server-monitor

[![Tests](https://github.com/philiprehberger/py-server-monitor/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-server-monitor/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-server-monitor.svg)](https://pypi.org/project/philiprehberger-server-monitor/)
[![GitHub release](https://img.shields.io/github/v/release/philiprehberger/py-server-monitor)](https://github.com/philiprehberger/py-server-monitor/releases)
[![Last updated](https://img.shields.io/github/last-commit/philiprehberger/py-server-monitor)](https://github.com/philiprehberger/py-server-monitor/commits/main)
[![License](https://img.shields.io/github/license/philiprehberger/py-server-monitor)](LICENSE)
[![Bug Reports](https://img.shields.io/github/issues/philiprehberger/py-server-monitor/bug)](https://github.com/philiprehberger/py-server-monitor/issues?q=is%3Aissue+is%3Aopen+label%3Abug)
[![Feature Requests](https://img.shields.io/github/issues/philiprehberger/py-server-monitor/enhancement)](https://github.com/philiprehberger/py-server-monitor/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub%20Sponsors-ec6cb9)](https://github.com/sponsors/philiprehberger)

System metrics collector for CPU, memory, disk, and network.

## Installation

```bash
pip install philiprehberger-server-monitor
```

## Usage

### Single Snapshot

```python
from philiprehberger_server_monitor import Monitor

monitor = Monitor()
snap = monitor.snapshot()
print(f"CPU: {snap.cpu.percent}%")
print(f"Memory: {snap.memory.used_gb:.1f}/{snap.memory.total_gb:.1f} GB")
print(f"Disk: {snap.disk['/'].percent}%")

# Export snapshot
data = snap.to_dict()
```

### Continuous Monitoring with Alerts

```python
from philiprehberger_server_monitor import Monitor, Alert

monitor = Monitor()
monitor.watch(
    interval=5.0,
    on_snapshot=lambda s: print(f"CPU: {s.cpu.percent}%"),
    alerts=[
        Alert(metric="cpu.percent", threshold=90, callback=lambda m, v, t: print(f"HIGH CPU: {v}%")),
        Alert(metric="memory.percent", threshold=85, callback=lambda m, v, t: print(f"HIGH MEM: {v}%")),
    ],
)
```

### Trend Tracking

```python
from philiprehberger_server_monitor import Monitor

monitor = Monitor()

# Start recording snapshots every 5 seconds (keeps last 720)
monitor.start_recording(interval=5.0, max_snapshots=720)

# Later, analyze trends over the last 5 minutes
trend = monitor.get_trend("cpu.percent", window_seconds=300)
print(f"CPU slope: {trend.slope:.4f}%/s")
print(f"CPU went from {trend.start_value}% to {trend.end_value}%")

# Stop recording
monitor.stop_recording()
```

## API

| Function / Class | Description |
|------------------|-------------|
| `Monitor` | System metrics monitor with `snapshot()`, `watch()`, `stop()`, and trend tracking methods |
| `Snapshot` | A point-in-time system metrics snapshot with `cpu`, `memory`, `disk`, `network` fields |
| `CpuInfo` | CPU metrics (percent, count, count_logical, per_cpu, freq_mhz) |
| `MemoryInfo` | Memory metrics (total, available, used, percent) with GB properties |
| `DiskInfo` | Disk metrics for a single mount point (total, used, free, percent) |
| `NetworkInfo` | Network metrics (bytes_sent, bytes_recv, packets_sent, packets_recv) |
| `Alert(metric, threshold, callback)` | Threshold-based alert configuration for continuous monitoring |
| `Trend` | Trend analysis result with metric, start_value, end_value, slope, duration_seconds |
| `monitor.start_recording(interval, max_snapshots)` | Start background snapshot recording into a ring buffer |
| `monitor.stop_recording()` | Stop the recording thread |
| `monitor.get_trend(metric, window_seconds)` | Compute linear trend for a metric over recent snapshots |

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```

## Support

If you find this package useful, consider giving it a star on GitHub — it helps motivate continued maintenance and development.

[![LinkedIn](https://img.shields.io/badge/Philip%20Rehberger-LinkedIn-0A66C2?logo=linkedin)](https://www.linkedin.com/in/philiprehberger)
[![More packages](https://img.shields.io/badge/more-open%20source%20packages-blue)](https://philiprehberger.com/open-source-packages)

## License

[MIT](LICENSE)
