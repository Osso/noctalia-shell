#!/usr/bin/env python3
"""Standalone NScrollView proof; no shell, services, or real settings access."""

import argparse
from collections import Counter
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def stage(directory, mutation):
    commons = directory / "qs/Commons"
    widgets = directory / "qs/Widgets"
    commons.mkdir(parents=True)
    widgets.mkdir(parents=True)
    (commons / "qmldir").write_text(
        "module qs.Commons\nsingleton Style 1.0 Style.qml\n"
        "singleton NColor 1.0 NColor.qml\n"
    )
    (commons / "Style.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {"
        "property real radiusM: 8; property int animationFast: 0 }\n"
    )
    (commons / "NColor.qml").write_text(
        "pragma Singleton\nimport QtQuick\nQtObject {"
        'property color mHover: "#404040"; property color transparent: "transparent" }\n'
    )
    (widgets / "qmldir").write_text(
        "module qs.Widgets\nNScrollView 1.0 NScrollView.qml\n"
    )
    source = (ROOT / "Widgets/NScrollView.qml").read_text()
    # Disposable negative control: palette ownership must affect rendered handles.
    if mutation == "palette":
        source = source.replace("root.handlePressedColor", "root.handleColor")
    (widgets / "NScrollView.qml").write_text(source)
    shutil.copyfile(
        ROOT / "Tests/Qml/ScrollViewWarningsHarness.qml",
        directory / "tst_scrollview.qml",
    )


def isolated_environment(directory):
    environment = os.environ.copy()
    for key in tuple(environment):
        if (
            key.startswith("QML")
            or key.startswith("QT_")
            or key
            in (
                "DISPLAY",
                "WAYLAND_DISPLAY",
                "DBUS_SESSION_BUS_ADDRESS",
                "NIRI_SOCKET",
                "HYPRLAND_INSTANCE_SIGNATURE",
                "SWAYSOCK",
            )
        ):
            environment.pop(key)
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        QML_DISABLE_DISK_CACHE="1",
    )
    return environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--mutation", choices=("palette",))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-scrollview-") as temporary:
        directory = Path(temporary)
        stage(directory, args.mutation)
        if args.mode == "lint":
            command = [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs/Widgets/NScrollView.qml"),
            ]
        else:
            command = [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_scrollview.qml"),
                "-import",
                str(directory),
            ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=isolated_environment(directory),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        if args.mode == "lint":
            counts = Counter(
                re.findall(r"\[([^]]+)\]", line)[-1]
                for line in output.splitlines()
                if line.startswith("Warning:")
            )
            print("SCROLLVIEW_LINT_COUNTS", dict(counts))
            assert not counts, dict(counts)
        else:
            assert "0 failed" in output, output
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
            ), output
        assert result.returncode == 0, f"{args.mode} exit {result.returncode}"


if __name__ == "__main__":
    main()
