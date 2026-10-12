#!/usr/bin/env python3
"""Strict staged harness lint and isolated interaction proof for ten widgets."""

import argparse
from collections import Counter
import importlib.util
import json
import os
import sys
from pathlib import Path
import re
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


isolation = load_helper("grid-list-warnings")


def deny_real_config(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args:
        path = args[0]
        if isinstance(path, (str, bytes, os.PathLike)):
            requested = Path(os.path.abspath(os.fsdecode(path)))
            protected = Path("/home/osso/.config")
            if requested == protected or protected in requested.parents:
                raise PermissionError(f"REAL_CONFIG_AUDIT_DENIED: {requested}")


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


def run_behavior(directory, environment):
    stage_runtime(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_simple_widgets.qml"),
            "-import",
            str(directory),
        ],
        "simple-widgets-runtime",
    )
    assert code == 0, f"widget behavior exit {code}"
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def lint_harness(directory, environment, inject_warning=False):
    stage_runtime(directory)
    harness = directory / "tst_simple_widgets.qml"
    if inject_warning:
        source = harness.read_text()
        harness.write_text(
            source.replace(
                "id: tests",
                "id: tests\n    property int injectedWarning: tests.missingLintProbe",
                1,
            )
        )
    code, output = isolation.run_audited(
        directory,
        environment,
        [
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
        ],
        "simple-widgets-harness-lint",
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("SIMPLE_WIDGETS_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
    assert not warnings or code != 0, "qmllint accepted harness warnings"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        code = lint_harness(staged, isolation.isolated_environment(staged), injected)
        if injected:
            assert code != 0, "genuine harness warning accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("SIMPLE_WIDGETS_HARNESS_WARNING_REJECTED")


def run_lint(directory, environment):
    load_helper("media-mini-warnings").stage_modules(directory)
    code, output = isolation.run_audited(
        directory,
        environment,
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            *(str(directory / "qs/Widgets" / f"{name}.qml") for name in NAMES),
        ],
        "simple-widgets-lint",
    )
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
    assert code == 0, f"qmllint exit {code}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "behavior", "lint-harness", "lint-harness-regression")
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="noctalia-simple-widget-proof-"
    ) as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        sys.addaudithook(deny_real_config)
        try:
            (Path("/home/osso/.config") / "fixture-denial-probe").read_bytes()
        except PermissionError as error:
            print(error)
        else:
            raise AssertionError("real config guard failed")
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, environment))
        elif args.mode == "lint-harness-regression":
            lint_harness_regression(directory)
        else:
            (run_lint if args.mode == "lint" else run_behavior)(directory, environment)


if __name__ == "__main__":
    main()
