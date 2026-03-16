# philiprehberger-server-monitor

[![Tests](https://github.com/philiprehberger/py-server-monitor/actions/workflows/publish.yml/badge.svg)](https://github.com/philiprehberger/py-server-monitor/actions/workflows/publish.yml)
[![PyPI version](https://img.shields.io/pypi/v/philiprehberger-server-monitor.svg)](https://pypi.org/project/philiprehberger-server-monitor/)
[![License](https://img.shields.io/github/license/philiprehberger/py-server-monitor)](LICENSE)

System metrics collector for CPU, memory, disk, and network.

## Install

```bash
pip install philiprehberger-server-monitor
```

## Usage

```python
from philiprehberger_server_monitor import Monitor, Alert

monitor = Monitor()

# Single snapshot
snap = monitor.snapshot()
print(f"CPU: {snap.cpu.percent}%")
print(f"Memory: {snap.memory.used_gb:.1f}/{snap.memory.total_gb:.1f} GB")
print(f"Disk: {snap.disk['/'].percent}%")

# Continuous monitoring with alerts
monitor.watch(
    interval=5.0,
    on_snapshot=lambda s: print(f"CPU: {s.cpu.percent}%"),
    alerts=[
        Alert(metric="cpu.percent", threshold=90, callback=lambda m, v, t: print(f"HIGH CPU: {v}%")),
        Alert(metric="memory.percent", threshold=85, callback=send_alert),
    ],
)

# Export snapshot
data = snap.to_dict()
```

## Metrics

| Category | Fields |
|----------|--------|
| CPU | percent, count, count_logical, per_cpu, freq_mhz |
| Memory | total, available, used, percent, total_gb, used_gb |
| Disk | mountpoint, total, used, free, percent |
| Network | bytes_sent, bytes_recv, packets_sent, packets_recv |

## License

MIT
