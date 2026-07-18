"use strict";

// Small helper around fetch that talks to the JSON API and refreshes the UI.
async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

function jsonPost(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

const PRESETS = [
  "#ff0000", "#ff7f00", "#ffff00", "#00ff00",
  "#00ffff", "#0000ff", "#8b00ff", "#ff00ff",
  "#ffffff", "#ff8c69", "#00ff9d", "#000000",
];

const grid = document.getElementById("led-grid");
const statusEl = document.getElementById("status");
const backendLabel = document.getElementById("backend-label");
const brightnessInput = document.getElementById("brightness");
const brightnessValue = document.getElementById("brightness-value");

function setStatus(message, isError) {
  statusEl.textContent = message;
  document.querySelector(".footer").classList.toggle("error", Boolean(isError));
}

function withStatus(promise, okMessage) {
  return promise
    .then((data) => {
      if (okMessage) setStatus(okMessage);
      return data;
    })
    .catch((err) => {
      setStatus(err.message, true);
      throw err;
    });
}

// Build the individual LED cards. Called once after we know how many LEDs exist.
function buildGrid(leds) {
  grid.innerHTML = "";
  leds.forEach((led) => {
    const card = document.createElement("div");
    card.className = "led-card";
    card.innerHTML = `
      <span class="led-number">LED ${led.number}</span>
      <div class="led-dot" id="dot-${led.number}"></div>
      <input type="color" id="color-${led.number}" />
      <button class="led-off" data-number="${led.number}">Off</button>
    `;
    grid.appendChild(card);

    const colorInput = card.querySelector(`#color-${led.number}`);
    colorInput.addEventListener("input", () => {
      updateDot(led.number, colorInput.value);
    });
    colorInput.addEventListener("change", () => {
      withStatus(
        api(`/api/led/${led.number}`, jsonPost({ hex: colorInput.value })),
        `LED ${led.number} updated`
      ).then(render);
    });

    card.querySelector(".led-off").addEventListener("click", () => {
      withStatus(
        api(`/api/led/${led.number}`, jsonPost({ hex: "#000000" })),
        `LED ${led.number} off`
      ).then(render);
    });
  });
}

function updateDot(number, hex) {
  const dot = document.getElementById(`dot-${number}`);
  if (!dot) return;
  const isOff = hex.toLowerCase() === "#000000";
  dot.style.background = isOff ? "#000" : hex;
  dot.style.boxShadow = isOff ? "none" : `0 0 14px ${hex}`;
}

// Reflect server state in the UI.
function render(state) {
  backendLabel.textContent =
    state.backend === "blinkt" ? "hardware connected" : "mock (no hardware)";

  state.leds.forEach((led) => {
    const colorInput = document.getElementById(`color-${led.number}`);
    if (colorInput) colorInput.value = led.hex;
    updateDot(led.number, led.hex);
  });

  const percent = Math.round(state.brightness * 100);
  brightnessInput.value = percent;
  brightnessValue.textContent = `${percent}%`;
}

function buildPresets() {
  const wrap = document.getElementById("presets");
  PRESETS.forEach((hex) => {
    const b = document.createElement("button");
    b.className = "swatch";
    b.style.background = hex;
    b.title = hex;
    b.addEventListener("click", () => {
      document.getElementById("all-color").value = hex;
      withStatus(api("/api/all", jsonPost({ hex })), `All LEDs → ${hex}`).then(render);
    });
    wrap.appendChild(b);
  });
}

// --- Global controls ---
document.getElementById("apply-all").addEventListener("click", () => {
  const hex = document.getElementById("all-color").value;
  withStatus(api("/api/all", jsonPost({ hex })), `All LEDs → ${hex}`).then(render);
});

document.getElementById("clear-all").addEventListener("click", () => {
  withStatus(api("/api/clear", jsonPost({})), "All LEDs off").then(render);
});

// Update the label live while dragging; send to the server when released.
brightnessInput.addEventListener("input", () => {
  brightnessValue.textContent = `${brightnessInput.value}%`;
});
brightnessInput.addEventListener("change", () => {
  const value = Number(brightnessInput.value);
  withStatus(
    api("/api/brightness", jsonPost({ brightness: value })),
    `Brightness ${value}%`
  ).then(render);
});

// --- Startup ---
async function init() {
  try {
    const state = await api("/api/state");
    buildGrid(state.leds);
    buildPresets();
    render(state);
    setStatus("Ready");
  } catch (err) {
    setStatus(`Could not load state: ${err.message}`, true);
  }
}

init();
