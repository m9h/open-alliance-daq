# Running the logger as a service on the Pi

```bash
# once, on the Pi
sudo raspi-config nonint do_spi 0
sudo apt install -y git python3-venv
git clone https://github.com/m9h/open-alliance-daq ~/open-alliance-daq
cd ~/open-alliance-daq
python3 -m venv .venv && .venv/bin/pip install -e '.[pi]'
cp config/channels.example.toml config/channels.toml   # then edit scaling to match the detectors
mkdir -p ~/hplc-runs

# sanity-check wiring before enabling the service
.venv/bin/alliance-daq live --rate 2 --channels config/channels.toml

# install the unit (edit --duration to your method run time first)
sudo cp deploy/alliance-daq.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alliance-daq
journalctl -u alliance-daq -f
```

The service waits on GPIO 25. Every Inject Start pulse from the e2695 starts a new CSV in
`~/hplc-runs/`, named by timestamp and label. `--count 0` keeps it armed indefinitely, so a
whole sample set records unattended. Stop it with `sudo systemctl stop alliance-daq`.

The `pi` user needs to be in the `gpio` and `spi` groups (default on Pi OS). If the unit
fails with "ID Read failed", SPI is not enabled or the HAT is not seated.

## Raspberry Pi OS quick path (any 64-bit Pi, e.g. a 3A+/3B+)

Use Raspberry Pi OS Lite 64-bit. The distro already ships `python3-spidev` and `RPi.GPIO`, so
build the venv on top of the system packages and nothing needs compiling:

```bash
sudo raspi-config nonint do_spi 0
sudo apt install -y git python3-venv python3-spidev python3-rpi.gpio
git clone https://github.com/m9h/open-alliance-daq ~/open-alliance-daq
cd ~/open-alliance-daq
python3 -m venv --system-site-packages .venv && .venv/bin/pip install -e .
.venv/bin/alliance-daq live --rate 2
sudo nmcli radio wifi off        # if on wired Ethernet (USB adapter on a 3A+)
```

The GPIO layer picks `RPi.GPIO` automatically when it imports; libgpiod is only needed where it
does not (Fedora, Pi 5). For the systemd unit, edit `User=` and the paths in
`deploy/alliance-daq.service` (or use `deploy/fedora-setup.sh`'s `sed` lines as a template).

## Fedora on the Pi (instead of Raspberry Pi OS)

Fedora boots the Pi 4 through UEFI/grub and ships with the SPI device-tree node disabled,
`/dev/gpiochip*` root-only, and no `RPi.GPIO`. The code handles the last part itself: the
GPIO layer in `alliance_daq/gpio.py` uses libgpiod when `RPi.GPIO` is absent. The rest is one
root script, then a reboot:

```bash
git clone https://github.com/m9h/open-alliance-daq ~/open-alliance-daq   # or rsync the tree over
sudo bash ~/open-alliance-daq/deploy/fedora-setup.sh                      # packages, SPI, udev, unit
sudo reboot
cd ~/open-alliance-daq && python3 -m venv .venv && .venv/bin/pip install -e '.[pi]'
.venv/bin/alliance-daq live --rate 2          # needs the HAT; prints all channels
```

What the script does: installs `python3-devel`, `gcc`, `libgpiod-utils`, `git`; appends
`dtparam=spi=on` to `/boot/efi/config.txt` (the Pi firmware applies it before handing the
device tree to grub); autoloads `spi-bcm2835` and `spidev`; creates `gpio` and `spi` groups
with udev rules for `/dev/gpiochip*` and `/dev/spidev*`; and installs the systemd unit with the
right user and paths. It does not enable the unit; do that after `live` shows sane numbers.

**Pi 5 caveat (Fedora).** The RP1 device-tree overlay in the Fedora/a64-kernel builds exposes
GPIO (`/dev/gpiochip4`, set `ALLIANCE_DAQ_GPIOCHIP=/dev/gpiochip4`) but no SPI controller, so
the ADS1263 HAT cannot be used on a Pi 5 under Fedora until RP1 SPI is upstream. Use a Pi 4 for
acquisition.

## Split setup: Pi 4 acquires, another machine analyses

The Pi stays a dumb appliance: it records to `~/hplc-runs/` and nothing else. The analysis
machine (here the DGX Spark) pulls new CSVs with rsync on a one-minute systemd *user* timer,
so no root is needed on either end. One-time setup on the analysis machine:

```bash
# let it log in to the Pi non-interactively
ssh-copy-id mhough@192.168.108.194
# install and start the timer
mkdir -p ~/.config/systemd/user
cp ~/open-alliance-daq/deploy/user-units/alliance-pull.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now alliance-pull.timer
loginctl enable-linger $USER      # keep user timers running when not logged in
systemctl --user list-timers | grep alliance
```

Then, on the analysis machine, `alliance-daq quant ~/hplc-runs/<run>.csv` or
`alliance-daq report ~/hplc-runs/*.csv --out report.pdf` as usual. tectonic installs without
root via `curl -fsSL https://drop-sh.fullyjustified.net | sh` in `~/.local/bin`.
