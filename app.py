"""Flask web app to control a Pimoroni Blinkt! (8 RGB LEDs) on a Raspberry Pi.

Run it with::

    python3 app.py

then open ``http://<pi-ip-address>:5000`` in a browser on the same network.

The web page lets you change the colour of all LEDs at once or each of the
eight LEDs individually, adjust global brightness, and switch everything off.
Everything the page does is also available as a small JSON REST API (see the
``/api/*`` routes below) so you can script the LEDs too.
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, render_template, request

from led_backend import LEDController, hex_to_rgb

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
controller = LEDController()


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

def _color_from_request(data: dict):
    """Extract an ``(r, g, b)`` colour from a request body.

    Accepts either ``{"hex": "#ff0000"}`` or ``{"r": 255, "g": 0, "b": 0}``.
    """
    if data is None:
        raise ValueError("Missing JSON body")

    if "hex" in data:
        return hex_to_rgb(str(data["hex"]))

    if all(k in data for k in ("r", "g", "b")):
        return (data["r"], data["g"], data["b"])

    raise ValueError('Provide a colour as {"hex": "#rrggbb"} or {"r":.., "g":.., "b":..}')


def _error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", num_leds=controller.num_leds)


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.get("/api/state")
def api_state():
    """Return the current state of every LED."""
    return jsonify({"ok": True, **controller.get_state()})


@app.post("/api/led/<int:number>")
def api_set_led(number: int):
    """Set a single LED. ``number`` is 1-based (1-8) to match the UI labels."""
    index = number - 1
    if not 0 <= index < controller.num_leds:
        return _error(f"LED number must be between 1 and {controller.num_leds}", 404)
    try:
        color = _color_from_request(request.get_json(silent=True))
        controller.set_pixel(index, color)
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, **controller.get_state()})


@app.post("/api/all")
def api_set_all():
    """Set every LED to the same colour."""
    try:
        color = _color_from_request(request.get_json(silent=True))
        controller.set_all(color)
    except ValueError as exc:
        return _error(str(exc))
    return jsonify({"ok": True, **controller.get_state()})


@app.post("/api/leds")
def api_set_leds():
    """Set several LEDs at once from ``{"leds": [{"number": 1, "hex": "#ff0000"}, ...]}``."""
    data = request.get_json(silent=True) or {}
    items = data.get("leds")
    if not isinstance(items, list):
        return _error('Body must be {"leds": [{"number": .., "hex"/"r,g,b": ..}, ...]}')
    try:
        for item in items:
            number = int(item["number"])
            index = number - 1
            if not 0 <= index < controller.num_leds:
                return _error(f"LED number must be between 1 and {controller.num_leds}")
            color = _color_from_request(item)
            controller.set_pixel(index, color, show=False)
        controller.show()
    except (ValueError, KeyError, TypeError) as exc:
        return _error(str(exc))
    return jsonify({"ok": True, **controller.get_state()})


@app.post("/api/brightness")
def api_brightness():
    """Set the global brightness. Accepts 0-1 (float) or 0-100 (percent)."""
    data = request.get_json(silent=True) or {}
    if "brightness" not in data:
        return _error('Provide {"brightness": 0.0-1.0}')
    try:
        value = float(data["brightness"])
    except (TypeError, ValueError):
        return _error("brightness must be a number")
    if value > 1:  # treat values above 1 as a 0-100 percentage
        value = value / 100.0
    controller.set_brightness(value)
    return jsonify({"ok": True, **controller.get_state()})


@app.post("/api/clear")
def api_clear():
    """Turn every LED off."""
    controller.clear()
    return jsonify({"ok": True, **controller.get_state()})


if __name__ == "__main__":
    # Listen on all interfaces so the page is reachable from other devices
    # on the same network (phone, laptop, ...).
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
