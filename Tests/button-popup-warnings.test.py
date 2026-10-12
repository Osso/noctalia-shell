#!/usr/bin/env python3
"""Bounded button/popup proof using real widgets and Quickshell offscreen.

Host config is absent from the child sandbox. Settings/services are inert;
PopupWindow, PopupAnchor, Qt input, layout, text and icons remain production.
"""

import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).absolute().parents[1]
NAMES = ("NButton", "NPopupContextMenu")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


isolation = load("grid-list-warnings")


def stage_runtime(directory, bound, mutation, owner_shadow):
    load("simple-widgets-warnings").stage_runtime(directory)
    (directory / "tst_simple_widgets.qml").unlink()
    # Do not replace Quickshell's actual window/anchor backend with fixtures.
    shutil.rmtree(directory / "Quickshell")
    widgets = directory / "qs/Widgets"
    shutil.rmtree(widgets)
    widgets.mkdir()
    (widgets / "qmldir").write_text(
        "module qs.Widgets\n"
        + "".join(f"{name} 1.0 {name}.qml\n" for name in (*NAMES, "NText", "NIcon"))
    )
    for name in (*NAMES, "NText", "NIcon"):
        source = (ROOT / f"Widgets/{name}.qml").read_text()
        if (
            name == "NPopupContextMenu"
            and bound
            and not source.startswith("pragma ComponentBehavior: Bound")
        ):
            source = "pragma ComponentBehavior: Bound\n" + source
        if name == "NButton" and owner_shadow:
            source = source.replace(
                "id: mouseArea", 'id: mouseArea\n    property string tooltipText: ""'
            )
        if name == "NButton" and mutation == "button-owner":
            source = source.replace("if (root.tooltipText)", "if (tooltipText)")
        if name == "NPopupContextMenu" and mutation == "popup-close":
            source = source.replace(
                "function close() {\n    visible = false;",
                "function close() {\n    visible = true;",
            )
        (widgets / f"{name}.qml").write_text(source)
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty real marginL: 12\nproperty real marginXS: 3\nproperty real radiusM: 8",
        )
    )
    # Quickshell resolves qs.* against the config root, not an import prefix.
    for module in (directory / "qs").iterdir():
        shutil.move(str(module), directory / module.name)
    (directory / "qs").rmdir()
    shutil.copyfile(
        ROOT / "Tests/Qml/ButtonPopupWarningsHarness.qml", directory / "shell.qml"
    )


def lint(directory, environment):
    load("media-mini-warnings").stage_modules(directory)
    for name in NAMES:
        code, output = isolation.run_audited(
            directory,
            environment,
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / f"qs/Widgets/{name}.qml"),
            ],
            name,
        )
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(name, "LINT_COUNTS", dict(counts), "EXIT", code)
        expected = {} if name == "NButton" else {"missing-property": 1}
        assert counts == expected, dict(counts)
        if expected:
            assert 'Member "updateAnchor" not found on type "PopupAnchor"' in output
        assert code == 0, code


def runtime(directory, environment, bound, mutation, owner_shadow):
    stage_runtime(directory, bound, mutation, owner_shadow)
    code, output = isolation.run_audited(
        directory,
        environment,
        ["quickshell", "--no-color", "-p", str(directory / "shell.qml")],
        "button-popup-runtime",
    )
    assert code == 0, code
    assert "BUTTON_POPUP_PASS 6 cases" in output, output
    diagnostics = [
        line
        for line in output.splitlines()
        if re.search(
            r" WARN[: ]| ERROR[: ]| FATAL[: ]|QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop",
            line,
        )
    ]
    platform_warnings = [
        line
        for line in diagnostics
        if line == "  WARN: This plugin does not support setting window masks"
    ]
    print("OFFSCREEN_WINDOW_MASK_WARNINGS", len(platform_warnings))
    assert diagnostics == platform_warnings, diagnostics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument(
        "--bound",
        action="store_true",
        help="private-copy Bound recreation proof before production edit",
    )
    parser.add_argument("--owner-shadow", action="store_true")
    parser.add_argument("--mutation", choices=("button-owner", "popup-close"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-button-popup-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_settings_guard(directory)
        isolation.prove_settings_guard()
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            lint(directory, environment)
        else:
            runtime(
                directory, environment, args.bound, args.mutation, args.owner_shadow
            )
