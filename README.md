# open-alliance-daq

Open-source data acquisition for a Waters Alliance HPLC stack: **e2695 Separations Module,
2489 UV/Vis detector, 2424 Evaporative Light Scattering detector**, plus a second optical
detector. No Empower, no Waters drivers. A Raspberry Pi 4 with a 32-bit ADC HAT records
the detectors' analog outputs, the e2695's Inject Start pulse provides hardware t0, and
Python integrates the peaks.

* [docs/plan.md](docs/plan.md) — why analog, what the closed ports are, the full design
* [docs/wiring.md](docs/wiring.md) — pin-by-pin wiring from the rear-panel photos
* [docs/instrument-identification.md](docs/instrument-identification.md) — what each module is, with evidence
* [docs/photos/](docs/photos/) — the rear-panel photos the plan is based on

## Hardware

| Item | Notes |
|---|---|
| Raspberry Pi 4 (2 GB is plenty) | Pi OS Bookworm 64-bit, SPI enabled |
| Waveshare High-Precision AD HAT (ADS1263) | 5 differential channels, 32-bit, open schematic |
| PC817 optocoupler + 1 kΩ + 10 kΩ | isolates the e2695 Inject Start closure from the Pi GPIO |
| Shielded twisted pair, 22–24 AWG | one pair per analog channel |
| Isolated 5 V USB-C supply for the Pi | breaks the mains ground loop |

## Quick start (no hardware)

```bash
uv venv && uv pip install -e '.[dev]'
uv run alliance-daq record --simulate --trigger now --duration 200 --label demo
uv run alliance-daq peaks runs/*_demo.csv
uv run pytest
```

## On the Pi

```bash
sudo raspi-config nonint do_spi 0          # enable SPI
uv pip install -e '.[pi]'
alliance-daq live --rate 2                 # check every channel reads what the front panel shows
alliance-daq record --duration 900 --label std-mix --count 0   # arm; each Inject Start pulse starts a 15 min run
```

Edit `config/channels.example.toml` to match your detector output scaling and pass it
with `--channels`. Each run lands in `runs/` as a CSV with metadata comment lines;
`pandas.read_csv(path, comment="#")` reads it, and OpenChrom or hplc-py can take it from there.

## Layout

```
alliance_daq/
  adc.py         ADS1263 back-end and a synthetic-chromatogram simulator
  trigger.py     Inject Start GPIO trigger (gpiozero), keyboard, timed, immediate
  channels.py    TOML channel map and unit scaling
  logger.py      fixed-rate acquisition loop -> CSV with metadata header
  analysis.py    ALS baseline, peak finding, trapezoid integration
  cli.py         alliance-daq record | live | peaks
  vendor/waveshare/   Waveshare's MIT ADS1263 driver, one import line patched
```

## License

MIT. The vendored Waveshare driver is also MIT; see `alliance_daq/vendor/waveshare/LICENSE`.
