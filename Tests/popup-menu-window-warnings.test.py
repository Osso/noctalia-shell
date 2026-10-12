#!/usr/bin/env python3
"""Bounded popup-window lint and isolated, non-desktop production lifecycle.

Production PanelWindow, Loader and layer-shell bindings remain real. Only
PanelService and tray content are inert fixtures; no real menu or settings load.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/MainScreen/PopupMenuWindow.qml")


def helper():
    spec = importlib.util.spec_from_file_location(
        "popup_window_helpers", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper().stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("POPUP_WINDOW_LINT_COUNTS", dict(counts))
    # Installed WindowInterface metadata makes PanelWindow uncreatable and
    # exposes screen/contentItem despite this component's existing public API.
    assert counts == {"uncreatable-type": 1, "property-override": 2}, dict(counts)
    overrides = re.findall(
        r'Property "([^"]+)" already exists in base type "WindowInterface"', output
    )
    assert sorted(overrides) == ["contentItem", "screen"], overrides
    assert result.returncode in (0, 255), result.returncode
    print("POPUP_WINDOW_LINT_PASS")


def stage_runtime(directory):
    target = directory / TARGET
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / TARGET, target)
    write = helper().write_singleton
    write(directory / "Commons", "NColor", 'property color transparent: "transparent"')
    write(
        directory / "Services/UI",
        "PanelService",
        """property var registeredWindow: null
property var registeredScreen: null
property string removedKey: ""
property int removals: 0
function registerPopupMenuWindow(screen, window) {
  registeredScreen = screen;
  registeredWindow = window;
}
function unregisterPopupMenuWindow(key, window) {
  if (registeredWindow !== window) throw new Error("wrong popup unregister");
  removedKey = key;
  registeredWindow = null;
  removals++;
}
""",
    )
    tray = directory / "Modules/Bar/Extras"
    tray.mkdir(parents=True)
    (tray / "TrayMenu.qml").write_text("""import QtQuick
import Quickshell
Item {
  property ShellScreen screen
  property int hiddenCount: 0
  function hideMenu() { hiddenCount++; }
}
""")
    shutil.copyfile(
        ROOT / "Tests/Qml/PopupMenuWindowWarningsHarness.qml", directory / "shell.qml"
    )


def runtime(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    if original is not None:
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
    stage_runtime(directory)
    environment = helper().isolate_environment(directory)
    for variable in ("NIRI_SOCKET", "HYPRLAND_INSTANCE_SIGNATURE", "SWAYSOCK"):
        environment.pop(variable, None)
    # Qt offscreen has no PanelWindow backend. A private headless Wayland
    # compositor exercises the real backend without an active desktop socket.
    environment.update(
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QT_QPA_PLATFORM="wayland",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/popup-test",
    )
    process = subprocess.Popen(
        ["cage", "--", "quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        try:
            stdout, stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            stop_process_group(process)
            stdout, stderr = process.communicate(timeout=3)
            print(stdout + stderr, end="")
            raise
        output = stdout + stderr
        print(output, end="")
        assert process.returncode == 0, process.returncode
        assert "POPUP_WINDOW_RUNTIME_PASS" in output, output
        platform_warnings = re.findall(
            r"^.* WARN: Failed to initialize layershell integration$", output, re.M
        )
        print("POPUP_WINDOW_PLATFORM_WARNINGS", len(platform_warnings))
        diagnostics = [
            line
            for line in output.splitlines()
            if re.search(
                r" WARN[: ]| ERROR[: ]| FATAL[: ]|ReferenceError|TypeError|Binding loop",
                line,
            )
        ]
        assert diagnostics == platform_warnings, diagnostics
    finally:
        stop_process_group(process)
        assert (settings.read_bytes() if settings.exists() else None) == original, (
            "real settings changed"
        )


def stop_process_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-popup-window-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        {"lint": lint, "runtime": runtime}[args.mode](directory)
