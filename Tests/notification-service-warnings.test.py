#!/usr/bin/env python3
"""Production NotificationService with inert delivery, storage and surface boundaries.

Offscreen QtTest never launches Quickshell or creates a desktop layer surface.
The empty-mask contract is observed through a fixture, not compositor input delivery.
"""

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
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/System/NotificationService.qml")
HOST_CONFIG = Path("/home/osso/.config")
HOST_CONFIG_RESOLVED = HOST_CONFIG.resolve()


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
    # Component captures resolve; adapter and upstream type inference remain.
    assert counts == {
        "unqualified": 2,
        "missing-property": 2,
        "unresolved-type": 1,
        "uncreatable-type": 1,
    }, dict(counts)


def stage_runtime(directory, owner_shadow=False):
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
  property bool closeAfterDismiss: false
  signal closed()
  function dismiss() {
    dismissals++;
    if (closeAfterDismiss)
      Qt.callLater(() => closed());
  }
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
    if owner_shadow:
        service = directory / "qs/Services/System/NotificationService.qml"
        # Component-local properties collide with the service's lexical root ID.
        source = service.read_text()
        for boundary, handler in (
            ("    NotificationServer {\n", "handleNotification(notification)"),
            ("    Connections {\n", "updateNotificationFromObject(id)"),
        ):
            assert source.count(boundary) == 1, boundary
            source = source.replace(
                boundary,
                boundary
                + "      property QtObject root: QtObject {\n"
                + f"        function {handler} {{}}\n"
                + "      }\n",
            )
        service.write_text(source)
    helpers = directory / "qs/Helpers"
    helpers.mkdir(parents=True)
    shutil.copyfile(ROOT / "Helpers/sha256.js", helpers / "sha256.js")
    shutil.copyfile(
        ROOT / "Tests/Qml/NotificationServiceHarness.qml", directory / "tst_service.qml"
    )
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir>"
        "<cachedir>/tmp/XDG_CACHE_HOME/fontconfig</cachedir></fontconfig>"
    )


def run_isolated(directory, command, timeout):
    environment = {"PATH": "/usr/bin"}
    sandbox_directories = []
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = "/tmp/" + key
        sandbox_directories.extend(["--dir", path, "--chmod", "0700", path])
        environment[key] = path
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        FONTCONFIG_FILE=str(directory / "fonts.conf"),
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent",
    )
    return subprocess.run(
        [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            *sandbox_directories,
            "--ro-bind",
            str(directory),
            str(directory),
            "--chdir",
            str(directory),
            *command,
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def lint_harness(directory, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_service.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "  id: root\n"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker + "  property int injectedWarning: root.missingLintProbe\n",
                1,
            )
        )
    result = run_isolated(
        directory,
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            str(harness),
        ],
        60,
    )
    (directory / "harness.lint.json").write_text(result.stdout)
    print(result.stdout, end="")
    print(result.stderr, end="")
    report = json.loads(result.stdout)
    counts = Counter(
        warning["type"] for entry in report["files"] for warning in entry["warnings"]
    )
    print(
        "NOTIFICATION_SERVICE_HARNESS_LINT_COUNTS",
        dict(counts),
        "exit",
        result.returncode,
    )
    return result.returncode


def lint_harness_regression(directory):
    clean = directory / "clean"
    clean.mkdir()
    assert lint_harness(clean) == 0, "clean harness lint failed"
    injected = directory / "injected"
    injected.mkdir()
    assert lint_harness(injected, True) != 0, "genuine warning was accepted"
    print("NOTIFICATION_SERVICE_HARNESS_WARNING_REJECTED")


def runtime(directory, owner_shadow=False):
    stage_runtime(directory, owner_shadow)
    result = run_isolated(
        directory,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_service.qml"),
            "-import",
            str(directory),
        ],
        45,
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert result.returncode == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Fontconfig error",
        output,
    ), output


def deny_host_config(event, args):
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).absolute()
        if path.is_relative_to(HOST_CONFIG) or path.resolve().is_relative_to(
            HOST_CONFIG_RESOLVED
        ):
            raise PermissionError(f"host config access denied: {path}")
    if event == "socket.connect":
        raise PermissionError("network access denied in notification service fixture")


def main():
    sys.addaudithook(deny_host_config)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "lint-harness-regression", "runtime")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--owner-shadow", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-notification-service-"
    ) as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        environment_directory = directory / "environment"
        environment_directory.mkdir(mode=0o700)
        environment = helper("media-mini-warnings").isolate_environment(
            environment_directory
        )
        os.environ.clear()
        os.environ.update(environment)
        try:
            sys.audit("open", "/home/osso/.config/noctalia/settings.json", "r", 0)
        except PermissionError:
            print("NOTIFICATION_SERVICE_HOST_CONFIG_DENIED")
        else:
            raise AssertionError("host config audit guard failed")
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        elif args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            if args.mode == "lint":
                lint(directory)
            else:
                runtime(directory, args.owner_shadow)


if __name__ == "__main__":
    main()
