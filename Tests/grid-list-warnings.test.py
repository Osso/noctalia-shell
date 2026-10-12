#!/usr/bin/env python3
"""Standalone grid/list proof. Never inspect real settings or desktop processes."""

import argparse
from collections import Counter
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).absolute().parents[1]
WIDGETS = ("NGridView", "NListView")


def install_settings_guard(directory):
    def guard(path):
        if not isinstance(path, (str, bytes, os.PathLike)):
            return
        text = os.fsdecode(path)
        if "settings.json" in text and not text.startswith(str(directory) + "/"):
            raise PermissionError(f"SETTINGS_AUDIT_DENIED: {text}")

    def audit(event, args):
        if event in ("open", "os.listdir", "os.scandir") and args:
            guard(args[0])

    original_resolve = Path.resolve
    original_readlink = os.readlink

    def guarded_resolve(path, *args, **kwargs):
        guard(path)
        return original_resolve(path, *args, **kwargs)

    def guarded_readlink(path, *args, **kwargs):
        guard(path)
        return original_readlink(path, *args, **kwargs)

    sys.addaudithook(audit)
    Path.resolve = guarded_resolve
    os.readlink = guarded_readlink


def prove_settings_guard():
    forbidden = Path("/home/osso/.config/noctalia/settings.json")
    for operation in (
        forbidden.read_bytes,
        forbidden.resolve,
        lambda: os.readlink(forbidden),
    ):
        try:
            operation()
        except PermissionError as error:
            assert "SETTINGS_AUDIT_DENIED" in str(error)
        else:
            raise AssertionError("settings audit guard failed")
    print("SETTINGS_AUDIT_GUARD: read/resolve/readlink denied before I/O")


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
        "module qs.Widgets\n" + "".join(f"{name} 1.0 {name}.qml\n" for name in WIDGETS)
    )
    for name in WIDGETS:
        source = (ROOT / f"Widgets/{name}.qml").read_text()
        if mutation == "palette":
            source = source.replace("root.handlePressedColor", "root.handleColor")
        if mutation == "selection":
            source = source.replace(
                "function incrementCurrentIndex() {",
                "function incrementCurrentIndex() { return;",
            )
        (widgets / f"{name}.qml").write_text(source)
    shutil.copyfile(
        ROOT / "Tests/Qml/GridListWarningsHarness.qml", directory / "tst_grid_list.qml"
    )


def isolated_environment(directory):
    environment = {"PATH": "/usr/bin", "LANG": "C.UTF-8"}
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


def run_audited(directory, environment, command, label):
    trace = directory / f"{label}.trace"
    sandbox = [
        "bwrap",
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib",
        "/lib64",
        "--ro-bind",
        "/etc/fonts",
        "/etc/fonts",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(directory),
        str(directory),
        "--chdir",
        str(directory),
        "--",
    ]
    result = subprocess.run(
        [
            "strace",
            "-f",
            "-qq",
            "-e",
            "trace=%file",
            "-o",
            str(trace),
            *sandbox,
            *command,
        ],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    accesses = trace.read_text()
    assert "settings.json" not in accesses, (
        "SETTINGS_AUDIT_DENIED: child settings access attempted"
    )
    print(
        f"CHILD_SETTINGS_AUDIT: {label} zero settings attempts; host home/config not mounted"
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime", "guard"))
    parser.add_argument("--mutation", choices=("palette", "selection"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-grid-list-") as temporary:
        directory = Path(temporary)
        install_settings_guard(directory)
        prove_settings_guard()
        environment = isolated_environment(directory)
        if args.mode == "guard":
            try:
                run_audited(
                    directory,
                    environment,
                    [
                        "/usr/bin/python3",
                        "-c",
                        "open('/home/osso/.config/noctalia/settings.json')",
                    ],
                    "guard-probe",
                )
            except AssertionError as error:
                assert "SETTINGS_AUDIT_DENIED" in str(error)
                print(
                    "CHILD_SETTINGS_AUDIT_GUARD: forbidden attempt detected in empty sandbox"
                )
            else:
                raise AssertionError("child settings audit guard failed")
            return
        stage(directory, args.mutation)
        if args.mode == "lint":
            counts_by_widget = {}
            exits = []
            for name in WIDGETS:
                code, output = run_audited(
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
                exits.append(code)
                counts_by_widget[name] = dict(counts)
                print(name, "LINT_COUNTS", dict(counts), "EXIT", code)
            assert not any(counts_by_widget.values()), counts_by_widget
            assert not any(exits), exits
        else:
            code, output = run_audited(
                directory,
                environment,
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory / "tst_grid_list.qml"),
                    "-import",
                    str(directory),
                ],
                "runtime",
            )
            assert code == 0, f"runtime exit {code}"
            assert "0 failed" in output, output
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
            ), output


if __name__ == "__main__":
    main()
