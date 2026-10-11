#!/usr/bin/env python3
"""One production tab: targeted lint and isolated offscreen state/geometry.

Production controls/layouts stay real. UPower, sysfs, processes, settings,
translations and palette are inert fixtures; no desktop or host IO is possible.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from qml_fixture_lint import check_harness

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Panels/Settings/Tabs/BatteryTab.qml")
SETTINGS = Path("/home/osso/.config/noctalia/settings.json")


def write_module(directory, name, sources):
    path = directory / name.replace(".", "/")
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for type_name, source in sources.items():
        (path / f"{type_name}.qml").write_text(source)
        prefix = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{prefix}{type_name} 1.0 {type_name}.qml\n")
    (path / "qmldir").write_text(f"module {name}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def lint(directory):
    spec = importlib.util.spec_from_file_location(
        "lint_staging", ROOT / "Tests/media-mini-warnings.test.py"
    )
    staging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(staging)
    staging.stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    counts = Counter(
        re.findall(r"\[([^]]+)\]", line)[-1]
        for line in output.splitlines()
        if line.startswith("Warning:")
    )
    print("BATTERY_TAB_LINT_COUNTS", dict(counts))
    assert not counts, f"Unexpected BatteryTab warnings: {dict(counts)}"
    assert result.returncode == 0, result.returncode


def stage_tab(directory):
    controls = (
        "NBox",
        "NHeader",
        "NText",
        "NIcon",
        "NLabel",
        "NValueSlider",
        "NSlider",
        "NDivider",
    )
    sources = {name: (ROOT / f"Widgets/{name}.qml").read_text() for name in controls}
    write_module(directory, "qs.Widgets", sources)
    write_module(directory, "qs.Tabs", {"BatteryTab": (ROOT / TARGET).read_text()})
    write_module(directory, "Quickshell", {"Fixture": "import QtQuick\nQtObject {}"})
    write_module(
        directory, "Quickshell.Widgets", {"Fixture": "import QtQuick\nQtObject {}"}
    )
    write_module(
        directory,
        "Quickshell.Services.UPower",
        {
            "UPowerDevice": """import QtQuick
QtObject {
  property bool ready: true
  property real percentage: 0.65
  property int state: UPowerDeviceState.Discharging
  property bool healthSupported: true
  property real healthPercentage: 85
  property int timeToFull: 0
  property int timeToEmpty: 7200
  property real changeRate: -12.5
}""",
            "UPowerDeviceState": singleton(
                "enum State { Discharging, Charging, FullyCharged }"
            ),
            "UPower": singleton("property UPowerDevice displayDevice: UPowerDevice {}"),
        },
    )
    write_module(
        directory,
        "Quickshell.Io",
        {
            "FileView": """import QtQuick
QtObject {
  property string path
  property bool printErrors
  signal loaded()
  signal loadFailed()
  function text() {
    if (path.endsWith('start_threshold')) return '20';
    if (path.endsWith('end_threshold')) return '80';
    return '123';
  }
  function reload() { loaded(); }
}""",
            "Process": """import QtQuick
