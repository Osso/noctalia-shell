#!/usr/bin/env python3
"""Shell-root-only diagnostics and private Quickshell cold-start/source reload.

Real ShellRoot, Variants, Loader, timers and qs module scanner; fake Settings,
screens and every service/window leaf. Host config, desktop sockets, network and
hardware are absent. No teardown callbacks reach into deleted fixture singletons.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).absolute().parents[1]


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = helper("grid-list-warnings.test.py")
fixtures = helper("about-tab-warnings.test.py")


def lint(directory, environment):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    source = directory / "qs/shell.qml"
    source.write_text((ROOT / "shell.qml").read_text())
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "--max-warnings",
            "0",
            "--json",
            "-",
            "-I",
            str(directory),
            str(source),
        ],
        "shell-root-lint",
    )
    files = json.loads(output)["files"]
    assert len(files) == 1, files
    # JSON includes block-scope diagnostics omitted from Qt's text output.
    warnings = [
        diagnostic
        for diagnostic in files[0]["warnings"]
        if diagnostic["type"] in {"warning", "error"}
    ]
    counts = Counter(diagnostic["id"] for diagnostic in warnings)
    print("SHELL_ROOT_LINT_COUNTS", dict(counts), "TOTAL", len(warnings), "EXIT", code)
    assert not warnings, warnings
    assert code == 0, code


def stage_runtime(directory, mutation):
    write, singleton = fixtures.write_module, fixtures.singleton
    write(
        directory,
        "qs.TestScreens",
        {
            "TestScreen": "import QtQuick\nQtObject { property string name }",
            "TestScreens": singleton("property var screens: []"),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""enum BootstrapState { Error = 2 }
property int bootstrapState: 0
property bool ready: false
property bool isDebug: false
property bool shouldOpenSetupWizard: false
property string errorMessage: "first diagnostic"
property string settingsFile: "/fixture/settings-path"
property int retries: 0
function retryBootstrap() { retries++; }"""),
            "I18n": singleton("signal translationsLoaded()"),
            "ShellState": singleton("property bool isLoaded: false"),
            "Logger": singleton("function i(...args) {}"),
            "SettingsLoadError": """import QtQuick
import qs.TestScreens
Item {
  property TestScreen targetScreen
  property string message
  property string settingsPath
  signal retryRequested()
}""",
        },
    )
    service_modules = {
        "Control": ["HooksService"],
        "Location": ["LocationService", "NightLightService", "DarkModeService"],
        "Networking": ["BluetoothService"],
        "Noctalia": ["GitHubService", "UpdateService"],
        "Power": ["IdleInhibitorService", "PowerProfileService"],
        "System": ["HostService", "FontService"],
        "Theming": ["AppThemeService", "ColorSchemeService"],
        "UI": ["WallpaperService"],
        "Hardware": [],
    }
    for module, names in service_modules.items():
        sources = {}
        for name in names:
            body = "function init() {}"
            if name == "NightLightService":
                body += "\nfunction apply() {}"
            if name == "HostService":
                body += "\nproperty bool isReady: false\nproperty bool isNixOS: false\nproperty bool osInfoLoadFailed: false"
            if name == "UpdateService":
                body += "\nfunction showLatestChangelog() {}"
            if name == "WallpaperService":
                body = "function init() { PanelService.initializations++; }"
            sources[name] = singleton(body)
        if module == "Control":
            sources.update(
                ShellReload="import QtQuick\nItem {}",
                IPCService="import QtQuick\nItem {}",
            )
        if module == "UI":
            sources["PanelService"] = """pragma Singleton
import QtQuick
import qs.TestScreens
QtObject {
  id: panels
  property int initializations: 0
  property int opens: 0
  property TestScreen openedScreen
  function getPanel(name, screen) {
    if (name !== "setupWizardPanel") throw new Error("unexpected panel " + name);
    panels.openedScreen = screen;
    return panels;
  }
  function open() { panels.opens++; }
}"""
        write(
            directory,
            "qs.Services." + module,
            sources or {"UnusedBoundary": "import QtQuick\nItem {}"},
        )
    for module, names in {
        "Background": ["Background"],
        "Bar": [],
        "Dock": ["Dock"],
        "LockScreen": ["LockScreen"],
        "MainScreen": ["AllScreens", "Overview"],
        "Notification": ["Notification"],
        "OSD": ["OSD"],
        "Startup": [],
        "Toast": ["ToastOverlay"],
    }.items():
        write(
            directory,
            "qs.Modules." + module,
            {name: "import QtQuick\nItem {}" for name in names or ["UnusedBoundary"]},
        )
    write(
        directory,
        "qs.Probe",
        {
            "ShellRootWarningsProbe": (
                ROOT / "Tests/Qml/ShellRootWarningsProbe.qml"
            ).read_text()
        },
    )
    # Preserve the installed Quickshell module; substitute only synthetic screens.
    source = (
        (ROOT / "shell.qml")
        .read_text()
        .replace(
            "import Quickshell\n",
            "import Quickshell\nimport qs.TestScreens\nimport qs.Probe\n",
        )
    )
    source = source.replace("Quickshell.screens", "TestScreens.screens")
    source = source.replace(
        "property ShellScreen modelData", "property TestScreen modelData"
    )
    source = source.replace(
        "  Variants {", "  Variants {\n    id: testErrorVariants", 1
    )
    source = source.replace("  Loader {", "  Loader {\n    id: testFullLoader", 1)
    if mutation:
        source = source.replace("Settings.ready &&", "false &&", 1)
    source = (
        source[: source.rfind("}")]
        + """  ShellRootWarningsProbe {
    shell: shellRoot
    fullLoader: testFullLoader
    errorVariants: testErrorVariants
  }
}
"""
    )
    (directory / "qs/shell.qml").write_text(source)
    # Exercise Quickshell's real qs scanner rather than a test-only resolver.
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    (directory / "qs").rmdir()
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    return directory / "shell.qml"


