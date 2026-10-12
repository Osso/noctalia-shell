#!/usr/bin/env python3
"""Bounded appearance lint/behavior with masked config and private offscreen Qt."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/SetupWizard/SetupAppearanceStep.qml")


def load_helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


geometry = load_helper("setup-layout-geometry.test.py")
isolation = load_helper("grouped-osd-settings-warnings.test.py")


def write_modules(sources):
    modules = {}
    for path in sorted(sources.rglob("*.qml")):
        relative = path.relative_to(sources)
        directory = relative.parent
        for parent in (directory, *directory.parents):
            modules.setdefault(parent, [])
        singleton = bool(
            re.search(r"^\s*pragma\s+Singleton\b", path.read_text(), re.MULTILINE)
        )
        prefix = "singleton " if singleton else ""
        modules[directory].append(f"{prefix}{path.stem} 1.0 {path.name}\n")
    for directory, declarations in modules.items():
        module = ".".join(("qs", *directory.parts))
        (sources / directory / "qmldir").write_text(
            f"module {module}\n" + "".join(declarations)
        )


def stage_behavior(root):
    geometry.prepare_sources(root)
    for name in ("Rose Pine", "Nord", "Catppuccin"):
        dark = dict(geometry.PALETTE, mSurface="#123456", mPrimary="#abcdef")
        light = dict(geometry.PALETTE, mSurface="#654321", mPrimary="#fedcba")
        (root / (name + ".json")).write_text(json.dumps({"dark": dark, "light": light}))
    (root / "Broken.json").write_text("{broken json")
    geometry.write_singleton(
        root,
        "Services/Theming/ColorSchemeService.qml",
        "property var schemes: "
        + json.dumps(
            [
                str(root / (name + ".json"))
                for name in ("Rose Pine", "Nord", "Catppuccin", "Broken")
            ]
        )
        + '\nproperty string appliedScheme: ""\n'
        + "function applyScheme(name) { appliedScheme = name; }",
    )
    geometry.write_singleton(
        root,
        "Services/Theming/AppThemeService.qml",
        "property int generations: 0\nfunction generate() { generations++; }",
    )
    harness = root / "shell.qml"
    shutil.copyfile(ROOT / "Tests/Qml/SetupAppearanceWarningsHarness.qml", harness)
    write_modules(root)
    return harness


def execute(args, directory):
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line for line in mounts
        ), path
    environment = geometry.isolated_environment(directory)
    root = directory / "qs"
    root.mkdir()
    if args.mode == "lint":
        for name in ("Commons", "Helpers", "Widgets", "Services", "Modules"):
            shutil.copytree(ROOT / name, root / name)
        write_modules(root)
        command = ["/usr/lib/qt6/bin/qmllint", "-I", str(directory), str(root / TARGET)]
    else:
        harness = stage_behavior(root)
        if args.mode == "lint-harness":
            if args.inject_warning:
                source = harness.read_text()
                marker = "  id: harness"
                assert source.count(marker) == 1
                harness.write_text(
                    source.replace(
                        marker,
                        marker
                        + "\n  property int injectedWarning: harness.missingLintProbe",
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
            command = ["quickshell", "--no-color", "-p", str(harness)]
    result = subprocess.run(
        command, cwd=root, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    (directory / f"{args.mode}.log").write_text(output)
    print(output, end="")
    if args.mode == "lint":
        warnings = re.findall(r"^Warning:.*$", output, re.MULTILINE)
        print("APPEARANCE_STATIC_WARNINGS", len(warnings))
        assert not warnings, warnings
    elif args.mode == "lint-harness":
        reports = json.loads(output)["files"]
        assert len(reports) == 1 and reports[0]["filename"] == str(harness), reports
        warnings = [warning for report in reports for warning in report["warnings"]]
        print(
            "APPEARANCE_HARNESS_LINT_WARNINGS", len(warnings), "EXIT", result.returncode
        )
        if args.inject_warning:
            assert any("missingLintProbe" in warning["message"] for warning in warnings)
            assert result.returncode != 0, "Injected semantic warning accepted"
            raise SystemExit(result.returncode)
        assert not warnings and reports[0]["success"], reports
    else:
        assert not re.search(r"\b(?:WARN|ERROR|FATAL)\b", output), output
        assert "PASS appearance: 4 width/scale cases" in output, output
    assert result.returncode == 0, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--sandbox", action="store_true", help=argparse.SUPPRESS)
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
        directory = args.artifacts.absolute()
        if args.sandbox:
            execute(args, directory)
            return
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
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
            str(directory),
            str(directory),
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--chdir",
            str(directory),
            "--",
            "/usr/bin/python3",
            str(Path(__file__).absolute()),
            args.mode,
            "--artifacts",
            str(directory),
            "--sandbox",
        ]
        if args.inject_warning:
            command.append("--inject-warning")
        code, _ = isolation.run_child(
            command,
            directory,
            {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": str(directory)},
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