QtObject {
  property var command
  property bool running: false
  signal exited(int exitCode)
}""",
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["ui"].update(fontDefault="Sans Serif", fontFixed="monospace")
    style = {
        "marginXXS": 2,
        "marginXS": 4,
        "marginS": 6,
        "marginM": 8,
        "marginL": 12,
        "radiusM": 8,
        "radiusL": 12,
        "borderS": 1,
        "borderL": 2,
        "fontSizeS": 10,
        "fontSizeM": 12,
        "fontSizeL": 14,
        "fontSizeXL": 16,
        "fontSizeXXL": 20,
        "fontWeightMedium": 500,
        "fontWeightSemiBold": 600,
        "fontWeightBold": 700,
        "animationFast": 0,
        "baseWidgetSize": 32,
        "sliderWidth": 200,
    }
    colors = {
        "mPrimary": "#3355aa",
        "mSecondary": "#557733",
        "mError": "#cc2233",
        "mTertiary": "#bbaa22",
        "mSurface": "#202020",
        "mSurfaceVariant": "#141414",
        "mOnSurface": "#ffffff",
        "mOnSurfaceVariant": "#aaaaaa",
        "mOutline": "#808080",
        "mHover": "#404040",
        "transparent": "transparent",
    }
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "property real uiScaleRatio: 1\nproperty real animationNormal: 300\n"
                + "\n".join(
                    f"readonly property real {key}: {value}"
                    for key, value in style.items()
                )
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"' for key, value in colors.items()
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
            "Time": singleton(
                "function formatVagueHumanReadableDuration(seconds) { return seconds + ' seconds'; }"
            ),
            "Logger": singleton(
                "function i(...args) {}\nfunction w(...args) { console.warn(...args); }"
            ),
            "Icons": singleton(
                "property string defaultIcon: 'battery'\nproperty string fontFamily: 'Sans Serif'\nfunction get(icon) { return icon; }"
            ),
        },
    )
    write_module(
        directory,
        "qs.Services.Hardware",
        {
            "BatteryService": singleton(
                "function getIcon(percent, charging, ready) { return ready ? (charging ? 'charging' : 'battery') : 'missing'; }"
            )
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "TooltipService": singleton(
                "function show(...args) { throw new Error('Unexpected tooltip'); }\nfunction hide() {}"
            )
        },
    )
    # Extend the existing behavioral harness without changing its tracked baseline.
    harness = (ROOT / "Tests/Qml/BatteryTabWarningsHarness.qml").read_text()
    harness = harness.replace("wait(50);", "wait(350);")
    harness = harness.replace("wait(100);", "wait(350);")
    harness = harness.replace(
        "UPower.displayDevice.timeToEmpty = 7200;",
        "UPower.displayDevice.timeToEmpty = 7200;\n    UPower.displayDevice.changeRate = -12.5;",
    )
    (directory / "tst_battery.qml").write_text(
        harness.rstrip()[:-1] + DISPLAY_TESTS + "}\n"
    )


DISPLAY_TESTS = """
  function test_powerAndHealth_data() {
    return [
      { tag: "charging-healthy", rate: 12.5, state: UPowerDeviceState.Charging, health: 80, color: NColor.mOnSurface },
      { tag: "discharging-warning", rate: -12.5, state: UPowerDeviceState.Discharging, health: 50, color: NColor.mTertiary },
      { tag: "idle-poor", rate: 0, state: UPowerDeviceState.FullyCharged, health: 49, color: NColor.mError }
    ];
  }

  function test_powerAndHealth(data) {
    UPower.displayDevice.ready = true;
    UPower.displayDevice.percentage = 0.65;
    UPower.displayDevice.healthSupported = true;
    UPower.displayDevice.changeRate = data.rate;
    UPower.displayDevice.state = data.state;
    UPower.displayDevice.healthPercentage = data.health;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(350);
    const visibleTexts = texts(tab);
    compare(visibleTexts.includes("settings.battery.status.power"), data.rate !== 0);
    compare(visibleTexts.includes("12.5 W"), data.rate !== 0);
    verify(!visibleTexts.some(text => text.includes("undefined") || text.includes("NaN") || text === "-12.5 W"));
    const healthLabel = descendants(tab).find(item => item.visible && item.text === "settings.battery.status.health");
    verify(healthLabel !== undefined);
    const health = descendants(tab).filter(item => item.visible && item.parent === healthLabel.parent && item.text === data.health + "%");
    compare(health.length, 1);
    compare(health[0].color, data.color);
    const stateText = data.state === UPowerDeviceState.Charging ? "battery.charging" :
                      data.state === UPowerDeviceState.Discharging ? "battery.discharging" : "battery.plugged-in";
    verify(visibleTexts.includes(stateText));
  }

  function test_progressAnimation_data() {
    return [{ tag: "normal-300ms", duration: 300 }, { tag: "scaled-600ms", duration: 600 }];
  }

  function test_progressAnimation(data) {
    Style.animationNormal = data.duration;
    UPower.displayDevice.ready = true;
    UPower.displayDevice.percentage = 0.2;
    const tab = createTemporaryObject(tabComponent, testCase);
    verify(tab !== null);
    wait(data.duration + 50);
    const track = progressTrack(tab);
    const fill = track.children[0];
    fuzzyCompare(fill.width, track.width * 0.2, 0.01);
    UPower.displayDevice.percentage = 0.8;
    wait(data.duration / 2);
    verify(fill.width > track.width * 0.4 && fill.width < track.width * 0.6,
           "Normal animation duration controls the observed midpoint");
    wait(data.duration / 2 + 50);
    fuzzyCompare(fill.width, track.width * 0.8, 0.01);
    compare(fill.height, track.height);
    console.log("BATTERY_ANIMATION_PASS " + data.duration + "ms midpoint/endpoint");
    Style.animationNormal = 300;
  }
"""


def lint_harness(directory):
    stage_tab(directory)
    harness = directory / "tst_battery.qml"
    harness.write_text((ROOT / "Tests/Qml/BatteryTabWarningsHarness.qml").read_text())
    return check_harness(directory, harness)


def behavior(directory, snapshot):
    stage_tab(directory)
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for name in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        path = directory / name
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    environment.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QUICK_BACKEND="software",
        DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/battery-tab-session",
        DBUS_SYSTEM_BUS_ADDRESS="unix:path=/nonexistent/battery-tab-system",
    )
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmltestrunner",
            "-input",
            str(directory / "tst_battery.qml"),
            "-import",
            str(directory),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=45,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    assert result.returncode == 0, "Offscreen production BatteryTab failed"
    assert not re.search(r"\b(?:QWARN|WARN|ERROR|FATAL)\b", output), output
    records = [
        json.loads(record)
        for record in re.findall(r"BATTERY_SNAPSHOT (\{[^\n]+\})", output)
    ]
    assert len(records) == 2, records
    snapshot.write_text(json.dumps(records, indent=2) + "\n")
    golden = json.loads((ROOT / "Tests/fixtures/battery-tab-geometry.json").read_text())
    assert records == golden, (
        "BatteryTab content/geometry changed from pre-fix baseline"
    )
    print("BATTERY_TAB_BEHAVIOR_PASS", snapshot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "behavior", "lint-harness"))
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.mode == "behavior" and not args.snapshot:
        parser.error("behavior requires --snapshot")
    with tempfile.TemporaryDirectory(prefix="noctalia-battery-tab-") as temporary:
        directory = Path(temporary)
        if args.mode == "lint-harness":
            raise SystemExit(lint_harness(directory))
        before = SETTINGS.read_bytes()
        backup = directory / "settings-backup.json"
        backup.write_bytes(before)
        backup.chmod(0o600)
        digest = hashlib.sha256(before).hexdigest()
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
        try:
            if args.mode == "lint":
                lint(directory)
            else:
                behavior(directory, args.snapshot)
        finally:
            assert hashlib.sha256(SETTINGS.read_bytes()).hexdigest() == digest, (
                "Real settings changed"
            )
            print("SETTINGS_SHA_UNCHANGED", digest)
