"""Generate docs/wiring.svg.  Run: python docs/tools/make_wiring_svg.py

Coordinates are explicit so the drawing can be adjusted in one place; the SVG is
committed so GitHub renders it without running anything.
"""

from __future__ import annotations

from pathlib import Path

W, H = 1200, 780
OUT = Path(__file__).resolve().parents[1] / "wiring.svg"

# Colours
RED, BLUE, GREEN, ORANGE, GREY, INK, BOX = "#c62828", "#1565c0", "#2e7d32", "#ef6c00", "#757575", "#212121", "#f5f5f5"

parts: list[str] = []


def text(x, y, s, size=13, anchor="start", weight="normal", fill=INK, family="Helvetica, Arial, sans-serif"):
    parts.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{s}</text>')


def box(x, y, w, h, title, sub=None):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{BOX}" stroke="{INK}" stroke-width="1.5"/>')
    text(x + 10, y + 20, title, 14, weight="bold")
    if sub:
        text(x + 10, y + 36, sub, 11, fill=GREY)


def terminal(x, y, label, side, pin=None):
    """Screw terminal: small square at (x, y); label inside the box on `side`."""
    parts.append(f'<rect x="{x-6}" y="{y-6}" width="12" height="12" fill="#fff" stroke="{INK}" stroke-width="1.2"/>')
    if side == "right":  # terminal on the right edge, label to the left
        text(x - 14, y + 4, label, 12, anchor="end")
        if pin:
            text(x + 12, y - 6, pin, 10, fill=GREY)
    else:  # terminal on the left edge, label to the right
        text(x + 14, y + 4, label, 12)
        if pin:
            text(x - 12, y + 4, pin, 10, anchor="end", fill=GREY)


def wire(points, color, dash=None, width=2):
    d = " ".join(f"{x},{y}" for x, y in points)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{extra}/>')


def resistor(x, y, label, vertical=False):
    if vertical:
        parts.append(f'<rect x="{x-7}" y="{y-18}" width="14" height="36" fill="#fff" stroke="{INK}" stroke-width="1.2"/>')
        text(x - 11, y + 4, label, 11, anchor="end")
    else:
        parts.append(f'<rect x="{x-18}" y="{y-7}" width="36" height="14" fill="#fff" stroke="{INK}" stroke-width="1.2"/>')
        text(x, y - 11, label, 11, anchor="middle")


# ---------------------------------------------------------------- instruments (left)
IX, IW, IR = 60, 250, 310  # block x, width, terminal x (right edge)

box(IX, 60, IW, 175, "Waters 2489 UV/Vis", "rear I/O block I")
uv = {}
for i, (pin, lab) in enumerate([("1", "Analog 1 Out +"), ("2", "Analog 1 Out −"), ("3", "Ground"), ("4", "Analog 2 Out +"), ("5", "Analog 2 Out −")]):
    y = 100 + 26 * i
    uv[pin] = y
    terminal(IR, y, lab, "right", pin)

box(IX, 255, IW, 100, "Waters 2424 ELSD", "rear I/O block I — confirm pins on its label")
els = {}
for i, (pin, lab) in enumerate([("1", "Analog Out +"), ("2", "Analog Out −")]):
    y = 316 + 26 * i
    els[pin] = y
    terminal(IR, y, lab, "right", pin)

box(IX, 375, IW, 160, "Waters e2695 Separations Module", "rear I/O block B")
sm = {}
for i, (pin, lab) in enumerate([("11", "Chart Out +"), ("12", "Chart Out −"), ("1", "Inject Start +"), ("2", "Inject Start −")]):
    y = 420 + 26 * i
    sm[pin] = y
    terminal(IR, y, lab, "right", "B" + pin)

# ---------------------------------------------------------------- ADS1263 HAT (centre)
HX, HW, HL = 560, 150, 560  # box x, width, terminal x (left edge)
box(HX, 60, HW, 510, "Waveshare AD HAT", "ADS1263, screw terminals")
hat = {}
for i, lab in enumerate(["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AINCOM", "AGND", "5V", "GND"]):
    y = 100 + 34 * i
    hat[lab] = y
    terminal(HL, y, lab, "left")
# differential pair brackets
for i in range(5):
    y0, y1 = hat[f"AIN{2*i}"], hat[f"AIN{2*i+1}"]
    parts.append(f'<path d="M{HX+HW-60},{y0} h8 v{y1-y0} h-8" fill="none" stroke="{GREY}" stroke-width="1"/>')
    text(HX + HW - 46, (y0 + y1) / 2 + 4, f"ch {i}", 11, fill=GREY)

# ---------------------------------------------------------------- Raspberry Pi (right)
PX, PW, PL = 900, 240, 900
box(PX, 60, PW, 300, "Raspberry Pi 4", "40-pin header; the HAT stacks on it")
pi = {}
for lab, pin, y in [("3V3", "pin 1", 130), ("GPIO 25", "pin 22", 200), ("GND", "pin 20", 270)]:
    pi[lab] = y
    terminal(PL, y, f"{lab}  ({pin})", "left")
