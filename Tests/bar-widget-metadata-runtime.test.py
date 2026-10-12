#!/usr/bin/env python3
"""Actual widgets with Loader's post-construction instance assignment, offscreen."""

import argparse
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "media_fixture", ROOT / "Tests/media-mini-warnings.test.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@contextmanager
def fixture_settings(directory):
    home = directory / "fixture/home"
    settings = home / ".config/noctalia/settings.json"
    settings.parent.mkdir(parents=True, mode=0o700)
    original = (ROOT / "Assets/settings-default.json").read_bytes()
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        path.touch(mode=0o600)
        path.write_bytes(original)
        assert path.read_bytes() == original, "fixture copy differs"
    try:
        yield
    finally:
        assert settings.read_bytes() == original, "fixture settings changed"
        assert backup.read_bytes() == original, "fixture backup changed"


def stage_widgets(directory):
    fixture.stage_widget(directory)
    source = ROOT / "Modules/Bar/Widgets/ActiveWindow.qml"
    shutil.copyfile(source, directory / "Modules/Bar/Widgets/ActiveWindow.qml")
    # Keep production metadata verbatim; omit registry components for unrelated widgets.
    registry = (ROOT / "Services/UI/BarWidgetRegistry.qml").read_text()
    metadata = re.search(r"property var widgetMetadata: (\(\{.*?\}\))", registry, re.S)
    assert metadata, "production registry metadata missing"
    (directory / "Modules/Bar/Extras/BarWidgetRegistry.qml").unlink()
    shutil.copyfile(
        ROOT / "Modules/Bar/Extras/BarWidgetLoader.qml",
        directory / "Modules/Bar/Extras/BarWidgetLoader.qml",
    )
    registry_body = """property var snapshots: []
property var constructed: ({})
property Component activeComponent: Component {
    ActiveWindow { Component.onCompleted: BarWidgetRegistry.capture(this, "ActiveWindow") }
}
property Component mediaComponent: Component {
    MediaMini { Component.onCompleted: BarWidgetRegistry.capture(this, "MediaMini") }
}
function getWidget(key) { return key === "ActiveWindow" ? activeComponent : mediaComponent; }
function hasWidget(key) { return key === "ActiveWindow" || key === "MediaMini"; }
function capture(item, key) { constructed[key] = item; }
function snapshotBeforeAssignment(key) {
    const item = constructed[key];
    const snapshot = {
        key: key, widgetId: item.widgetId,
        metadataReady: item.widgetMetadata !== undefined,
        width: item.implicitWidth, height: item.implicitHeight,
        visible: item.visible, maxWidth: item.maxWidth, fixed: item.useFixedWidth
    };
    console.log("BEFORE_ONLOADED_ASSIGNMENT", JSON.stringify(snapshot));
    snapshots.push(snapshot);
}
"""
    registry_target = directory / "Services/UI/BarWidgetRegistry.qml"
    registry_target.write_text(
        "pragma Singleton\nimport QtQuick\nimport qs.Modules.Bar.Widgets\nQtObject {\n"
        + "property var widgetMetadata: "
        + metadata[1]
        + "\n"
        + registry_body
        + "}\n"
    )
    logger = directory / "Commons/Logger.qml"
    # The production Loader logs before applying widgetProps. Observe that exact
    # onLoaded boundary without modifying Loader or overriding widget bindings.
    logger.write_text(
        logger.read_text()
        .replace("import QtQuick", "import QtQuick\nimport qs.Services.UI")
        .replace(
            "function w(...args)",
            "function d(category, message, key) { BarWidgetRegistry.snapshotBeforeAssignment(key); }\n"
            "function w(...args)",
        )
    )
    bar_service = directory / "Services/UI/BarService.qml"
    bar_service.write_text(
        bar_service.read_text().replace(
            "function getTooltipDirection()",
            "function registerWidget(...args) {}\nfunction unregisterWidget(...args) {}\n"
            "function getTooltipDirection()",
        )
    )
    fixture.write_singleton(
        directory / "Services/Compositor",
        "CompositorService",
        """property var focusedWindow: null
property bool isHyprland: false
signal activeWindowChanged()
signal windowListChanged()
function getFocusedWindow() { return focusedWindow; }
function getFocusedWindowTitle() { return focusedWindow ? focusedWindow.title : ""; }""",
    )
    fixture.write_singleton(
        directory / "Services/UI",
        "ThemeIcons",
        """function iconFromName(name) { return ""; }
function iconForAppId(name) { return ""; }""",
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/BarWidgetMetadataHarness.qml", directory / "shell.qml"
    )


def isolate_environment(directory):
    environment = fixture.isolate_environment(directory)
    for variable in list(environment):
        if variable.startswith("QS_"):
            del environment[variable]
    environment["DBUS_SESSION_BUS_ADDRESS"] = (
        "unix:path=/nonexistent/noctalia-test-session"
    )
    environment["DBUS_SYSTEM_BUS_ADDRESS"] = (
        "unix:path=/nonexistent/noctalia-test-system"
    )
    home = directory / "fixture/home"
    environment.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        NOCTALIA_CONFIG_DIR=str(home / ".config/noctalia"),
    )
    return environment


def lint_harness(directory):
    runtime = directory / "runtime"
    runtime.mkdir()
    stage_widgets(runtime)
    imports = directory / "imports"
    fixture.stage_modules(imports, source_root=runtime)
    return check_harness(imports, imports / "qs/shell.qml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", nargs="?", default="behavior", choices=("behavior", "lint-harness")
    )
    args = parser.parse_args()
    if args.mode == "lint-harness":
        with tempfile.TemporaryDirectory(
            prefix="noctalia-widget-metadata-lint-"
        ) as temporary:
            raise SystemExit(lint_harness(Path(temporary)))
    with tempfile.TemporaryDirectory(prefix="noctalia-widget-metadata-") as temporary:
        directory = Path(temporary)
        with fixture_settings(directory):
            stage_widgets(directory)
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
                cwd=ROOT,
                env=isolate_environment(directory),
                capture_output=True,
                text=True,
                timeout=15,
            )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"widget runtime exit {result.returncode}"
        assert "BAR_WIDGET_METADATA_PASS" in output, "behavior assertions incomplete"
        assert not any(level in output for level in (" WARN ", " ERROR ", " FATAL ")), (
            output
        )


if __name__ == "__main__":
    main()
