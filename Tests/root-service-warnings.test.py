#!/usr/bin/env python3
"""Six-service root lint slice and production services with inert I/O boundaries."""

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
    Path(f"Services/{name}.qml")
    for name in (
        "Compositor/CompositorService",
        "Control/IPCService",
        "Hardware/BrightnessService",
        "Media/AudioService",
        "Networking/BluetoothService",
        "System/NotificationService",
    )
]


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    remaining = []
    for service in SERVICES:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "--json",
                "-",
                "-I",
                str(directory),
                str(directory / "qs" / service),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        (directory / f"{service.stem}.json").write_text(result.stdout)
        warnings = json.loads(result.stdout)["files"][0]["warnings"]
        counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
        eligible = [
            w
            for w in warnings
            if any(
                s.get("isAutoApplicable")
                and any(
                    e["replacement"] == "root." and e["location"]["length"] == 0
                    for e in s.get("documentEdits", [])
                )
                for s in w.get("suggestions", [])
            )
        ]
        print(service, "WARNINGS", dict(counts), "ROOT_FIXITS", len(eligible))
        remaining.extend((str(service), w["line"]) for w in eligible)
    assert not remaining, remaining


def extend_module(directory, uri, sources):
    module = directory.joinpath(*uri.split("."))
    existing = {p.stem: p.read_text() for p in module.glob("*.qml")}
    helper("workspace-runtime").write_module(directory, uri, existing | sources)


def stage_wayland_attachment(directory):
    module = directory / "Quickshell/Wayland"
    module.mkdir(parents=True)
    source = module / "root-services-wayland.cpp"
    shutil.copyfile(ROOT / "Tests/fixtures/root-services-wayland.cpp", source)
    includes = subprocess.check_output(
        ["pkg-config", "--cflags", "Qt6Qml"], text=True
    ).split()
    subprocess.run(
        [
            "/usr/lib/qt6/moc",
            *includes,
            str(source),
            "-o",
            str(source.with_suffix(".moc")),
        ],
        check=True,
        timeout=30,
    )
    flags = subprocess.check_output(
        ["pkg-config", "--cflags", "--libs", "Qt6Qml"], text=True
    ).split()
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-shared",
            "-fPIC",
            "-Wall",
            "-Wextra",
            str(source),
            "-o",
            str(module / "libfixturewayland.so"),
            *flags,
        ],
        check=True,
        timeout=60,
    )
    (module / "qmldir").write_text("module Quickshell.Wayland\nplugin fixturewayland\n")


