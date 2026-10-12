#!/usr/bin/env python3
"""Production Workspace + Niri normalization, isolated offscreen QtTest.

Only desktop/process/settings boundaries are fixtures. No Quickshell instance
is launched; activation commands are recorded instead of reaching Niri.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


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


def main():
    with tempfile.TemporaryDirectory(prefix="noctalia-workspace-") as temporary:
        directory = Path(temporary)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
            and key
            not in (
                "DISPLAY",
                "DBUS_SESSION_BUS_ADDRESS",
                "HOME",
                "NIRI_SOCKET",
                "HYPRLAND_INSTANCE_SIGNATURE",
                "SWAYSOCK",
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
        environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
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
                timeout=30,
            )
            output = result.stdout + result.stderr
            print(output, end="")
            assert result.returncode == 0, f"Workspace runtime exit {result.returncode}"
            assert "0 failed" in result.stdout
            assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), (
                output
            )
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"


if __name__ == "__main__":
    main()
