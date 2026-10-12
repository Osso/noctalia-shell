#!/usr/bin/env python3
"""Busy/divider owner proof: masked host config, private offscreen Qt."""

import argparse
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
TARGETS = ("NBusyIndicator", "NDivider")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load("grouped-osd-settings-warnings")


def stage(directory, shadow):
    commons = directory / "qs/Commons"
    commons.mkdir(parents=True)
    (commons / "qmldir").write_text(
        "module qs.Commons\nsingleton Style 1.0 Style.qml\nsingleton NColor 1.0 NColor.qml\n"
    )
    (commons / "Style.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n"
        "property int baseWidgetSize: 40\nproperty int borderL: 4\n"
        "property int borderS: 2\nproperty int animationSlow: 100\n}\n"
    )
    (commons / "NColor.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n"
        'property color mPrimary: "#ff0000"\nproperty color mOutline: "#00ff00"\n'
        'property color transparent: "transparent"\n}\n'
    )
    # Neither target uses a Quickshell type; resolve unused imports without a shell plugin.
    for module in ("Quickshell", "Quickshell.Widgets"):
        module_path = directory.joinpath(*module.split("."))
        module_path.mkdir(parents=True, exist_ok=True)
        (module_path / "qmldir").write_text(
            f"module {module}\nFixtureMarker 1.0 FixtureMarker.qml\n"
        )
        (module_path / "FixtureMarker.qml").write_text("import QtQuick\nQtObject {}\n")
    widgets = directory / "qs/Widgets"
    widgets.mkdir()
    (widgets / "qmldir").write_text(
        "module qs.Widgets\n" + "".join(f"{name} 1.0 {name}.qml\n" for name in TARGETS)
    )
    for name in TARGETS:
        source = (ROOT / f"Widgets/{name}.qml").read_text()
        if shadow:
            if name == "NBusyIndicator":
                source = source.replace(
                    "id: canvas", "id: canvas\nproperty int strokeWidth: 20", 1
                )
            else:
                source = source.replace(
                    "gradient: Gradient {",
                    "gradient: Gradient {\nproperty bool vertical: false",
                    1,
                )
        (widgets / f"{name}.qml").write_text(source)
    harness = directory / "tst_busy_divider.qml"
    shutil.copyfile(ROOT / "Tests/Qml/BusyDividerWarningsHarness.qml", harness)
    return harness


def run_sandboxed(args, directory):
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line for line in mounts
        ), path
    environment = isolation.isolated_environment(directory)
    if args.mode == "lint":
        load("media-mini-warnings").stage_modules(directory)
        command = [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            "--max-warnings",
            str(args.expect_warnings * len(TARGETS)),
            *[str(directory / f"qs/Widgets/{name}.qml") for name in TARGETS],
        ]
    else:
        harness = stage(directory, args.shadow)
        if args.mode == "lint-harness":
            if args.inject_warning:
                source = harness.read_text()
                marker = "  id: scene"
                assert source.count(marker) == 1, "injection owner must be unique"
                harness.write_text(
                    source.replace(
                        marker,
                        marker
                        + "\n  property int injectedWarning: scene.missingLintProbe",
                        1,
                    )
                )
            command = [
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
    if args.mode == "lint":
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        counts = {
            name: sum(f"/{name}.qml:" in line for line in warnings) for name in TARGETS
        }
        print("BUSY_DIVIDER_WARNINGS", counts, "EXIT", code)
        assert all(count == args.expect_warnings for count in counts.values()), counts
        assert len(warnings) == sum(counts.values()), warnings
        assert all("[unqualified]" in line for line in warnings), warnings
    elif args.mode == "lint-harness":
        reports = json.loads(output)["files"]
        assert len(reports) == 1, reports
        assert reports[0]["filename"] == str(harness), reports
        warnings = [warning for report in reports for warning in report["warnings"]]
        print("BUSY_DIVIDER_HARNESS_LINT_WARNINGS", len(warnings), "EXIT", code)
        if args.inject_warning:
            assert any(
                "missingLintProbe" in warning["message"] for warning in warnings
            ), "semantic warning injection was not diagnosed"
            assert code != 0, "injected warning was accepted"
            raise SystemExit(code)
        assert not warnings, warnings
        assert reports[0]["success"], reports
    else:
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
            output,
        ), output
        if args.mode == "behavior":
            assert "6 passed, 0 failed, 0 skipped, 0 blacklisted" in output, output
    assert code == 0, code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--shadow", action="store_true")
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--expect-warnings", type=int, default=0)
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
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
        with tempfile.TemporaryDirectory(prefix="noctalia-busy-divider-") as temporary:
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
            if args.inject_warning:
                command.append("--inject-warning")
            code, _ = isolation.run_child(
                command,
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
