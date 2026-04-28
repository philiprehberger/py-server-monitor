"""System metrics collector for CPU, memory, disk, and network."""

from __future__ import annotations

import collections
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import psutil

__all__ = [
    "Monitor",
    "Snapshot",
    "CpuInfo",
    "MemoryInfo",
    "DiskInfo",
    "NetworkInfo",
    "Alert",
    "Trend",
]


@dataclass
class CpuInfo:
    """CPU metrics."""

    percent: float
    count: int
    count_logical: int
    per_cpu: list[float]
    freq_mhz: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "percent": self.percent,
            "count": self.count,
            "count_logical": self.count_logical,
            "per_cpu": self.per_cpu,
            "freq_mhz": self.freq_mhz,
        }


@dataclass
class MemoryInfo:
    """Memory metrics."""

    total: int
    available: int
    used: int
    percent: float

    @property
    def total_gb(self) -> float:
        return self.total / (1024 ** 3)

    @property
    def used_gb(self) -> float:
        return self.used / (1024 ** 3)

    @property
    def available_gb(self) -> float:
        return self.available / (1024 ** 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "available": self.available,
            "used": self.used,
            "percent": self.percent,
            "total_gb": round(self.total_gb, 2),
            "used_gb": round(self.used_gb, 2),
        }


@dataclass
class DiskInfo:
    """Disk metrics for a single mount point."""

    mountpoint: str
    total: int
    used: int
    free: int
    percent: float

    @property
    def total_gb(self) -> float:
        return self.total / (1024 ** 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mountpoint": self.mountpoint,
            "total": self.total,
            "used": self.used,
            "free": self.free,
            "percent": self.percent,
        }


@dataclass
class NetworkInfo:
    """Network metrics."""

    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "packets_sent": self.packets_sent,
            "packets_recv": self.packets_recv,
        }


@dataclass
class Snapshot:
    """A point-in-time system metrics snapshot."""

    timestamp: float
    cpu: CpuInfo
    memory: MemoryInfo
    disk: dict[str, DiskInfo]
    network: NetworkInfo
    load_avg: tuple[float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu": self.cpu.to_dict(),
            "memory": self.memory.to_dict(),
            "disk": {k: v.to_dict() for k, v in self.disk.items()},
            "network": self.network.to_dict(),
            "load_avg": self.load_avg,
        }


@dataclass
class Alert:
    """Threshold-based alert configuration."""

    metric: str  # e.g., "cpu.percent", "memory.percent", "disk./.percent"
    threshold: float
    callback: Callable[[str, float, float], None]  # (metric, value, threshold)
    _triggered: bool = field(default=False, repr=False)


@dataclass
class Trend:
    """Result of a trend analysis over a time window."""

    metric: str
    start_value: float
    end_value: float
    slope: float
    duration_seconds: float


