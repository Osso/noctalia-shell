#!/usr/bin/env python3
"""Private Background cold-start/source reload with the real Quickshell resolver.

Only production Background is loaded, with fixture services and invisible windows.
Host config, devices, desktop sockets and network are absent from the sandbox.
"""

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def load_background_tests():
    spec = importlib.util.spec_from_file_location(
        "background_tests", ROOT / "Tests/background-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RELOAD_PROBE = """
    Timer {
        property int shaderIndex: 0
        property var types: ["fade", "wipe", "disc", "stripes"]

        function check(condition, message) {
            if (!condition)
                throw new Error("BACKGROUND_RELOAD_ASSERT: " + message);

        }

        interval: 100
        running: true
        repeat: true
        onTriggered: {
            if (root.isStartupTransition)
                return ;

            currentWallpaper.source = Qt.resolvedUrl(Quickshell.shellDir + "/red.svg");
            nextWallpaper.source = Qt.resolvedUrl(Quickshell.shellDir + "/blue.svg");
            if (currentWallpaper.status !== Image.Ready || nextWallpaper.status !== Image.Ready)
                return ;

            check(root.monitorScreen !== null && root.monitorName.length > 0, "modelData handoff");
            root.transitionType = types[shaderIndex];
            root.transitionProgress = 0.37;
            const shader = shaderLoader.item;
            check(shader !== null, "shader creation");
            check(shader.source1 === currentWallpaper && shader.source2 === nextWallpaper, "lexical image IDs");
            check(shader.progress === root.transitionProgress, "progress binding");
            root.transitionProgress = 0.64;
            check(shader.progress === 0.64, "progress update");
            shaderLoader.active = false;
            check(shaderLoader.item === null, "unload");
            shaderLoader.active = true;
            check(shaderLoader.item !== null && shaderLoader.item !== shader, "recreation");
            check(shaderLoader.item.progress === 0.64, "recreated binding");
            console.log("BACKGROUND_RELOAD_SHADER", types[shaderIndex]);
            shaderIndex++;
            if (shaderIndex === types.length) {
                running = false;
                console.log("BACKGROUND_RESOLUTION_READY");
            }
        }
    }

"""


def stage(directory, fixtures):
    fixtures.stage_runtime(directory)
    shutil.rmtree(directory / "Quickshell")
    # Quickshell's actual qs module scanner expects Modules/, Commons/, Services/.
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    (directory / "qs").rmdir()
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    source = directory / fixtures.TARGET
    qml = source.read_text().replace(
        "sourceComponent: PanelWindow {",
        "sourceComponent: Window {\n      visible: false\n      width: 640; height: 360",
    )
    qml = re.sub(r"\n      anchors \{[^}]+\}", "", qml, count=1)
    qml = qml.replace(
        "Component.onCompleted: setWallpaperInitial()",
        "Component.onCompleted: setWallpaperInitial()" + RELOAD_PROBE,
    )
    source.write_text(qml)
    (directory / "shell.qml").write_text("""import QtQuick
import Quickshell
import qs.Modules.Background
ShellRoot {
  Background {}
  Connections {
    target: Quickshell
    function onReloadCompleted() { Quickshell.inhibitReloadPopup(); }
  }
}
""")
    return source


def wait_ready(process, selector, output):
    deadline = time.monotonic() + 15
    start = len(output)
    while time.monotonic() < deadline:
        for key, _ in selector.select(0.1):
            chunk = os.read(key.fileobj.fileno(), 65536).decode()
            output.append(chunk)
            print(chunk, end="", flush=True)
            assert not re.search(
                r" WARN | ERROR | FATAL |ReferenceError|TypeError|BACKGROUND_RELOAD_ASSERT",
                chunk,
            ), "".join(output)
            if "BACKGROUND_RESOLUTION_READY" in "".join(output[start:]):
                for shader in ("fade", "wipe", "disc", "stripes"):
                    assert "BACKGROUND_RELOAD_SHADER " + shader in "".join(
                        output[start:]
                    )
                return
        assert process.poll() is None, "".join(output)
    raise AssertionError("Background ready timed out:\n" + "".join(output))


def run_reload(directory, fixtures):
    source = stage(directory, fixtures)
    environment = fixtures.load_helpers(
        "media-mini-warnings.test.py"
    ).isolate_environment(directory)
    environment.update(
        QT_QPA_PLATFORM="wayland",
        WLR_BACKENDS="headless",
        WLR_RENDERER="pixman",
        WLR_LIBINPUT_NO_DEVICES="1",
        QS_NO_RELOAD_POPUP="1",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/background-test-system",
    )
    sandbox = fixtures.load_helpers("wallpaper-panel-warnings.test.py").sandbox_command
    isolation = subprocess.run(
        sandbox(
            directory,
            [
                "/usr/bin/python3",
                "-c",
                "import pathlib,socket\nfor p in ('/home/osso/.config','/syncthing','/run/user'):\n assert not pathlib.Path(p).exists(),p\ns=socket.socket();s.settimeout(1)\ntry:s.connect(('1.1.1.1',443))\nexcept OSError:print('BACKGROUND_MASKS_NETWORK_PASS')\nelse:raise AssertionError('network accessible')\n",
            ],
        ),
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert isolation.returncode == 0, isolation.stdout + isolation.stderr
    print(isolation.stdout, end="")
    output = []
    with (
        subprocess.Popen(
            sandbox(
                directory,
                ["cage", "--", "quickshell", "--no-color", "-p", str(directory)],
            ),
            cwd=directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            wait_ready(process, selector, output)
            print("BACKGROUND_COLD_START_PASS")
            source.write_text(source.read_text() + "\n// private source reload\n")
            wait_ready(process, selector, output)
            print("BACKGROUND_SOURCE_RELOAD_PASS")
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                tail, _ = process.communicate(timeout=5)
            print(tail.decode(), end="")
    assert process.poll() is not None
    print("BACKGROUND_PRIVATE_PROCESS_EXITED")


def main():
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    with tempfile.TemporaryDirectory(prefix="noctalia-background-reload-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert (
            hashlib.sha256(backup.read_bytes()).digest()
            == hashlib.sha256(original).digest()
        )
        try:
            run_reload(directory, load_background_tests())
        finally:
            assert settings.read_bytes() == original, "real settings changed"


if __name__ == "__main__":
    main()
