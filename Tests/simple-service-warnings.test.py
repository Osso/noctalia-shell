#!/usr/bin/env python3
"""Seven-service owner slice; actual QML with inert, controlled I/O boundaries.

Standalone modes. Process fixtures emit streams -> exited -> running=false;
no OS process, network, gamma, recorder or canonical shell is launched here.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
SERVICES = [
    Path("Services/Noctalia/GitHubService.qml"),
    Path("Services/Networking/NetworkService.qml"),
    Path("Services/Networking/VPNService.qml"),
    Path("Services/Media/CavaService.qml"),
    Path("Services/Media/ScreenRecorderService.qml"),
    Path("Services/Location/NightLightService.qml"),
    Path("Services/UI/BarService.qml"),
]


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    expected = {
        "NetworkService": {"unqualified": 5, "incompatible-type": 1},
        "ScreenRecorderService": {"missing-property": 4},
    }
    failures = []
    for service in SERVICES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / service),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / f"{service.stem}.log").write_text(output)
        counts = Counter(
            (re.findall(r"\[([^]]+)\]", line) or ["block-scope-var"])[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(service, "LINT_COUNTS", dict(counts))
        residual = expected.get(service.stem, {})
        if dict(counts) != residual or (not residual and result.returncode):
            failures.append((str(service), dict(counts), result.returncode))
    assert not failures, failures


def stage_runtime(directory):
    utilities = helper("workspace-runtime")
    write = utilities.write_module
    singleton = utilities.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nQtObject { default property list<QtObject> children }",
            "Quickshell": singleton("""property string shellDir: "/fixture"
property var commands: []
signal screensChanged()
function env(name) { return ""; }
function execDetached(argv) { commands = commands.concat([argv]); }"""),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("""property var processes: []
property int liveProcesses: 0
property int writes: 0
function find(prefix) {
  for (let i = processes.length - 1; i >= 0; i--) {
    const p = processes[i];
    if (p && p.command.join(" ").startsWith(prefix)) return p;
  }
  throw new Error("No process for " + prefix);
}"""),
            "Process": """import QtQuick
QtObject {
  id: process
  property bool running: false
  property var command: []
  property var environment: ({})
  property bool stdinEnabled: false
  property QtObject stdout
  property QtObject stderr
  property var input: []
  signal started()
  signal exited(int exitCode, int exitStatus)
  function write(value) { input = input.concat([value]); }
  function exec(options) { command = options.command; running = true; }
  function finish(code, output, error) {
    if (stdout) { stdout.text = output; stdout.streamFinished(); }
    if (stderr) { stderr.text = error; stderr.streamFinished(); }
    exited(code, 0);
    running = false;
  }
  onRunningChanged: { if (running) started(); }
  Component.onCompleted: {
    FixtureIo.processes = FixtureIo.processes.concat([process]);
    FixtureIo.liveProcesses++;
  }
  Component.onDestruction: {
    FixtureIo.processes = FixtureIo.processes.filter(p => p !== process);
    FixtureIo.liveProcesses--;
  }
}""",
            "StdioCollector": 'import QtQuick\nQtObject { property string text: ""; signal streamFinished() }',
            "SplitParser": "import QtQuick\nQtObject { signal read(string data) }",
            "JsonAdapter": "import QtQuick\nQtObject {}",
            "FileView": """import QtQuick
Item {
  property string path
  property bool watchChanges: false
  property bool printErrors: false
  signal fileChanged()
  signal adapterUpdated()
  signal loaded()
  signal loadFailed(var error)
  function reload() {}
  function writeAdapter() { FixtureIo.writes++; }
}""",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["screenRecorder"]["videoSource"] = "portal"
    defaults["nightLight"].update(enabled=False, forced=True)
    settings = 'property string cacheDir: "/fixture/"\nproperty string cacheDirImages: "/fixture/"\n'
    for name in ("network", "nightLight"):
        component = name[0].upper() + name[1:] + "Settings"
        settings += f"component {component}: QtObject {{\n"
        for key, value in defaults[name].items():
            kind = (
                "bool"
                if isinstance(value, bool)
                else "real"
                if isinstance(value, (int, float))
                else "var"
            )
            settings += f"property {kind} {key}: {json.dumps(value)}\n"
        settings += "}\n"
    settings += "component ServiceSettings: QtObject {\n"
    for name in ("network", "nightLight"):
        component = name[0].upper() + name[1:] + "Settings"
        settings += f"property {component} {name}: {component} {{}}\n"
    for name in ("audio", "screenRecorder", "bar"):
        settings += f"property var {name}: {json.dumps(defaults[name])}\n"
    settings += "}\nproperty ServiceSettings data: ServiceSettings {}\n"
    settings += "function preprocessPath(path) { return path; }"
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(settings),
            "Logger": singleton("""property var messages: []
function i(...args) {}
function d(...args) {}
function w(...args) { messages = messages.concat([args.join(" ")]); }
function e(...args) { messages = messages.concat([args.join(" ")]); }"""),
            "I18n": singleton("function tr(key, args) { return key; }"),
            "Time": singleton(
                'property real timestamp: 10000\nfunction getFormattedTimestamp() { return "fixture"; }'
            ),
            "Style": singleton("property int marginM: 8\nproperty int barHeight: 40"),
        },
    )
    modules = {}
    for service in SERVICES:
        uri = "qs." + ".".join(service.parent.parts)
        modules.setdefault(uri, {})[service.stem] = (ROOT / service).read_text()
    modules["qs.Services.UI"].update(
        {
            "ToastService": singleton("""property var messages: []
function showNotice(...args) { messages = messages.concat([args]); }
function showWarning(...args) { messages = messages.concat([args]); }
function showError(...args) { messages = messages.concat([args]); }"""),
            "PanelService": singleton(
                "property var lockScreen: null\nproperty var openedPanel: null"
            ),
        }
    )
    modules["qs.Services.Networking"]["BluetoothService"] = singleton(
        "property bool airplaneModeToggled: false"
    )
    modules["qs.Services.Location"]["LocationService"] = (
        singleton("""property bool coordinatesReady: false
property real stableLatitude: 32.78
property real stableLongitude: -96.8""")
    )
    modules["qs.Services.System"] = {
        "ProgramCheckerService": singleton("""property bool cavaAvailable: false
property bool gpuScreenRecorderAvailable: false
signal checksCompleted()""")
    }
    for uri, sources in modules.items():
        write(directory, uri, sources)
    shutil.copyfile(
        ROOT / "Tests/Qml/SimpleServiceHarness.qml", directory / "tst_services.qml"
    )


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_services.qml")


def behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and key
        not in (
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "SWAYSOCK",
            "HYPRLAND_INSTANCE_SIGNATURE",
        )
    }
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
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )
        output = result.stdout + result.stderr
        (directory / "behavior.log").write_text(output)
        print(output, end="")
        assert result.returncode == 0 and "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        assert backup.read_bytes() == original, "backup changed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    command = {"lint": lint, "behavior": behavior, "lint-harness": lint_harness}[
        args.mode
    ]
    if args.artifacts:
        args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
        return command(args.artifacts.resolve())
    with tempfile.TemporaryDirectory(prefix="noctalia-simple-services-") as temporary:
        return command(Path(temporary))


if __name__ == "__main__":
    raise SystemExit(main())
