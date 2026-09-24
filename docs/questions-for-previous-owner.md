# Questions for the previous owner

This stack was donated. Everything in `plan.md` and `wiring.md` was worked out from the
rear-panel photos and Waters part numbers; the items below can only be answered by someone
who ran the system. Answers can go straight into this file or as GitHub issues.

## Identity and history

1. What is the module in [photo 04](photos/04-rear-second-detector-io.jpg)? It has the
   2489's I/O legend but a 195 VA / F3.15 A rating. Second 2489, 2998 PDA, or something else?
2. Was the system run under Empower? If so, was the e2695 controlled over Ethernet or IEEE-488,
   and was there a busLAC/E card or an Ethernet switch in the loop? (Tells us how the
   modules were last configured.)
3. Firmware versions on the e2695 and the detectors, if known. The e2695 shows it under
   Menu/Status → Configure.
4. Any known faults: seal wear, lamp hours on the 2489, ELSD nebulizer condition, pressure
   transducer offset, autosampler needle or syringe issues.
5. When was the last PM, and what columns and mobile phases were run last? (Residual buffer
   salts matter before the first flush.)

## I/O and wiring

6. Were the detectors' analog outputs ever used? If yes, what full-scale (AU/V) and offset
   were set, and did anything else share the I/O blocks?
7. Is the e2695 *Inject Start* output (block B pins 1/2) a dry contact closure or does it source
   a voltage? Our optocoupler circuit handles both but it changes the LED-side wiring.
8. Which e2695 I/O lines were wired to which detector inputs (the Inject Start daisy-chain to
   the 2489's block II, etc.)? Any cables still attached are the best evidence.
9. Was Chart Out on the e2695 configured, and to what (pressure, flow, temperature)?
10. The 2424 ELSD's I/O block was not photographed. Which pins carry its analog output, and
    what nebulizer gas and pressure were used?

## Operation

11. Typical methods run on this stack: flow rate, column, temperature, detection wavelengths.
    A known-good method is the fastest acceptance test for the DAQ.
12. Any front-panel quirks, e.g. settings that don't survive a power cycle, or a keypad
    sequence needed to run sample sets standalone without Empower.
13. Is there an Empower project export or printed report from this system? Even a single
    chromatogram with peak areas lets us validate the open integrator against Waters'.
