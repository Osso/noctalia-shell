#!/usr/bin/env python3
"""Mango-only real-metadata lint and masked offscreen fake-backend behavior.

No real settings are read; no Quickshell or compositor process is launched.
Production parsers, timers, workspace model and window mapping remain real.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Services/Compositor/MangoService.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deny_host_access(directory):
    def audit(event, args):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise PermissionError("network denied")
        if event not in ("open", "os.listdir", "os.scandir"):
            return
        if not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        path = Path(os.path.abspath(os.fsdecode(args[0])))
        if path.is_relative_to(directory):
            return
        if path.is_relative_to(ROOT) and path.suffix in (".qml", ".js", ".py", ".pyc"):
            return
        if path.is_relative_to("/home") or path.is_relative_to("/syncthing"):
            raise PermissionError(f"host resource denied: {path}")

    sys.addaudithook(audit)


def run_isolated(directory, command):
    environment = {
        "PATH": "/usr/bin",
        "HOME": "/home/fixture",
        "XDG_CONFIG_HOME": "/home/fixture/config",
        "XDG_CACHE_HOME": "/tmp/cache",
        "XDG_DATA_HOME": "/tmp/data",
        "XDG_STATE_HOME": "/tmp/state",
        "XDG_RUNTIME_DIR": "/tmp/runtime",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "FONTCONFIG_FILE": "/fixture/fonts.conf",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent",
    }
    return subprocess.run(
        [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/home",
            "--tmpfs",
            "/syncthing",
            "--tmpfs",
            "/run",
            "--dir",
            "/home/fixture",
            "--dir",
            "/home/fixture/config",
            "--dir",
            "/tmp/runtime",
            "--chmod",
            "0700",
            "/tmp/runtime",
            "--ro-bind",
            str(directory),
            "/fixture",
            "--chdir",
            "/fixture",
            *command,
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )


def lint(directory):
    # Actual source imports + installed Qt/Quickshell metadata, never runtime stubs.
    helper("media-mini-warnings").stage_modules(directory)
    result = run_isolated(
        directory,
        [
            "/usr/lib/qt6/bin/qmllint",
            "--bare",
            "-I",
            "/fixture",
            "-I",
            "/usr/lib/qt6/qml",
            "--max-warnings",
            "0",
            "--json",
            "-",
            "/fixture/qs/" + str(TARGET),
        ],
    )
    (directory / "lint.json").write_text(result.stdout)
    print(result.stdout, end="")
    print(result.stderr, end="")
    report = json.loads(result.stdout)
    diagnostics = [
        warning for entry in report["files"] for warning in entry["warnings"]
    ]
    assert result.returncode == 0 and not diagnostics, (result.returncode, diagnostics)
    print("MANGO_LINT_ZERO_DIAGNOSTICS")


def stage_runtime(directory, mutation):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton("""property var commands: []
function execDetached(argv) { commands = commands.concat([argv]); }"""),
        },
    )
    write(
        directory,
        "Quickshell.Io",
        {
            "FixtureIo": singleton("property var processes: []"),
            "Process": """import QtQuick
Item {
  id: process
  property bool running: false
  property var command: []
  property QtObject stdout
  signal exited(int exitCode)
  Component.onCompleted: FixtureIo.processes = FixtureIo.processes.concat([process])
}""",
            "SplitParser": "import QtQuick\nQtObject { signal read(string line) }",
        },
    )
    write(
        directory,
        "Quickshell.Wayland",
        {
            "ToplevelManager": singleton("""component ToplevelList: QtObject {
  property var values: []
}
property ToplevelList toplevels: ToplevelList {}"""),
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Logger": singleton("""function i(...args) {}
function e(...args) { console.error(...args); }"""),
        },
    )
    write(
        directory,
        "qs.Services.Keyboard",
        {
            "KeyboardLayoutService": singleton("""property string currentLayout: ""
function setCurrentLayout(value) { currentLayout = value; }"""),
        },
    )
    source = (ROOT / TARGET).read_text()
    if mutation:
        old = "\\s+tags\\s+" if mutation == "tags" else "\\s+scale_factor\\s+"
        assert source.count(old) == 1
        source = source.replace(old, "\\s+INVALID_FIXTURE\\s+")
    write(
        directory,
        "qs.Services.Compositor",
        {
            "MangoService": source,
            "CompositorService": singleton("""property var displayScales: ({})
property int scaleUpdates: 0
function onDisplayScalesUpdated(value) { displayScales = value; scaleUpdates++; }"""),
        },
    )
    shutil.copyfile(
        ROOT / "Tests/Qml/MangoServiceHarness.qml", directory / "tst_mango.qml"
    )
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/fonts</cachedir></fontconfig>"
    )


def assert_isolation(directory):
    probe = """import os
from pathlib import Path
for path in ('/home/osso/.config', '/syncthing/Sync', '/run/user'):
    assert not Path(path).exists(), path
assert os.environ['XDG_CONFIG_HOME'] == '/home/fixture/config'
assert not any(key in os.environ for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'NIRI_SOCKET', 'SWAYSOCK', 'HYPRLAND_INSTANCE_SIGNATURE'))
print('MANGO_HOST_CONFIG_AND_DESKTOP_MASKED')
"""
    result = run_isolated(directory, ["/usr/bin/python3", "-c", probe])
    print(result.stdout, end="")
    print(result.stderr, end="")
    assert result.returncode == 0, result.returncode


def runtime(directory, mutation):
    stage_runtime(directory, mutation)
    assert_isolation(directory)
    result = run_isolated(
        directory,
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            "/fixture/tst_mango.qml",
            "-import",
            "/fixture",
        ],
    )
    output = result.stdout + result.stderr
    (directory / "runtime.log").write_text(output)
    print(output, end="")
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:", output
    ), output
    if mutation:
        case = "stream_window_tags" if mutation == "tags" else "scales"
        assert result.returncode != 0 and re.search(
            r"FAIL!\s+:.*::test_" + case + r"\(\)", output
        ), (result.returncode, output)
        print("MANGO_MUTATION_REJECTED", mutation)
    else:
        assert result.returncode == 0 and "4 passed, 0 failed" in output, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "runtime"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--mutation", choices=("tags", "scale"))
    args = parser.parse_args()
    assert args.mutation is None or args.mode == "runtime"
    directory = args.artifacts.resolve()
    directory.mkdir(mode=0o700)
    deny_host_access(directory)
    if args.mode == "lint":
        lint(directory)
    elif args.mode == "lint-harness":
        stage_runtime(directory, None)
        result = run_isolated(
            directory,
            [
                "/usr/lib/qt6/bin/qmllint",
                "--bare",
                "-I",
                "/fixture",
                "-I",
                "/usr/lib/qt6/qml",
                "--max-warnings",
                "0",
                "--json",
                "-",
                "/fixture/tst_mango.qml",
            ],
        )
        (directory / "harness-lint.json").write_text(result.stdout)
        print(result.stdout, end="")
        print(result.stderr, end="")
        assert result.returncode == 0, result.returncode
    else:
        runtime(directory, args.mutation)


if __name__ == "__main__":
    main()