class Monitor:
    """System metrics monitor."""

    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._recording = False
        self._record_thread: threading.Thread | None = None
        self._snapshots: collections.deque[Snapshot] = collections.deque()

    def snapshot(self) -> Snapshot:
        """Take a single point-in-time snapshot of system metrics."""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per = psutil.cpu_percent(interval=0, percpu=True)
        cpu_count = psutil.cpu_count(logical=False) or 0
        cpu_count_logical = psutil.cpu_count(logical=True) or 0
        freq = psutil.cpu_freq()
        cpu = CpuInfo(
            percent=cpu_percent,
            count=cpu_count,
            count_logical=cpu_count_logical,
            per_cpu=cpu_per,
            freq_mhz=freq.current if freq else None,
        )

        # Memory
        mem = psutil.virtual_memory()
        memory = MemoryInfo(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            percent=mem.percent,
        )

        # Disk
        disk: dict[str, DiskInfo] = {}
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk[part.mountpoint] = DiskInfo(
                    mountpoint=part.mountpoint,
                    total=usage.total,
                    used=usage.used,
                    free=usage.free,
                    percent=usage.percent,
                )
            except PermissionError:
                continue

        # Network
        net = psutil.net_io_counters()
        network = NetworkInfo(
            bytes_sent=net.bytes_sent,
            bytes_recv=net.bytes_recv,
            packets_sent=net.packets_sent,
            packets_recv=net.packets_recv,
        )

        # Load average (not available on Windows)
        load_avg = None
        try:
            load_avg = psutil.getloadavg()
        except (AttributeError, OSError):
            pass

        return Snapshot(
            timestamp=time.time(),
            cpu=cpu,
            memory=memory,
            disk=disk,
            network=network,
            load_avg=load_avg,
        )

    def _get_metric_value(self, snapshot: Snapshot, metric: str) -> float | None:
        """Extract a metric value from a snapshot using dot notation."""
        parts = metric.split(".")
        if len(parts) == 2:
            section, key = parts
            obj = getattr(snapshot, section, None)
            if obj is None:
                return None
            return getattr(obj, key, None)
        elif len(parts) == 3:
            section, name, key = parts
            if section == "disk":
                disk_info = snapshot.disk.get(name) or snapshot.disk.get(f"/{name}")
                if disk_info:
                    return getattr(disk_info, key, None)
        return None

    def watch(
        self,
        interval: float = 5.0,
        on_snapshot: Callable[[Snapshot], None] | None = None,
        alerts: list[Alert] | None = None,
        background: bool = False,
    ) -> None:
        """Continuously monitor system metrics.

        Args:
            interval: Seconds between snapshots.
            on_snapshot: Callback for each snapshot.
            alerts: List of Alert configurations.
            background: If True, run in a background thread.
        """
        self._running = True
        alerts = alerts or []

        def loop() -> None:
            while self._running:
                snap = self.snapshot()
                if on_snapshot:
                    on_snapshot(snap)

                for alert in alerts:
                    value = self._get_metric_value(snap, alert.metric)
                    if value is not None and value >= alert.threshold:
                        if not alert._triggered:
                            alert.callback(alert.metric, value, alert.threshold)
                            alert._triggered = True
                    else:
                        alert._triggered = False

                time.sleep(interval)

        if background:
            self._thread = threading.Thread(target=loop, daemon=True)
            self._thread.start()
        else:
            try:
                loop()
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stop continuous monitoring."""
        self._running = False

    def start_recording(
        self,
        interval: float = 5.0,
        max_snapshots: int = 720,
    ) -> None:
        """Start a background thread that records snapshots at regular intervals.

        Args:
            interval: Seconds between snapshots.
            max_snapshots: Maximum number of snapshots to keep in the ring buffer.
        """
        if self._recording:
            return
        self._snapshots = collections.deque(maxlen=max_snapshots)
        self._recording = True

        def record_loop() -> None:
            while self._recording:
                self._snapshots.append(self.snapshot())
                time.sleep(interval)

        self._record_thread = threading.Thread(target=record_loop, daemon=True)
        self._record_thread.start()

    def stop_recording(self) -> None:
        """Stop the recording thread."""
        self._recording = False

    def snapshots(self) -> list[Snapshot]:
        """Return a copy of the recorded snapshot ring buffer.

        Safe to call while a recorder is running — the returned list is a
        snapshot of the buffer at call time.
        """
        return list(self._snapshots)

    def export_json(self, path: str | Path) -> None:
        """Write the recorded snapshots to a JSON file.

        Each snapshot is serialised via ``Snapshot.to_dict()``. Existing files
        are overwritten.

        Args:
            path: Destination file path.
        """
        out_path = Path(path)
        payload = {"snapshots": [s.to_dict() for s in self._snapshots]}
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_trend(self, metric: str, window_seconds: float = 300) -> Trend:
        """Compute a linear trend for a metric over recent snapshots.

        Args:
            metric: Dot-notation metric name (e.g., "cpu.percent", "memory.percent").
            window_seconds: How far back to look, in seconds.

        Returns:
            A Trend object with start/end values and slope (change per second).

        Raises:
            ValueError: If there are fewer than 2 data points in the window.
        """
        now = time.time()
        cutoff = now - window_seconds

        points: list[tuple[float, float]] = []
        for snap in self._snapshots:
            if snap.timestamp >= cutoff:
                value = self._get_metric_value(snap, metric)
                if value is not None:
                    points.append((snap.timestamp, value))

        if len(points) < 2:
            raise ValueError(
                f"Not enough data points for metric '{metric}': "
                f"need at least 2, got {len(points)}"
            )

        first_t, first_v = points[0]
        last_t, last_v = points[-1]
        duration = last_t - first_t

        if duration == 0:
            slope = 0.0
        else:
            slope = (last_v - first_v) / duration

        return Trend(
            metric=metric,
            start_value=first_v,
            end_value=last_v,
            slope=slope,
            duration_seconds=duration,
        )
