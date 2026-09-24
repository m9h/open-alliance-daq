# Plan: open-source data from a Waters Alliance stack

## Goal

Record chromatograms from the e2695 / 2489 / 2424 stack with hardware and software that are
fully open, and integrate peaks without Empower.

## Why analog

The stack's digital ports are closed. Ethernet and IEEE-488 on the e2695 carry Waters'
proprietary instrument-control protocol, implemented only in Empower and the Waters driver
packs; no public specification or open implementation exists. The RS-232 ports on this
generation are service ports. Reverse-engineering the Ethernet protocol is possible in
principle but is a large project with no guarantee of completeness and no way to validate
against Waters' own data path.

Every module in the stack can nevertheless be operated **standalone from its own keypad**:
methods and sample sets on the e2695, wavelengths and output scaling on the 2489, gain and
nebulizer settings on the 2424. The detectors then present their signal on 0–2 V analog
outputs, and the e2695 raises a contact closure at every injection. That is the same path
third-party chromatography data systems (Clarity, Chromeleon with A/D box, ChromPerfect) use.
This project replaces their proprietary A/D box with a Raspberry Pi and an open ADC HAT.

## Design

```
 e2695 ──Inject Start──► optocoupler ──► GPIO 25 ─┐
 2489  ──Analog 1/2───► ADS1263 ch 0,1 ─────────┤   Raspberry Pi 4
 2424  ──Analog───────► ADS1263 ch 2 ───────────┤   alliance-daq record
 e2695 ──Chart Out────► ADS1263 ch 3 ───────────┘        │
                                                          ▼
                                        runs/<timestamp>_<label>.csv
                                                          │
                    alliance-daq quant (hplc-py)  /  alliance-daq peaks (quick look)
```

**ADC.** Waveshare High-Precision AD HAT, ADS1263, 32-bit, five differential inputs,
internal 2.5 V reference so full scale is ±2.5 V. At its 400 SPS internal rate with the
FIR filter, then decimated to 20 Hz by the logger, noise is roughly 1 µV. The 2489's own
specified noise floor at 1 V/AU is a few µV, so the ADC does not limit the measurement.

**Rate.** HPLC peaks on a 4.6 mm column are 3–20 s wide. 20 samples/s gives 60+ points across
the narrowest peak, which is more than integration algorithms need. `--rate` sets it.

**Trigger.** The Inject Start closure gives a hardware t0 accurate to the logger's loop
period (50 ms at 20 Hz). Retention-time repeatability is therefore limited by the instrument,
not the logger. `--count 0` re-arms after every run so a full sample set records unattended.

**File format.** One CSV per injection with `# key: value` metadata lines (label, start
time, rate, per-channel scaling and source), then `time_s` plus one column per channel in
native units. It reads with `pandas.read_csv(path, comment="#")` and into R with `read.csv(comment.char = "#")`.

**Analysis.** Two tiers, both open source and both in this repo's Python stack.

