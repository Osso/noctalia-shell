#!/usr/bin/env python3
"""Bounded owner lint and nonvisible production-component behavior.

No real screens, config writes, wallpaper, layer surfaces, or compositor access.
Standalone only; offscreen event routing is not live layer-shell input proof.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "backgrounds": Path("Modules/MainScreen/Backgrounds/AllBackgrounds.qml"),
    "loader": Path("Modules/Bar/Extras/BarWidgetLoader.qml"),
}


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory, target):
    modules = helper("about-tab-warnings.test.py")
    write, singleton = modules.write_module, modules.singleton
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Singleton": "import QtQuick\nQtObject {}",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""component FixtureUi: QtObject { property real panelBackgroundOpacity: 0.6 }
component FixtureBar: QtObject { property real backgroundOpacity: 0.8; property var monitors: [] }
component FixtureData: QtObject {
  property FixtureUi ui: FixtureUi {}
  property FixtureBar bar: FixtureBar {}
  property QtObject general: QtObject {
    property bool enableShadows: false
    property real shadowOffsetX: 0
    property real shadowOffsetY: 0
  }
}
property FixtureData data: FixtureData {}"""),
            "NColor": singleton(
                'property color mSurface: "#204060"\nproperty color black: "black"'
            ),
            "Style": singleton("""property real radiusL: 0
property int animationFast: 0
property real shadowOpacity: 0.5
property real shadowBlur: 0.5
property int shadowBlurMax: 32"""),
            "Logger": singleton(
                "function d(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
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
            "BarService": singleton("""property bool isVisible: true
property var widgets: ({})
property var events: []
function registerWidget(screen, section, widget, index, item) {
  const key = [screen, section, widget, index].join('|');
  if (widgets[key]) throw new Error('Duplicate registration: ' + key);
  const next = Object.assign({}, widgets);
  next[key] = item;
  widgets = next;
  events = events.concat(['register:' + key]);
}
function unregisterWidget(screen, section, widget, index) {
  const key = [screen, section, widget, index].join('|');
  if (!widgets[key]) throw new Error('Missing registration: ' + key);
  const next = Object.assign({}, widgets);
  delete next[key];
  widgets = next;
  events = events.concat(['unregister:' + key]);
}"""),
            "BarWidgetRegistry": """pragma Singleton
import QtQuick
import Quickshell
QtObject {
  property Component widget: Component {
    Item {
      property ShellScreen screen
      property real scaling: 1
      property string section: ''
      property int sectionWidgetIndex: -1
      property string label: ''
      property string hideMode: ''
      property int loadedCalls: 0
      property bool registeredBeforeLoaded: false
      implicitWidth: 23.6 * scaling
      implicitHeight: 15.4 * scaling
      function onLoaded() {
        const key = [screen.name, section, 'Fixture', sectionWidgetIndex].join('|');
        registeredBeforeLoaded = BarService.widgets[key] === this;
        loadedCalls++;
      }
    }
  }
  function getWidget(id) { return id === 'Fixture' ? widget : null; }
  function hasWidget(id) { return id === 'Fixture'; }
}
""",
        },
    )
    if target == "backgrounds":
        write(
            directory,
            "qs.Modules.MainScreen.Backgrounds",
            {
                name: (ROOT / f"Modules/MainScreen/Backgrounds/{name}.qml").read_text()
                for name in (
                    "AllBackgrounds",
                    "BarBackground",
                    "PanelBackground",
                    "BackgroundRegion",
                    "ShapeCornerHelper",
                )
            },
        )
        write(
            directory,
            "qs.Widgets",
            {"NDropShadow": (ROOT / "Widgets/NDropShadow.qml").read_text()},
        )
    else:
        write(
            directory,
            "qs.Modules.Bar.Extras",
            {"BarWidgetLoader": (ROOT / TARGETS[target]).read_text()},
        )
    harness = (
        "AllBackgroundsOwnerHarness.qml"
        if target == "backgrounds"
        else "BarWidgetLoaderOwnerHarness.qml"
    )
    shutil.copyfile(ROOT / "Tests/Qml" / harness, directory / "tst_owner.qml")


def lint_background_harness(directory, inject_warning):
    stage_behavior(directory, "backgrounds")
    harness = directory / "tst_owner.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n  property int lintProbe: scene.missingLintProbe",
                1,
            )
        )
    isolation = helper("grid-list-warnings.test.py")
    environment = isolation.isolated_environment(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
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
        "background-harness-lint",
    )
    report = json.loads(output)
    headers = [
        warning
        for entry in report["files"]
        for warning in entry["warnings"]
        if warning["type"] in ("warning", "error")
    ]
    print("BACKGROUND_HARNESS_DIAGNOSTICS", len(headers), "EXIT", code)
    if inject_warning:
        assert code != 0 and "missingLintProbe" in output, output
    return code or bool(headers)


def execute(directory, target, mode):
    if mode == "lint-harness":
        stage_behavior(directory, target)
        assert check_harness(directory, directory / "tst_owner.qml") == 0
        return
    if mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        argv = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGETS[target]),
        ]
    else:
        stage_behavior(directory, target)
        argv = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_owner.qml"),
            "-import",
            str(directory),
        ]
    environment = helper("display-tab-warnings.test.py").isolated_environment(directory)
    environment["NOCTALIA_CONFIG_DIR"] = environment["XDG_CONFIG_HOME"]
    environment["NOCTALIA_CACHE_DIR"] = environment["XDG_CACHE_HOME"]
    isolation = helper("grid-list-warnings.test.py")
    code, output = isolation.run_audited(directory, environment, argv, mode)
    (directory / f"{mode}.log").write_text(output)
    print(output, end="")
    if mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        print("OWNER_WARNINGS", target, len(warnings))
        if target == "backgrounds":
            assert not warnings, warnings
        else:
            # Loader.item is statically QObject; dynamic widget fields stay unsuppressed.
            residuals = [
                re.search(r'Member "([^"]+)".*\[missing-property\]$', line)
                for line in warnings
            ]
            assert len(residuals) == 3 and all(residuals), warnings
            assert sorted(match.group(1) for match in residuals) == [
                "onLoaded",
                "scaling",
                "screen",
            ], warnings
            print("RETAINED_DYNAMIC_WIDGET_DIAGNOSTICS", "onLoaded scaling screen")
    else:
        assert "0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=TARGETS)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and (
        args.mode != "lint-harness" or args.target != "backgrounds"
    ):
        parser.error("--inject-warning requires backgrounds lint-harness")
    directory = args.artifacts.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    if args.mode == "lint-harness":
        if args.target == "backgrounds":
            raise SystemExit(lint_background_harness(directory, args.inject_warning))
        execute(directory, args.target, args.mode)
        return
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    backup = directory / "settings.backup.json"
    descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(original)
    assert backup.stat().st_mode & 0o777 == 0o600
    assert backup.read_bytes() == original
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    print("SETTINGS_BACKUP_VERIFIED", backup, digest)
    try:
        execute(directory, args.target, args.mode)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert backup.read_bytes() == original, "Backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
