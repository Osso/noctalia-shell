#!/usr/bin/env python3
"""Bounded popup and power-service proofs; all external boundaries are inert."""

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
    Path("Modules/Panels/Wallpaper/WallhavenSettingsPopup.qml"),
    Path("Services/Power/PowerProfileService.qml"),
)


def helper(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "Tests" / (name + ".test.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated(directory, argv):
    return helper("brightness-keyboard-services-warnings").run_isolated(
        directory, argv, 60
    )


def stage(directory, mutation):
    writer = helper("wallpaper-panel-warnings")
    write, singleton = writer.write_module, writer.singleton
    popup = (ROOT / TARGETS[0]).read_text()
    service = (ROOT / TARGETS[1]).read_text()
    if mutation == "selection":
        popup = popup.replace(
            "WallhavenService.sorting = key;", 'WallhavenService.sorting = "broken";'
        )
    if mutation == "resolution":
        popup = popup.replace(
            "WallhavenService.minResolution = resolution;",
            'WallhavenService.minResolution = "broken";',
        )
    if mutation == "power":
        service = service.replace(
            "setProfile(PowerProfile.Performance);",
            "setProfile(PowerProfile.Balanced);",
        )
    write(
        directory,
        "Quickshell",
        {
            "Singleton": "import QtQuick\nItem {}",
            "ShellScreen": "import QtQuick\nQtObject {}",
        },
    )
    write(
        directory,
        "Quickshell.Services.UPower",
        {
            "PowerProfile": "import QtQuick\nQtObject { enum Profile { PowerSaver = 0, Balanced = 1, Performance = 2 } }",
            "PowerProfiles": singleton(
                "property bool hasPerformanceProfile: true\nproperty int profile: 1"
            ),
        },
    )
    settings = dict(
        useWallhaven=True,
        wallhavenSorting="relevance",
        wallhavenOrder="desc",
        wallhavenPurity="100",
        wallhavenCategories="111",
        wallhavenResolutionWidth="1920",
        wallhavenResolutionHeight="1080",
        wallhavenResolutionMode="atleast",
        wallhavenQuery="forest",
    )
    fields = "\n".join(
        f"property {'bool' if isinstance(value, bool) else 'string'} {key}: {json.dumps(value)}"
        for key, value in settings.items()
    )
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property QtObject data: QtObject { property QtObject wallpaper: QtObject {\n"
                + fields
                + "\n} }"
            ),
            "Style": singleton(
                "\n".join(
                    f"property real {name}: {0 if name.startswith('animation') else 12}"
                    for name in sorted(set(re.findall(r"Style\.(\w+)", popup)))
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {name}: "#808080"'
                    for name in sorted(set(re.findall(r"NColor\.(\w+)", popup)))
                )
            ),
            "I18n": singleton(
                'function tr(key, values) { return values ? key + ":" + values.profile : key; }'
            ),
            "Logger": singleton(
                "property var errors: []\nfunction d(...args) {}\nfunction e(...args) { errors = errors.concat([args]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "WallhavenService": singleton(
                "property var searches: []\n"
                + "\n".join(
                    "property string " + name
                    for name in (
                        "sorting",
                        "order",
                        "purity",
                        "categories",
                        "minResolution",
                        "resolutions",
                    )
                )
                + "\nfunction search(query, page) { searches = searches.concat([{query: query, page: page}]); }"
            ),
            "ToastService": singleton(
                "property var notices: []\nfunction showNotice(title, body, icon) { notices = notices.concat([{title: title, body: body, icon: icon}]); }"
            ),
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NIconButton": "import QtQuick\nItem { property string icon; property string tooltipText; property real baseSize; signal clicked }",
            "NComboBox": "import QtQuick\nItem { property var model; property string currentKey; signal selected(string key); implicitHeight: 30 }",
            "NTextInput": "import QtQuick.Controls\nTextField { id: input; property alias inputItem: input }",
            "NDivider": "import QtQuick\nItem { implicitHeight: 1 }",
            "NButton": "import QtQuick\nItem { property string text; signal clicked; implicitHeight: 30 }",
            "NDropShadow": "import QtQuick\nItem { property Item source }",
        },
    )
    write(directory, "qs.Modules.Panels.Wallpaper", {"WallhavenSettingsPopup": popup})
    write(directory, "qs.Services.Power", {"PowerProfileService": service})
    (directory / "tst_bounded.qml").write_text(
        (ROOT / "Tests/Qml/WallhavenPowerWarningsHarness.qml").read_text()
    )
    (directory / "fonts.conf").write_text(
        "<fontconfig><dir>/usr/share/fonts</dir><cachedir>/tmp/fonts</cachedir></fontconfig>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode", choices=("lint", "runtime", "isolation", "lint-harness")
    )
    parser.add_argument("--mutation", choices=("selection", "resolution", "power"))
    parser.add_argument("--expected", nargs=2, type=int, default=[0, 0])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-wallhaven-power-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        helper("wallpaper-tab-warnings").install_audit(directory)
        if args.mode == "lint":
            helper("media-mini-warnings").stage_modules(directory)
            counts = []
            for target in TARGETS:
                result = isolated(
                    directory,
                    [
                        "/usr/lib/qt6/bin/qmllint",
                        "-I",
                        "/fixture",
                        str(Path("/fixture/qs") / target),
                    ],
                )
                output = result.stdout + result.stderr
                print(output, end="")
                blocks = re.split(r"(?=Warning:)", output)[1:]
                warnings = Counter(
                    re.findall(r"\[([^]]+)\]", block)[0] for block in blocks
                )
                print(target, dict(warnings), "exit", result.returncode)
                counts.append(sum(warnings.values()))
                assert result.returncode == 0
            assert counts == args.expected, (counts, args.expected)
        elif args.mode == "isolation":
            probe = "import pathlib, socket\nfor p in ('/home/osso', '/syncthing', '/run', '/etc', '/sys', '/dev/dri', '/dev/cpu', '/dev/input'):\n assert not pathlib.Path(p).exists(), p\n print('MASK_ABSENT', p)\ns = socket.socket(); s.settimeout(1)\ntry: s.connect(('1.1.1.1', 443))\nexcept OSError: print('NETWORK_DENIED')\nelse: raise AssertionError('network accessible')\nfinally: s.close()\n"
            result = isolated(directory, ["/usr/bin/python3", "-c", probe])
            print(result.stdout + result.stderr, end="")
            assert result.returncode == 0
        else:
            stage(directory, args.mutation)
            if args.mode == "lint-harness":
                argv = [
                    "/usr/lib/qt6/bin/qmllint",
                    "--bare",
                    "-I",
                    "/fixture",
                    "-I",
                    "/usr/lib/qt6/qml",
                    "--max-warnings",
                    "0",
                    "/fixture/tst_bounded.qml",
                ]
            else:
                argv = [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    "/fixture/tst_bounded.qml",
                    "-import",
                    "/fixture",
                ]
            result = isolated(directory, argv)
            output = result.stdout + result.stderr
            print(output, end="")
            if args.mutation:
                assert result.returncode != 0 and "FAIL!" in output
            else:
                assert result.returncode == 0
            assert not re.search(
                r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
                output,
            ), output


if __name__ == "__main__":
    main()
