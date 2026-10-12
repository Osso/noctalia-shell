#!/usr/bin/env python3
"""Scoped background-path lint and offscreen fill-containment regression.

Production ShapePaths and corner helper are unchanged. Fixtures supply geometry,
style and visibility only; no layer surfaces, real settings or wallpaper access.
Negative controls mutate staged copies, never canonical production sources.
All 13 panel/12 bar diagnostics are retained: panelItem and four corner-state
fields belong to anonymous Items in MainScreen.qml/SmartPanel.qml, not Item's
static metadata. Resolving them needs an out-of-scope shared typed contract.
"""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MODULE = Path("Modules/MainScreen/Backgrounds")
TARGETS = {"PanelBackground": 13, "BarBackground": 12}


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_behavior(directory, mutation):
    modules = helper("about-tab-warnings.test.py")
    write, singleton = modules.write_module, modules.singleton
    write(directory, "Quickshell", {"Singleton": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton(
                "property real radiusL: 12\nproperty int animationFast: 0"
            ),
            "Settings": singleton("""property QtObject data: QtObject {
  property QtObject bar: QtObject { property var monitors: [] }
}"""),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {"BarService": singleton("property bool isVisible: true")},
    )
    sources = {
        name: (ROOT / MODULE / f"{name}.qml").read_text()
        for name in (*TARGETS, "ShapeCornerHelper")
    }
    if mutation:
        name, fault = mutation.split("-")
        target = f"{name.title()}Background"
        old, new = (
            ("startY: panelY", "startY: panelY + 200")
            if target == "PanelBackground"
            else ("startY: barMappedPos.y", "startY: barMappedPos.y + 200")
        )
        if fault == "rounding":
            old, new = "return effectiveRadius;", "return 0;"
        assert sources[target].count(old) == 1
        sources[target] = sources[target].replace(old, new)
    write(directory, "qs.Modules.MainScreen.Backgrounds", sources)
    shutil.copyfile(
        ROOT / "Tests/Qml/BackgroundPathsHarness.qml", directory / "tst_paths.qml"
    )


def execute(directory, argv):
    environment = helper("display-tab-warnings.test.py").isolated_environment(directory)
    environment.update(
        NOCTALIA_CONFIG_DIR=environment["XDG_CONFIG_HOME"],
        NOCTALIA_CACHE_DIR=environment["XDG_CACHE_HOME"],
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
    )
    result = subprocess.run(
        argv, cwd=directory, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    for name, expected in TARGETS.items():
        command_directory = directory / name
        command_directory.mkdir(mode=0o700)
        code, output = execute(
            command_directory,
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / MODULE / f"{name}.qml"),
            ],
        )
        (directory / f"{name}.lint.log").write_text(output)
        warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
        assert code == 0, code
        assert len(warnings) == expected, warnings
        assert all("[missing-property]" in line for line in warnings), warnings
        members = [re.search(r'Member "([^"]+)"', line).group(1) for line in warnings]
        corners = [
            "topLeftCornerState",
            "topRightCornerState",
            "bottomRightCornerState",
            "bottomLeftCornerState",
        ]
        expected_members = corners * 3 + (
            ["panelItem"] if name == "PanelBackground" else []
        )
        assert sorted(members) == sorted(expected_members), members
        print("RETAINED_METADATA_WARNINGS", name, len(warnings), "exit", code)


def behavior(directory, mutation):
    stage_behavior(directory, mutation)
    code, output = execute(
        directory,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_paths.qml"),
            "-import",
            str(directory),
        ],
    )
    (directory / "behavior.log").write_text(output)
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output
    if mutation:
        assert code != 0 and "FAIL!" in output, "negative control escaped"
        test_name = (
            "test_layout_tracks_position_and_size"
            if mutation.endswith("layout")
            else "test_rounded_and_square_edges"
        )
        assert re.search(r"FAIL!.*BackgroundPaths::" + test_name, output), output
        print("NEGATIVE_CONTROL_DETECTED", mutation)
    else:
        assert code == 0 and "13 passed, 0 failed" in output, output
        print("BACKGROUND_PATHS_BEHAVIOR_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument(
        "--mutation",
        choices=("panel-layout", "bar-layout", "panel-rounding", "bar-rounding"),
    )
    args = parser.parse_args()
    assert not args.mutation or args.mode == "behavior"
    directory = args.artifacts.resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
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
        if args.mode == "lint":
            lint(directory)
        else:
            behavior(directory, args.mutation)
    finally:
        assert settings.read_bytes() == original, "Real settings changed"
        assert backup.read_bytes() == original, "Backup changed"
        print("SETTINGS_SHA_UNCHANGED", digest)


if __name__ == "__main__":
    main()
