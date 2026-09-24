"""Vendored Waveshare High-Precision AD HAT (ADS1263) driver.

Source: https://github.com/waveshareteam/High-Pricision_AD_HAT (MIT, (c) 2021 waveshare).
Local changes: ``import config`` -> ``from . import config``; the RPi.GPIO import is replaced by
a two-constant shim and config.py gains a ``PortableGpio`` backend that drives the pins through
``alliance_daq.gpio`` (RPi.GPIO on Raspberry Pi OS, libgpiod elsewhere, e.g. Fedora).
"""
