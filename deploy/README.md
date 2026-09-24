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
