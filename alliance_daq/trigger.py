"""Run-start triggers.

The e2695 pulses its *Inject Start* output (I/O block B, pins 1-2) at every injection.
Wire that closure to a Raspberry Pi GPIO (see docs/wiring.md) and the logger will
time-stamp t0 from hardware rather than from a keypress.
"""

from __future__ import annotations

import threading
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

    Uses gpiozero, which works on Pi 4 (RPi.GPIO backend) and Pi 5 (lgpio backend).
    ``bounce_s`` suppresses relay chatter; Inject Start is a clean pulse >= 100 ms.
    """

    def __init__(self, pin: int, bounce_s: float = 0.05):
        from gpiozero import Button

        self._btn = Button(pin, pull_up=True, bounce_time=bounce_s)
        self._event = threading.Event()
        self._btn.when_pressed = self._event.set

    def wait(self, timeout: float | None = None) -> bool:
        self._event.clear()
        return self._event.wait(timeout)

    def close(self) -> None:
        self._btn.close()


class TimedTrigger:
    """Fires after a fixed delay.  Used by the simulator to mimic an autosampler."""

    def __init__(self, delay_s: float):
        self._delay = delay_s

    def wait(self, timeout: float | None = None) -> bool:
        time.sleep(self._delay if timeout is None else min(self._delay, timeout))
        return timeout is None or self._delay <= timeout

    def close(self) -> None:
        pass
