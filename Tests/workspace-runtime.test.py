#!/usr/bin/env python3
"""Production Workspace + Niri normalization, isolated offscreen QtTest.

Only desktop/process/settings boundaries are fixtures. No Quickshell instance
is launched; activation commands are recorded instead of reaching Niri.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).absolute().parents[1]


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def write_module(directory, uri, sources):
    module = directory.joinpath(*uri.split("."))
    module.mkdir(parents=True, exist_ok=True)
    declarations = ["module " + uri]
    for name, source in sources.items():
        (module / f"{name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{name} 1.0 {name}.qml")
    (module / "qmldir").write_text("\n".join(declarations) + "\n")


def stage_runtime(directory):
    write_module(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name }",
            "Quickshell": singleton("""property var commands: []
function env(name) { return ""; }
function execDetached(argv) { commands = commands.concat([argv]); }"""),
        },
    )
    write_module(
        directory,
        "Quickshell.Io",
        {
            "Socket": """import QtQuick
QtObject {
  property string path
  property bool connected: false
  property QtObject parser
  function write(value) {}
  function flush() {}
}""",
            "SplitParser": "import QtQuick\nQtObject { signal read(string line) }",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"].update(position="top", density="comfortable")
    style = dict(
        capsuleHeight=40,
        barHeight=40,
        marginS=4,
        marginXS=3,
        radiusM=8,
        fontWeightBold=700,
        fontWeightMedium=500,
        fontSizeM=12,
        uiScaleRatio=1,
        animationNormal=0,
        animationFast=0,
        animationSlow=0,
    )
    colors = dict(
        mPrimary="#00ff00",
        mOnPrimary="#000000",
        mError="#ff0000",
        mOnError="#ffffff",
        mSecondary="#222222",
        mOnSecondary="#eeeeee",
        mOnSurface="#ffffff",
        mOutline="#888888",
        transparent="transparent",
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
                + '\nproperty color capsuleColor: "#202020"'
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Logger": singleton("""function e(...args) { console.error(...args); }
function i(...args) {}
function d(...args) {}"""),
        },
    )
    write_module(
        directory,
        "qs.Services.Keyboard",
        {
            "KeyboardLayoutService": singleton("function setCurrentLayout(name) {}"),
        },
    )
    write_module(
        directory,
        "qs.Services.Compositor",
        {
            "NiriService": (ROOT / "Services/Compositor/NiriService.qml").read_text(),
            "CompositorService": """pragma Singleton
import QtQuick
QtObject {
  id: facade
  property ListModel workspaces: ListModel {}
  property NiriService backend: NiriService {
    onWorkspaceChanged: {
      facade.workspaces.clear();
      for (let i = 0; i < workspaces.count; i++)
        facade.workspaces.append(workspaces.get(i));
      facade.workspacesChanged();
    }
  }
  function switchToWorkspace(workspace) { backend.switchToWorkspace(workspace); }
}""",
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton(
                "function getPopupMenuWindow(screen) { return null; }"
            ),
            "BarService": singleton("function openWidgetSettings(...args) {}"),
        },
    )
    write_module(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetRegistry": singleton("""property var widgetMetadata: ({Workspace: {
labelMode: "index", hideUnoccupied: false, followFocusedScreen: false, characterCount: 3
}})"""),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            "NText": (ROOT / "Widgets/NText.qml").read_text(),
            "NPopupContextMenu": """import QtQuick
Item {
  property var model
  signal triggered(string action)
  function openAtItem(anchor, x, y) {}
}""",
        },
    )
    write_module(
        directory,
        "qs.Modules.Bar.Widgets",
        {
            "Workspace": (ROOT / "Modules/Bar/Widgets/Workspace.qml").read_text(),
        },
    )
    (directory / "tst_workspace.qml").write_text(
        (ROOT / "Tests/Qml/WorkspaceHarness.qml").read_text()
    )


def lint_harness(isolation, directory, environment, inject_warning=False):
    harness = directory / "tst_workspace.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: scene",
                "id: scene\n  property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
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
        "workspace-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("WORKSPACE_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert any(
            warning["type"] == "warning"
            and warning["id"] == "missing-property"
            and "missingLintProbe" in warning["message"]
            for result in diagnostics["files"]
            for warning in result["warnings"]
        ), "injected semantic warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert warnings == 0, f"harness warnings remain: {warnings}"
        assert code == 0, f"harness lint exit {code}"
        assert all(result["success"] for result in diagnostics["files"]), diagnostics
    return code


def lint_harness_regression(isolation, directory):
    for label, injected in (("clean", False), ("injected", True)):
        staged = directory / label
        staged.mkdir(mode=0o700)
        stage_runtime(staged)
        code = lint_harness(
            isolation, staged, isolation.isolated_environment(staged), injected
        )
        assert code != 0 if injected else code == 0, code
    print("WORKSPACE_HARNESS_WARNING_REJECTED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        nargs="?",
        default="runtime",
        choices=("runtime", "lint-harness", "lint-harness-regression"),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    spec = importlib.util.spec_from_file_location(
        "workspace_isolation", ROOT / "Tests/grid-list-warnings.test.py"
    )
    isolation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(isolation)
    with tempfile.TemporaryDirectory(prefix="noctalia-workspace-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        if args.mode == "lint-harness-regression":
            lint_harness_regression(isolation, directory)
            return
        environment = isolation.isolated_environment(directory)
        settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
        settings.parent.mkdir(mode=0o700, parents=True)
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        settings.touch(mode=0o600)
        settings.write_bytes(original)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert backup.read_bytes() == original, "fixture backup bytes differ"
        stage_runtime(directory)
        try:
            if args.mode == "lint-harness":
                raise SystemExit(
                    lint_harness(isolation, directory, environment, args.inject_warning)
                )
            code, output = isolation.run_audited(
                directory,
                environment,
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory),
                    "-import",
                    str(directory),
                ],
                "workspace-runtime",
            )
            assert code == 0, f"Workspace runtime exit {code}"
            assert "Totals: 10 passed, 0 failed" in output, output
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
            ), output
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"


if __name__ == "__main__":
    main()
