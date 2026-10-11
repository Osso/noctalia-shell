#!/usr/bin/env python3
"""OSD cold-start/reload through Quickshell's real qs resolver, no surfaces."""

import hashlib
import importlib.util
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/OSD/OSD.qml")


def stage(directory):
    spec = importlib.util.spec_from_file_location(
        "osd_fixtures", ROOT / "Tests/osd-warnings.test.py"
    )
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    fixtures.stage_osd(directory)
    # Use installed Quickshell and its real qs module scanner.
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    (directory / "shell.qml").write_text("""import QtQuick
import Quickshell
import qs.Modules.OSD
import Quickshell.Io
ShellRoot {
  IpcHandler {
    target: "osd-test"
    function reload(): void { Quickshell.reload(false); }
  }
  OSD { Component.onCompleted: console.log("OSD_RESOLUTION_READY") }
}
""")


def private_environment(directory):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="wayland",
        QT_QUICK_BACKEND="software",
        QS_NO_RELOAD_POPUP="1",
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/osd-resolution-system",
    )
    return environment


def wait_message(process, selector, output, marker, allow_failure=False):
    deadline = time.monotonic() + 10
    start = len(output)
    while time.monotonic() < deadline:
        for key, _ in selector.select(0.1):
            chunk = os.read(key.fileobj.fileno(), 65536).decode()
            output.append(chunk)
            print(chunk, end="", flush=True)
            if not allow_failure:
                assert "Failed to load configuration" not in chunk, "".join(output)
                assert "is not a type" not in chunk, "".join(output)
            if marker in "".join(output[start:]):
                return
        assert process.poll() is None, "".join(output)
    raise AssertionError("OSD load timed out:\n" + "".join(output))


def resolution(directory, mode):
    stage(directory)
    source = directory / TARGET
    production = source.read_bytes()
    if mode != "cold-start":
        source.write_text(
            "import QtQuick\nimport Quickshell\nVariants { model: []; delegate: Component { QtObject {} } }\n"
        )
    environment = private_environment(directory)
    output = []
    with (
        subprocess.Popen(
            ["cage", "--", "quickshell", "--no-color", "-p", str(directory)],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        ) as process,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            wait_message(process, selector, output, "OSD_RESOLUTION_READY")
            if mode == "reload-after-failure":
                # Introduce an inline type into a previously loaded module, the
                # exact lifetime boundary missed by fresh qmltestrunner engines.
                source.write_text("""import QtQuick
import Quickshell
Variants {
  model: []
  delegate: OsdLoader {}
  component OsdLoader: Loader {}
}
""")
                wait_message(process, selector, output, "OsdLoader is not a type", True)
            if mode != "cold-start":
                source.write_bytes(production)
                if mode == "reload-after-failure":
                    # Failed generations restore file watchers asynchronously.
                    # Explicit private IPC reload tests recovery after failure,
                    # without racing that restoration or touching canonical IPC.
                    result = subprocess.run(
                        [
                            "quickshell",
                            "ipc",
                            "--path",
                            str(directory),
                            "--any-display",
                            "call",
                            "osd-test",
                            "reload",
                        ],
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    assert result.returncode == 0, result.stdout + result.stderr
                wait_message(
                    process,
                    selector,
                    output,
                    "OSD_RESOLUTION_READY",
                    mode == "reload-after-failure",
                )
        finally:
            spec = importlib.util.spec_from_file_location(
                "osd_cleanup", ROOT / "Tests/osd-warnings.test.py"
            )
            fixtures = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fixtures)
            fixtures.stop_process_group(process)
            tail, _ = process.communicate(timeout=5)
            output.append(tail)
            print(tail, end="")
    if mode != "reload-after-failure":
        assert "Failed to load configuration" not in "".join(output)
    print("OSD_RESOLUTION_PASS", mode)


def main():
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    with tempfile.TemporaryDirectory(prefix="noctalia-osd-resolution-") as temporary:
        directory = Path(temporary)
        if original is not None:
            backup = directory / "settings.backup.json"
            backup.touch(mode=0o600)
            backup.write_bytes(original)
            assert (
                hashlib.sha256(backup.read_bytes()).digest()
                == hashlib.sha256(original).digest()
            )
        try:
            for index, mode in enumerate(
                ("cold-start", "reload", "reload-after-failure")
            ):
                case = directory / str(index)
                case.mkdir(mode=0o700)
                resolution(case, mode)
        finally:
            assert (settings.read_bytes() if settings.exists() else None) == original


if __name__ == "__main__":
    main()
