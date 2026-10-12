#!/usr/bin/env python3
"""Two-file lint and offscreen production behavior; real config masked by bwrap.

Real NIconButton/NIcon/NText and both targets. Services, popup surface and
shadow rendering are inert boundaries; no notification server or compositor.
"""

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("Modules/Bar/Widgets/NotificationHistory.qml"),
    Path("Modules/Toast/SimpleToast.qml"),
)


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"Tests/{name}.test.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sandbox(argv, environment):
    return subprocess.run(
        [
            "bwrap",
            "--ro-bind",
            "/",
            "/",
            "--tmpfs",
            "/home/osso/.config",
            "--tmpfs",
            "/run",
            "--unshare-net",
            "--die-with-parent",
            "--",
            *argv,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


def lint(directory, maximum):
    media = helper("media-mini-warnings")
    media.stage_modules(directory)
    environment = media.isolate_environment(directory)
    failures = []
    for target in TARGETS:
        result = sandbox(
            [
                "/usr/lib/qt6/bin/qmllint",
                "-I",
                str(directory),
                str(directory / "qs" / target),
            ],
            environment,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        counts = Counter(
            re.findall(r"\[([^]]+)\]", line)[-1]
            for line in output.splitlines()
            if line.startswith("Warning:")
        )
        print(target, "WARNING_COUNTS", dict(counts), "EXIT", result.returncode)
        if sum(counts.values()) > maximum or result.returncode != 0:
            failures.append(str(target))
    assert not failures, failures


def stage(directory):
    workspace = helper("workspace-runtime")
    write = workspace.write_module
    singleton = workspace.singleton
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    style = dict(
        uiScaleRatio=1,
        capsuleHeight=40,
        baseWidgetSize=40,
        marginM=8,
        marginL=12,
        marginXXS=2,
        radiusL=12,
        radiusXS=2,
        borderS=1,
        borderM=2,
        animationNormal=20,
        animationFast=30,
        fontSizeXXL=20,
        fontSizeL=14,
        fontSizeM=12,
        fontWeightBold=700,
        fontWeightMedium=500,
        opacityFull=1,
        opacityMedium=0.5,
    )
    colors = dict(
        mSurface="#202020",
        mSurfaceVariant="#303030",
        mPrimary="#00ff00",
        mError="#ff0000",
        mOutline="#808080",
        mOnSurface="#ffffff",
        mHover="#404040",
        mOnHover="#eeeeee",
        transparent="transparent",
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
                + '\nproperty color capsuleColor: "#202020"'
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Icons": singleton(
                'property string defaultIcon: "bell"\nproperty string fontFamily: "sans-serif"\nfunction get(name) { return name; }'
            ),
            "Logger": singleton(
                "function w(...args) { console.warn(...args); }\nfunction callStack() { console.trace(); }"
            ),
        },
    )
    write(
        directory,
        "Quickshell",
        {"ShellScreen": "import QtQuick\nQtObject { property string name }"},
    )
    for uri in ("Quickshell.Wayland", "Quickshell.Widgets", "qs.Modules.Bar.Extras"):
        write(directory, uri, {"InertBoundary": "import QtQuick\nQtObject {}"})
    write(
        directory,
        "qs.Services.System",
        {
            "NotificationService": singleton("""property bool doNotDisturb: false
property real lastSeenTs: 100
property ListModel historyList: ListModel {}
property int clearCount: 0
function clearHistory() { clearCount++; historyList.clear(); }""")
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "BarWidgetRegistry": singleton(
                'property var widgetMetadata: ({"NotificationHistory": {showUnreadBadge: true, hideWhenZero: true}})'
            ),
            "PanelService": singleton("""property int closeCount: 0
property var popup: ({close: function() { PanelService.closeCount++; }})
function getPopupMenuWindow(screen) { return popup; }
function getPanel(name, screen) { return null; }"""),
            "BarService": singleton(
                'function getTooltipDirection() { return "bottom"; }\nfunction openWidgetSettings(...args) {}\nfunction getContextMenuPosition(...args) { return {x: 0, y: 0}; }'
            ),
            "TooltipService": singleton(
                "function show(...args) {}\nfunction hide() {}"
            ),
        },
    )
    widgets = {
        name: (ROOT / f"Widgets/{name}.qml").read_text()
        for name in ("NIconButton", "NIcon", "NText")
    }
    widgets.update(
        {
            "NDropShadow": "import QtQuick\nItem { property Item source; property bool autoPaddingEnabled }",
            "NPopupContextMenu": "import QtQuick\nItem { property var model; signal triggered(string action); function openAtItem(...args) {} }",
        }
    )
    write(directory, "qs.Widgets", widgets)
    for target in TARGETS:
        write(
            directory,
            "qs." + str(target.parent).replace("/", "."),
            {target.stem: (ROOT / target).read_text()},
        )
    (directory / "tst_history_toast.qml").write_text(
        (ROOT / "Tests/Qml/HistorySimpleToastHarness.qml").read_text()
    )


def lint_harness(directory, inject_warning=False):
    stage(directory)
    environment = helper("media-mini-warnings").isolate_environment(directory)
    harness = directory / "tst_history_toast.qml"
    if inject_warning:
        harness.write_text(
            harness.read_text().replace(
                "Item {", 'Item {\n  property int fixtureLintWarning: "injected"', 1
            )
        )
    result = sandbox(
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
        environment,
    )
    print(result.stdout)
    print(result.stderr, end="")
    diagnostics = json.loads(result.stdout)
    counts = Counter(
        warning["id"] for file in diagnostics["files"] for warning in file["warnings"]
    )
    print("HISTORY_TOAST_HARNESS_LINT_COUNTS", dict(counts), "EXIT", result.returncode)
    assert not counts, f"harness diagnostics remain: {dict(counts)}"
    assert result.returncode == 0, result.returncode


def behavior(directory):
    stage(directory)
    environment = helper("media-mini-warnings").isolate_environment(directory)
    denial = sandbox(
        [
            "python3",
            "-c",
            "from pathlib import Path; assert not Path('/home/osso/.config/noctalia/settings.json').exists(); print('REAL_CONFIG_MASKED')",
        ],
        environment,
    )
    print(denial.stdout + denial.stderr, end="")
    assert denial.returncode == 0, "real config mask failed"
    result = sandbox(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory),
            "-import",
            str(directory),
        ],
        environment,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, result.returncode
    assert "0 failed" in output
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop", output
    ), output
    print(
        "LIMIT: offscreen item clicks/geometry only; no compositor/input-region/cursor proof"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "lint-harness", "behavior"))
    parser.add_argument("--max-warnings", type=int, default=0)
    parser.add_argument("--inject-warning", action="store_true")
    args = parser.parse_args()
    if args.inject_warning and args.mode != "lint-harness":
        parser.error("--inject-warning requires lint-harness")
    with tempfile.TemporaryDirectory(prefix="noctalia-history-toast-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            lint(directory, args.max_warnings)
        elif args.mode == "lint-harness":
            lint_harness(directory, args.inject_warning)
        else:
            behavior(directory)


if __name__ == "__main__":
    main()