* `alliance-daq quant` is the method-grade path. It wraps
  [hplc-py](https://github.com/cremerlab/hplc-py) (Chure & Cremer, JOSS 2024), which fits a
  mixture of skew-normal peaks to the baseline-corrected signal. Overlapping peaks are
  resolved by deconvolution rather than split at a valley, known retention times can seed
  the fit, and the output is a peak table (retention time, amplitude, width, skew, area in
  signal-units × seconds) plus hplc-py's reconstruction figure. Calibration curves are a
  few lines of pandas on top of the peak tables.
* `alliance-daq peaks` is the quick look: asymmetric-least-squares baseline, SciPy peak
  detection with a noise-derived threshold, trapezoid integration. It needs nothing beyond
  SciPy and is what the tests and CI exercise first.

If an R workflow is preferred, [chromatographR](https://github.com/ethanbass/chromatographR)
(Bass, CRAN) covers the same ground for HPLC-UV/DAD: preprocessing, retention-time alignment
across many runs, Gaussian / exponential-Gaussian peak fitting, and peak-table construction.
Its alignment tools are the better choice once there are dozens of runs to compare. It reads
this project's CSVs directly.

**Reporting.** `alliance-daq report` renders a LaTeX PDF per run set: acquisition metadata,
channel map, small-multiple traces, each hplc-py fit with shaded components, and a peak table
(retention time, amplitude, width, skew, area, area %). Figures are vector PDF and the `.tex`
is kept, so a report can be hand-edited or rebuilt. It compiles with tectonic (no TeX Live
needed) or latexmk. For an R workflow, `r/report.Rnw` is a knitr template that does the same
with chromatographR (EGH peak fits); it reads the same CSVs and was verified against the
simulated run. chromatographR is installed from the author's r-universe, not CRAN. Pweave was considered and rejected: no release
since 2018 and it no longer imports against current IPython.

No desktop chromatography data system is part of the plan. The CSV format is deliberately
plain so any future tool can import it.

## Compute

**Acquisition runs on the Pi 4** (Fedora 44, the same kernel family). Its BCM2835 SPI
controller is fully supported and its device tree already carries the disabled `spi0` node
plus `spidev` children, so `dtparam=spi=on` is all it needs. The load is 20 SPI transactions
per second and a CSV append. **The Pi 5 (16 GB) is the analysis machine**: hplc-py fits,
reports, and the JAX work, reading the run CSVs from the Pi 4. See the Pi 5 note below for
why it is not the acquisition box yet.

**OS: Fedora.** Fedora is the lab's standard and the project targets it first. What differs
from Raspberry Pi OS, and how it is handled:

* `RPi.GPIO` does not work on Fedora (no `/dev/gpiomem`) and does not work on any Pi 5. The
  GPIO layer in `alliance_daq/gpio.py` uses libgpiod, so the same code runs on Fedora, on
  Raspberry Pi OS, and on Pi 4 or Pi 5. The chip is `/dev/gpiochip0` on Pi 4; on Pi 5 set
  `ALLIANCE_DAQ_GPIOCHIP` to whichever chip `gpiodetect` labels `pinctrl-rp1`.
* SPI is enabled through the Pi firmware's `config.txt` in `/boot/efi` (`dtparam=spi=on`),
  which Fedora's `bcm283x-firmware` package supports the same way Raspberry Pi OS does.
  `deploy/fedora-setup.sh` does this, plus udev rules for `/dev/spidev*` and `/dev/gpiochip*`.
* **Pi 5 cannot drive the HAT under Fedora today.** On the Pi 5 the header SPI lives in the
  RP1 I/O chip, and the mainline kernel describes RP1 through a device-tree overlay applied by
  the `rp1_pci` driver. As of the `pbrobinson/a64-kernel` 7.2.2 build (Fedora 44, checked
  2026-09-24) that overlay provides clocks, GPIO/pinctrl, PWM, I2C, Ethernet, USB and CSI, but
  **no SPI controller**, and `spi-dw-mmio` has no RP1 binding. `/dev/spidev*` therefore cannot
  exist, whatever `config.txt` says. RP1 GPIO does work (`/dev/gpiochip4`, compatible
  `raspberrypi,rp1-gpio`), so the trigger input would be fine; only SPI is missing. Revisit
  when RP1 SPI lands upstream (it is in the in-flight RP1 series from SUSE) and reaches that
  COPR; until then the Pi 5 is the analysis and reporting machine, not the acquisition one.

Raspberry Pi OS remains a supported fallback and needs only `raspi-config` to enable SPI.

## Steps

1. **Identify the fourth module** (photo 04). Read its front label. If it is a 2998 PDA,
   plan on its two analog channels only.
2. **Bench-test the DAQ** with the simulator: `alliance-daq record --simulate --trigger now
   --duration 200` then `alliance-daq peaks`. Confirms software before touching the HPLC.
3. **Wire the ADC** per `wiring.md`, one channel at a time, checking `alliance-daq live`
   against the detector display after each.
4. **Wire the trigger** and confirm with a manual injection that `record` starts on the
   pulse.
5. **Calibrate scaling** by setting the 2489 to a known output and reading it back; adjust
   `volts_per_unit` in the channel map.
6. **Record a standard** (e.g. caffeine or a uracil/toluene test mix) and compare retention
   time and area repeatability across five injections. Target: RT RSD < 0.2 %, area RSD
   < 1 % for a well-behaved peak. This is the acceptance test.
7. **Build the calibration curve** from `alliance-daq quant` peak tables over a standard
   dilution series; keep it as a CSV next to the runs.

## Out of scope for now

* Instrument control from the Pi. Would need the Waters protocol.
* PDA spectra. Only reachable through Empower.
* Mass detection. Not present in this stack.

## Bill of materials

| Item | Approx. cost |
|---|---|
| Raspberry Pi 4 (2 GB), case, PSU, 32 GB card | $60–80 |
| Waveshare High-Precision AD HAT (ADS1263) | $40 |
| PC817 optocouplers, resistors, proto board | $5 |
| Shielded twisted pair, ferrules, Phoenix-style plugs for the detector I/O blocks (3.5 mm pitch, 10/12-position) | $20 |
| **Total** | **≈ $130** |
