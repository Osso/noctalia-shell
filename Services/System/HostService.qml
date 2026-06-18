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

  function parseOsRelease(rawText) {
    const lines = rawText.split("\n");
    const val = k => {
      const l = lines.find(x => x.startsWith(k + "="));
      return l ? l.split("=")[1].replace(/"/g, "") : "";
    };
    const osPretty = val("PRETTY_NAME") || val("NAME");
    const osId = (val("ID") || "").toLowerCase();
    const isNixOS = osId === "nixos" || (osPretty || "").toLowerCase().includes("nixos");

    return {
      "osPretty": osPretty,
      "isNixOS": isNixOS,
      "logoName": val("LOGO"),
      "isReady": true
    };
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
        const parsed = parseOsRelease(text());
        root.osPretty = parsed.osPretty;
        Logger.i("HostService", "Detected", root.osPretty);
        root.isNixOS = parsed.isNixOS;
        if (parsed.logoName) {
          resolveLogo(parsed.logoName);
        }
        root.isReady = parsed.isReady;
      } catch (e) {
        Logger.w("HostService", "failed to read os-release", e);
      }
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
