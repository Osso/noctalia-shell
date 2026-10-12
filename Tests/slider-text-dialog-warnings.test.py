#!/usr/bin/env python3
"""Seven scoped hoisting diagnostics and config-denied offscreen control proof."""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
TARGETS = (
    Path("Widgets/NColorSlider.qml"),
    Path("Widgets/NTextInput.qml"),
    Path("Modules/Panels/Settings/ControlCenter/ControlCenterWidgetSettingsDialog.qml"),
)


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = load("active-window-settings-warnings")


def stage_runtime(directory):
    load("simple-widgets-warnings").stage_runtime(directory)
    (directory / "tst_simple_widgets.qml").unlink()
    modules = load("workspace-runtime")
    widgets = directory / "qs/Widgets"
    for name in ("NColorSlider", "NTextInput", "NButton"):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as stream:
            stream.write(f"{name} 1.0 {name}.qml\n")
    commons = directory / "qs/Commons"
    for name, body in {
        "Style": "property real marginXL: 16\nproperty real marginL: 12\nproperty real marginXS: 2\nproperty real radiusM: 8\nproperty int fontWeightRegular: 400",
        "NColor": 'property color mSecondary: "#fedcba"\nproperty color mOnSecondary: "#101010"\nproperty color mError: "#ff0000"',
    }.items():
        path = commons / f"{name}.qml"
        path.write_text(path.read_text().replace("QtObject {", "QtObject {\n" + body))
    (commons / "I18n.qml").write_text(
        modules.singleton("function tr(key, options) { return key; }")
    )
    with (commons / "qmldir").open("a") as stream:
        stream.write("singleton I18n 1.0 I18n.qml\n")
    services = directory / "qs/Services/UI"
    (services / "ControlCenterWidgetRegistry.qml").write_text(
        modules.singleton(
            'property var widgetMetadata: ({CustomButton: {caption: "fixture-default"}})'
        )
    )
    with (services / "qmldir").open("a") as stream:
        stream.write(
            "singleton ControlCenterWidgetRegistry 1.0 ControlCenterWidgetRegistry.qml\n"
        )
    modules.write_module(
        directory,
        "qs.Modules.Panels.Settings.ControlCenter",
        {"ControlCenterWidgetSettingsDialog": (ROOT / TARGETS[2]).read_text()},
    )
    editor = directory / "qs/Modules/Panels/Settings/ControlCenter/WidgetSettings"
    editor.mkdir()
    (editor / "CustomButtonSettings.qml").write_text("""import QtQuick
import qs.Widgets
Item {
  id: editor
  property var widgetData
  property var widgetMetadata
  property int saves: 0
  implicitWidth: 440
  implicitHeight: 60
  NTextInput {
    id: caption
    width: parent.width
    text: editor.widgetData.caption !== undefined ? editor.widgetData.caption : editor.widgetMetadata.caption
  }
  function saveSettings() {
    saves++;
    return {id: widgetData.id, caption: caption.text, enabled: widgetData.enabled};
  }
}
""")
    harness = directory / "tst_slider_text_dialog.qml"
    shutil.copyfile(ROOT / "Tests/Qml/SliderTextDialogWarningsHarness.qml", harness)
    return harness


def run_lint(directory, environment):
    load("media-mini-warnings").stage_modules(directory)
    failures = []
    for target in TARGETS:
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            "--block-scope-var-declaration",
            "error",
            "--json",
            "-",
            str(directory / "qs" / target),
        ]
        code, output = guard.run_child(command, directory, environment)
        (directory / f"{target.stem}.lint.json").write_text(output)
        diagnostics = json.loads(output)
        headers = [
            warning for file in diagnostics["files"] for warning in file["warnings"]
        ]
        counts = Counter(header["id"] for header in headers if header["type"] != "info")
        print(target, "ALL_HEADERS", json.dumps(headers, sort_keys=True), flush=True)
        print(target, "WARNINGS", dict(counts), "EXIT", code, flush=True)
        expected = (
            Counter({"missing-property": 2}) if target == TARGETS[2] else Counter()
        )
        residuals = [header for header in headers if header["id"] == "missing-property"]
        truthful_residuals = all(
            '"saveSettings"' in header["message"] and '"QObject"' in header["message"]
            for header in residuals
        )
        if counts != expected or code != 0 or not truthful_residuals:
            failures.append(f"{target}: {dict(counts)}, exit {code}")
    assert not failures, "; ".join(failures)


def run_sandboxed(args):
    directory = args.sandbox
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for parent in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == parent and " - tmpfs " in line for line in mounts
        ), parent
    environment = guard.isolated_environment(directory)
    print(
        "CONFIG_DENY: host home/config and desktop runtime masked; private HOME/XDG; unshared network",
        flush=True,
    )
    if args.mode == "lint":
        run_lint(directory, environment)
        return
    harness = stage_runtime(directory)
    if args.mode == "lint-harness":
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            str(directory),
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            str(harness),
        ]
    else:
        command = [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ]
    code, output = guard.run_child(command, directory, environment)
    (directory / f"{args.mode}.log").write_text(output)
    assert code == 0, output
    if args.mode == "runtime":
        assert "10 passed, 0 failed" in output, output
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    sys.addaudithook(guard.audit)
    with (
        patch("os.stat", guard.guard_metadata(os.stat)),
        patch("os.lstat", guard.guard_metadata(os.lstat)),
        patch("os.readlink", guard.guard_metadata(os.readlink)),
    ):
        guard.prove_denial()
        if args.sandbox:
            run_sandboxed(args)
            return
        if args.artifacts:
            args.artifacts.mkdir(mode=0o700)
        with tempfile.TemporaryDirectory(
            prefix="noctalia-slider-text-dialog-"
        ) as temporary:
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
                "/home",
                "--tmpfs",
                "/syncthing",
                "--ro-bind",
                str(ROOT),
                str(ROOT),
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
                str(Path(__file__).absolute()),
                args.mode,
                "--sandbox",
                temporary,
            ]
            code, output = guard.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            if args.artifacts:
                (args.artifacts / "output.log").write_text(output)
                for path in directory.glob("*.log"):
                    shutil.copyfile(path, args.artifacts / path.name)
                for path in directory.glob("*.json"):
                    shutil.copyfile(path, args.artifacts / path.name)
            raise SystemExit(code)


if __name__ == "__main__":
    main()
