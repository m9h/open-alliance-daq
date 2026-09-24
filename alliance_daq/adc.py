"""ADC back-ends.

Two implementations share one tiny interface:

* :class:`ADS1263Adc` drives the Waveshare High-Precision AD HAT on a Raspberry Pi
  through the vendored Waveshare driver.
* :class:`SimulatedAdc` synthesises a chromatogram so the logger and analysis code
  can be exercised on any machine.

Both return **volts** per differential channel.  Differential channel ``i`` on the HAT
is the pair ``AIN(2i)`` / ``AIN(2i+1)``, so there are five channels, 0-4.
"""

from __future__ import annotations

import math
import random
import time
from typing import Protocol, Sequence


class Adc(Protocol):
    def read(self, channels: Sequence[int]) -> list[float]:
        """Return one voltage per requested differential channel."""

    def close(self) -> None: ...


class ADS1263Adc:
    """Waveshare ADS1263 HAT, ADC1, differential mode, internal 2.5 V reference.

    The Waveshare driver defaults to the 5 V analog supply as reference (REFMUX 0x24).
    For 0-2 V detector outputs the internal 2.5 V reference is quieter and more stable,
    so it is selected here after init.  The full-scale input is then +/-2.5 V, which
    covers every analog output in the Alliance stack.
    """

    REF_VOLTS = 2.5
    _RATE_NAMES = {
        2.5: "ADS1263_2d5SPS", 5: "ADS1263_5SPS", 10: "ADS1263_10SPS",
        16.6: "ADS1263_16d6SPS", 20: "ADS1263_20SPS", 50: "ADS1263_50SPS",
        60: "ADS1263_60SPS", 100: "ADS1263_100SPS", 400: "ADS1263_400SPS",
    }

    def __init__(self, adc_rate_sps: float = 400):
        # Imports here so the module is importable off-Pi.
        from .vendor.waveshare import ADS1263

        self._mod = ADS1263
        self._adc = ADS1263.ADS1263()
        rate = self._RATE_NAMES.get(adc_rate_sps)
        if rate is None:
            raise ValueError(f"unsupported ADC rate {adc_rate_sps}; choose from {sorted(self._RATE_NAMES)}")
        if self._adc.ADS1263_init_ADC1(rate) == -1:
            raise RuntimeError("ADS1263 init failed (chip ID mismatch). Check SPI is enabled and the HAT is seated.")
        self._adc.ADS1263_SetMode(1)  # differential pairs
        self._adc.ADS1263_WriteReg(ADS1263.ADS1263_REG["REG_REFMUX"], 0x00)  # internal 2.5 V ref

    def read(self, channels: Sequence[int]) -> list[float]:
        out = []
        for ch in channels:
            raw = self._adc.ADS1263_GetChannalValue(ch)
            out.append(self._raw_to_volts(raw))
        return out

    @classmethod
    def _raw_to_volts(cls, raw: int) -> float:
        # 32-bit two's complement, full scale = +/-REF (gain 1).
        if raw & 0x80000000:
            raw -= 1 << 32
        return raw * cls.REF_VOLTS / 0x7FFFFFFF

    def close(self) -> None:
        self._adc.ADS1263_Exit()


class SimulatedAdc:
    """Synthetic detector signals for testing without hardware.

    Channel 0 and 1 carry a three-peak chromatogram (UV-like, volts), channel 2 an
    ELSD-like response to the same peaks, channel 3 a slowly drifting 'pressure'.
    ``t0`` is set when :meth:`start_run` is called; before that the outputs sit at baseline.
    """

    PEAKS = [  # (retention time s, height V, sigma s)
        (60.0, 0.80, 2.5),
        (95.0, 1.40, 3.0),
        (140.0, 0.45, 4.0),
    ]

    def __init__(self, noise_v: float = 20e-6, seed: int | None = 0, clock=time.monotonic):
        self._rng = random.Random(seed)
        self._noise = noise_v
        self._clock = clock
        self._t0: float | None = None

    def start_run(self) -> None:
        self._t0 = self._clock()

    def _signal(self, t: float) -> float:
        return sum(h * math.exp(-0.5 * ((t - rt) / s) ** 2) for rt, h, s in self.PEAKS)

    def read(self, channels: Sequence[int]) -> list[float]:
        t = 0.0 if self._t0 is None else self._clock() - self._t0
        s = self._signal(t) if self._t0 is not None else 0.0
        vals = {
            0: 0.002 + s,
            1: 0.001 + 0.6 * s,
            2: 0.005 + 0.3 * s * s,
            3: 1.20 + 0.02 * math.sin(t / 30.0),
            4: 0.0,
        }
        return [vals.get(c, 0.0) + self._rng.gauss(0.0, self._noise) for c in channels]

    def close(self) -> None:
        pass
