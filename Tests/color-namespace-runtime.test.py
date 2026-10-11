#!/usr/bin/env python3
"""Resolve the production palette in Qt/Quickshell without desktop/config access."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

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


def test_custom_file_reload(directory, environment):
    colors_file = directory / "config" / "colors.json"
    colors_file.write_text(
        json.dumps({"mPrimary": "#123456", "mOnSurface": "#80402010"})
    )
    shutil.copyfile(ROOT / "Tests/Qml/ColorFileHarness.qml", directory / "shell.qml")
    log_path = directory / "custom-colors.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 12
            while "COLOR_FILE_LOAD_PASS" not in log_path.read_text():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise AssertionError(
                        "custom palette did not load:\n" + log_path.read_text()
                    )
                time.sleep(0.05)
            colors_file.write_text(
                json.dumps({"mPrimary": "#abcdef", "mOnSurface": "#40203040"})
            )
            process.wait(timeout=12)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
    output = log_path.read_text()
    print(output, end="")
    if any(level in output for level in (" WARN ", " ERROR ", " FATAL ")):
        raise AssertionError("custom palette harness must run without warnings/errors")
    if process.returncode != 0 or "COLOR_FILE_RELOAD_PASS" not in output:
        raise AssertionError(
            f"custom palette reload failed (exit {process.returncode})"
        )


def main():
    with tempfile.TemporaryDirectory(prefix="noctalia-color-namespace-") as temporary:
        directory = Path(temporary)
        commons = directory / "Commons"
        commons.mkdir(mode=0o700)
        shutil.copyfile(ROOT / "Commons/NColor.qml", commons / "NColor.qml")
        config_path = json.dumps(str(directory / "config") + "/")
        (commons / "Settings.qml").write_text(
            SETTINGS.replace("CONFIG_PATH", config_path)
        )
        (commons / "Logger.qml").write_text(LOGGER)
        shutil.copyfile(
            ROOT / "Tests/Qml/ColorNamespaceHarness.qml", directory / "shell.qml"
        )

        # Remove desktop/session connections and isolate every writable user path.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
            and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
        }
        for variable, name in {
            "HOME": "home",
            "XDG_CONFIG_HOME": "config",
            "XDG_CACHE_HOME": "cache",
            "XDG_DATA_HOME": "data",
            "XDG_STATE_HOME": "state",
            "XDG_RUNTIME_DIR": "runtime",
        }.items():
            path = directory / name
            path.mkdir(mode=0o700)
            environment[variable] = str(path)
        (directory / "config" / "colors.json").write_text("{}\n")
        environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if " WARN " in output:
            raise AssertionError("isolated palette harness must run without warnings")
        if result.returncode != 0 or "COLOR_NAMESPACE_PASS" not in output:
            raise AssertionError(
                f"offscreen palette/window test failed (exit {result.returncode})"
            )
        test_custom_file_reload(directory, environment)


if __name__ == "__main__":
    main()