text(PX + 10, 330, "SPI0 + GPIO 17/18/22 are used by the HAT", 11, fill=GREY)

# ---------------------------------------------------------------- analog wires
# Each wire runs right from the instrument terminal to its own vertical lane, then to the HAT.
lanes = iter(range(345, 545, 16))


def analog(y_src, hat_lab, color, dash=None):
    x = next(lanes)
    wire([(IR + 6, y_src), (x, y_src), (x, hat[hat_lab]), (HL - 6, hat[hat_lab])], color, dash)


analog(uv["1"], "AIN0", RED)
analog(uv["2"], "AIN1", BLUE)
analog(uv["4"], "AIN2", RED)
analog(uv["5"], "AIN3", BLUE)
analog(els["1"], "AIN4", RED)
analog(els["2"], "AIN5", BLUE)
analog(sm["11"], "AIN6", RED)
analog(sm["12"], "AIN7", BLUE)
analog(uv["3"], "AGND", GREEN)  # single signal-ground reference
# cable shields: drawn once, dashed, to AGND only
x = next(lanes)
wire([(x, uv["1"] - 10), (x, hat["AGND"]), (HL - 6, hat["AGND"])], GREY, dash="5,4", width=1.5)
text(x + 4, 52, "cable shields → AGND (HAT end only)", 11, anchor="end", fill=GREY)

# ---------------------------------------------------------------- trigger: PC817 optocoupler
OX, OY = 640, 610
parts.append(f'<rect x="{OX}" y="{OY}" width="120" height="90" rx="4" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
text(OX + 60, OY + 22, "PC817", 13, anchor="middle", weight="bold")
text(OX + 60, OY + 38, "optocoupler", 11, anchor="middle", fill=GREY)
# LED side pins (left): 1 anode top, 2 cathode bottom
text(OX + 8, OY + 62, "1 A", 11)
text(OX + 8, OY + 84, "2 K", 11)
# transistor side (right): 4 collector top, 3 emitter bottom
text(OX + 112, OY + 62, "4 C", 11, anchor="end")
text(OX + 112, OY + 84, "3 E", 11, anchor="end")
ya, yk = OY + 58, OY + 80  # anode / cathode y
yc, ye = OY + 58, OY + 80  # collector / emitter y

# B1 (+) -> 1 kΩ -> anode ; B2 (−) -> cathode
wire([(IR + 6, sm["1"]), (330, sm["1"]), (330, ya), (OX, ya)], ORANGE)
resistor(480, ya, "1 kΩ")
wire([(IR + 6, sm["2"]), (322, sm["2"]), (322, yk), (OX, yk)], ORANGE)
# collector -> GPIO 25, with 10 kΩ pull-up to 3V3
wire([(OX + 120, yc), (860, yc), (860, pi["GPIO 25"]), (PL - 6, pi["GPIO 25"])], ORANGE)
wire([(820, yc), (820, pi["3V3"]), (PL - 6, pi["3V3"])], ORANGE)
resistor(820, 420, "10 kΩ pull-up", vertical=True)
parts.append(f'<circle cx="820" cy="{yc}" r="3" fill="{ORANGE}"/>')
# emitter -> Pi GND
wire([(OX + 120, ye), (880, ye), (880, pi["GND"]), (PL - 6, pi["GND"])], GREEN)

text(60, 562, "Inject Start closure → isolated trigger", 12, weight="bold")
text(60, 580, "GPIO 25 idles high, pulled low at injection.", 11, fill=GREY)
text(60, 596, "If B1/B2 is a dry contact, feed the LED from", 11, fill=GREY)
text(60, 612, "the HAT's 5 V via the 1 kΩ (see wiring.md).", 11, fill=GREY)

# ---------------------------------------------------------------- legend + title
text(60, 32, "open-alliance-daq wiring — Waters Alliance stack → ADS1263 HAT → Raspberry Pi 4", 16, weight="bold")
lx, ly = 900, 420
box(lx, ly, 240, 140, "Legend")
for i, (c, lab, dash) in enumerate([(RED, "analog +", None), (BLUE, "analog −", None), (GREEN, "signal / power ground", None), (ORANGE, "trigger", None), (GREY, "cable shield", "5,4")]):
    y = ly + 52 + 16 * i
    wire([(lx + 12, y), (lx + 44, y)], c, dash)
    text(lx + 52, y + 4, lab, 11)
text(60, 740, "All instrument pin numbers were read from the rear-panel legends in docs/photos/. Verify each against the physical label before wiring; power everything down first.", 11, fill=GREY)
text(60, 758, "Only ONE instrument ground (2489 block I pin 3) goes to AGND. The differential inputs need it for common-mode reference; a second ground makes a loop.", 11, fill=GREY)

svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n<rect width="{W}" height="{H}" fill="#fff"/>\n' + "\n".join(parts) + "\n</svg>\n"
OUT.write_text(svg)
print(f"wrote {OUT} ({len(svg)} bytes)")
