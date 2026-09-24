"""Run-start triggers.

The e2695 pulses its *Inject Start* output (I/O block B, pins 1-2) at every injection.
Wire that closure to a Raspberry Pi GPIO (see docs/wiring.md) and the logger will
time-stamp t0 from hardware rather than from a keypress.
"""

from __future__ import annotations

import time
from typing import Protocol


class Trigger(Protocol):
    def wait(self, timeout: float | None = None) -> bool:
        """Block until a trigger edge arrives.  Return False on timeout."""

    def close(self) -> None: ...


class ImmediateTrigger:
    """Fires as soon as it is waited on.  For manual starts and tests."""

    def wait(self, timeout: float | None = None) -> bool:
        return True

    def close(self) -> None:
        pass


class KeyboardTrigger:
    """Fires when the operator presses Enter."""

    def wait(self, timeout: float | None = None) -> bool:
        input("Press Enter at the moment of injection... ")
        return True

    def close(self) -> None:
        pass


class GpioTrigger:
    """Fires on a falling edge of a pulled-up GPIO, i.e. a contact closure to ground.

    Uses :mod:`alliance_daq.gpio`, so it works with RPi.GPIO on Raspberry Pi OS and with
    libgpiod on other distributions.  Inject Start is a clean pulse >= 100 ms, so no extra
    debounce is applied beyond the kernel's edge detection.
    """

    def __init__(self, pin: int):
        from .gpio import open_gpio

        self._pin = pin
        self._gpio = open_gpio({}, [pin])

    def wait(self, timeout: float | None = None) -> bool:
        return self._gpio.wait_falling(self._pin, timeout)

    def close(self) -> None:
        self._gpio.close()


class TimedTrigger:
    """Fires after a fixed delay.  Used by the simulator to mimic an autosampler."""

    def __init__(self, delay_s: float):
        self._delay = delay_s

    def wait(self, timeout: float | None = None) -> bool:
        time.sleep(self._delay if timeout is None else min(self._delay, timeout))
        return timeout is None or self._delay <= timeout

    def close(self) -> None:
        pass