def stage_runtime(directory):
    helper("simple-service-warnings").stage_runtime(directory)
    (directory / "tst_services.qml").unlink()
    stage_wayland_attachment(directory)
    singleton = helper("workspace-runtime").singleton
    extend_module(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem { property string reloadableId }",
            "ShellScreen": "import QtQuick\nQtObject { property string name; property string model }",
            "ObjectModel": "import QtQuick\nQtObject { property var values: [] }",
            "Quickshell": singleton("""property var screens: []
property var commands: []
function env(name) { return name === "NIRI_SOCKET" ? "fixture" : ""; }
function execDetached(argv) { commands = commands.concat([argv]); }"""),
            "PanelWindow": """import QtQuick
import Quickshell
Item { property ShellScreen screen: Quickshell.screens.length > 1 ? Quickshell.screens[1] : null; property QtObject mask; property color color; visible: false }""",
            "Region": "import QtQuick\nQtObject {}",
            "Variants": """import QtQuick
QtObject { property var model; property var instances: []; default property Component delegate }""",
        },
    )
    extend_module(
        directory,
        "Quickshell.Io",
        {
            "IpcHandler": "import QtQuick\nQtObject { property string target }",
            "FileView": """import QtQuick
Item {
  property string path
  property bool printErrors: false
  property bool watchChanges: false
  signal loaded()
  signal loadFailed(int error)
  signal fileChanged()
  function writeAdapter() { FixtureIo.writes++; }
}""",
        },
    )
    extend_module(
        directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["brightness"]["enableDdcSupport"] = False
    defaults["notifications"]["enabled"] = False
    settings = "component FixtureData: QtObject {\n"
    settings += (
        "component BrightnessSettings: QtObject {\n"
        + "\n".join(
            f"property {'bool' if isinstance(v, bool) else 'real'} {k}: {json.dumps(v)}"
            for k, v in defaults["brightness"].items()
        )
        + "\n}\nproperty BrightnessSettings brightness: BrightnessSettings {}\n"
    )
    for name in ("notifications", "general", "bar"):
        settings += f"property var {name}: {json.dumps(defaults[name])}\n"
    settings += (
        "}\nproperty FixtureData data: FixtureData {}\nproperty bool isLoaded: false\n"
    )
    settings += 'property string cacheDir: "/fixture/"\nproperty string cacheDirImagesNotifications: "/fixture/images/"\n'
    settings += "signal settingsLoaded()\nsignal settingsSaved()"
    extend_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(settings),
            "NColor": singleton('property color transparent: "transparent"'),
            "ShellState": singleton("""property bool isLoaded: false
property var display: ({})
function getDisplay() { return display; }
function setDisplay(value) { display = value; }
function getNotifications() { return {lastSeenTs: 0}; }
function setNotifications(value) {}"""),
        },
    )
    backend = """import QtQuick
Item {
  property ListModel workspaces: ListModel {}
  property var windows: []
  property int focusedWindowIndex: -1
  property bool initialized: false
  signal workspaceChanged()
  signal activeWindowChanged()
  signal windowListChanged()
  function initialize() { initialized = true; }
}"""
    extend_module(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": (ROOT / SERVICES[0]).read_text(),
            "FixtureCompositor": singleton("property NiriService backend"),
            "NiriService": backend.replace(
                "Item {",
                "Item {\n  id: backend\n  Component.onCompleted: FixtureCompositor.backend = backend",
            ),
            **{name + "Service": backend for name in ("Sway", "Hyprland", "Mango")},
        },
    )
    extend_module(
        directory,
        "qs.Services.Media",
        {
            name: singleton("")
            for name in (
                "AudioService",
                "MediaService",
                "CavaService",
                "ScreenRecorderService",
            )
        },
    )
    extend_module(
        directory,
        "qs.Services.Networking",
        {
            "NetworkService": singleton(
                "property var requests: []; function setWifiEnabled(value) { requests = requests.concat([value]); }"
            ),
        },
    )
    for service in (SERVICES[1], SERVICES[2], SERVICES[4], SERVICES[5]):
        extend_module(
            directory,
            "qs." + ".".join(service.parent.parts),
            {
                service.stem: (ROOT / service).read_text(),
            },
        )
    extend_module(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton(
                "component LockScreen: QtObject { property bool active: false; property var item: null }\n"
                "property LockScreen lockScreen: LockScreen {}"
            ),
        },
    )
    extend_module(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": singleton(
                "property bool noctaliaPerformanceMode: false"
            ),
        },
    )
    extend_module(
        directory, "qs.Services.Theming", {"ColorSchemeService": singleton("")}
    )
    extend_module(
        directory,
        "Quickshell.Bluetooth",
        {
            "BluetoothAdapter": """import QtQuick
import Quickshell
QtObject { property int state: BluetoothAdapterState.Disabled; property bool enabled: false
property bool discovering: false; property ObjectModel devices: ObjectModel {} }""",
            "Bluetooth": singleton(
                "property BluetoothAdapter defaultAdapter: BluetoothAdapter {}"
            ),
            "BluetoothAdapterState": "import QtQuick\nQtObject { enum State { Disabled, Enabled, Enabling, Disabling, Blocked } }",
            "BluetoothDeviceState": "import QtQuick\nQtObject { enum State { Disconnected, Connected, Disconnecting, Connecting } }",
        },
    )
    extend_module(
        directory,
        "Quickshell.Services.Notifications",
        {
            "Notification": "import QtQuick\nQtObject {}",
            "NotificationServer": "import QtQuick\nQtObject { property bool keepOnReload; property bool imageSupported; property bool actionsSupported; signal notification(var notification) }",
        },
    )
    for source in ("Helpers/BrightnessParsing.js", "Helpers/sha256.js"):
        target = directory / "qs" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    shutil.copyfile(
        ROOT / "Tests/Qml/RootServiceHarness.qml", directory / "tst_root.qml"
    )


def lint_harness(directory):
    stage_runtime(directory)
    return check_harness(directory, directory / "tst_root.qml")


def behavior(directory):
    stage_runtime(directory)
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and k
        not in (
            "HOME",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
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
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    (directory / "behavior.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    directory = args.artifacts or Path(
        tempfile.mkdtemp(prefix="noctalia-root-services-")
    )
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    backup = directory / "settings.backup"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    try:
        if args.mode == "lint-harness":
            return lint_harness(directory)
        globals()[args.mode](directory)
        return 0
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        if not args.artifacts:
            shutil.rmtree(directory)


if __name__ == "__main__":
    raise SystemExit(main())
