"""LED backend for a Pimoroni Blinkt! (8 x APA102 RGB LEDs).

The controller keeps the authoritative state (colour of every pixel plus a
global brightness) in memory and renders it through a *driver*.

Two drivers are provided:

* ``_BlinktDriver`` talks to the real Blinkt! hardware. It is used
  automatically when the ``blinkt`` Python library is importable, i.e. when
  running on the Raspberry Pi.
* ``_MockDriver`` is a no-op driver that simply logs the pixel state. It lets
  the web interface and REST API be developed and tested on any machine that
  does not have the hardware attached.

Because the state lives in the controller (not the driver), the API behaves
identically whether or not real hardware is present.
"""

from __future__ import annotations

import logging
import threading
from typing import List, Tuple

logger = logging.getLogger(__name__)

#: Number of LEDs on a Blinkt! board.
NUM_LEDS = 8

Color = Tuple[int, int, int]


def _clamp_channel(value) -> int:
    """Clamp a single colour channel to the valid 0-255 integer range."""
    return max(0, min(255, int(round(float(value)))))


def clamp_color(color) -> Color:
    """Return ``(r, g, b)`` with each channel clamped to 0-255."""
    r, g, b = color
    return (_clamp_channel(r), _clamp_channel(g), _clamp_channel(b))


def hex_to_rgb(value: str) -> Color:
    """Convert a ``#rrggbb`` (or ``rrggbb``) hex string to an ``(r, g, b)`` tuple."""
    original = value
    value = value.strip().lstrip("#")
    if len(value) == 3:  # short form, e.g. "f0a"
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(f"Invalid hex colour: {original!r} (expected e.g. #ff8800)")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_to_hex(color: Color) -> str:
    """Convert an ``(r, g, b)`` tuple to a ``#rrggbb`` hex string."""
    r, g, b = clamp_color(color)
    return f"#{r:02x}{g:02x}{b:02x}"


class _MockDriver:
    """Driver used when no Blinkt! hardware is available."""

    name = "mock"

    def render(self, pixels: List[Color], brightness: float) -> None:
        swatches = " ".join(rgb_to_hex(p) for p in pixels)
        logger.debug("MOCK render (brightness=%.2f): %s", brightness, swatches)


class _BlinktDriver:
    """Driver that renders to the real Pimoroni Blinkt! board."""

    name = "blinkt"

    def __init__(self) -> None:
        import blinkt  # noqa: WPS433 (imported lazily so non-Pi machines still work)

        self._blinkt = blinkt
        # Make sure the LEDs are turned off when the process exits.
        self._blinkt.set_clear_on_exit(True)

    def render(self, pixels: List[Color], brightness: float) -> None:
        for i, (r, g, b) in enumerate(pixels):
            self._blinkt.set_pixel(i, r, g, b, brightness)
        self._blinkt.show()


def _make_driver():
    """Return a hardware driver if possible, otherwise the mock driver."""
    try:
        driver = _BlinktDriver()
        logger.info("Using Blinkt! hardware driver.")
        return driver
    except Exception as exc:  # ImportError on non-Pi, RuntimeError without GPIO, etc.
        logger.warning("Blinkt! hardware not available (%s); using mock driver.", exc)
        return _MockDriver()


class LEDController:
    """Thread-safe controller for the strip of LEDs.

    All colour values are ``(r, g, b)`` integer tuples in the 0-255 range.
    ``brightness`` is a float in the 0.0-1.0 range applied globally.
    """

    def __init__(self, num_leds: int = NUM_LEDS, brightness: float = 0.3) -> None:
        self.num_leds = num_leds
        self._pixels: List[Color] = [(0, 0, 0) for _ in range(num_leds)]
        self._brightness = self._clamp_brightness(brightness)
        self._lock = threading.Lock()
        self._driver = _make_driver()
        self.show()

    # -- properties ---------------------------------------------------------

    @property
    def backend(self) -> str:
        """Name of the active driver (``"blinkt"`` or ``"mock"``)."""
        return self._driver.name

    @property
    def brightness(self) -> float:
        return self._brightness

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _clamp_brightness(value) -> float:
        return max(0.0, min(1.0, float(value)))

    def _check_index(self, index: int) -> None:
        if not 0 <= index < self.num_leds:
            raise IndexError(
                f"LED index {index} out of range (valid: 0-{self.num_leds - 1})"
            )

    def show(self) -> None:
        """Push the current state to the driver."""
        self._driver.render(list(self._pixels), self._brightness)

    # -- public API ---------------------------------------------------------

    def set_pixel(self, index: int, color: Color, show: bool = True) -> None:
        """Set a single LED (0-based index) to ``color``."""
        self._check_index(index)
        with self._lock:
            self._pixels[index] = clamp_color(color)
            if show:
                self.show()

    def set_all(self, color: Color, show: bool = True) -> None:
        """Set every LED to the same ``color``."""
        color = clamp_color(color)
        with self._lock:
            self._pixels = [color for _ in range(self.num_leds)]
            if show:
                self.show()

    def set_pixels(self, colors: List[Color], show: bool = True) -> None:
        """Set every LED from a list of colours (length must equal ``num_leds``)."""
        if len(colors) != self.num_leds:
            raise ValueError(
                f"Expected {self.num_leds} colours, got {len(colors)}"
            )
        with self._lock:
            self._pixels = [clamp_color(c) for c in colors]
            if show:
                self.show()

    def clear(self, show: bool = True) -> None:
        """Turn every LED off."""
        self.set_all((0, 0, 0), show=show)

    def set_brightness(self, brightness: float, show: bool = True) -> None:
        """Set the global brightness (0.0-1.0)."""
        with self._lock:
            self._brightness = self._clamp_brightness(brightness)
            if show:
                self.show()

    def get_state(self) -> dict:
        """Return a JSON-serialisable snapshot of the current state."""
        with self._lock:
            return {
                "backend": self.backend,
                "num_leds": self.num_leds,
                "brightness": round(self._brightness, 3),
                "leds": [
                    {
                        "index": i,          # 0-based internal index
                        "number": i + 1,     # 1-based, matches the UI labels
                        "rgb": list(color),
                        "hex": rgb_to_hex(color),
                        "on": color != (0, 0, 0),
                    }
                    for i, color in enumerate(self._pixels)
                ],
            }
