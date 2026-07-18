# Blinkt! LED Controller

A small web app for controlling **Pimoroni Blinkt!** LEDs (8 individually
addressable RGB LEDs) from a **Raspberry Pi 3B**. Open the page in any browser
on your network — phone, tablet, or laptop — and:

- Set **all 8 LEDs** to a colour at once.
- Change **each LED individually** (labelled **1–8**).
- Adjust **global brightness**.
- Turn everything **off** with one tap.
- Use quick **colour presets**.

Everything the page does is also available as a tiny JSON **REST API**, so you
can script the lights too.

> **Hardware:** This targets the Pimoroni **Blinkt!** (8 × APA102 LEDs on the
> GPIO header), which matches "8 individual LEDs" exactly. If you have a
> different Pimoroni board, see [Using other boards](#using-other-boards).

---

## 1. Wire up the hardware

Push the **Blinkt!** board onto the Raspberry Pi's 40-pin GPIO header (it
covers pins 1–16, with the LEDs facing up and away from the USB ports). No
soldering needed.

## 2. Enable SPI (recommended)

Blinkt! uses two GPIO pins by default and works without any config, but
enabling SPI is harmless and recommended:

```bash
sudo raspi-config    # Interface Options → SPI → Enable
```

## 3. Install

On the Raspberry Pi:

```bash
git clone https://github.com/newtonnowatzke-tech/led-controller.git
cd led-controller

python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

> `--system-site-packages` lets the virtual environment see the system
> `RPi.GPIO`, which the Blinkt! library depends on. If `pip install blinkt`
> has trouble, you can instead use Pimoroni's one-line installer:
> `curl https://get.pimoroni.com/blinkt | bash`.

## 4. Run

```bash
python3 app.py
```

Then, from any device on the same network, open:

```
http://<your-pi-ip>:5000
```

Find your Pi's IP with `hostname -I`. Example: `http://192.168.1.42:5000`.

The page header shows **"hardware connected"** when it's driving the real
Blinkt!, or **"mock (no hardware)"** when running on a machine without it.

## 5. (Optional) Start automatically on boot

A `systemd` unit is included:

```bash
sudo cp led-controller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now led-controller
```

Check status with `systemctl status led-controller` and view logs with
`journalctl -u led-controller -f`. Edit the paths/user in the file first if
your project isn't in `/home/pi/led-controller`.

---

## Develop / test without a Pi

The app runs on any machine. Without the Blinkt! hardware it uses a **mock
backend** that keeps the LED state in memory (and logs it), so the whole
interface and API work for development:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # installs Flask; skips blinkt off-Pi
python3 app.py
# open http://localhost:5000
```

---

## REST API

All colours accept either a hex string (`{"hex": "#ff8800"}`) or separate
channels (`{"r": 255, "g": 136, "b": 0}`). LED numbers are **1-based (1–8)**
to match the on-screen labels.

| Method & path            | Body                                             | Description                          |
| ------------------------ | ------------------------------------------------ | ------------------------------------ |
| `GET /api/state`         | –                                                | Current state of every LED.          |
| `POST /api/led/<n>`      | `{"hex": "#ff0000"}`                             | Set LED `n` (1–8).                   |
| `POST /api/all`          | `{"hex": "#00ff00"}`                             | Set all LEDs to one colour.          |
| `POST /api/leds`         | `{"leds": [{"number":1,"hex":"#f00"}, ...]}`     | Set several LEDs in one request.     |
| `POST /api/brightness`   | `{"brightness": 30}`                             | Brightness: 0–1 (float) or 0–100.    |
| `POST /api/clear`        | –                                                | Turn every LED off.                  |

Examples with `curl`:

```bash
# LED 3 → blue
curl -X POST http://<pi-ip>:5000/api/led/3 -H 'Content-Type: application/json' \
     -d '{"hex": "#0000ff"}'

# All LEDs → warm white at 50% brightness
curl -X POST http://<pi-ip>:5000/api/all -H 'Content-Type: application/json' \
     -d '{"r": 255, "g": 200, "b": 150}'
curl -X POST http://<pi-ip>:5000/api/brightness -H 'Content-Type: application/json' \
     -d '{"brightness": 50}'

# Everything off
curl -X POST http://<pi-ip>:5000/api/clear
```

---

## Using other boards

The hardware access lives entirely in `led_backend.py`. The number of LEDs is
set by `NUM_LEDS` (default **8**). To support a different Pimoroni board
(e.g. a longer strip driven by APA102, or Neopixels), add a new driver class
with a `render(pixels, brightness)` method and return it from `_make_driver()`.
The web UI adapts to whatever `NUM_LEDS` is.

---

## Project layout

```
led-controller/
├── app.py                  # Flask server + REST API
├── led_backend.py          # LED state + hardware/mock drivers
├── requirements.txt
├── led-controller.service  # optional systemd autostart unit
├── templates/
│   └── index.html          # web interface
└── static/
    ├── style.css
    └── app.js
```
