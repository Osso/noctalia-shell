#!/usr/bin/env python3
"""Two production widgets, offscreen; config denied to parent and Qt child.

Software QtTest proves property/lifecycle behavior, not rendered shader pixels.
Synthetic service and shellDir fixtures replace desktop/bootstrap boundaries.
"""

import argparse
from collections import Counter
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("NDropShadow", "NImageRounded")
PROTECTED = ("/home/osso/.config", "/syncthing/Sync/Provisioning/config")


def deny_config(event, args):
    if event not in ("open", "os.listdir", "os.scandir"):
        return
    if not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    path = os.path.abspath(os.fsdecode(args[0]))
    if any(path == prefix or path.startswith(prefix + "/") for prefix in PROTECTED):
        raise PermissionError(f"real config access denied: {path}")


sys.addaudithook(deny_config)


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_command(command, directory, environment):
    result = subprocess.run(
        command,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def stage_runtime(directory):
    helper = load_helper("workspace-runtime")
    write = helper.write_module
    singleton = helper.singleton
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property var data: ({general: {enableShadows: true, shadowOffsetX: 2, shadowOffsetY: 3}})"
            ),
            "Style": singleton(
                "property real shadowOpacity: 0.4\nproperty real shadowBlur: 0.6\nproperty int shadowBlurMax: 32\nproperty real fontSizeXXL: 20"
            ),
            "NColor": singleton(
                'property color black: "black"\nproperty color transparent: "transparent"'
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
    write(
        directory,
        "Quickshell",
        {
            "Quickshell": singleton(f'property string shellDir: "{ROOT}"'),
        },
    )
    write(
        directory,
        "Quickshell.Widgets",
        {"FixtureMarker": "import QtQuick\nQtObject {}"},
    )
    write(
        directory,
        "qs.Widgets",
        {
            **{name: (ROOT / f"Widgets/{name}.qml").read_text() for name in NAMES},
            "NIcon": "import QtQuick\nItem { property string icon; property real pointSize }",
        },
    )
    for name, color in (("red", "red"), ("blue", "blue")):
        (directory / f"{name}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="16"><rect width="24" height="16" fill="{color}"/></svg>'
        )
    (directory / "tst_image_shadow.qml").write_text(
        (ROOT / "Tests/Qml/ImageShadowWarningsHarness.qml").read_text()
    )


def run_sandboxed(args):
    directory = args.sandbox
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for parent in ("/home/osso", PROTECTED[1]):
        assert any(line.split()[4] == parent and " - tmpfs " in line for line in mounts)
    for prefix in PROTECTED:
        try:
            Path(prefix + "/noctalia/settings.json").read_bytes()
        except PermissionError:
            print("AUDIT_CONFIG_DENIED", prefix)
        else:
            raise AssertionError("audit failed to deny real config")
    environment = {
        "PATH": "/usr/bin",
        "LANG": "C.UTF-8",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent/session",
        "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/nonexistent/system",
    }
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    child_probe = """
import errno
from pathlib import Path
for prefix in ("/home/osso/.config", "/syncthing/Sync/Provisioning/config"):
    try:
        Path(prefix + "/noctalia/settings.json").read_bytes()
    except OSError as error:
        assert error.errno == errno.EACCES, error
        print("CHILD_CONFIG_DENIED", prefix, "EACCES")
    else:
        raise AssertionError("Qt child namespace exposes real config")
"""
    code, _ = run_command(
        ["/usr/bin/python3", "-c", child_probe], directory, environment
    )
    assert code == 0, "config mask probe failed"
    if args.mode == "lint":
        load_helper("media-mini-warnings").stage_modules(directory)
        for name in NAMES:
            code, output = run_command(
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    str(directory),
                    str(directory / f"qs/Widgets/{name}.qml"),
                ],
                directory,
                environment,
            )
            warnings = [
                line for line in output.splitlines() if line.startswith("Warning:")
            ]
            counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
            print("IMAGE_SHADOW_LINT", name, dict(counts))
            assert code == 0, code
            expected_count = (
                args.shadow_count if name == "NDropShadow" else args.image_count
            )
            assert counts == (
                {"unqualified": expected_count} if expected_count else {}
            ), dict(counts)
        return
    stage_runtime(directory)
    if args.mutation:
        name, original, replacement = {
            "shadow": ("NDropShadow", "source: root.source", "source: null"),
            "image": (
                "NImageRounded",
                "Math.max(0, root.radius - root.borderWidth)",
                "0",
            ),
        }[args.mutation]
        target = directory / f"qs/Widgets/{name}.qml"
        source = target.read_text()
        assert source.count(original) == 1
        target.write_text(source.replace(original, replacement))
    code, output = run_command(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        directory,
        environment,
    )
    assert code == 0, f"runtime exit {code}"
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--shadow-count", type=int, default=0)
    parser.add_argument("--image-count", type=int, default=0)
    parser.add_argument("--mutation", choices=("shadow", "image"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sandbox:
        run_sandboxed(args)
        return
    with tempfile.TemporaryDirectory(prefix="noctalia-image-shadow-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        command = [
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
            "/home/osso",
            "--perms",
            "000",
            "--tmpfs",
            PROTECTED[1],
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
            str(Path(__file__).resolve()),
            args.mode,
            "--sandbox",
            temporary,
            "--shadow-count",
            str(args.shadow_count),
            "--image-count",
            str(args.image_count),
        ]
        if args.mutation:
            command.extend(("--mutation", args.mutation))
        environment = {"PATH": "/usr/bin", "HOME": temporary, "LANG": "C.UTF-8"}
        code, _ = run_command(command, directory, environment)
        raise SystemExit(code)


if __name__ == "__main__":
    main()
