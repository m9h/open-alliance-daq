# Instrument identification

Identified from the five photos in `photos/`, plus Waters part-number lookups.

| Photo | Module | Evidence | Rear I/O |
|---|---|---|---|
| 01-front-stack | **Alliance e2695 Separations Module** (pump + autosampler + column heater) | front label "Waters e2695 Separations Module", asset tag RAM-502143 | see photo 03 |
| 02-rear-2489-uvvis | **2489 UV/Visible detector** | REF 186248900 (Waters/UVISON list this as the 2489), SN H1987E894A, "Nitrogen purge max 20 psi", 200 VA, F5A fuse, Product of Singapore | blocks I/II, RS-232, Ethernet |
| 03-rear-e2695-io | e2695 rear | I/O connectors A and B, RS-232, Ethernet, IEEE-488, 950 VA | contact-closure I/O + Chart Out |
| 04-rear-second-detector-io | **second optical detector, model unconfirmed** | same I/O legend as the 2489 (Analog 1/2 Out, Switch 1/2, Inject Start, Lamp On/Off, Chart Mark, Auto Zero) but 195 VA, F3.15A fuse; REF label not in frame | blocks I/II, RS-232, Ethernet |
| 05-rear-2424-elsd | **2424 Evaporative Light Scattering detector** | REF 186017005 (Waters Driver Pack release notes list this as the 2424 ELS Detector), SN L19VEL166M, GAS 100 psi max, EXHAUST hose, Product of USA | analog out on its own I/O block (not photographed) |

## Open question

Photo 04's module is either a second 2489 or a 2998 PDA. Both share this I/O legend. The
power rating (195 VA vs 200 VA) argues for a different model. Read its front-panel label or
the REF sticker on the rear. If it is a 2998 PDA, only its two analog channels are reachable
from outside; the spectral data never leaves Empower.

## Which ports are usable

| Port | On | Status for open-source use |
|---|---|---|
| Analog 1 / Analog 2 Out (block I) | 2489, second detector | **Usable.** 0–2 V differential, scaled by the detector's AU full-scale setting |
| Analog Out | 2424 ELSD | **Usable.** 0–2 V |
| Chart Out (B11/B12) | e2695 | **Usable.** 0–2 V analog of pressure, flow, or column temperature (set on the keypad) |
| Inject Start (B1/B2) | e2695 | **Usable.** Contact closure at every injection; hardware t0 |
| Run Stopped (A11/A12), Stop Flow, Hold Inject, Switch 1–4 | e2695 | Usable contact-closure I/O for sync and safety |
| Ethernet | all | Proprietary Waters instrument-control protocol, Empower/driver-pack only. No public spec |
| IEEE-488 | e2695 | Legacy busLAC/E protocol, also proprietary |
| RS-232 | e2695, detectors | Service/firmware port on this generation, not a data port |

## References

* [UVISON: Waters 2489 UV/Visible detector, 186248900](https://uvison.com/chromatography-supplies/waters-hplc-columns-spare-parts/waters-hplc-uplc-alliance-ms-spare-parts/waters-hplc-spare-parts/waters-2489-uv-visible-detector-blue-186248900)
* [Waters 2489 Operator's Manual (ManualsLib)](https://www.manualslib.com/manual/2574772/Waters-2489.html)
* [Waters Driver Pack 2023 R1 release notes, 186017005 = 2424 ELS Detector](https://help.waters.com/content/dam/waters/en/support/releasenotes/2024/715008470/715008470v04.pdf)
