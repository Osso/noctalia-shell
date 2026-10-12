#!/usr/bin/env python3
"""Overview-only proof in a private offscreen sandbox.

Production Loader, bindings, callbacks and overlay geometry run. Variants uses
Qt Instantiator; layer-shell and image decoding are inert boundaries. No wallpaper
resources, compositor routing, blur pixels or memory claims. Parent/child deny
host config. RED at 35cc9734c9: recreation logs undefined timerDisableFx; target
lint has five warnings. Coverage: two screen sizes/resize, monitor routing, all
three enable gates, Loader and screen-list recreation. Staged negative controls
break cover anchors, overview enable gating, and image fill geometry.
"""

import argparse
import errno
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Background/Overview.qml")


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Tests" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_runtime(directory, mutation):
    writer = helper("wallpaper-panel-warnings.test.py")
    write, singleton = writer.write_module, writer.singleton
    write(
        directory,
        "Quickshell",
        {
            "ShellScreen": "import QtQuick\nQtObject { property string name; property int width; property int height }",
            "Quickshell": singleton(
                'property list<ShellScreen> screens: [ShellScreen { name: "wide"; width: 800; height: 450 }, ShellScreen { name: "tall"; width: 450; height: 800 }]'
            ),
            "Variants": """import QtQuick
QtObject {
  id: variants
  property var model
  property Component delegate
  property Instantiator instances: Instantiator {
    model: variants.model
    delegate: variants.delegate
  }
}""",
            "PanelWindow": """import QtQuick
Window {
  visible: false
  contentItem.width: width
  contentItem.height: height
  property ShellScreen screen
  property FixtureAnchors anchors: FixtureAnchors {}
  property int layer
  property int exclusionMode
  property string namespace
  width: screen && anchors.left && anchors.right ? screen.width : 0
  height: screen && anchors.top && anchors.bottom ? screen.height : 0
}""",
            "FixtureAnchors": "import QtQuick\nQtObject { property bool top; property bool bottom; property bool left; property bool right }",
        },
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("""component WallpaperSettings: QtObject {
  property bool enabled: true
  property bool overviewEnabled: true
}
component ColorSchemeSettings: QtObject {
  property bool darkMode: true
}
component SettingsData: QtObject {
  property WallpaperSettings wallpaper: WallpaperSettings {}
  property ColorSchemeSettings colorSchemes: ColorSchemeSettings {}
}
property SettingsData data: SettingsData {}"""),
            "Logger": singleton("function d(...args) {}"),
            "NColor": singleton(
                'property color transparent: "transparent"\nproperty color mSurface: "#202020"\nproperty color mOnSurface: "#eeeeee"'
            ),
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {"CompositorService": singleton("property bool isNiri: true")},
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "WallpaperService": singleton("""property bool isInitialized: true
signal wallpaperChanged(string screenName, string path)
function getWallpaper(name) { return "fixture-" + name; }""")
        },
    )
    write(
        directory,
        "qs.OverviewFixtures",
        {
            "PreviewImage": """import QtQuick
Item {
  property url source
  property int fillMode
  property bool smooth
  property bool mipmap
  property bool cache
  property bool asynchronous
  property size sourceSize
}"""
        },
    )
    source = (ROOT / TARGET).read_text()
    source = source.replace("import Quickshell.Wayland", "import qs.OverviewFixtures")
    source = (
        source.replace("WlrLayershell.", "")
        .replace("WlrLayer.Background", "0")
        .replace("ExclusionMode.Ignore", "0")
    )
    source = source.replace("Image {", "PreviewImage {")
    if mutation == "cover":
        source = source.replace("right: true", "right: false")
    elif mutation == "visibility":
        source = source.replace("Settings.data.wallpaper.overviewEnabled", "true")
    elif mutation == "geometry":
        source = source.replace("anchors.fill: parent", "width: 1; height: 1", 1)
    write(directory, "qs.Modules.Background", {"Overview": source})
    (directory / "tst_overview.qml").write_text(
        (ROOT / "Tests/Qml/OverviewWarningsHarness.qml").read_text()
    )


