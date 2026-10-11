#!/usr/bin/env python3
"""Preserve observed date/time token geometry using real widgets offscreen.

Only bootstrap singletons are fixtures. Expected geometry comes from the four
pre/post-8fdbee18f cases (60 delegates); this is not a layout-warning lint test.
Run directly with python3; no live shell, services, or settings are loaded.
"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HARNESS = """import QtQuick
import QtTest
import qs.Widgets

TestCase {
    id: suite

    function findList(item) {
        if (typeof item.itemAtIndex === "function" && item.model !== undefined)
            return item;

        for (let child of item.children) {
            let found = findList(child);
            if (found)
                return found;
        }
        return null;
    }

    function compareRect(item, x, y, width, height) {
        compare(item.x, x, "x");
        compare(item.y, y, "y");
        compare(item.width, width, "width");
        compare(item.height, height, "height");
    }

    function test_geometry_data() {
        return [
            {
                "tag": "wide-normal",
                "parentWidth": 800,
                "longContent": false,
                "heights": [16]
            },
            {
                "tag": "narrow-normal",
                "parentWidth": 320,
                "longContent": false,
                "heights": [80]
            },
            {
                "tag": "wide-long",
                "parentWidth": 800,
                "longContent": true,
                "heights": [48, 16, 16]
            },
            {
                "tag": "narrow-long",
                "parentWidth": 320,
                "longContent": true,
                "heights": [400, 96, 32]
            }
        ];
    }

    function test_geometry(data) {
        let root = createTemporaryObject(component, suite, {
            "width": data.parentWidth,
            "height": 10000,
            "sampleDate": new Date(2023, 11, 25, 14, 30, 45)
        });
        verify(root !== null);
        let list = findList(root);
        verify(list !== null);
        if (data.longContent)
            list.model = [
                {
                    "category": "Exceptionally long translated category",
                    "token": "dddd, MMMM dd yyyy HH:mm:ss AP t",
                    "description": "A very long translated date and time description with many words for wrapping across multiple lines and preserving the geometry of every fixed size badge."
                },
                {
                    "category": "Month",
                    "token": "MMMM",
                    "description": "Supercalifragilisticexpialidocious repeated long unbroken description words"
                },
                {
                    "category": "Common",
                    "token": "yyyy-MM-dd",
                    "description": "Short description"
                }
            ];

        list.forceLayout();
        wait(100);
        compare(list.count, data.longContent ? 3 : 27);
        let top = 0;
        for (let index = 0; index < list.count; ++index) {
            let delegate = list.itemAtIndex(index);
            verify(delegate !== null, "Missing delegate " + index);
            let row = delegate.children.find(child => {
                return child.children.length === 4;
            });
            verify(row !== undefined, "Missing token row " + index);
            let textHeight = data.heights[data.longContent ? index : 0];
            let rowHeight = Math.max(22, textHeight) - 2;
            let badgeY = Math.max(0, (textHeight - 22) / 2);
            let textY = textHeight < 22 ? 3 : 0;
            let rowWidth = data.parentWidth - 20;
            compareRect(delegate, 0, top, data.parentWidth - 12, rowHeight + 8);
            compareRect(row, 4, 4, rowWidth, rowHeight);
            compareRect(row.children[0], 0, badgeY, 70, 22);
            compareRect(row.children[1], 79, badgeY, 100, 22);
            compareRect(row.children[2], 188, textY, rowWidth - 287, textHeight);
            compareRect(row.children[3], rowWidth - 90, badgeY, 90, 22);
            top += rowHeight + 8;
        }
        compare(list.contentHeight, top);
    }

    name: "DateTimeTokensGeometry"
    width: 1000
    height: 10000
    when: true

    Component {
        id: component

        NDateTimeTokens {}
    }
}
"""


def write_singleton(directory, name, body):
    (directory / f"{name}.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"
    )


def stage_harness(directory):
    commons = directory / "qs/Commons"
    widgets = directory / "qs/Widgets"
    for path in (commons, widgets):
        path.mkdir(parents=True, mode=0o700)
    names = ("NDateTimeTokens", "NListView", "NText")
    for name in names:
        shutil.copyfile(ROOT / f"Widgets/{name}.qml", widgets / f"{name}.qml")
    (widgets / "qmldir").write_text(
        "module qs.Widgets\n" + "".join(f"{name} 1.0 {name}.qml\n" for name in names)
    )
    style = {
        "fontSizeXS": 9,
        "fontSizeS": 10,
        "fontSizeM": 11,
        "fontWeightMedium": 500,
        "fontWeightBold": 700,
        "radiusS": 12,
        "radiusM": 16,
        "borderS": 1,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 9,
        "animationFast": 0,
        "uiScaleRatio": 1,
    }
    write_singleton(
        commons,
        "Style",
        "\n".join(f"property real {name}: {value}" for name, value in style.items()),
    )
    write_singleton(
        commons,
        "NColor",
        "\n".join(
            f'property color {name}: "#808080"'
            for name in (
                "mSurface",
                "mOutline",
                "mPrimary",
                "mOnPrimary",
                "mSurfaceVariant",
                "mOnSurface",
                "mOnSurfaceVariant",
                "mSecondary",
                "mOnSecondary",
                "mTertiary",
                "mOnTertiary",
                "mError",
                "mOnError",
                "mHover",
            )
        )
        + '\nproperty color transparent: "transparent"',
    )
    write_singleton(
        commons,
        "Settings",
        'property var data: ({ui: {fontDefault: "DejaVu Sans", '
        "fontDefaultScale: 1, fontFixedScale: 1}})",
    )
    write_singleton(
        commons,
        "I18n",
        'property var locale: Qt.locale("en_US")\n'
        'function tr(key) { return "24-hour time with seconds"; }',
    )
    (commons / "qmldir").write_text(
        "module qs.Commons\n"
        + "".join(
            f"singleton {name} 1.0 {name}.qml\n"
            for name in ("Style", "NColor", "Settings", "I18n")
        )
    )
    (directory / "tst_geometry.qml").write_text(HARNESS)


def isolate_environment(directory):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_", "QS_"))
        and key
        not in (
            "HOME",
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "DBUS_SYSTEM_BUS_ADDRESS",
        )
    }
    for variable, name in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "config",
        "XDG_CACHE_HOME": "cache",
        "XDG_DATA_HOME": "data",
        "XDG_STATE_HOME": "state",
        "XDG_RUNTIME_DIR": "runtime",
        "NOCTALIA_CONFIG_DIR": "noctalia-config",
        "NOCTALIA_CACHE_DIR": "noctalia-cache",
    }.items():
        path = directory / name
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QT_QUICK_CONTROLS_STYLE="Basic",
        QT_FORCE_STDERR_LOGGING="1",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/noctalia-test-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/noctalia-test-system",
    )
    return environment


def main():
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes() if settings.exists() else None
    with tempfile.TemporaryDirectory(prefix="noctalia-datetime-layout-") as temporary:
        directory = Path(temporary)
        if original is not None:
            backup = directory / "settings.backup.json"
            backup.touch(mode=0o600)
            backup.write_bytes(original)
            assert (
                hashlib.sha256(backup.read_bytes()).digest()
                == hashlib.sha256(original).digest()
            ), "settings backup hash mismatch"
        stage_harness(directory)
        try:
            result = subprocess.run(
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory / "tst_geometry.qml"),
                    "-import",
                    str(directory),
                ],
                cwd=directory,
                env=isolate_environment(directory),
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            current = settings.read_bytes() if settings.exists() else None
            assert current == original, "real settings changed"
        output = result.stdout + result.stderr
        print(output, end="")
        assert result.returncode == 0, f"geometry test failed: exit {result.returncode}"
        assert "6 passed, 0 failed" in output, "four geometry cases did not finish"
        assert "QWARN" not in output and "QFATAL" not in output, output
        print("Real settings unchanged; isolated runtime cleaned up.")


if __name__ == "__main__":
    main()
