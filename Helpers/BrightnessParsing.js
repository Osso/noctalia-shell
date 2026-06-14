.pragma library

function parseDdcMonitors(output) {
  const text = String(output || "").trim();
  if (text === "") {
    return [];
  }

  return text.split("\n\n").map(displayText => {
    const unsupported = /(This monitor does not support DDC\/CI|Invalid display)/.test(displayText);
    const modelMatch = displayText.match(/Model:\s*(.*)/);
    const busMatch = displayText.match(/I2C bus:[ ]*\/dev\/i2c-([0-9]+)/);

    return {
      model: modelMatch ? modelMatch[1] : "Unknown",
      busNum: busMatch ? busMatch[1] : "Unknown",
      isDdc: !unsupported,
    };
  });
}

function parseDdcBrightness(output) {
  const parts = String(output || "").trim().split(/\s+/);
  if (parts.length < 5) {
    return null;
  }

  const current = parseInt(parts[3]);
  const max = parseInt(parts[4]);
  if (isNaN(current) || isNaN(max) || max <= 0) {
    return null;
  }

  return {
    current,
    max,
    ratio: current / max,
  };
}

function parseAppleBrightness(output) {
  const current = parseInt(String(output || "").trim());
  if (isNaN(current)) {
    return null;
  }

  return {
    current,
    max: 101,
    ratio: current / 101,
  };
}

function parseInternalBacklight(output) {
  const lines = String(output || "").trim().split("\n");
  if (lines.length < 3) {
    return null;
  }

  const current = parseInt(lines[1]);
  const max = parseInt(lines[2]);
  if (isNaN(current) || isNaN(max) || max <= 0) {
    return null;
  }

  return {
    devicePath: lines[0],
    brightnessPath: `${lines[0]}/brightness`,
    maxBrightnessPath: `${lines[0]}/max_brightness`,
    current,
    max,
    ratio: current / max,
  };
}

function isValidBrightnessRatio(value) {
  return typeof value === "number" && isFinite(value);
}
