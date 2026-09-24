#!/usr/bin/env bash
# One-time root setup for open-alliance-daq on Fedora (tested: Fedora 44 Server, Raspberry Pi 4).
# Run:  sudo bash deploy/fedora-setup.sh [username]     then reboot.
# Idempotent: safe to re-run.
set -euo pipefail
USER_NAME="${1:-${SUDO_USER:-$(id -un)}}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
REPO="$HOME_DIR/open-alliance-daq"
echo "== user=$USER_NAME repo=$REPO"

echo "== packages (build deps for spidev + gpiod Python bindings, gpiod CLI tools)"
dnf install -y -q python3-devel gcc libgpiod-utils git

echo "== SPI: enable spi0 via firmware config.txt"
CFG=/boot/efi/config.txt
touch "$CFG"
grep -q '^dtparam=spi=on' "$CFG" || echo 'dtparam=spi=on' >> "$CFG"
grep -q '^spi-bcm2835\|^spidev' /etc/modules-load.d/alliance-daq.conf 2>/dev/null || printf 'spi-bcm2835\nspidev\n' > /etc/modules-load.d/alliance-daq.conf

echo "== device permissions: gpio + spi groups"
groupadd -f gpio
groupadd -f spi
usermod -aG gpio,spi "$USER_NAME"
cat > /etc/udev/rules.d/99-alliance-daq.rules <<'RULES'
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
SUBSYSTEM=="spidev", KERNEL=="spidev*", GROUP="spi", MODE="0660"
RULES
udevadm control --reload-rules
udevadm trigger --subsystem-match=gpio || true

echo "== systemd unit (armed logger)"
sed -e "s|User=pi|User=$USER_NAME|" \
    -e "s|/home/pi/open-alliance-daq|$REPO|g" \
    -e "s|/home/pi/hplc-runs|$HOME_DIR/hplc-runs|g" \
    "$REPO/deploy/alliance-daq.service" > /etc/systemd/system/alliance-daq.service
mkdir -p "$HOME_DIR/hplc-runs" && chown "$USER_NAME:" "$HOME_DIR/hplc-runs"
systemctl daemon-reload
echo "   installed /etc/systemd/system/alliance-daq.service (not enabled; enable after wiring is verified)"

echo
echo "== done. Reboot to apply the SPI device tree change and group membership:"
echo "   sudo reboot"
echo "   then check:  ls -l /dev/spidev0.* /dev/gpiochip0 ; gpiodetect"
