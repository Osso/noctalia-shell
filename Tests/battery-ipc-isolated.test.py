#!/usr/bin/env python3
"""Battery IPC retirement at native Quickshell registry/dispatch; private sandbox only."""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = "Services/Control/IPCService.qml"


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, expected):
    load_helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--max-warnings",
            "0",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "lint.log").write_text(output)
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("IPC_LINT", dict(counts), "exit", result.returncode)
    assert len(warnings) == expected, counts
    if expected == 0:
        assert result.returncode == 0, output


def stage_runtime(directory):
    owner = load_helper("ipc-idle-services-warnings")
    owner.stage_runtime(directory, None)
    # Keep real Quickshell types, registration, socket transport and dispatch.
    shutil.rmtree(directory / "Quickshell")
    (directory / "tst_services.qml").unlink()
    workspace = load_helper("workspace-runtime")
    # Offscreen has no native PanelWindow backend. Replace only the unused
    # screen-detection surface; all IpcHandlers and their bodies stay production.
    ipc_source = (
        (ROOT / TARGET)
        .read_text()
        .replace("      WlrLayershell.exclusionMode: ExclusionMode.Ignore\n", "")
        .replace(
            "sourceComponent: PanelWindow {", "sourceComponent: FixturePanelWindow {"
        )
    )
    workspace.write_module(
        directory,
        "qs.Services.Control",
        {
            "IPCService": ipc_source,
            "FixturePanelWindow": "import QtQuick\nItem { property var screen: null; property color color; property QtObject mask }",
        },
    )
    workspace.write_module(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": workspace.singleton(""),
            "IdleInhibitorService": workspace.singleton(""),
        },
    )
    workspace.write_module(
        directory,
        "qs.Services.UI",
        {
            "BarService": workspace.singleton("property bool isVisible: true"),
            "ToastService": workspace.singleton(""),
            "PanelService": workspace.singleton(""),
        },
    )
    workspace.write_module(
        directory,
        "qs.Services.Hardware",
        {
            "BatteryService": workspace.singleton(
                'function getIcon() { return "battery"; }'
            ),
            "BrightnessService": workspace.singleton(""),
            "AudioService": workspace.singleton(""),
        },
    )
    for module in (directory / "qs").iterdir():
        shutil.move(str(module), str(directory / module.name))
    (directory / "qs").rmdir()
    (directory / "shell.qml").write_text("""import QtQuick
import Quickshell
import Quickshell.Io
import qs.Services.Control
import qs.Services.UI
import qs.Services.Media

ShellRoot {
    IPCService { id: ipc }
    QtObject {
        id: batteryPanel
        property bool opened: false
        function toggle() { opened = !opened; }
    }
    IpcHandler {
        target: "fixture"
        function snapshot(): string {
            return JSON.stringify({barVisible: BarService.isVisible,
                batteryPanelOpen: batteryPanel.opened, seeks: MediaService.seeks});
        }
        // Probe helper behavior, not a production battery-panel IPC command.
        function toggleBatteryPanel() { ipc.togglePanel(batteryPanel); }
    }
}
""")
    environment = owner.private_environment(directory)
    environment["LANG"] = "C.UTF-8"
    return environment


def sandbox_argv(directory, argv):
    return [
        "bwrap",
        "--die-with-parent",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/home",
        "--tmpfs",
        "/syncthing",
        "--tmpfs",
        "/run",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--chdir",
        str(directory),
        "--",
        *argv,
    ]


def runtime(directory):
    environment = stage_runtime(directory)
    shell = directory / "shell.qml"
    with (directory / "runtime.log").open("w+") as log:
        process = subprocess.Popen(
            sandbox_argv(directory, ["quickshell", "--no-color", "-p", str(shell)]),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:

            def ipc(*args):
                result = subprocess.run(
                    sandbox_argv(
                        directory, ["quickshell", "ipc", "-p", str(shell), *args]
                    ),
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                print(
                    "IPC",
                    args,
                    "exit",
                    result.returncode,
                    result.stdout.strip(),
                    result.stderr.strip(),
                )
                return result

            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, (
                    "Private shell exited before registration"
                )
                registry = ipc("show")
                if registry.returncode == 0:
                    break
                assert time.monotonic() < deadline, "Private IPC registry timeout"
                time.sleep(0.1)
            assert "batteryManager" not in registry.stdout, registry.stdout
            assert "bar" in registry.stdout and "media" in registry.stdout, (
                registry.stdout
            )
            print("PASS removed target absent from native registry")
            for command in [
                ("cycle",),
                ("set", "full"),
                ("set", "balanced"),
                ("set", "lifespan"),
            ]:
                rejected = ipc("call", "batteryManager", *command)
                # Native Quickshell reports dispatch rejection in stdout but
                # returns zero; assert its explicit result, not shell exit status.
                assert rejected.returncode == 0, rejected
                assert rejected.stdout.strip() == "Target not found.", rejected
                assert rejected.stderr == "", rejected
            print("PASS removed commands fail explicitly at dispatch")

            def call(target, command, *args):
                result = ipc("call", target, command, *args)
                assert result.returncode == 0, result
                return result.stdout

            def snapshot():
                return json.loads(call("fixture", "snapshot"))

            assert snapshot() == {
                "barVisible": True,
                "batteryPanelOpen": False,
                "seeks": [],
            }
            call("bar", "toggle")
            assert snapshot()["barVisible"] is False
            call("bar", "toggle")
            assert snapshot()["barVisible"] is True
            call("media", "seekRelative", "-12.5")
            call("media", "seekByRatio", "0.75")
            assert snapshot()["seeks"] == [{"relative": -12.5}, {"ratio": 0.75}]
            print("PASS supported bar/media native dispatch and state")
            call("fixture", "toggleBatteryPanel")
            assert snapshot()["batteryPanelOpen"] is True
            call("fixture", "toggleBatteryPanel")
            assert snapshot()["batteryPanelOpen"] is False
            print("PASS production panel-toggle helper via private probe")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            log.seek(0)
            output = log.read()
            print(output, end="")
        assert not re.search(
            r"ReferenceError|TypeError|QWARN|QFATAL|QCRITICAL|Binding loop", output
        ), output
        print("PASS private process terminated; no runtime errors")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("runtime", "lint"), default="runtime", nargs="?"
    )
    parser.add_argument("--expected-warnings", type=int, default=0)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.artifacts:
        args.artifacts.mkdir(mode=0o700)
        directory = args.artifacts.resolve()
        if args.mode == "lint":
            lint(directory, args.expected_warnings)
        else:
            runtime(directory)
    else:
        with tempfile.TemporaryDirectory(prefix="noctalia-battery-ipc-") as temporary:
            directory = Path(temporary)
            if args.mode == "lint":
                lint(directory, args.expected_warnings)
            else:
                runtime(directory)


if __name__ == "__main__":
    main()
