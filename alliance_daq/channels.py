"""Channel map: which ADC pair carries which instrument signal, and how to scale it.

Loaded from a TOML file (see config/channels.example.toml).  Each channel has:

name            column name in the CSV
adc_channel     differential pair on the HAT, 0-4
volts_per_unit  detector output scaling, e.g. 1.0 when the 2489 is set to 1 V/AU
unit            label for the scaled value ("AU", "mV", "psi", ...)
offset_volts    subtracted before scaling (detector analog offset, if any)
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    name: str
    adc_channel: int
    volts_per_unit: float = 1.0
    unit: str = "V"
    offset_volts: float = 0.0
    source: str = ""

    def scale(self, volts: float) -> float:
        return (volts - self.offset_volts) / self.volts_per_unit


@dataclass
class ChannelMap:
    channels: list[Channel] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "ChannelMap":
        data = tomllib.loads(Path(path).read_text())
        chans = [Channel(**c) for c in data.get("channel", [])]
        cls._validate(chans)
        return cls(chans)

    @staticmethod
    def _validate(chans: list[Channel]) -> None:
        names = [c.name for c in chans]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate channel names: {names}")
        pairs = [c.adc_channel for c in chans]
        if len(set(pairs)) != len(pairs):
            raise ValueError(f"an ADC pair is used twice: {pairs}")
        bad = [p for p in pairs if not 0 <= p <= 4]
        if bad:
            raise ValueError(f"adc_channel must be 0-4, got {bad}")

    @property
    def adc_channels(self) -> list[int]:
        return [c.adc_channel for c in self.channels]

    @property
    def names(self) -> list[str]:
        return [c.name for c in self.channels]


DEFAULT_MAP = ChannelMap([
    Channel("uv1", 0, 1.0, "AU", source="2489 Analog 1"),
    Channel("uv2", 1, 1.0, "AU", source="2489 Analog 2"),
    Channel("els", 2, 1.0, "V", source="2424 Analog 1"),
    Channel("pressure", 3, 2.0 / 5000.0, "psi", source="e2695 Chart Out"),
])
