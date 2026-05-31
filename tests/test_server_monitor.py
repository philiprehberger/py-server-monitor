"""Tests for philiprehberger_server_monitor."""

from __future__ import annotations

import collections
import json
import time

import pytest

from philiprehberger_server_monitor import (
    Alert,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    Monitor,
    NetworkInfo,
    Snapshot,
    Trend,
)


def _make_snapshot(timestamp: float, cpu_pct: float = 10.0, mem_pct: float = 50.0) -> Snapshot:
    return Snapshot(
        timestamp=timestamp,
        cpu=CpuInfo(percent=cpu_pct, count=4, count_logical=8, per_cpu=[cpu_pct] * 4, freq_mhz=2400.0),
        memory=MemoryInfo(total=16 * 1024**3, available=8 * 1024**3, used=8 * 1024**3, percent=mem_pct),
        disk={"/": DiskInfo(mountpoint="/", total=100, used=40, free=60, percent=40.0)},
        network=NetworkInfo(bytes_sent=100, bytes_recv=200, packets_sent=1, packets_recv=2),
        load_avg=(0.1, 0.2, 0.3),
    )


def test_snapshot_returns_valid_types():
    snap = Monitor().snapshot()
    assert isinstance(snap, Snapshot)
    assert isinstance(snap.cpu, CpuInfo)
    assert isinstance(snap.memory, MemoryInfo)
    assert isinstance(snap.network, NetworkInfo)
    assert snap.timestamp > 0


def test_snapshot_to_dict_round_trips():
    snap = _make_snapshot(timestamp=1.0)
    d = snap.to_dict()
    assert d["cpu"]["percent"] == 10.0
    assert d["memory"]["percent"] == 50.0
    assert d["disk"]["/"]["percent"] == 40.0


def test_memory_gb_properties():
    mem = MemoryInfo(total=2 * 1024**3, available=1 * 1024**3, used=1 * 1024**3, percent=50.0)
    assert mem.total_gb == 2.0
    assert mem.used_gb == 1.0
    assert mem.available_gb == 1.0


def test_get_metric_value_two_part_path():
    monitor = Monitor()
    snap = _make_snapshot(timestamp=1.0, cpu_pct=42.5)
    assert monitor._get_metric_value(snap, "cpu.percent") == 42.5
    assert monitor._get_metric_value(snap, "memory.percent") == 50.0


def test_get_metric_value_three_part_disk_path():
    monitor = Monitor()
    snap = _make_snapshot(timestamp=1.0)
    assert monitor._get_metric_value(snap, "disk./.percent") == 40.0


def test_get_metric_value_unknown_returns_none():
    monitor = Monitor()
    snap = _make_snapshot(timestamp=1.0)
    assert monitor._get_metric_value(snap, "cpu.bogus") is None
    assert monitor._get_metric_value(snap, "ghost.field") is None


def test_snapshots_returns_copy_of_buffer():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    monitor._snapshots.append(_make_snapshot(timestamp=1.0))
    monitor._snapshots.append(_make_snapshot(timestamp=2.0))

    out = monitor.snapshots()
    assert len(out) == 2
    # Must be a defensive copy
    out.clear()
    assert len(monitor._snapshots) == 2


def test_export_json_round_trip(tmp_path):
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    monitor._snapshots.append(_make_snapshot(timestamp=1.0, cpu_pct=11.0))
    monitor._snapshots.append(_make_snapshot(timestamp=2.0, cpu_pct=22.0))

    path = tmp_path / "snapshots.json"
    monitor.export_json(path)

    data = json.loads(path.read_text())
    assert "snapshots" in data
    assert len(data["snapshots"]) == 2
    assert data["snapshots"][0]["cpu"]["percent"] == 11.0
    assert data["snapshots"][1]["cpu"]["percent"] == 22.0


def test_export_json_empty_buffer(tmp_path):
    path = tmp_path / "empty.json"
    Monitor().export_json(path)
    data = json.loads(path.read_text())
    assert data == {"snapshots": []}


def test_get_trend_computes_slope():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    now = time.time()
    monitor._snapshots.append(_make_snapshot(timestamp=now - 10, cpu_pct=10.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now, cpu_pct=30.0))

    trend = monitor.get_trend("cpu.percent", window_seconds=60)
    assert isinstance(trend, Trend)
    assert trend.start_value == 10.0
    assert trend.end_value == 30.0
    assert trend.duration_seconds == pytest.approx(10.0, abs=0.5)
    assert trend.slope == pytest.approx(2.0, abs=0.5)


def test_get_trend_raises_with_too_few_points():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    monitor._snapshots.append(_make_snapshot(timestamp=time.time(), cpu_pct=10.0))
    with pytest.raises(ValueError, match="at least 2"):
        monitor.get_trend("cpu.percent")


def test_average_cpu_within_window():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    now = time.time()
    monitor._snapshots.append(_make_snapshot(timestamp=now - 5, cpu_pct=20.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 3, cpu_pct=40.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 1, cpu_pct=60.0))

    assert monitor.average_cpu(window_seconds=60) == pytest.approx(40.0)


def test_average_memory_within_window():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    now = time.time()
    monitor._snapshots.append(_make_snapshot(timestamp=now - 5, mem_pct=30.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 3, mem_pct=50.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 1, mem_pct=70.0))

    assert monitor.average_memory(window_seconds=60) == pytest.approx(50.0)


def test_average_excludes_snapshots_outside_window():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    now = time.time()
    # Outside the 10s window
    monitor._snapshots.append(_make_snapshot(timestamp=now - 120, cpu_pct=99.0, mem_pct=99.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 100, cpu_pct=99.0, mem_pct=99.0))
    # Inside the 10s window
    monitor._snapshots.append(_make_snapshot(timestamp=now - 5, cpu_pct=10.0, mem_pct=20.0))
    monitor._snapshots.append(_make_snapshot(timestamp=now - 1, cpu_pct=30.0, mem_pct=40.0))

    assert monitor.average_cpu(window_seconds=10) == pytest.approx(20.0)
    assert monitor.average_memory(window_seconds=10) == pytest.approx(30.0)


def test_average_returns_zero_with_no_snapshots():
    monitor = Monitor()
    assert monitor.average_cpu() == 0.0
    assert monitor.average_memory() == 0.0


def test_average_returns_zero_when_all_snapshots_outside_window():
    monitor = Monitor()
    monitor._snapshots = collections.deque(maxlen=10)
    now = time.time()
    monitor._snapshots.append(_make_snapshot(timestamp=now - 500, cpu_pct=50.0, mem_pct=50.0))

    assert monitor.average_cpu(window_seconds=60) == 0.0
    assert monitor.average_memory(window_seconds=60) == 0.0


def test_alert_dataclass_defaults():
    fired: list[tuple[str, float, float]] = []
    alert = Alert(
        metric="cpu.percent",
        threshold=80.0,
        callback=lambda m, v, t: fired.append((m, v, t)),
    )
    assert alert._triggered is False
    alert.callback("cpu.percent", 90.0, 80.0)
    assert fired == [("cpu.percent", 90.0, 80.0)]
