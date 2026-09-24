"""Acquisition loop: wait for a trigger, sample at a fixed rate, write one CSV per run.

CSV layout::

    # open-alliance-daq run
    # started: 2026-09-23T15:04:05
    # rate_hz: 20
    # channel uv1: adc=0 volts_per_unit=1.0 unit=AU source=2489 Analog 1
    time_s,uv1,uv2,els,pressure
    0.000,0.001234,...

Comment lines carry metadata; ``pandas.read_csv(path, comment="#")`` reads the table.
"""

from __future__ import annotations

import csv
import datetime as dt
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .adc import Adc
from .channels import ChannelMap
from .trigger import Trigger


@dataclass
class RunResult:
    path: Path
    samples: int
    duration_s: float


class RunLogger:
    def __init__(
        self,
        adc: Adc,
        channels: ChannelMap,
        rate_hz: float = 20.0,
        out_dir: str | Path = "runs",
        clock: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if rate_hz <= 0:
            raise ValueError("rate_hz must be positive")
        self.adc = adc
        self.channels = channels
        self.rate_hz = rate_hz
        self.out_dir = Path(out_dir)
        self._clock = clock
        self._sleep = sleep
        self.stop_requested = False

    def _header_lines(self, started: dt.datetime, label: str) -> list[str]:
        lines = [
            "# open-alliance-daq run",
            f"# label: {label}",
            f"# started: {started.isoformat(timespec='seconds')}",
            f"# rate_hz: {self.rate_hz:g}",
        ]
        for c in self.channels.channels:
            lines.append(
                f"# channel {c.name}: adc={c.adc_channel} volts_per_unit={c.volts_per_unit:g} "
                f"unit={c.unit} offset_volts={c.offset_volts:g} source={c.source}"
            )
        return lines

    def record(self, duration_s: float, label: str = "run", on_start: Callable[[], None] | None = None) -> RunResult:
        """Sample for ``duration_s`` starting now.  ``on_start`` runs at t0 (used by the simulator)."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        started = dt.datetime.now()
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in label)
        path = self.out_dir / f"{started:%Y%m%d-%H%M%S}_{safe}.csv"
        period = 1.0 / self.rate_hz
        n_total = int(round(duration_s * self.rate_hz))
        adc_chans = self.channels.adc_channels
        n = 0
        with path.open("w", newline="") as fh:
            for line in self._header_lines(started, label):
                fh.write(line + "\n")
            writer = csv.writer(fh)
            writer.writerow(["time_s", *self.channels.names])
            if on_start:
                on_start()
            t0 = self._clock()
            while n < n_total and not self.stop_requested:
                target = t0 + n * period
                now = self._clock()
                if target > now:
                    self._sleep(target - now)
                volts = self.adc.read(adc_chans)
                t = self._clock() - t0
                writer.writerow([f"{t:.3f}", *(f"{c.scale(v):.7g}" for c, v in zip(self.channels.channels, volts))])
                n += 1
        return RunResult(path, n, n / self.rate_hz)

    def run_triggered(self, trigger: Trigger, duration_s: float, label: str = "run", timeout_s: float | None = None) -> RunResult | None:
        """Wait for ``trigger``, then record.  Returns None if the trigger timed out."""
        if not trigger.wait(timeout_s):
            return None
        on_start = getattr(self.adc, "start_run", None)
        return self.record(duration_s, label, on_start=on_start)
