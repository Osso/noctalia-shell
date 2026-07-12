pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Singleton {
  id: root

  // Public properties
  property string osPretty: ""
  property string osLogo: ""
  property bool isNixOS: false
  property bool isReady: false
  property bool osInfoLoadFailed: false
  property string osInfoError: ""

  // User info
  readonly property string username: (Quickshell.env("USER") || "")
  readonly property string envRealName: (Quickshell.env("NOCTALIA_REALNAME") || "")
  property string realName: ""

  readonly property string displayName: resolveDisplayName(envRealName, realName, username)

  function resolveDisplayName(explicitRealName, resolvedRealName, userName) {
    if (explicitRealName && explicitRealName.length > 0) {
      return explicitRealName;
    }

    if (resolvedRealName && resolvedRealName.length > 0) {
      return resolvedRealName;
    }

    if (userName && userName.length > 0) {
      return userName.charAt(0).toUpperCase() + userName.slice(1);
    }

    return "User";
  }

  function init() {
    Logger.i("HostService", "Service started");
  }

  // Internal helpers
  function buildCandidates(name) {
    const n = (name || "").trim();
    const isValidLogoName = /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(n);
    if (!n || !isValidLogoName)
      return [];

    const sizes = ["512x512", "256x256", "128x128", "64x64", "48x48", "32x32", "24x24", "22x22", "16x16"];
    const exts = ["svg", "png"];
    const candidates = [];

    // pixmaps
    for (const ext of exts) {
      candidates.push(`/usr/share/pixmaps/${n}.${ext}`);
    }

    // hicolor scalable and raster sizes
    candidates.push(`/usr/share/icons/hicolor/scalable/apps/${n}.svg`);
    for (const s of sizes) {
      for (const ext of exts) {
        candidates.push(`/usr/share/icons/hicolor/${s}/apps/${n}.${ext}`);
      }
    }

    // NixOS hicolor paths
    candidates.push(`/run/current-system/sw/share/icons/hicolor/scalable/apps/${n}.svg`);
    for (const s of sizes) {
      for (const ext of exts) {
        candidates.push(`/run/current-system/sw/share/icons/hicolor/${s}/apps/${n}.${ext}`);
      }
    }

    // Generic icon themes under /usr/share/icons (common cases)
    for (const ext of exts) {
      candidates.push(`/usr/share/icons/${n}.${ext}`);
      candidates.push(`/usr/share/icons/${n}/${n}.${ext}`);
      candidates.push(`/usr/share/icons/${n}/apps/${n}.${ext}`);
    }

    return candidates;
  }

  function resolveLogo(name) {
    const all = buildCandidates(name);
    if (all.length === 0)
      return;
    const script = all.map(p => `if [ -f "${p}" ]; then echo "${p}"; exit 0; fi`).join("; ") + "; exit 1";
    probe.command = ["sh", "-c", script];
    probe.running = true;
  }

  function decodeDoubleQuotedOsReleaseValue(value) {
    let decoded = "";
    for (let index = 1; index < value.length; index++) {
      const character = value.charAt(index);
      if (character === "\\") {
        index++;
        if (index >= value.length)
          throw new Error("unterminated quoted os-release value");
        const escaped = value.charAt(index);
        decoded += ['"', "\\", "$", "`"].includes(escaped) ? escaped : `\\${escaped}`;
      } else if (character === '"') {
        if (index !== value.length - 1)
          throw new Error("malformed double-quoted os-release value");
        return decoded;
      } else {
        decoded += character;
      }
    }
    throw new Error("unterminated quoted os-release value");
  }

  function decodeUnquotedOsReleaseValue(value) {
    if (value.includes('"') || value.includes("'"))
      throw new Error("malformed unquoted os-release value");

    let decoded = "";
    for (let index = 0; index < value.length; index++) {
      const character = value.charAt(index);
      if (character === "\\") {
        index++;
        if (index >= value.length)
          throw new Error("unterminated escaped os-release value");
        decoded += value.charAt(index);
      } else if (/\s/.test(character)) {
        throw new Error("malformed unquoted os-release value");
      } else {
        decoded += character;
      }
    }
    return decoded;
  }

  function decodeOsReleaseValue(rawValue) {
    const value = String(rawValue || "").trimStart();
    if (!value)
      return "";

    const quote = value.charAt(0);
    if (quote === "'") {
      if (!value.endsWith("'") || value.slice(1, -1).includes("'"))
        throw new Error("malformed single-quoted os-release value");
      return value.slice(1, -1);
    }
    if (quote === '"')
      return root.decodeDoubleQuotedOsReleaseValue(value);
    return root.decodeUnquotedOsReleaseValue(value);
  }

  function parseOsRelease(rawText) {
    const values = {};
    const lines = rawText.split("\n");
    for (const line of lines) {
      const trimmedStart = line.trimStart();
      if (!trimmedStart || trimmedStart.startsWith("#"))
        continue;

      const match = trimmedStart.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
      if (!match)
        throw new Error("malformed os-release line");

      const key = match[1];
      values[key] = root.decodeOsReleaseValue(match[2]);
    }

    const osPretty = (values.PRETTY_NAME || values.NAME || "").trim();
    const osId = (values.ID || "").trim().toLowerCase();
    if (!osPretty && !osId)
      throw new Error("os-release is missing NAME and ID");
    const isNixOS = osId === "nixos" || osPretty.toLowerCase().includes("nixos");

    return {
      "osPretty": osPretty,
      "isNixOS": isNixOS,
      "logoName": values.LOGO || "",
      "isReady": true
    };
  }

  function handleOsInfoLoadFailure(error) {
    root.isReady = false;
    root.osInfoLoadFailed = true;
    root.osInfoError = String(error || "Unknown os-release load failure");
    Logger.w("HostService", "failed to read os-release", root.osInfoError);
  }

  function applyOsRelease(rawText) {
    const parsed = root.parseOsRelease(rawText);
    root.osPretty = parsed.osPretty;
    Logger.i("HostService", "Detected", root.osPretty);
    root.isNixOS = parsed.isNixOS;
    if (parsed.logoName)
      root.resolveLogo(parsed.logoName);
    root.osInfoLoadFailed = false;
    root.osInfoError = "";
    root.isReady = parsed.isReady;
  }

  function handleLogoProbeExit(exitCode) {
    const p = String(probe.stdout.text || "").trim();
    if (exitCode === 0 && p) {
      osLogo = `file://${p}`;
      Logger.d("HostService", "Found", osLogo);
    } else {
      osLogo = "";
      Logger.w("HostService", "None logo found");
    }
  }

  // Read /etc/os-release and trigger resolution
  FileView {
    id: osInfo
    path: "/etc/os-release"
    onLoaded: {
      try {
        root.applyOsRelease(text());
      } catch (e) {
        root.handleOsInfoLoadFailure(e);
      }
    }
    onLoadFailed: function (error) {
      root.handleOsInfoLoadFailure(error);
    }
  }

  Process {
    id: probe
    onExited: code => {
      root.handleLogoProbeExit(code);
    }
    stdout: StdioCollector {}
    stderr: StdioCollector {}
  }

  // Resolve GECOS real name once on startup
  Process {
    id: realNameProcess
    command: ["sh", "-c", "getent passwd \"$USER\" | cut -d: -f5 | cut -d, -f1"]
    running: true

    stdout: StdioCollector {
      onStreamFinished: {
        const name = String(text || "").trim();
        if (name.length > 0) {
          root.realName = name;
          Logger.i("HostService", "resolved real name", name);
        }
      }
    }
    stderr: StdioCollector {}
  }
}
