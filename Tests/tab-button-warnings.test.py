#!/usr/bin/env python3
"""Bounded real tab-button lint/runtime under audited, masked private config."""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
NAMES = ("NIconTabButton", "NTabButton", "NTabBar")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ISOLATION = helper("audio-notification-settings-warnings.test.py")


def stage(directory):
    fixtures = helper("clock-settings-warnings.test.py")
    write, singleton = fixtures.write_module, fixtures.singleton
    write(
        directory,
        "qs.Widgets",
        {
            name: (ROOT / "Widgets" / f"{name}.qml").read_text()
            for name in (*NAMES, "NText", "NIcon")
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Style": singleton("""
property int marginS: 8
property int marginXS: 4
property int baseWidgetSize: 32
property int radiusXS: 4
property int radiusS: 8
property int animationFast: 0
property int fontSizeM: 12
property int fontSizeL: 14
property int fontWeightSemiBold: 600
property int fontWeightRegular: 400
property int fontWeightMedium: 500
property real uiScaleRatio: 1
"""),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "{color}"'
                    for name, color in {
                        "mPrimary": "#ff0000",
                        "mHover": "#00ff00",
                        "mSurface": "#111111",
                        "mSurfaceVariant": "#222222",
                        "mOnPrimary": "#ffffff",
                        "mOnHover": "#000000",
                        "mOnSurface": "#dddddd",
                    }.items()
                )
            ),
            "Settings": singleton("""
component Ui: QtObject {
  property string fontDefault: "DejaVu Sans"
  property real fontDefaultScale: 1
  property real fontFixedScale: 1
}
component Data: QtObject { property Ui ui: Ui {} }
property Data data: Data {}
"""),
            "Icons": singleton(
                'property string fontFamily: "DejaVu Sans"\nproperty string defaultIcon: "star"\nfunction get(key) { return "*"; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                "function show(item, text) {}\nfunction hide() {}"
            )
        },
    )
    write(directory, "Quickshell", {"Fixture": "import QtQuick\nQtObject {}"})
    harness = directory / "tst_tabs.qml"
    shutil.copyfile(ROOT / "Tests/Qml/TabButtonWarningsHarness.qml", harness)
    return harness


def lint(directory, environment):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    code, output = ISOLATION.run_child(
        [
            "/usr/lib/qt6/bin/qmllint",
            "--max-warnings",
            "0",
            "--json",
            "-",
            "-I",
            str(directory),
            *(str(directory / "qs/Widgets" / f"{name}.qml") for name in NAMES),
        ],
        directory,
        environment,
    )
    (directory / "lint.json").write_text(output)
    for result in json.loads(output)["files"]:
        warnings = [
            entry
            for entry in result["warnings"]
            if entry["type"] in ("warning", "error")
        ]
        print(
            Path(result["filename"]).name,
            "WARNINGS",
            len(warnings),
            Counter(entry["id"] for entry in warnings),
            flush=True,
        )
    assert code == 0, output
    assert all(
        not [
            entry
            for entry in result["warnings"]
            if entry["type"] in ("warning", "error")
        ]
        for result in json.loads(output)["files"]
    ), output


def runtime(directory, environment):
    harness = stage(directory)
    code, output = ISOLATION.run_child(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(harness),
            "-import",
            str(directory),
        ],
        directory,
        environment,
    )
    (directory / "runtime.log").write_text(output)
    assert code == 0 and "6 passed, 0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output


def with_private_settings(directory, environment, action):
    defaults = (ROOT / "Assets/settings-default.json").read_bytes()
    settings = Path(environment["XDG_CONFIG_HOME"]) / "noctalia/settings.json"
    settings.parent.mkdir(mode=0o700)
    backup = directory / "settings.backup.json"
    for path in (settings, backup):
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(defaults)
    digest = hashlib.sha256(defaults).digest()
    assert hashlib.sha256(backup.read_bytes()).digest() == digest
    assert settings.stat().st_mode & 0o777 == backup.stat().st_mode & 0o777 == 0o600
    try:
        action(directory, environment)
    finally:
        assert settings.read_bytes() == defaults, "fixture settings changed"
        assert hashlib.sha256(backup.read_bytes()).digest() == digest, (
            "fixture backup changed"
        )


def reload(directory, environment):
    stage(directory)
    shutil.rmtree(directory / "Quickshell")
    for path in (directory / "qs").iterdir():
        shutil.move(str(path), directory / path.name)
    (directory / "qs").rmdir()
    for declaration in directory.rglob("qmldir"):
        declaration.unlink()
    shutil.copyfile(
        ROOT / "Tests/Qml/TabButtonReloadHarness.qml", directory / "shell.qml"
    )
    environment["QS_NO_RELOAD_POPUP"] = "1"
    output = []
    source = directory / "Widgets/NTabBar.qml"
    waiter = helper("tray-widget-reload.test.py").wait_for
    with (
        subprocess.Popen(
            ["quickshell", "--no-color", "-p", str(directory)],
            cwd=directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process,
        selectors.DefaultSelector() as selector,
    ):
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            waiter(process, selector, output, "TAB_PRIVATE_READY")
            print("TAB_PRIVATE_COLD_START_PASS", flush=True)
            source.write_text(
                source.read_text() + "\n// Private source reload probe.\n"
            )
            waiter(process, selector, output, "TAB_PRIVATE_READY")
            print("TAB_PRIVATE_SOURCE_RELOAD_PASS", flush=True)
        finally:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                tail, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                tail, _ = process.communicate(timeout=5)
            output.append(tail.decode())
            (directory / "reload.log").write_text("".join(output))
    assert process.poll() is not None
    assert not re.search(
        r" WARN | ERROR | FATAL |ReferenceError|TypeError|Binding loop|TAB_RELOAD_ASSERT",
        "".join(output),
    ), "".join(output)
    print("TAB_PRIVATE_PROCESS_EXITED", flush=True)


def run_sandboxed(mode, directory):
    mounts = Path("/proc/self/mountinfo").read_text()
    for path in ("/home", "/syncthing", "/run"):
        assert any(
            line.split()[4] == path and " - tmpfs " in line
            for line in mounts.splitlines()
        ), path
    environment = ISOLATION.isolated_environment(directory)
    if mode == "lint":
        lint(directory, environment)
    else:
        with_private_settings(
            directory, environment, {"runtime": runtime, "reload": reload}[mode]
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "runtime", "reload"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.addaudithook(ISOLATION.audit)
    with (
        patch("os.stat", ISOLATION.guard_metadata(os.stat)),
        patch("os.lstat", ISOLATION.guard_metadata(os.lstat)),
        patch("os.readlink", ISOLATION.guard_metadata(os.readlink)),
    ):
        ISOLATION.prove_denial()
        if args.sandbox:
            run_sandboxed(args.mode, args.sandbox)
            return
        with tempfile.TemporaryDirectory(prefix="noctalia-tabs-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            code, _ = ISOLATION.run_child(
                [
                    "bwrap",
                    "--die-with-parent",
                    "--unshare-all",
                    "--new-session",
                    "--ro-bind",
                    "/",
                    "/",
                    "--perms",
                    "000",
                    "--tmpfs",
                    "/home",
                    "--tmpfs",
                    "/syncthing",
                    "--ro-bind",
                    str(ROOT),
                    str(ROOT),
                    "--tmpfs",
                    "/tmp",
                    "--tmpfs",
                    "/run",
                    "--bind",
                    temporary,
                    temporary,
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "--chdir",
                    temporary,
                    "--",
                    "/usr/bin/python3",
                    str(Path(__file__).absolute()),
                    args.mode,
                    "--sandbox",
                    temporary,
                ],
                directory,
                {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": temporary},
            )
            raise SystemExit(code)


if __name__ == "__main__":
    main()
