#!/usr/bin/env python3
"""Six layout diagnostics; exact production descendant geometry offscreen.

Widths 480/1000, scales 1/1.25. Bootstrap/settings/services are inert;
components, supporting widgets, Style and icon font remain production sources.
No physical input, live-service, locale matrix or whole-shell proof is claimed.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Modules/Cards/CalendarHeaderCard.qml"),
    Path("Modules/Cards/SystemMonitorCard.qml"),
    Path("Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml"),
)
GOLDEN = ROOT / "Tests/fixtures/remaining-layout-geometry.json"
SETTINGS = Path("/home/osso/.config/noctalia/settings.json")


def load_helpers():
    spec = importlib.util.spec_from_file_location(
        "setup_geometry", ROOT / "Tests/setup-layout-geometry.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory, expected):
    spec = importlib.util.spec_from_file_location(
        "lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
    counts = []
    for target in TARGETS:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        (directory / (target.stem + ".lint.log")).write_text(output)
        count = sum(
            line.startswith("Warning:") and "[Quick.layout-positioning]" in line
            for line in output.splitlines()
        )
        counts.append(count)
        print(
            f"{target}: {count} layout warnings (other diagnostics retained in artifacts)"
        )
    assert counts == expected, f"layout warnings {counts} != {expected}"


def stage_runtime(directory, helpers, source_root):
    for relative in ("Commons", "Widgets", "Helpers", "Assets"):
        shutil.copytree(source_root / relative, directory / relative)
    for target in TARGETS:
        destination = directory / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / target, destination)
    helpers.write_singleton(
        directory,
        "Commons/Settings.qml",
        "property var data: ("
        + (ROOT / "Assets/settings-default.json").read_text()
        + ")",
    )
    palette = dict(
        helpers.PALETTE,
        mOnSecondary="#1a151f",
        mOnTertiary="#1a151f",
        mOnError="#1a151f",
    )
    helpers.write_singleton(
        directory,
        "Commons/NColor.qml",
        "\n".join(
            f'readonly property color {key}: "{value}"'
            for key, value in palette.items()
        ),
    )
    osd = directory / "Modules/OSD/OSD.qml"
    osd.parent.mkdir(parents=True, exist_ok=True)
    osd.write_text(
        "import QtQuick\nQtObject { enum Type { Volume, InputVolume, Brightness, LockKey } }\n"
    )
    fixtures = {
        "Commons/Logger.qml": "function i(...args) {}\nfunction d(...args) {}\nfunction w(...args) { console.warn(...args); }\nfunction e(...args) { console.error(...args); }\nfunction callStack() { console.trace(); }",
        "Commons/I18n.qml": 'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }',
        "Commons/Time.qml": "readonly property date now: new Date(2023, 11, 25, 14, 30, 45)\nfunction beginSecondUpdates() {}\nfunction endSecondUpdates() {}",
        "Services/Power/PowerProfileService.qml": "readonly property bool noctaliaPerformanceMode: false",
        "Services/System/SystemStatService.qml": 'readonly property real cpuUsage: 37\nreadonly property real cpuTemp: 52\nreadonly property real memPercent: 64\nreadonly property var diskPercents: ({"/": 28})',
        "Services/System/FontService.qml": 'property ListModel availableFonts: ListModel { ListElement { key: "DejaVu Sans"; name: "DejaVu Sans" } }',
        "Services/Location/LocationService.qml": 'readonly property var data: ({weather: {timezone_abbreviation: "CST"}})',
        "Services/UI/TooltipService.qml": "function show(...args) { throw new Error('Unexpected tooltip'); }\nfunction hide() {}",
    }
    for relative, body in fixtures.items():
        helpers.write_singleton(directory, relative, body)
    shutil.copyfile(
        ROOT / "Tests/Qml/RemainingLayoutGeometryHarness.qml", directory / "shell.qml"
    )


def lint_harness(directory, source_root):
    sources = directory / "qs"
    sources.mkdir()
    stage_runtime(sources, load_helpers(), source_root)
    modules = {}
    for path in sorted(sources.rglob("*.qml")):
        relative = path.relative_to(sources)
        for parent in (relative.parent, *relative.parent.parents):
            modules.setdefault(parent, [])
        singleton = bool(
            re.search(r"^\s*pragma\s+Singleton\b", path.read_text(), re.MULTILINE)
        )
        prefix = "singleton " if singleton else ""
        modules[relative.parent].append(f"{prefix}{path.stem} 1.0 {path.name}\n")
    for parent, declarations in modules.items():
        module = ".".join(("qs", *parent.parts))
        (sources / parent / "qmldir").write_text(
            f"module {module}\n" + "".join(declarations)
        )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--max-warnings",
            "0",
            "-I",
            str(directory),
            str(sources / "shell.qml"),
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    (directory / "harness-lint.log").write_text(output)
    print(output, end="")
    warning_count = len(re.findall(r"^Warning:", output, re.MULTILINE))
    print("REMAINING_LAYOUT_HARNESS_LINT_WARNINGS", warning_count)
    return result.returncode or int(warning_count > 0)


def assert_content(snapshots, helpers):
    assert len(snapshots) == 12
    for snapshot in snapshots:
        scenario = snapshot["scenario"]
        nodes = list(helpers.flatten(snapshot["tree"]))
        assert snapshot["tree"]["width"] == scenario["width"], scenario
        assert all(node["width"] >= 0 and node["height"] >= 0 for node in nodes), (
            scenario
        )
        texts = [node.get("text", "") for node in nodes]
        if scenario["component"] == "calendar":
            assert "25" in texts and "Dallas" in texts and " (CST)" in texts, texts
        elif scenario["component"] == "monitor":
            gauges = [node for node in nodes if "contentScale" in node]
            assert [node["value"] for node in gauges] == [37, 52, 64, 28]
            assert all(
                node["height"] == round(65 * scenario["scale"]) for node in gauges
            )
            assert all(
                node["width"] == 68 and node["contentScale"] == 0.8 for node in gauges
            )
            assert all(text in texts for text in ["37%", "52°C", "64%", "28%"])
        else:
            assert "HH:mm" in texts and "yyyy-MM-dd" in texts, texts
            assert any(node.get("contentHeight", 0) > 0 for node in nodes)


def behavior(directory, capture_only, source_root):
    helpers = load_helpers()
    stage_runtime(directory, helpers, source_root)
    environment = helpers.isolated_environment(directory)
    for variable in ("NOCTALIA_CONFIG_DIR", "NOCTALIA_CACHE_DIR"):
        path = directory / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    try:
        result = subprocess.run(
            ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or b"") + (error.stderr or b"")
        (directory / "runtime.log").write_bytes(output)
        raise AssertionError(
            f"Offscreen runtime timed out; see {directory / 'runtime.log'}"
        ) from error
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    assert result.returncode == 0 and not re.search(
        r"\b(?:WARN|ERROR|FATAL)\b", output
    ), output
    match = re.search(r"REMAINING_LAYOUT_GEOMETRY (\[.*\])", output)
    assert match, output
    snapshots = json.loads(match[1])
    (directory / "geometry.json").write_text(json.dumps(snapshots, indent=2) + "\n")
    assert_content(snapshots, helpers)
    if not capture_only:
        helpers.assert_geometry(snapshots, json.loads(GOLDEN.read_text()))
    print(
        "PASS: 12 production geometry/content snapshots; widths 480/1000, scales 1/1.25"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--capture-only", action="store_true")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=ROOT,
        help="Immutable pre-edit source staging for baseline capture",
    )
    parser.add_argument("--expected-layout", nargs=3, type=int, default=[0, 0, 0])
    args = parser.parse_args()
    args.artifacts.mkdir(mode=0o700, parents=True, exist_ok=False)
    before = SETTINGS.read_bytes()
    backup = args.artifacts / "settings.backup.json"
    with backup.open("xb") as stream:
        os.chmod(backup, 0o600)
        stream.write(before)
    assert (
        hashlib.sha256(backup.read_bytes()).digest() == hashlib.sha256(before).digest()
    )
    exit_code = 0
    try:
        if args.mode == "lint-harness":
            exit_code = lint_harness(args.artifacts, args.source_root)
        elif args.mode == "lint":
            lint(args.artifacts, args.expected_layout)
        else:
            behavior(args.artifacts, args.capture_only, args.source_root)
    finally:
        assert SETTINGS.read_bytes() == before, "real settings changed"
    print("Real settings unchanged; bounded processes exited.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
