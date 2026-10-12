#!/usr/bin/env python3
"""Bounded customization lint and production offscreen form/selection behavior."""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/SetupWizard/SetupCustomizeStep.qml")
spec = importlib.util.spec_from_file_location(
    "setup_geometry", ROOT / "Tests/setup-layout-geometry.test.py"
)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def lint_customize(artifacts):
    with tempfile.TemporaryDirectory(prefix="noctalia-customize-lint-") as temporary:
        root = Path(temporary)
        sources = root / "qs"
        for directory in ("Commons", "Helpers", "Widgets", "Services", "Modules"):
            shutil.copytree(ROOT / directory, sources / directory)
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
        result = subprocess.run(
            ["/usr/lib/qt6/bin/qmllint", "-I", str(root), str(sources / TARGET)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (artifacts / "lint.log").write_text(output)
        warnings = re.findall(r"^Warning:.*$", output, re.MULTILINE)
        print(output, end="")
        print("CUSTOMIZE_STATIC_WARNINGS", len(warnings))
        assert not warnings and result.returncode == 0, (
            f"Customize lint: {len(warnings)} warnings, exit {result.returncode}"
        )


def exercise_customize(artifacts):
    with tempfile.TemporaryDirectory(
        prefix="noctalia-customize-offscreen-"
    ) as temporary:
        root = Path(temporary)
        geometry.prepare_sources(root)
        shutil.copyfile(
            ROOT / "Tests/Qml/SetupCustomizeWarningsHarness.qml", root / "shell.qml"
        )
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(root / "shell.qml")],
            cwd=root,
            env=geometry.isolated_environment(root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (artifacts / "behavior.log").write_text(output)
        assert result.returncode == 0 and not re.search(
            r"\b(?:WARN|ERROR|FATAL)\b", output
        ), output
        assert "PASS customize: 4 width/scale cases" in output, output
        print(
            "PASS customize: 4 width/scale cases; form, signals, selection, model reorder"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    if args.mode == "lint":
        lint_customize(args.artifacts)
        return
    before = geometry.SETTINGS.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(before)
    digest = hashlib.sha256(before).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    try:
        exercise_customize(args.artifacts)
    finally:
        assert geometry.SETTINGS.read_bytes() == before, "Real settings changed"
        print("REAL_SETTINGS_SHA256", digest, "unchanged")


if __name__ == "__main__":
    main()
