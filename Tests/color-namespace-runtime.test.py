#!/usr/bin/env python3
"""Resolve the production palette in Qt/Quickshell without desktop/config access."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = """pragma Singleton
import QtQuick
QtObject {
  readonly property bool directoriesCreated: true
  readonly property string configDir: CONFIG_PATH
}
"""
LOGGER = """pragma Singleton
import QtQuick
QtObject {
  function i(...args) { console.log(...args); }
}
"""


def main():
    with tempfile.TemporaryDirectory(prefix="noctalia-color-namespace-") as temporary:
        directory = Path(temporary)
        commons = directory / "Commons"
        commons.mkdir(mode=0o700)
        shutil.copyfile(ROOT / "Commons/NColor.qml", commons / "NColor.qml")
        config_path = json.dumps(str(directory / "config") + "/")
        (commons / "Settings.qml").write_text(SETTINGS.replace("CONFIG_PATH", config_path))
        (commons / "Logger.qml").write_text(LOGGER)
        shutil.copyfile(ROOT / "Tests/Qml/ColorNamespaceHarness.qml", directory / "shell.qml")

        # Remove desktop/session connections and isolate every writable user path.
        environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
            and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
        }
        for variable, name in {
            "HOME": "home", "XDG_CONFIG_HOME": "config", "XDG_CACHE_HOME": "cache",
            "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "runtime",
        }.items():
            path = directory / name
            path.mkdir(mode=0o700)
            environment[variable] = str(path)
        environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment, capture_output=True, text=True, timeout=15,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if "Unable to assign [undefined] to QString" in output:
            raise AssertionError("isolated palette config path must be a valid string")
        if result.returncode != 0 or "COLOR_NAMESPACE_PASS" not in output:
            raise AssertionError(f"offscreen palette/window test failed (exit {result.returncode})")


if __name__ == "__main__":
    main()
