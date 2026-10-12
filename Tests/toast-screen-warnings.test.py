#!/usr/bin/env python3
"""Toast-only native Region/owner proof on the existing private Winit adapter.

Real ToastScreen, SimpleToast, PanelWindow and Regions; inert service/widgets.
No host desktop, settings, device access or installed changes. Retain raw client
and Wayland diagnostics, geometry snapshots and private cleanup evidence.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Toast/ToastScreen.qml")


def helpers():
    spec = importlib.util.spec_from_file_location(
        "toast_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helpers().stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("TOAST_SCREEN_LINT_COUNTS", dict(counts))
    assert counts == {"missing-property": 6}, dict(counts)
    assert result.returncode == 0, result.returncode


def stage_runtime(directory, shadow=False):
    write = helpers().write_singleton
    for relative in (TARGET, Path("Modules/Toast/SimpleToast.qml")):
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["notifications"].update(location="top_right", overlayLayer=True)
    defaults["bar"].update(
        position="top", floating=True, marginVertical=2, marginHorizontal=3
    )
    write(
        directory / "Commons", "Settings", "property var data: " + json.dumps(defaults)
    )
    style = dict(
        uiScaleRatio=1,
        marginM=8,
        marginL=12,
        marginXL=16,
        marginXXS=2,
        radiusL=12,
        borderM=2,
        barHeight=32,
        animationNormal=0,
        animationFast=20,
        fontSizeXXL=20,
        fontSizeL=14,
        fontSizeM=12,
        fontWeightBold=700,
    )
    write(
        directory / "Commons",
        "Style",
        "\n".join(f"property real {key}: {value}" for key, value in style.items()),
    )
    colors = dict(
        mSurface="#202020",
        mPrimary="#00ff00",
        mError="#ff0000",
        mOutline="#808080",
        mOnSurface="#ffffff",
        transparent="transparent",
    )
    write(
        directory / "Commons",
        "NColor",
        "\n".join(f'property color {key}: "{value}"' for key, value in colors.items()),
    )
    write(directory / "Commons", "Logger", "function d(...args) {}")
    write(
        directory / "Services/UI",
        "ToastService",
        "signal notify(string message, string description, string icon, string type, int duration)",
    )
    widgets = directory / "Widgets"
    widgets.mkdir()
    for name, source in {
        "NText": "Text { property real pointSize: 12; font.pointSize: pointSize }",
        "NIcon": 'Text { property string icon; property real pointSize: 12; text: "*"; font.pointSize: pointSize }',
        "NDropShadow": "Item { property Item source; property bool autoPaddingEnabled }",
    }.items():
        (widgets / f"{name}.qml").write_text("import QtQuick\n" + source + "\n")
    target = directory / TARGET
    source = target.read_text()
    if shadow:
        # A colliding property in the nested component must not capture either
        # owner's screen or hidden callback. Keep both native views independent.
        source = source.replace(
            "      id: panel\n",
            "      id: panel\n"
            '      property var root: ({screen: "shadow-screen", onToastHidden: function() {\n'
            '        console.log("TOAST_SHADOW_HIDDEN");\n'
            "      }})\n",
            1,
        )
    target.write_text(source)
    shutil.copyfile(
        ROOT / "Tests/Qml/ToastScreenWarningsHarness.qml", directory / "shell.qml"
    )


def lint_harness(directory):
    runtime = directory / "runtime"
    runtime.mkdir()
    stage_runtime(runtime)
    imports = directory / "imports"
    helpers().stage_modules(imports, source_root=runtime)
    return check_harness(imports, imports / "qs/shell.qml")


def private_display():
    spec = importlib.util.spec_from_file_location(
        "toast_private_display", ROOT / "Tests/popup-private-display.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_native_regions(trace):
    """Assert compositor-facing masks and layer teardown, ignoring object IDs."""
    layers = []
    active_layers = {}
    surfaces = {}
    regions = {}
    for line in trace.splitlines():
        created = re.search(
            r"get_layer_surface\(new id zwlr_layer_surface_v1#(\d+), wl_surface#(\d+), wl_output#\d+, (\d+),",
            line,
        )
        if created:
            layer_id, surface_id, level = created.groups()
            layer = {"level": int(level), "masks": [], "destroyed": False}
            layers.append(layer)
            active_layers[layer_id] = layer
            surfaces[surface_id] = layer
        rectangle = re.search(r"wl_region#(\d+)\.(add|subtract)\(([^)]+)\)", line)
        if rectangle:
            region_id, operation, coordinates = rectangle.groups()
            regions.setdefault(region_id, []).append(
                [operation, *[int(value) for value in coordinates.split(",")]]
            )
        applied = re.search(
            r"wl_surface#(\d+)\.set_input_region\(wl_region#(\d+)\)", line
        )
        if applied:
            surface_id, region_id = applied.groups()
            assert surface_id in surfaces, "input mask without a native layer"
            surfaces[surface_id]["masks"].append(regions[region_id])
        region_destroyed = re.search(r"wl_region#(\d+)\.destroy\(\)", line)
        if region_destroyed:
            regions.pop(region_destroyed[1], None)
        policy = re.search(
            r"zwlr_layer_surface_v1#(\d+)\.(set_anchor|set_margin|set_exclusive_zone|set_keyboard_interactivity)\(([^)]+)\)",
            line,
        )
        if policy:
            layer_id, name, arguments = policy.groups()
            active_layers[layer_id][name] = [
                int(value) for value in arguments.split(",")
            ]
        destroyed = re.search(r"zwlr_layer_surface_v1#(\d+)\.destroy\(\)", line)
        if destroyed:
            active_layers.pop(destroyed[1])["destroyed"] = True
    assert len(layers) == 4 and not active_layers, layers
    for index, layer in enumerate(layers):
        assert layer["level"] == 3 and layer["destroyed"], layer
        assert layer["set_anchor"] == [9], layer
        assert layer["set_margin"] == [64, 0, 0, 0], layer
        assert layer["set_exclusive_zone"] == [-1], layer
        assert layer["set_keyboard_interactivity"] == [0], layer
        assert layer["masks"][0] == [["add", 0, 0, 400, 103]], layer
        final = [["add", 13, 17, 447, 143]] if index == 0 else [["add", 0, 0, 400, 103]]
        assert layer["masks"][-1] == final, layer
    return layers


def behavior(directory, shadow=False):
    stage_runtime(directory, shadow=shadow)
    display = private_display()
    log = directory / "client.stdout.raw"
    errors = directory / "client.stderr.raw"
    with (
        display.PopupPrivateDisplay(directory / "display") as environment,
        log.open("w") as stdout,
        errors.open("w") as stderr,
    ):
        environment["WAYLAND_DEBUG"] = "1"
        process = subprocess.Popen(
            display.sandbox(
                directory,
                ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
            ),
            cwd=directory,
            env=environment,
            stdout=stdout,
            stderr=stderr,
            text=True,
            start_new_session=True,
        )
        try:
            process.wait(timeout=20)
        finally:
            display.stop_owned(process)
            assert process.poll() is not None, "private toast client survived"
    output = log.read_text() + errors.read_text()
    print(log.read_text(), end="")
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(
            r" WARN[: ]| ERROR[: ]| FATAL[: ]|ReferenceError|TypeError|Binding loop|^warning:|queue destroyed",
            line,
            re.IGNORECASE,
        )
    ]
    print("TOAST_CLIENT_DIAGNOSTICS", diagnostics)
    assert process.returncode == 0, output
    assert not diagnostics, diagnostics
    assert "TOAST_SCREEN_BEHAVIOR_PASS" in output, output
    assert "TOAST_SHADOW_HIDDEN" not in output, output
    layers = assert_native_regions(errors.read_text())
    (directory / "native-regions.json").write_text(json.dumps(layers, indent=2) + "\n")
    print(
        "TOAST_NATIVE_REGION_PASS four layers destroyed; native masks and policy preserved"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "lint-harness", "behavior", "owner-shadow")
    )
    parser.add_argument(
        "--out", type=Path, help="retain raw evidence in a fresh directory"
    )
    args = parser.parse_args()

    def execute(directory):
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        if args.mode == "lint":
            lint(directory)
        else:
            behavior(directory, shadow=args.mode == "owner-shadow")

    if args.out is not None:
        directory = args.out.absolute()
        directory.mkdir(mode=0o700)
        execute(directory)
    else:
        with tempfile.TemporaryDirectory(prefix="toast-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            execute(directory)


if __name__ == "__main__":
    main()
