#!/usr/bin/env python3
"""Bounded AboutTab lint and offscreen production UI behavior; no host actions."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/AboutTab.qml")
SETTINGS = Path.home() / ".config/noctalia/settings.json"


def write_module(directory, name, sources):
    path = directory.joinpath(*name.split("."))
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for type_name, source in sources.items():
        (path / f"{type_name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{type_name} 1.0 {type_name}.qml\n")
    (path / "qmldir").write_text(f"module {name}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_behavior(directory):
    write_module(directory, "qs.Tabs", {"AboutTab": (ROOT / TARGET).read_text()})
    controls = ("NHeader", "NText", "NIcon", "NButton", "NDivider")
    write_module(
        directory,
        "qs.Widgets",
        {name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls},
    )
    write_module(
        directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    write_module(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton("""
      property string shellDir: '/fixture/noctalia-shell'
      property var launches: []
      property var processes: []
      property string packageOutput: 'noctalia-shell-git 3.4.0.r112.g3f00bec8-1'
      property int packageExit: 0
      property string gitOutput: 'abc1234'
      property int gitExit: 0
      property int processDelay: 20
      function execDetached(argv) { launches = launches.concat([argv]); }
    """)
        },
    )
    write_module(
        directory,
        "Quickshell.Io",
        {
            "StdioCollector": "import QtQuick\nQtObject { property string text: '' }",
            "Process": """import QtQuick
import Quickshell
QtObject {
  id: process
  property var command: []
  property string workingDirectory: ''
  property bool running: false
  property StdioCollector stdout
  property StdioCollector stderr
  signal started()
  signal exited(int exitCode)
  onRunningChanged: {
    if (running) {
      Quickshell.processes = Quickshell.processes.concat([command]);
      started();
      completion.start();
    } else {
      completion.stop();
    }
  }
  property Timer completion: Timer {
    interval: Quickshell.processDelay
    onTriggered: {
      const packageQuery = process.command[0] === 'pacman';
      process.stdout.text = packageQuery ? Quickshell.packageOutput : Quickshell.gitOutput;
      process.running = false;
      process.exited(packageQuery ? Quickshell.packageExit : Quickshell.gitExit);
    }
  }
}""",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    style = {
        "uiScaleRatio": 1,
        "marginXXS": 2,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 9,
        "marginL": 13,
        "marginXL": 18,
        "radiusS": 4,
        "radiusM": 8,
        "borderS": 1,
        "borderM": 2,
        "baseWidgetSize": 32,
        "fontSizeXS": 9,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 16,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
        "animationFast": 0,
        "opacityFull": 1,
        "opacityMedium": 0.6,
    }
    colors = {
        "mPrimary": "#3355aa",
        "mSecondary": "#557733",
        "mOnPrimary": "#ffffff",
        "mSurfaceVariant": "#141414",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#aaaaaa",
        "mOutline": "#808080",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in colors.items()
                )
            ),
            "I18n": singleton(
                "function tr(key, values) { return values ? key + ':' + values.count : key; }"
            ),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
            "Icons": singleton(
                "property string defaultIcon: 'person'\nproperty string fontFamily: 'Sans Serif'\nfunction get(icon) { return icon; }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.Noctalia",
        {
            "GitHubService": singleton(
                "property string latestVersion: 'v3.5.0'\nproperty var contributors: []\nproperty var cachedCircularAvatars: ({})"
            ),
            "UpdateService": singleton("property string currentVersion: 'v3.4.0'"),
        },
    )
    write_module(
        directory,
        "qs.Services.System",
        {"HostService": singleton("property bool isNixOS: false")},
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "ToastService": singleton(
                "property var notices: []\nfunction showNotice(title, body) { notices = notices.concat([{title: title, body: body}]); }"
            ),
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
        },
    )
    (directory / "tst_about.qml").write_text(
        (ROOT / "Tests/Qml/AboutTabWarningsHarness.qml").read_text()
    )
    # Local image bytes only: production Image caching branch never reaches a URL.
    (directory / "avatar.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>'
    )


def lint_harness(directory):
    stage_behavior(directory)
    return check_harness(directory, directory / "tst_about.qml")


def behavior(directory):
    stage_behavior(directory)
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/about-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/about-system",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_about.qml"),
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
    print(output, end="")
    assert result.returncode == 0, "Production AboutTab behavior failed"
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(r"\b(?:QWARN|WARN|ERROR|FATAL)\b", line)
    ]
    assert not diagnostics, "Unexpected runtime diagnostics: " + repr(diagnostics)
    print("ABOUT_TAB_BEHAVIOR_PASS")


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "about_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
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
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    print("ABOUT_LINT_COUNTS", {"total": len(warnings)})
    assert not warnings, "Actionable AboutTab warnings remain"
    assert result.returncode == 0, result.returncode
    print("ABOUT_TAB_LINT_PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-about-tab-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        before = SETTINGS.read_bytes()
        backup = directory / "settings-backup.json"
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(before)
        digest = hashlib.sha256(before).hexdigest()
        assert backup.stat().st_mode & 0o777 == 0o600
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        print("SETTINGS_BACKUP_VERIFIED", backup, digest)
        try:
            (lint if args.mode == "lint" else behavior)(directory)
        finally:
            assert SETTINGS.read_bytes() == before, "Real settings changed"
            print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
