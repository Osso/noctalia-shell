#!/usr/bin/env python3
"""Bounded production visualizer/profile proof with denied host IO.

QtTest uses real visual children; services and uptime process are inert boundaries.
Harness lint uses the exact runtime doubles. No desktop, live audio or host settings.
"""

import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Modules/Bar/Widgets/AudioVisualizer.qml"),
    Path("Modules/Cards/ProfileCard.qml"),
)
CONFIG = "/syncthing/Sync/Provisioning/config"


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(argv, directory, environment):
    result = subprocess.run(
        argv, cwd=directory, env=environment, capture_output=True, text=True, timeout=60
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def audit(event, args):
    if event in ("open", "os.listdir", "os.scandir") and isinstance(
        args[0], (str, bytes, os.PathLike)
    ):
        path = os.path.abspath(os.fsdecode(args[0]))
        if (
            path.startswith("/home/osso/")
            or path.startswith(CONFIG + "/")
            or path.endswith("/settings.json")
        ):
            raise PermissionError(f"host/settings access denied: {path}")
    if event.startswith("socket."):
        raise PermissionError(f"network denied: {event}")


def stage(directory):
    status = helper("bar-status-warnings")
    status.stage_behavior(directory)
    (directory / "tst_bar_status.qml").unlink()
    controls = helper("bar-controls-warnings")
    writer = helper("workspace-runtime")
    singleton = writer.singleton

    def add(uri, sources):
        controls.add_module(writer, directory, uri, sources)

    add("qs.Modules.Cards", {"ProfileCard": (ROOT / TARGETS[1]).read_text()})
    add(
        "qs.Widgets",
        {
            name: (ROOT / f"Widgets/{name}.qml").read_text()
            for name in ("NBox", "NImageRounded")
        },
    )
    add(
        "qs.Commons",
        {
            "Time": singleton(
                'function formatVagueHumanReadableDuration(seconds) { return seconds + " seconds"; }'
            ),
            "I18n": singleton(
                'function tr(key, values) { return values ? "Uptime: " + values.uptime : key; }'
            ),
        },
    )
    settings = directory / "qs/Commons/Settings.qml"
    settings.write_text(
        settings.read_text().replace(
            "QtObject {", "QtObject {\nfunction preprocessPath(path) { return path; }"
        )
    )
    style = directory / "qs/Commons/Style.qml"
    style.write_text(
        style.read_text().replace(
            "QtObject {",
            "QtObject {\nproperty real fontSizeS: 10\nproperty real fontSizeXXL: 20",
        )
    )
    add(
        "qs.Services.System",
        {"HostService": singleton('property string displayName: "Fixture User"')},
    )
    add(
        "qs.Modules.Panels.Settings",
        {"SettingsPanel": "import QtQuick\nQtObject { enum Tab { General, Display } }"},
    )
    add(
        "Quickshell.Io",
        {
            "Process": """import QtQuick
QtObject {
  property var command: []
  property bool running: false
  property QtObject stdout
}""",
            "StdioCollector": """import QtQuick
QtObject {
  property string text: "900.5 100"
  signal streamFinished()
}""",
        },
    )
    add(
        "qs.Services.UI",
        {
            "PanelService": singleton("""property var events: []
property var lastScreen: null
property var lastMenu: null
property var panel: ({requestedTab: -1, open: function() { PanelService.events = PanelService.events.concat(["open"]); }, close: function() { PanelService.events = PanelService.events.concat(["close"]); }})
property var popup: ({close: function() { PanelService.events = PanelService.events.concat(["close"]); }, showContextMenu: function(menu) { PanelService.lastMenu = menu; }})
function getPanel(name, screen) { lastScreen = screen; events = events.concat([name]); return panel; }
function getPopupMenuWindow(screen) { lastScreen = screen; return popup; }""")
        },
    )
    (directory / "tst_visualizer_profile.qml").write_text(
        (ROOT / "Tests/Qml/VisualizerProfileHarness.qml").read_text()
    )


def lint_harness(directory, environment, inject_warning=False):
    stage(directory)
    harness = directory / "tst_visualizer_profile.qml"
    if inject_warning:
        source = harness.read_text()
        marker = "id: scene"
        assert source.count(marker) == 1, "injection owner must be unique"
        harness.write_text(
            source.replace(
                marker,
                marker + "\n    property int injectedWarning: scene.missingLintProbe",
                1,
            )
        )
    code, output = command(
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
        directory,
        environment,
    )
    diagnostics = json.loads(output)
    warnings = sum(
        warning["type"] == "warning"
        for result in diagnostics["files"]
        for warning in result["warnings"]
    )
    print("VISUALIZER_PROFILE_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
    return code


def lint_harness_regression(directory):
    for name, injected in (("clean", False), ("injected", True)):
        staged = directory / name
        staged.mkdir(mode=0o700)
        environment = helper("media-mini-warnings").isolate_environment(staged)
        code = lint_harness(staged, environment, injected)
        if injected:
            assert code != 0, "genuine harness warning accepted"
        else:
            assert code == 0, "clean harness lint failed"
    print("VISUALIZER_PROFILE_HARNESS_WARNING_REJECTED")


def inside(args):
    directory = args.sandbox
    for mask in ("/home/osso", CONFIG):
        assert any(
            line.split()[4] == mask and " - tmpfs " in line
            for line in Path("/proc/self/mountinfo").read_text().splitlines()
        )
    sys.addaudithook(audit)
    for path in (
        "/home/osso/.config/noctalia/settings.json",
        CONFIG + "/noctalia/settings.json",
    ):
        try:
            Path(path).read_bytes()
        except PermissionError:
            print("AUDIT_DENIED", path)
        else:
            raise AssertionError("settings readable")
    environment = helper("media-mini-warnings").isolate_environment(directory)
    if args.mode == "lint-harness":
        raise SystemExit(lint_harness(directory, environment))
    if args.mode == "lint-harness-regression":
        lint_harness_regression(directory)
        return
    if args.mode in ("lint", "baseline"):
        helper("media-mini-warnings").stage_modules(directory)
        for target in TARGETS:
            code, output = command(
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "--bare",
                    "-I",
                    str(directory),
                    "-I",
                    "/usr/lib/qt6/qml",
                    "--json",
                    "-",
                    str(directory / "qs" / target),
                ],
                directory,
                environment,
            )
            warnings = json.loads(output)["files"][0]["warnings"]
            counts = Counter(w["id"] for w in warnings if w["type"] == "warning")
            print(target, "COUNTS", dict(counts), "EXIT", code)
            if args.mode == "lint":
                expected = {} if target == TARGETS[0] else {"unqualified": 4}
                assert counts == expected, counts
                assert code == 0, code
        return
    stage(directory)
    if args.mutation:
        target = directory / "qs" / TARGETS[0]
        target.write_text(target.read_text().replace("root.isVerticalBar", "false"))
    code, output = command(
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
    assert code == 0 and "0 failed" in output, output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "runtime",
            "lint",
            "baseline",
            "lint-harness",
            "lint-harness-regression",
        ),
    )
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--mutation", action="store_true")
    parser.add_argument("--sandbox", type=Path)
    args = parser.parse_args()
    if args.sandbox:
        inside(args)
        return
    sys.addaudithook(audit)
    with tempfile.TemporaryDirectory(prefix="noctalia-vp-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        argv = [
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
            CONFIG,
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
        ]
        if args.mutation:
            argv.append("--mutation")
        code, _ = command(
            argv, directory, {"PATH": "/usr/bin", "HOME": temporary, "LANG": "C.UTF-8"}
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
