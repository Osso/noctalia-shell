#!/usr/bin/env python3
"""Bounded lint and offscreen interaction proof for ten production widgets."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "NIconButtonHot",
    "NSlider",
    "NIconButton",
    "NCircleStat",
    "NSpinBox",
    "NDropShadow",
    "NLabel",
    "NToggle",
    "NRadioButton",
    "NCheckbox",
)


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    write = helper.write_module
    singleton = helper.singleton
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(
        fontDefault="sans-serif",
        fontFixed="monospace",
        fontDefaultScale=1,
        fontFixedScale=1,
    )
    defaults["general"].update(
        animationDisabled=True, enableShadows=False, shadowOffsetX=2, shadowOffsetY=3
    )
    style = dict(
        baseWidgetSize=32,
        uiScaleRatio=1,
        sliderWidth=200,
        radiusXS=2,
        radiusS=4,
        radiusL=12,
        borderS=1,
        borderM=2,
        borderL=3,
        marginXXS=2,
        marginS=4,
        marginM=8,
        fontSizeXS=8,
        fontSizeS=10,
        fontSizeM=12,
        fontSizeL=14,
        fontWeightMedium=500,
        fontWeightSemiBold=600,
        fontWeightBold=700,
        animationNormal=0,
        animationFast=0,
        opacityFull=1,
        opacityMedium=0.5,
        shadowOpacity=0.4,
        shadowBlur=0.6,
        shadowBlurMax=32,
    )
    colors = dict(
        mSurface="#202020",
        mSurfaceVariant="#303030",
        mPrimary="#abcdef",
        mOnPrimary="#101010",
        mOnSurface="#ffffff",
        mOnSurfaceVariant="#cccccc",
        mHover="#404040",
        mOnHover="#00ff00",
        mOutline="#808080",
        transparent="transparent",
        black="#000000",
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f"property color {key}: {json.dumps(value)}"
                    for key, value in colors.items()
                )
            ),
            "Icons": singleton(
                'property string defaultIcon: "disc"\nproperty string fontFamily: "sans-serif"\nfunction get(name) { return "*"; }'
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            name: (ROOT / f"Widgets/{name}.qml").read_text()
            for name in (*NAMES, "NText", "NIcon")
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                'property string lastText: ""\nfunction show(item, text, direction) { lastText = text; }\nfunction hide() { lastText = ""; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.Power",
        {
            "PowerProfileService": singleton(
                "property bool noctaliaPerformanceMode: false"
            ),
        },
    )
    # NIconButton's unused Quickshell imports must resolve without a shell instance.
    for module in ("Quickshell", "Quickshell.Widgets"):
        write(directory, module, {"FixtureMarker": "import QtQuick\nQtObject {}"})
    (directory / "tst_simple_widgets.qml").write_text(
        (ROOT / "Tests/Qml/SimpleWidgetsWarningsHarness.qml").read_text()
    )


def run_behavior(directory):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    assert (
        hashlib.sha256(backup.read_bytes()).digest()
        == hashlib.sha256(original).digest()
    )
    stage_runtime(directory)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory),
                "-import",
                str(directory),
            ],
            cwd=ROOT,
            env=load_helper("media-mini-warnings").isolate_environment(directory),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"widget behavior exit {result.returncode}"
        assert "0 failed" in output
        assert not re.search(
            r"QWARN|QFATAL|ReferenceError|TypeError|Binding loop", output
        ), output
    finally:
        assert settings.read_bytes() == original, "real settings changed"


def run_lint(directory):
    load_helper("media-mini-warnings").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            *(str(directory / "qs/Widgets" / f"{name}.qml") for name in NAMES),
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
    print("SIMPLE_WIDGETS_LINT_COUNTS", dict(counts))
    # layer.effect is an implicit Component; its root refs are already qualified.
    # Preserve that boundary rather than adding ComponentBehavior: Bound.
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    assert counts == {"unqualified": 7}, f"unexpected widget warnings: {dict(counts)}"
    assert all("/Widgets/NDropShadow.qml:" in line for line in warnings), output
    assert result.returncode == 0, f"qmllint exit {result.returncode}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-simple-widget-proof-"
    ) as temporary:
        directory = Path(temporary)
        (run_lint if args.mode == "lint" else run_behavior)(directory)


if __name__ == "__main__":
    main()
