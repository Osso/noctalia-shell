#!/usr/bin/env python3
"""SessionMenuTab-only diagnostics and sandboxed production UI with synthetic settings."""

import argparse
import json
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/SessionMenuTab.qml")


def helper(filename):
    spec = spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory):
    writer = helper("about-tab-warnings.test.py")
    write = writer.write_module
    singleton = writer.singleton
    controls = (
        "NHeader",
        "NText",
        "NIcon",
        "NLabel",
        "NDivider",
        "NToggle",
        "NComboBox",
        "NValueSlider",
        "NSlider",
        "NListView",
    )
    write(
        directory,
        "qs.Widgets",
        {name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls},
    )
    write(directory, "qs.Tabs", {"SessionMenuTab": (ROOT / TARGET).read_text()})
    write(directory, "Quickshell", {"Fixture": "import QtQuick\nQtObject {}"})
    write(directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Services.UI",
        {"TooltipService": singleton("function show(...args) {}\nfunction hide() {}")},
    )
    settings = {
        "ui": {
            "fontDefault": "Sans Serif",
            "fontFixed": "monospace",
            "fontDefaultScale": 1,
            "fontFixedScale": 1,
        },
        "sessionMenu": {
            "position": "center",
            "showHeader": True,
            "enableCountdown": True,
            "countdownDuration": 5000,
            "powerOptions": [],
        },
    }
    style = {
        "uiScaleRatio": 1,
        "marginXXS": 2,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 9,
        "marginL": 13,
        "radiusXS": 2,
        "radiusS": 4,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "borderM": 2,
        "borderL": 3,
        "baseWidgetSize": 32,
        "sliderWidth": 200,
        "fontSizeXS": 9,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 16,
        "fontWeightRegular": 400,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
        "animationFast": 0,
        "animationNormal": 0,
    }
    colors = {
        "mPrimary": "#3355aa",
        "mSecondary": "#557733",
        "mOnPrimary": "#ffffff",
        "mSurface": "#202020",
        "mSurfaceVariant": "#141414",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#aaaaaa",
        "mOutline": "#808080",
        "mHover": "#404040",
        "mOnHover": "#ffffff",
        "transparent": "transparent",
    }
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(settings)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}" for key, value in style.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in colors.items()
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Icons": singleton(
                'property string defaultIcon: "disc"\nproperty string fontFamily: "Sans Serif"\nfunction get(name) { return "*"; }'
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    (directory / "tst_session_menu_tab.qml").write_text(
        (ROOT / "Tests/Qml/SessionMenuTabWarningsHarness.qml").read_text()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "isolation"))
    parser.add_argument("--mutation", action="store_true")
    args = parser.parse_args()
    isolation = helper("wallpaper-tab-warnings.test.py")
    with tempfile.TemporaryDirectory(prefix="noctalia-session-menu-tab-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        isolation.install_audit(directory)
        environment = isolation.isolated_environment(directory)
        if args.mode == "lint":
            helper("media-mini-warnings.test.py").stage_modules(directory)
            argv = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                temporary,
                str(directory / "qs" / TARGET),
            ]
        elif args.mode == "runtime":
            stage_runtime(directory)
            if args.mutation:
                staged = directory / "qs/Tabs/SessionMenuTab.qml"
                original = staged.read_text()
                mutated = original.replace(
                    '"enabled": !delegateItem.entryEnabled',
                    '"enabled": delegateItem.entryEnabled',
                )
                assert mutated != original, "Mutation did not apply"
                staged.write_text(mutated)
            argv = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_session_menu_tab.qml"),
                "-import",
                temporary,
            ]
        else:
            argv = [
                "/usr/bin/python3",
                "-c",
                """import os, pathlib
home = pathlib.Path(os.environ['HOME'])
assert home.is_dir()
for path in ('/home/osso/.config/noctalia/settings.json', '/syncthing', '/run/user'):
    assert not pathlib.Path(path).exists(), path
    print('SANDBOX_PATH_ABSENT', path)
for mode in ('rb', 'wb'):
    try:
        open('/home/osso/.config/noctalia/settings.json', mode)
    except OSError:
        print('SANDBOX_SETTINGS_DENIED', mode)
    else:
        raise AssertionError('real settings accessible')
""",
            ]
        result = subprocess.run(
            isolation.sandbox_command(directory, argv),
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
            print("SESSION_MENU_TAB_LINT_COUNTS", dict(counts), "TOTAL", len(warnings))
            # itemAtIndex() advertises QQuickItem, not this delegate's drag fields.
            # Keep these diagnostics visible; do not cast or fabricate metadata.
            assert counts == {"missing-property": 3}, dict(counts)
            blocked_members = re.findall(
                r'Member "([^"]+)" not found on type "QQuickItem"', output
            )
            assert sorted(blocked_members) == [
                "dragStartIndex",
                "dragTargetIndex",
                "dragging",
            ], blocked_members
        elif args.mode == "runtime":
            assert "0 failed" in output, "Missing successful QtTest completion"
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
                output,
            ), output
        assert result.returncode == 0, result.returncode


if __name__ == "__main__":
    main()