def sandbox(directory, command):
    return [
        "bwrap",
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "--",
        *command,
    ]


def wait_ready(process, selector, output):
    deadline = time.monotonic() + 15
    start = len(output)
    while time.monotonic() < deadline:
        for key, _ in selector.select(0.1):
            chunk = os.read(key.fileobj.fileno(), 65536).decode()
            output.append(chunk)
            print(chunk, end="", flush=True)
            assert not re.search(
                r" WARN | ERROR | FATAL |ReferenceError|TypeError|SHELL_ROOT_ASSERT|Binding loop",
                chunk,
            ), "".join(output)
            if "SHELL_ROOT_RESOLUTION_READY 9 lifecycle cases" in "".join(
                output[start:]
            ):
                return
        assert process.poll() is None, "".join(output)
    raise AssertionError("shell-root ready timed out:\n" + "".join(output))


def runtime(directory, environment, mutation):
    source = stage_runtime(directory, mutation)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/bin/python3",
            "-c",
            """import pathlib, socket
for path in ("/home/osso/.config", "/syncthing", "/run/user", "/dev/dri", "/dev/input"):
 assert not pathlib.Path(path).exists(), path
sock = socket.socket(); sock.settimeout(1)
try: sock.connect(("1.1.1.1", 443))
except OSError: print("SHELL_ROOT_MASKS_NETWORK_PASS")
else: raise AssertionError("network accessible")
""",
        ],
        "shell-root-isolation",
    )
    assert code == 0 and "SHELL_ROOT_MASKS_NETWORK_PASS" in output, output
    trace = directory / "runtime.trace"
    output = []
    with (
        subprocess.Popen(
            [
                "strace",
                "-f",
                "-qq",
                "-e",
                "trace=%file",
                "-o",
                str(trace),
                *sandbox(directory, ["quickshell", "--no-color", "-p", str(directory)]),
            ],
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
            print("SHELL_ROOT_COLD_START_PASS")
            source.write_text(source.read_text() + "\n// private source reload\n")
            wait_ready(process, selector, output)
            print("SHELL_ROOT_SOURCE_RELOAD_PASS")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                tail, _ = process.communicate(timeout=5)
            output.append(tail.decode())
            print(tail.decode(), end="")
            assert process.poll() is not None
            assert "settings.json" not in trace.read_text(), (
                "child attempted settings I/O"
            )
            print("SHELL_ROOT_PRIVATE_PROCESS_EXITED; zero settings attempts")
    assert not re.search(
        r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop", "".join(output)
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-shell-root-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            lint(directory, environment)
        else:
            runtime(directory, environment, args.mutation)


if __name__ == "__main__":
    main()
