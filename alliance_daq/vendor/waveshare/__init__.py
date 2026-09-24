"""Vendored Waveshare High-Precision AD HAT (ADS1263) driver.

Source: https://github.com/waveshareteam/High-Pricision_AD_HAT (MIT, (c) 2021 waveshare).
Local change: ``import config`` -> ``from . import config`` so it works as a package.
Imports RPi.GPIO and spidev at module load, so only import this on a Raspberry Pi.
"""
