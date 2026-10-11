#!/usr/bin/env python3
"""Bounded appearance lint and actual offscreen delegate/cache behavior."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/SetupWizard/SetupAppearanceStep.qml")
spec = importlib.util.spec_from_file_location(
    "setup_geometry", ROOT / "Tests/setup-layout-geometry.test.py"
)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def lint_appearance(artifacts):
    with tempfile.TemporaryDirectory(prefix="noctalia-appearance-lint-") as temporary:
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
        print("APPEARANCE_STATIC_WARNINGS", len(warnings))
        assert not warnings and result.returncode == 0, (
            f"Appearance lint: {len(warnings)} warnings, exit {result.returncode}"
        )


def exercise_appearance(artifacts):
    with tempfile.TemporaryDirectory(
        prefix="noctalia-appearance-offscreen-"
    ) as temporary:
        root = Path(temporary)
        geometry.prepare_sources(root)
        for name in ("Rose Pine", "Nord", "Catppuccin"):
            dark = dict(geometry.PALETTE, mSurface="#123456", mPrimary="#abcdef")
            light = dict(geometry.PALETTE, mSurface="#654321", mPrimary="#fedcba")
            (root / (name + ".json")).write_text(
                json.dumps({"dark": dark, "light": light})
            )
        broken = root / "Broken.json"
        broken.write_text("{broken json")
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
        shutil.copyfile(
            ROOT / "Tests/Qml/SetupAppearanceWarningsHarness.qml", root / "shell.qml"
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
        assert "PASS appearance: 4 width/scale cases" in output, output
        print(
            "PASS appearance: 4 width/scale cases; delegates, clicks, cache, dark/light, invalid JSON, invalidation"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    if args.mode == "lint":
        lint_appearance(args.artifacts)
        return
    before = geometry.SETTINGS.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(before)
    assert (
        hashlib.sha256(backup.read_bytes()).digest() == hashlib.sha256(before).digest()
    )
    try:
        exercise_appearance(args.artifacts)
    finally:
        assert geometry.SETTINGS.read_bytes() == before, "Real settings changed"


if __name__ == "__main__":
    main()
