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
