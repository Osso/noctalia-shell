#!/usr/bin/env python3
"""Production NotificationService with inert delivery, storage and surface boundaries.

Offscreen QtTest never launches Quickshell or creates a desktop layer surface.
The empty-mask contract is observed through a fixture, not compositor input delivery.
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

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/System/NotificationService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--json",
            "-",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    (directory / "lint.json").write_text(result.stdout)
    print(result.stderr, end="")
    warnings = json.loads(result.stdout)["files"][0]["warnings"]
    counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
    for warning in warnings:
        print(warning["line"], warning["id"], warning["message"])
    print("NOTIFICATION_SERVICE_LINT", dict(counts))
    assert result.returncode == 0, result.returncode
    # Unbound Component owner/adapter IDs and upstream type inference remain.
    assert counts == {
        "unqualified": 10,
        "missing-property": 2,
        "unresolved-type": 1,
        "uncreatable-type": 1,
    }, dict(counts)


def stage_runtime(directory):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "Quickshell": singleton("""property var commands: []
function env(name) { return ""; }
function execDetached(argv) { commands = commands.concat([argv]); }"""),
            "PanelWindow": "import QtQuick\nItem { property color color; property QtObject mask; visible: false }",
            "Region": "import QtQuick\nQtObject { readonly property bool empty: true }",
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("property int writes: 0"),
            "FileView": """import QtQuick
Item {
  property string path
  property bool printErrors
  signal loaded()
  signal loadFailed(int error)
  function writeAdapter() { FixtureIo.writes++; }
}""",
            "JsonAdapter": "import QtQuick\nQtObject {}",
        },
    )
    write(
        directory,
        "Quickshell.Services.Notifications",
        {
            "Notification": """import QtQuick
QtObject {
  property int id
  property string summary
  property string body: "Body"
  property string appName: "Fixture"
  property string desktopEntry
  property int urgency: 1
  property int expireTimeout: 0
  property string appIcon
  property string image
  property var actions: []
  property bool tracked: false
  property int dismissals: 0
  signal closed()
  function dismiss() { dismissals++; }
}""",
            "NotificationServer": """import QtQuick
QtObject {
  property bool keepOnReload
  property bool imageSupported
  property bool actionsSupported
  signal notification(Notification notification)
}""",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""property bool isLoaded: false
property var data: ({notifications: {enabled: true, lowUrgencyDuration: 3, normalUrgencyDuration: 8, criticalUrgencyDuration: 15}})
property string cacheDir: "/fixture/"
property string cacheDirImagesNotifications: "/fixture/images/"
signal settingsLoaded()
signal settingsSaved()"""),
            "NColor": singleton('property color transparent: "transparent"'),
            "ShellState": singleton("""property bool isLoaded: false
property real lastSeenTs: 1234
function getNotificationsState() { return {lastSeenTs: lastSeenTs}; }
function setNotificationsState(value) { lastSeenTs = value.lastSeenTs; }"""),
            "Time": singleton("property real timestamp: 12"),
            "Logger": singleton("""function e(...args) { console.error(...args); }
function d(...args) {}"""),
            "I18n": singleton("function tr(key) { return key; }"),
            "ThemeIcons": singleton('function iconFromName(name) { return ""; }'),
        },
    )
    write(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": singleton(
                "property bool noctaliaPerformanceMode: false"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton("""property var messages: []
function showNotice(...args) { messages = messages.concat([args]); }"""),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "NotificationService": (ROOT / TARGET).read_text(),
        },
    )
    helpers = directory / "qs/Helpers"
    helpers.mkdir(parents=True)
    shutil.copyfile(ROOT / "Helpers/sha256.js", helpers / "sha256.js")
    shutil.copyfile(
        ROOT / "Tests/Qml/NotificationServiceHarness.qml", directory / "tst_service.qml"
    )


def runtime(directory):
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
        )
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
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
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    args = parser.parse_args()
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-notification-service-"
    ) as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        backup = directory / "settings.backup"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        digest = hashlib.sha256(original).hexdigest()
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        try:
            globals()[args.mode](directory)
        finally:
            assert settings.read_bytes() == original, "real settings changed"
            print("SETTINGS_SHA256", digest)


if __name__ == "__main__":
    main()
