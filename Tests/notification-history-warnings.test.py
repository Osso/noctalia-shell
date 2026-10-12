#!/usr/bin/env python3
"""Production history panel on offscreen QtTest; inert panel/widgets/services.

Real Repeater, list layout, filtering and handlers; no shell, toast, persistence,
compositor, desktop input or full widget rendering proof.
"""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/NotificationHistory/NotificationHistoryPanel.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
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
    print("HISTORY_LINT_COUNTS", dict(counts))
    assert not counts, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory):
    helpers = helper("workspace-runtime.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    for uri in (
        "Quickshell",
        "Quickshell.Services.Notifications",
        "Quickshell.Wayland",
    ):
        write(directory, uri, {"Inert": "import QtQuick\nQtObject {}"})
    style = dict(
        uiScaleRatio=1,
        marginXS=2,
        marginS=4,
        marginM=8,
        marginL=12,
        radiusM=8,
        radiusL=12,
        borderS=1,
        baseWidgetSize=32,
        fontSizeXXS=8,
        fontSizeXS=10,
        fontSizeS=11,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXXL=20,
        fontWeightBold=700,
        opacityMedium=0.5,
        animationFast=0,
    )
    colors = dict(
        transparent="transparent",
        mPrimary="#00ff00",
        mOnPrimary="#000000",
        mHover="#404040",
        mOnHover="#ffffff",
        mOnSurface="#ffffff",
        mSurfaceVariant="#202020",
        mOnSurfaceVariant="#cccccc",
        mOutline="#808080",
        mError="#ff0000",
        mSecondary="#abcdef",
    )
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "Settings": singleton(
                "property var data: ({general: {animationDisabled: true}})"
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "Time": singleton(
                "function formatRelativeTime(ts) { return new Date(ts).toISOString(); }"
            ),
            "NotificationService": singleton("""
property ListModel historyList: ListModel {}
property bool doNotDisturb: false
property int seenCount: 0
property var removed: []
function updateLastSeenTs() { seenCount++; }
function removeFromHistory(id) {
  removed = removed.concat([id]);
  for (let i = 0; i < historyList.count; i++) {
    if (historyList.get(i).id === id) { historyList.remove(i); return; }
  }
  throw new Error("Unknown notification " + id);
}
function clearHistory() { historyList.clear(); }
"""),
        },
    )
    write(
        directory,
        "qs.Modules.MainScreen",
        {
            "SmartPanel": """import QtQuick
Item {
  property Component panelContent
  property real preferredWidth
  property real preferredHeight
  property int closeCount: 0
  property alias contentItem: loader.item
  signal opened()
  function close() { closeCount++; }
  Loader { id: loader; anchors.fill: parent; sourceComponent: parent.panelContent }
}"""
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NBox": "import QtQuick\nRectangle {}",
            "NText": "import QtQuick\nText { property real pointSize; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NImageRounded": """import QtQuick
Item { property real radius; property string imagePath; property color borderColor
property real borderWidth; property string fallbackIcon; property real fallbackIconSize }""",
            "NIconButton": """import QtQuick
Item { property string icon; property string tooltipText; property real baseSize
width: baseSize; height: baseSize; signal clicked() }""",
            "NButton": """import QtQuick
Item { property string text; property real fontSize; property bool outlined
property bool hovered: false; property color backgroundColor; property color textColor
property color hoverColor; signal clicked() }""",
            "NScrollView": "import QtQuick.Controls\nScrollView {}",
        },
    )
    write(
        directory,
        "qs.Modules.Panels.NotificationHistory",
        {
            "NotificationHistoryPanel": (ROOT / TARGET).read_text(),
        },
    )
    (directory / "tst_history.qml").write_text(
        (ROOT / "Tests/Qml/NotificationHistoryWarningsHarness.qml").read_text()
    )


def isolate_environment(directory):
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent/session",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent/system",
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
    return environment


def runtime(directory):
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_history.qml"),
            "-import",
            str(directory),
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def run_sandboxed(args):
    directory = args.sandbox
    safety = helper("image-shadow-warnings.test.py")
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for parent in ("/home/osso", safety.PROTECTED[1]):
        assert any(line.split()[4] == parent and " - tmpfs " in line for line in mounts)
    for prefix in safety.PROTECTED:
        try:
            Path(prefix + "/noctalia/settings.json").read_bytes()
        except PermissionError:
            print("HISTORY_CONFIG_DENIED", prefix)
        else:
            raise AssertionError("config mask failed")
    environment = isolate_environment(directory)
    os.environ.clear()
    os.environ.update(environment)
    if args.mode == "lint":
        lint(directory)
        return
    stage_runtime(directory)
    if args.mode == "lint-harness":
        harness = directory / "tst_history.qml"
        if args.mutation:
            source = harness.read_text()
            harness.write_text(
                source.replace(
                    "  id: scene",
                    "  property int lintFailure: missingFixtureValue\n  id: scene",
                    1,
                )
            )
        raise SystemExit(check_harness(directory, harness))
    runtime(directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    parser.add_argument("--mutation", choices=("semantic",))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.mutation and args.mode != "lint-harness":
        parser.error("semantic mutation requires lint-harness")
    if args.sandbox:
        run_sandboxed(args)
        raise SystemExit(0)
    with tempfile.TemporaryDirectory(prefix="noctalia-history-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        command = [
            "bwrap",
            "--die-with-parent",
            "--unshare-all",
            "--new-session",
            "--ro-bind",
            "/",
            "/",
            "--perms",
            "000",
            "--tmpfs",
            "/home/osso",
            "--perms",
            "000",
            "--tmpfs",
            "/syncthing/Sync/Provisioning/config",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/run",
            "--bind",
            temporary,
            temporary,
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            temporary,
            "--",
            "/usr/bin/python3",
            str(Path(__file__).resolve()),
            args.mode,
            "--sandbox",
            temporary,
        ]
        if args.mutation:
            command.extend(("--mutation", args.mutation))
        result = subprocess.run(
            command,
            env={"PATH": "/usr/bin", "HOME": temporary, "LANG": "C.UTF-8"},
            check=False,
            timeout=90,
        )
        raise SystemExit(result.returncode)
