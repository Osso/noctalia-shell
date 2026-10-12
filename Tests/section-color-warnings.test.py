#!/usr/bin/env python3
"""Scoped section/editor-picker proof with denied host config and private Qt."""

import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
TARGETS = ("NSectionEditor", "NColorPicker")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load("grouped-osd-settings-warnings")


def stage(directory, shadow):
    load("color-picker-warnings").stage_runtime(directory)
    (directory / "tst_color_picker.qml").unlink()
    widgets = directory / "qs/Widgets"
    for name in (
        *TARGETS,
        "NSearchableComboBox",
        "NContextMenu",
        "NListView",
        "NLabel",
    ):
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
        with (widgets / "qmldir").open("a") as stream:
            stream.write(f"{name} 1.0 {name}.qml\n")
    shutil.copyfile(
        ROOT / "Helpers/FuzzySort.js", directory / "qs/Helpers/FuzzySort.js"
    )
    colors = directory / "qs/Commons/NColor.qml"
    colors.write_text(
        colors.read_text().replace(
            "QtObject {",
            'QtObject {\nproperty color mOnTertiary: "#111111"\nproperty color mOnError: "#ffffff"',
        )
    )
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {", "QtObject {\nproperty real opacityLight: 0.2"
        )
    )
    dialog = widgets / "NColorPickerDialog.qml"
    dialog.write_text(
        dialog.read_text().replace(
            "id: root", 'id: root\nobjectName: visible ? "testColorDialog" : ""', 1
        )
    )
    if shadow:
        picker = widgets / "NColorPicker.qml"
        picker.write_text(
            picker.read_text().replace(
                "MouseArea {", 'MouseArea {\nproperty color selectedColor: "#ffffff"', 1
            )
        )
        section = widgets / "NSectionEditor.qml"
        section.write_text(
            section.read_text().replace(
                "id: flowDragArea",
                'id: flowDragArea\nproperty var widgetModel: []\nproperty string sectionId: "wrong-section"\nfunction reorderWidget(section, from, to) { throw new Error("WRONG_OWNER reorder"); }',
                1,
            )
        )
    harness = directory / "tst_section_color.qml"
    shutil.copyfile(ROOT / "Tests/Qml/SectionColorWarningsHarness.qml", harness)
    return harness


def run_sandboxed(args, directory):
    environment = isolation.isolated_environment(directory)
    if args.mode == "lint":
        load("media-mini-warnings").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            *[str(directory / f"qs/Widgets/{name}.qml") for name in TARGETS],
        ]
    else:
        harness = stage(directory, args.shadow)
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
    code, output = isolation.run_child(command, directory, environment)
    (directory / f"{args.mode}.log").write_text(output)
    if args.mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = {
            name: sum(f"/{name}.qml:" in line for line in warnings) for name in TARGETS
        }
        print("SECTION_COLOR_WARNINGS", counts, "EXIT", code)
        assert all(count == args.expect_warnings for count in counts.values()), counts
        assert len(warnings) == sum(counts.values()), warnings
    else:
        assert code == 0, code
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
        if args.mode == "behavior":
            assert "0 failed" in output, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--expect-warnings", type=int, default=0)
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(isolation.audit)
    with (
        patch("os.stat", isolation.guard_metadata(os.stat)),
        patch("os.lstat", isolation.guard_metadata(os.lstat)),
        patch("os.readlink", isolation.guard_metadata(os.readlink)),
    ):
        isolation.prove_denial()
        if args.sandbox:
            run_sandboxed(args, args.sandbox)
            return
        with tempfile.TemporaryDirectory(prefix="noctalia-section-color-") as temporary:
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
                "--expect-warnings",
                str(args.expect_warnings),
            ]
            if args.shadow:
                command.append("--shadow")
            code, _ = isolation.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