def execute(argv, directory, environment):
    result = subprocess.run(
        argv,
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    return result.returncode, output


def lint_harness(directory, environment, inject_warning):
    harness = directory / "tst_overview.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "id: test",
                "id: test\n  property int injectedWarning: test.missingLintProbe",
                1,
            )
        )
    code, output = execute(
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
    print("OVERVIEW_HARNESS_LINT_WARNINGS", warnings, "EXIT", code)
    if inject_warning:
        assert warnings > 0, "injected warning not diagnosed"
        assert code != 0, "injected warning accepted"
    else:
        assert code != 0 or warnings == 0, "warnings accepted by strict lint"
    return code


def inside(args):
    directory = args.sandbox
    mounts = Path("/proc/self/mountinfo").read_text()
    for parent in ("/home/osso", args.config_parent):
        assert any(
            line.split()[4] == parent and " - tmpfs " in line
            for line in mounts.splitlines()
        ), parent
        path = (
            parent
            + ("/.config" if parent == "/home/osso" else "")
            + "/noctalia/settings.json"
        )
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError as error:
            assert error.errno == errno.EACCES, (path, error)
        else:
            os.close(descriptor)
            raise AssertionError("host config accessible")
        print("CONFIG_ACCESS_DENIED", path)
    environment = {
        "PATH": "/usr/bin",
        "HOME": str(directory / "home"),
        "XDG_CONFIG_HOME": str(directory / "config"),
        "XDG_CACHE_HOME": str(directory / "cache"),
        "XDG_RUNTIME_DIR": str(directory / "run"),
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_BACKEND": "software",
        "LANG": "C.UTF-8",
    }
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
        Path(environment[key]).mkdir(mode=0o700)
    if args.mode == "lint":
        helper("media-mini-warnings.test.py").stage_modules(directory)
        code, output = execute(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / TARGET),
            ],
            directory,
            environment,
        )
        warnings = re.findall(r"^Warning:.*$", output, re.M)
        print("OVERVIEW_WARNINGS", len(warnings))
        assert len(warnings) == args.expected, warnings
        assert code == 0, code
    else:
        stage_runtime(directory, args.mutation)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory, environment, args.inject_warning))
        code, output = execute(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_overview.qml"),
                "-import",
                str(directory),
            ],
            directory,
            environment,
        )
        assert not re.search(
            r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
        ), output
        if args.mutation:
            failed_case = (
                "test_visibility_and_recreation"
                if args.mutation == "visibility"
                else "test_cover_screen_and_geometry"
            )
            assert code != 0 and re.search(
                r"FAIL!.*Overview::" + failed_case, output
            ), "negative control escaped"
            print("OVERVIEW_NEGATIVE_DETECTED", args.mutation)
        else:
            assert code == 0 and "0 failed" in output, output
            print("OVERVIEW_RUNTIME_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("lint", "runtime", "lint-harness"))
    parser.add_argument("--inject-warning", action="store_true")
    parser.add_argument("--max-warnings", type=int, choices=(0,), default=0)
    parser.add_argument("--expected", type=int, default=0)
    parser.add_argument("--mutation", choices=("cover", "visibility", "geometry"))
    parser.add_argument("--sandbox", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--config-parent", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    if args.sandbox:
        inside(args)
        return
    config_parent = str((Path.home() / ".config/noctalia").resolve().parent)
    with tempfile.TemporaryDirectory(prefix="noctalia-overview-") as temporary:
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
            "--tmpfs",
            "/syncthing",
            "--ro-bind",
            str(ROOT),
            str(ROOT),
            "--perms",
            "000",
            "--tmpfs",
            "/home/osso",
            "--perms",
            "000",
            "--tmpfs",
            config_parent,
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
            "--expected",
            str(args.expected),
            "--sandbox",
            temporary,
            "--config-parent",
            config_parent,
        ]
        if args.inject_warning:
            argv.append("--inject-warning")
        if args.mutation:
            argv.extend(["--mutation", args.mutation])
        code, _ = execute(
            argv,
            directory,
            {"PATH": "/usr/bin", "HOME": "/home/osso", "LANG": "C.UTF-8"},
        )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
