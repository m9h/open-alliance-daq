# Wiring

All pin numbers are read off the rear-panel legends in `photos/`. **Verify each one against
the physical label before connecting anything.** Power everything down while wiring.

## Waveshare ADS1263 HAT pin usage

The HAT's screw terminals expose AIN0–AIN9, AINCOM, AGND, 5 V, and GND. In differential
mode the pairs are:

| Channel | + | − |
|---|---|---|
| 0 | AIN0 | AIN1 |
| 1 | AIN2 | AIN3 |
| 2 | AIN4 | AIN5 |
| 3 | AIN6 | AIN7 |
| 4 | AIN8 | AIN9 |

The HAT uses Pi SPI0 (CE0), GPIO 17 (DRDY), GPIO 18 (RST), GPIO 22 (CS). Those are taken.
GPIO 25 is used here for the Inject Start trigger; any free GPIO works (`--trigger-pin`).

## Analog signals

Use shielded twisted pair for every channel. Tie each cable's shield to AGND on the HAT
**at the HAT end only**. Do not connect the shield at the instrument end.

| Signal | Instrument terminal | HAT terminal | Default channel |
|---|---|---|---|
| 2489 Analog 1 Out + | block I pin 1 | AIN0 | `uv1` |
| 2489 Analog 1 Out − | block I pin 2 | AIN1 | |
| 2489 Analog 2 Out + | block I pin 4 | AIN2 | `uv2` |
| 2489 Analog 2 Out − | block I pin 5 | AIN3 | |
| 2424 ELSD Analog Out + | ELSD block I pin 1 (confirm on its label) | AIN4 | `els` |
| 2424 ELSD Analog Out − | ELSD block I pin 2 (confirm) | AIN5 | |
| e2695 Chart Out + | block B pin 11 | AIN6 | `pressure` |
| e2695 Chart Out − | block B pin 12 | AIN7 | |
| Signal ground | block I pin 3 (2489) | AGND | one instrument only |

Connect **one** instrument signal ground (2489 block I pin 3) to the HAT's AGND so the
differential inputs stay inside the ADC's common-mode range. Do not ground the others; the
instruments already share a chassis ground through their mains cords.

The second optical detector (photo 04) has the same block-I layout as the 2489. If you want
its output too, the fifth pair (AIN8/AIN9) is free.

## Detector output settings

On the 2489 keypad set Analog 1 and Analog 2 output to a known volts-per-AU (e.g. 1.000 AU
full scale = 2 V, so `volts_per_unit = 2.0`; or 2.000 AU full scale so `volts_per_unit = 1.0`).
Put the same number in `config/channels.example.toml`. Set the output time constant to
0.5–1 s to match a 20 Hz sample rate. Set Chart Out on the e2695 to *System Pressure*
(2 V full scale is 5000 psi on the 2695 series; check the value your firmware reports).

## Inject Start trigger (hardware t0)

The e2695's Inject Start output on block B pins 1 (+) and 2 (−) closes at each injection.
Waters specifies it as a contact closure; confirm with a meter that it is a closure and not a
voltage source before connecting.

Isolate it with a PC817 optocoupler so no current path exists between the instrument I/O
ground and the Pi:

```
e2695 B1 (+) ──[1 kΩ]──► PC817 anode (pin 1)
e2695 B2 (−) ───────────► PC817 cathode (pin 2)
       Pi 3V3 ──[10 kΩ]──┬── PC817 collector (pin 4) ── GPIO 25
       Pi GND ───────────┴── PC817 emitter (pin 3)
```

If B1/B2 is a dry contact rather than a source, supply the LED side from the HAT's 5 V:
`5 V ──[1 kΩ]── B1`, `B2 ── PC817 anode`, `PC817 cathode ── GND`. Either way GPIO 25 is
pulled high and goes low on injection, which is what `GpioTrigger` expects.

Optional: wire *Run Stopped* (block A pins 11/12) the same way to a second GPIO if you want
runs to end on the instrument's method time rather than on `--duration`.

## Grounding and power

* Power the Pi from its own isolated USB-C supply, not from a bench supply shared with the
  HPLC.
* Keep the analog cable bundle away from the e2695's mains cord and the ELSD gas line.
* First test: with detectors idle and pump at flow, run `alliance-daq live --rate 2`. Each
  channel should sit within a few hundred µV of the number on the detector's own display,
  and should not drift when you touch the cable shield.
