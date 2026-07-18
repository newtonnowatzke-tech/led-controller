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

## What you need

- Raspberry Pi 3B (any Pi with a 40-pin header works)
- Pimoroni **Blinkt!** board (8 RGB LEDs)
- A **microSD card** (8 GB or larger) + a way to plug it into your computer
- 5 V power supply for the Pi, and your home Wi-Fi (or Ethernet)

## 1. Wire up the hardware

With the Pi **powered off**, push the **Blinkt!** board onto the Raspberry Pi's
40-pin GPIO header (it covers pins 1–16, with the LEDs facing up and away from
the USB ports). No soldering needed.

## 2. Prepare the SD card (flash Raspberry Pi OS)

The Raspberry Pi boots and runs everything from its microSD card, so first put
the operating system on the card:

1. On your computer, install the **Raspberry Pi Imager**:
   <https://www.raspberrypi.com/software/>
2. Insert the microSD card.
3. Open Imager and choose:
   - **Device:** Raspberry Pi 3
   - **Operating System:** *Raspberry Pi OS (64-bit)* — the "Lite" version is
     fine (no desktop needed, since we use it over the network)
   - **Storage:** your microSD card
4. Click **Next → Edit Settings** and set up, so the Pi is reachable with no
   monitor/keyboard:
   - a **hostname** (e.g. `ledpi` → you'll reach it at `ledpi.local`)
   - a **username and password** (remember these — you'll SSH in with them)
   - your **Wi-Fi** name and password (and country)
   - enable **SSH** on the *Services* tab
5. Click **Save → Write** and wait for it to finish.
6. Put the card into the Pi and power it on. Give it a minute to boot and join
   Wi-Fi.
7. Connect to it from your computer's terminal (use the username/hostname you
   set):
   ```bash
   ssh <username>@<hostname>.local     # e.g. ssh newton@ledpi.local
   ```
   Everything from here on runs on the Pi in that SSH session.

## 3. Download the code

Get the project onto your Raspberry Pi using whichever method you prefer.

**Option A — `git clone` (recommended, easy to update later).** Run this on the
Pi (open a terminal, or SSH in):

```bash
git clone https://github.com/newtonnowatzke-tech/led-controller.git
cd led-controller
```

Later, pull the newest version any time with `git pull`.

> If `git` isn't installed: `sudo apt update && sudo apt install -y git`.

**Option B — download a ZIP (no git needed).**

1. Open the repo in a browser:
   <https://github.com/newtonnowatzke-tech/led-controller>
2. Click the green **`< > Code`** button → **Download ZIP**.
3. Unzip it. On the Pi you can do this from a terminal:
   ```bash
   cd ~/Downloads
   unzip led-controller-main.zip
   cd led-controller-main
   ```
   (On the Pi's desktop you can also just right-click the ZIP → *Extract Here*.)

**Option C — download directly on the Pi from the command line:**

```bash
cd ~
curl -L https://github.com/newtonnowatzke-tech/led-controller/archive/refs/heads/main.tar.gz -o led-controller.tar.gz
tar -xzf led-controller.tar.gz
cd led-controller-main
```

> Downloaded the ZIP on another computer? Copy it to the Pi with
> `scp led-controller-main.zip pi@<your-pi-ip>:~/` (replace `pi` with your
> username), then unzip it there.

## 4. Install & run — one command

From inside the project folder on the Pi, run the installer:

```bash
bash install.sh
```

That's it. The script installs the dependencies, enables SPI, and sets the
controller up as a service so it **starts automatically every time the Pi boots**
(and restarts itself if it ever crashes). When it finishes it prints the exact
address to open, for example:

```
Open in a browser:  http://192.168.1.42:5000
```

Open that address from your phone, tablet, or laptop on the same network and
start changing the LEDs. The page header shows **"hardware connected"** when
it's driving the real Blinkt!.

Handy commands afterwards:

```bash
systemctl status led-controller      # is it running?
journalctl -u led-controller -f      # live logs
sudo systemctl restart led-controller
sudo systemctl disable --now led-controller   # stop it starting on boot
```

To update later: download the newest code (or `git pull`) and run
`bash install.sh` again.

## 5. Manual install (alternative)

If you'd rather not use the script, do it by hand from the project folder:

```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open `http://<your-pi-ip>:5000` (find the IP with `hostname -I`). This runs
in the foreground and stops when you close the session — to make it start on
boot, use `install.sh` or install the included `led-controller.service` manually.

> `--system-site-packages` lets the virtual environment see the system
> `RPi.GPIO`, which the Blinkt! library depends on. If `pip install blinkt`
> has trouble, you can instead use Pimoroni's one-line installer:
> `curl https://get.pimoroni.com/blinkt | bash`. SPI can be enabled with
> `sudo raspi-config` → *Interface Options → SPI → Enable*.

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
├── install.sh              # one-command Pi installer (deps + boot service)
├── requirements.txt
├── led-controller.service  # systemd autostart unit (template)
├── templates/
│   └── index.html          # web interface
└── static/
    ├── style.css
    └── app.js
```
