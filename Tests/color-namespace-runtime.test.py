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
DEFAULT_COLORS = {
    "mPrimary": "#c7a1d8",
    "mOnPrimary": "#1a151f",
    "mSecondary": "#a984c4",
    "mOnSecondary": "#f3edf7",
    "mTertiary": "#e0b7c9",
    "mOnTertiary": "#20161f",
    "mError": "#e9899d",
    "mOnError": "#1e1418",
    "mSurface": "#1c1822",
    "mOnSurface": "#e9e4f0",
    "mSurfaceVariant": "#262130",
    "mOnSurfaceVariant": "#a79ab0",
    "mOutline": "#342c42",
    "mShadow": "#120f18",
    "mHover": "#e0b7c9",
    "mOnHover": "#20161f",
}
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
    initial_bytes = b'{"mPrimary": "#123456", "mOnSurface": "#80402010"}'
    reloaded_bytes = b'{"mPrimary": "#abcdef", "mOnSurface": "#40203040"}'
    colors_file.write_bytes(initial_bytes)
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
            assert colors_file.read_bytes() == initial_bytes
            colors_file.write_bytes(reloaded_bytes)
            process.wait(timeout=12)
            assert colors_file.read_bytes() == reloaded_bytes
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
        environment.update(
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            NOCTALIA_CONFIG_DIR=str(directory / "config"),
            NOCTALIA_CACHE_DIR=str(directory / "cache"),
        )
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
        assert (directory / "config" / "colors.json").read_bytes() == b"{}\n"
        test_custom_file_reload(directory, environment)
        colors_file = directory / "config" / "colors.json"
        colors_file.unlink()
        shutil.copyfile(
            ROOT / "Tests/Qml/ColorNamespaceHarness.qml", directory / "shell.qml"
        )
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0 and "COLOR_NAMESPACE_PASS" in output
        # Missing-file creation can race FileView's initial reload and report a
        # dropped operation; keep that diagnostic visible, not a palette failure.
        assert not any(level in output for level in (" ERROR ", " FATAL "))
        created_bytes = colors_file.read_bytes()
        assert json.loads(created_bytes) == DEFAULT_COLORS
        # A fresh process must reload the generated palette without rewriting it.
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0 and "COLOR_NAMESPACE_PASS" in output
        assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL "))
        assert colors_file.read_bytes() == created_bytes


if __name__ == "__main__":
    main()
