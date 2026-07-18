#!/usr/bin/env bash
#
# One-command installer for the Blinkt! LED controller on a Raspberry Pi.
#
# Run it from inside the project folder on the Pi:
#
#     bash install.sh
#
# It will:
#   1. install the system packages it needs (python3-venv, python3-pip),
#   2. enable the SPI interface (best effort; Blinkt! works without it too),
#   3. create a Python virtual environment and install the dependencies,
#   4. install a systemd service so the controller starts automatically on
#      boot and restarts if it ever crashes,
#   5. start it now and print the URL to open.
#
# The script is safe to re-run (e.g. after updating the code).

set -euo pipefail

# --- Where the project lives, and who should own/run it -------------------
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# When run with sudo, prefer the real login user so files aren't owned by root.
RUN_USER="${SUDO_USER:-$(id -un)}"
VENV="${PROJECT_DIR}/.venv"
PYTHON="${VENV}/bin/python"
SERVICE_NAME="led-controller"
PORT="${PORT:-5000}"

# Helper: run a command as the target user (handles being launched via sudo).
run_as_user() {
    if [ "$(id -un)" = "${RUN_USER}" ]; then
        "$@"
    else
        sudo -u "${RUN_USER}" -H "$@"
    fi
}

echo "==> Installing LED controller"
echo "    project : ${PROJECT_DIR}"
echo "    user    : ${RUN_USER}"
echo "    port    : ${PORT}"
echo

# --- 1. System packages ----------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
    echo "==> Installing system packages (python3-venv, python3-pip, git)..."
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip git
else
    echo "==> 'apt-get' not found; skipping system package install."
fi

# --- 2. Enable SPI (recommended, but Blinkt! also works without it) --------
if command -v raspi-config >/dev/null 2>&1; then
    echo "==> Enabling SPI interface..."
    # In raspi-config's non-interactive mode, 0 = enable.
    sudo raspi-config nonint do_spi 0 || echo "    (could not toggle SPI automatically; continuing)"
else
    echo "==> 'raspi-config' not found; skipping SPI step (fine for non-Pi installs)."
fi

# --- 3. Python virtual environment + dependencies --------------------------
echo "==> Creating virtual environment and installing dependencies..."
run_as_user python3 -m venv "${VENV}" --system-site-packages
run_as_user "${VENV}/bin/pip" install --upgrade pip
run_as_user "${VENV}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"

# --- 4. systemd service (generated with the real paths and user) -----------
echo "==> Installing systemd service '${SERVICE_NAME}'..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=Pimoroni Blinkt! LED web controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON} ${PROJECT_DIR}/app.py
Restart=on-failure
RestartSec=3
Environment=PORT=${PORT}

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# --- 5. Done ---------------------------------------------------------------
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "==> Done! The LED controller is running and will start on every boot."
echo
if [ -n "${IP}" ]; then
    echo "    Open in a browser:  http://${IP}:${PORT}"
else
    echo "    Open in a browser:  http://<your-pi-ip>:${PORT}   (find the IP with: hostname -I)"
fi
echo
echo "    Service status:  systemctl status ${SERVICE_NAME}"
echo "    Live logs:       journalctl -u ${SERVICE_NAME} -f"
echo "    Stop / disable:  sudo systemctl disable --now ${SERVICE_NAME}"
