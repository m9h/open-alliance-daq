"""Minimal GPIO layer with two back-ends.

* ``RPi.GPIO`` on Raspberry Pi OS (what the Waveshare driver was written for).
* ``gpiod`` (libgpiod v2 Python bindings) everywhere else, e.g. Fedora on a Pi 4, where
  /dev/gpiomem does not exist and RPi.GPIO cannot work.  BCM numbering maps directly to
  line offsets on ``/dev/gpiochip0`` on Pi 4 and earlier; on Pi 5 use ``chip="/dev/gpiochip4"``.

Only what the ADS1263 driver and the trigger need: output write, input read, and a blocking
wait for a falling edge.
"""

from __future__ import annotations

import os
import time

LOW, HIGH = 0, 1


def backend_name() -> str:
    try:
        import RPi.GPIO  # noqa: F401

        return "rpi"
    except Exception:
        return "gpiod"


class RpiGpio:
    def __init__(self, outputs: dict[int, int], inputs: list[int]):
        import RPi.GPIO as GPIO

        self.G = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin, val in outputs.items():
            GPIO.setup(pin, GPIO.OUT, initial=val)
        for pin in inputs:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def write(self, pin: int, value: int) -> None:
        self.G.output(pin, value)

    def read(self, pin: int) -> int:
        return self.G.input(pin)

    def wait_falling(self, pin: int, timeout_s: float | None) -> bool:
        ms = None if timeout_s is None else int(timeout_s * 1000)
        return self.G.wait_for_edge(pin, self.G.FALLING, timeout=ms) is not None

    def close(self) -> None:
        self.G.cleanup()


class GpiodGpio:
    def __init__(self, outputs: dict[int, int], inputs: list[int], chip: str | None = None):
        import gpiod
        from gpiod.line import Bias, Direction, Edge, Value

        self._V = Value
        chip = chip or os.environ.get("ALLIANCE_DAQ_GPIOCHIP", "/dev/gpiochip0")
        cfg = {}
        for pin, val in outputs.items():
            cfg[pin] = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.ACTIVE if val else Value.INACTIVE)
        for pin in inputs:
            cfg[pin] = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING)
        self._req = gpiod.request_lines(chip, consumer="alliance-daq", config=cfg)
        self._inputs = set(inputs)

    def write(self, pin: int, value: int) -> None:
        self._req.set_value(pin, self._V.ACTIVE if value else self._V.INACTIVE)

    def read(self, pin: int) -> int:
        return 1 if self._req.get_value(pin) == self._V.ACTIVE else 0

    def wait_falling(self, pin: int, timeout_s: float | None) -> bool:
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if not self._req.wait_edge_events(remaining):
                return False
            for ev in self._req.read_edge_events():
                if ev.line_offset == pin:
                    return True
            if remaining == 0.0:
                return False

    def close(self) -> None:
        self._req.release()


def open_gpio(outputs: dict[int, int], inputs: list[int]):
    """Return an RpiGpio on Raspberry Pi OS, else a GpiodGpio."""
    if backend_name() == "rpi":
        return RpiGpio(outputs, inputs)
    return GpiodGpio(outputs, inputs)
