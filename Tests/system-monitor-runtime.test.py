#!/usr/bin/env python3
"""Exercise production SystemMonitor offscreen with isolated service fixtures."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/Bar/Widgets/SystemMonitor.qml")


def write_module(directory, module, sources):
    path = directory / module.replace(".", "/")
    path.mkdir(parents=True, exist_ok=True)
    declarations = []
    for name, source in sources.items():
        (path / f"{name}.qml").write_text(source)
        singleton = "singleton " if source.startswith("pragma Singleton") else ""
        declarations.append(f"{singleton}{name} 1.0 {name}.qml\n")
    (path / "qmldir").write_text(f"module {module}\n" + "".join(declarations))


def singleton(body):
    return "pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n"


def stage_runtime(directory):
    # qmltestrunner cannot load Quickshell's executable-only plugin. The widget
    # only carries this screen object to services; test that identity explicitly.
    write_module(
        directory, "Quickshell", {"ShellScreen": "import QtQuick\nQtObject {}"}
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["bar"]["position"] = "top"
    defaults["bar"]["density"] = "comfortable"
    metadata = dict(
        usePrimaryColor=False,
        showCpuUsage=True,
        showCpuTemp=True,
        showMemoryUsage=True,
        showMemoryAsPercent=True,
        showNetworkStats=True,
        showDiskUsage=True,
        diskPath="/",
        showFanSpeed=True,
    )
    write_module(
        directory,
        "qs.Modules.Bar.Widgets",
        {
            "SystemMonitor": (ROOT / TARGET).read_text(),
        },
    )
    write_module(
        directory,
        "qs.Commons",
        {
            "Settings": singleton("property var data: " + json.dumps(defaults)),
            "Style": singleton(
                "\n".join(
                    f"property real {key}: {value}"
                    for key, value in {
                        "capsuleHeight": 40,
                        "marginM": 8,
                        "marginS": 4,
                        "marginXS": 3,
                        "marginXXS": 2,
                        "radiusM": 8,
                        "fontWeightMedium": 500,
                        "animationNormal": 0,
                    }.items()
                )
                + '\nproperty color capsuleColor: "#202020"'
            ),
            "NColor": singleton(
                "\n".join(
                    f'property color {key}: "{value}"'
                    for key, value in {
                        "mTertiary": "#ffaa00",
                        "mError": "#ff0000",
                        "mOnHover": "#000000",
                        "mPrimary": "#00ff00",
                        "mOnSurface": "#ffffff",
                        "mHover": "#808080",
                        "mSurfaceVariant": "#222222",
                    }.items()
                )
            ),
            "I18n": singleton("function tr(key) { return key; }"),
        },
    )
    write_module(
        directory,
        "qs.Modules.Bar.Extras",
        {
            "BarWidgetRegistry": singleton(
                "property var widgetMetadata: ({SystemMonitor: "
                + json.dumps(metadata)
                + "})"
            ),
        },
    )
    write_module(
        directory,
        "qs.Modules.Panels.Settings",
        {
            "SettingsFixture": "import QtQuick\nQtObject {}",
        },
    )
    write_module(
        directory,
        "qs.Services.System",
        {
            "SystemStatService": singleton("""
property real cpuUsage: 95
property real cpuTemp: 70
property real memPercent: 60
property real memGb: 8.5
property var diskPercents: ({"/": 75})
property real rxSpeed: 123
property real txSpeed: 456
property var refs: ({})
function beginPolling(metric) { refs[metric] = (refs[metric] || 0) + 1; }
function endPolling(metric) { refs[metric] -= 1; }
function formatSpeed(value) { return value + " B/s"; }
function formatCompactSpeed(value) { return value + "B"; }
"""),
        },
    )
    write_module(
        directory,
        "qs.Services.Hardware",
        {
            "FanService": singleton("""
property bool available: true
property bool sensorDetected: true
property var fans: [{label: "CPU", rpm: 1200}]
property int refs: 0
function beginPolling() { refs += 1; }
function endPolling() { refs -= 1; }
function isPollingActive() { return refs > 0; }
function formatRpm(value) { return value + "rpm"; }
function getMaxRpm() { return 1200; }
"""),
        },
    )
    write_module(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("""
property int toggles: 0
property int closes: 0
property int menus: 0
property var lastAnchor
property var lastScreen
function getPanel(name, screen) {
  lastScreen = screen;
  return {toggle: anchor => { toggles += 1; lastAnchor = anchor; }};
}
function getPopupMenuWindow(screen) {
  lastScreen = screen;
  return {close: () => { closes += 1; }, showContextMenu: menu => { menus += 1; }};
}
"""),
            "BarService": singleton("""
property var openedSettings
function openWidgetSettings(screen, section, index, widgetId, settings) {
  openedSettings = [screen, section, index, widgetId, settings];
}
function getContextMenuPosition(anchor, width, height) { return {x: 7, y: 9}; }
function getTooltipDirection() { return "bottom"; }
"""),
            "TooltipService": singleton("""
property string text: ""
property int hides: 0
function show(anchor, value, direction) { text = value; }
function hide() { hides += 1; }
"""),
        },
    )
    write_module(
        directory,
        "qs.Widgets",
        {
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize; property bool applyUiScale; text: icon; font.pointSize: pointSize }",
            "NText": "import QtQuick\nText { property string family; property real pointSize; property bool applyUiScale; font.family: family; font.pointSize: pointSize }",
            "NPopupContextMenu": """import QtQuick
Item {
  property var model
  property var screen: null
  property point openedAt
  signal triggered(string action)
  function openAtItem(anchor, x, y) { openedAt = Qt.point(x, y); }
}
""",
        },
    )
    (directory / "tst_system_monitor.qml").write_text(HARNESS)


HARNESS = """import QtQuick
import QtTest
import Quickshell
import qs.Commons
import qs.Modules.Bar.Widgets
import qs.Services.System
import qs.Services.Hardware
import qs.Services.UI

Item {
  width: 600; height: 400
  ShellScreen { id: testScreen }
  SystemMonitor {
    id: monitor
    screen: testScreen
    widgetId: "SystemMonitor"
    section: "left"
    sectionWidgetIndex: 0
    width: 400; height: 40
  }
  Component {
    id: fanMonitorComponent
    SystemMonitor {
      screen: testScreen
      widgetId: "SystemMonitor"
      width: 400; height: 40
    }
  }
  TestCase {
    name: "SystemMonitor"
    when: windowShown

    function objects(parent, predicate) {
      let matches = [];
      for (const child of parent.children) {
        if (predicate(child)) matches.push(child);
        matches = matches.concat(objects(child, predicate));
      }
      return matches;
    }
    function configure(position, density) {
      const data = JSON.parse(JSON.stringify(Settings.data));
      data.bar.position = position;
      data.bar.density = density;
      data.bar.widgets.left = [{id: "SystemMonitor", showCpuUsage: true}];
      Settings.data = data;
    }
    function test_fan_contract() {
      configure("top", "comfortable");
      const originalData = Settings.data;
      const icon = objects(monitor, child => child.icon === "propeller")[0];
      verify(icon !== undefined);
      const container = icon.parent.parent.parent;
      const text = objects(container, child => child.family !== undefined)[0];
      compare(text.text, "1200rpm");
      const hover = objects(container, child => child.acceptedButtons === Qt.NoButton)[0];
      verify(hover !== undefined);
      FanService.fans = [{label: "CPU", rpm: 2100}, {label: "Chassis", rpm: 980}];
      hover.entered();
      compare(TooltipService.text, "CPU: 2100 RPM\\nChassis: 980 RPM");
      hover.exited();
      compare(TooltipService.hides, 1);
      for (const enabled of [true, false]) {
        const data = JSON.parse(JSON.stringify(Settings.data));
        data.bar.widgets.left = [{id: "SystemMonitor", showFanSpeed: enabled}];
        Settings.data = data;
        for (const available of [true, false]) {
          for (const detected of [true, false]) {
            FanService.available = available;
            FanService.sensorDetected = detected;
            compare(container.visible, enabled && (available || detected));
            compare(FanService.refs, enabled ? 1 : 0);
          }
        }
      }
      monitor.visible = false;
      compare(FanService.refs, 0);
      const temporary = fanMonitorComponent.createObject(monitor.parent);
      verify(temporary !== null);
      compare(FanService.refs, 1);
      FanService.refs = 0;
      FanService.sensorDetected = !FanService.sensorDetected;
      compare(FanService.refs, 1, "sensor change restores polling after service reset");
      temporary.destroy();
      tryCompare(FanService, "refs", 0);
      Settings.data = originalData;
      FanService.available = true;
      FanService.sensorDetected = true;
      FanService.fans = [{label: "CPU", rpm: 1200}];
      TooltipService.hides = 0;
      TooltipService.text = "";
      monitor.visible = true;
    }
    function test_scaling() {
      configure("top", "comfortable");
      compare(monitor.textSize, 13.2);
      compare(monitor.pillHeight, 26);
      configure("top", "compact");
      compare(monitor.textSize, 17.2);
      compare(monitor.pillHeight, 34);
      configure("left", "compact");
      monitor.width = 18;
      wait(30);
      fuzzyCompare(monitor.textSize, 18 * 0.82 * 0.43, 0.0001);
      const texts = objects(monitor, child => child.family !== undefined);
      compare(texts.length, 7);
      for (const text of texts) {
        fuzzyCompare(text.scale, Math.min(1, 18 / text.implicitWidth), 0.0001);
        verify(text.scale <= 1 && text.scale > 0);
      }
      monitor.width = 400;
      configure("top", "comfortable");
      wait(30);
      for (const text of texts) compare(text.scale, 1);
    }
    function test_interactions() {
      configure("top", "comfortable");
      wait(30);
      const areas = objects(monitor, child => child.acceptedButtons !== undefined);
      compare(areas.length, 3);
      const main = areas.filter(child => child.acceptedButtons === (Qt.LeftButton | Qt.RightButton))[0];
      const menus = objects(monitor, child => child.openedAt !== undefined);
      compare(menus.length, 1);
      mouseClick(main, main.width / 2, main.height / 2, Qt.LeftButton);
      compare(PanelService.toggles, 1);
      compare(PanelService.lastAnchor, monitor);
      compare(PanelService.lastScreen, testScreen);
      mouseClick(main, main.width / 2, main.height / 2, Qt.RightButton);
      compare(PanelService.menus, 1);
      compare(menus[0].openedAt, Qt.point(7, 9));
      menus[0].triggered("widget-settings");
      compare(PanelService.closes, 1);
      compare(BarService.openedSettings[0], null);
      compare(PanelService.lastScreen, null);
      compare(BarService.openedSettings[1], "left");
      compare(BarService.openedSettings[2], 0);
      compare(BarService.openedSettings[3], "SystemMonitor");
      compare(BarService.openedSettings[4].showCpuUsage, true);
      const hoverAreas = areas.filter(child => child.acceptedButtons === Qt.NoButton);
      hoverAreas[0].entered();
      compare(TooltipService.text, "/");
      hoverAreas[1].entered();
      compare(TooltipService.text, "CPU: 1200 RPM");
      hoverAreas[1].exited();
      compare(TooltipService.hides, 1);
      mouseMove(main, main.width / 2, main.height / 2);
      tryCompare(monitor, "isHovered", true);
      compare(monitor.textColor, NColor.mOnHover);
      compare(monitor.iconColor, NColor.mOnHover);
    }
    function test_indicator_and_polling() {
      configure("top", "comfortable");
      wait(30);
      const indicators = objects(monitor, child => child.indicatorWidth !== undefined);
      compare(indicators.length, 4);
      const metrics = ["cpu", "temp", "mem", "disk"];
      for (const level of ["Warning", "Critical", "None"]) {
        SystemStatService.cpuUsage = level === "None" ? 0 : monitor["cpu" + level + "Threshold"] + 1;
        SystemStatService.cpuTemp = level === "None" ? 0 : monitor["temp" + level + "Threshold"] + 1;
        SystemStatService.memPercent = level === "None" ? 0 : monitor["mem" + level + "Threshold"] + 1;
        SystemStatService.diskPercents = {"/": level === "None" ? 0 : monitor["disk" + level + "Threshold"] + 1};
        wait(10);
        for (let index = 0; index < indicators.length; index++) {
          const indicator = indicators[index];
          compare(indicator.warning, monitor[metrics[index] + "Warning"]);
          compare(indicator.critical, level === "Critical");
          compare(indicator.scale, level === "None" ? 0 : 1);
          compare(indicator.opacity, level === "None" ? 0 : 1);
          compare(indicator.color, level === "Critical" ? monitor.criticalColor : monitor.warningColor);
        }
      }
      const originalData = Settings.data;
      const coloredData = JSON.parse(JSON.stringify(originalData));
      coloredData.systemMonitor.useCustomColors = true;
      coloredData.systemMonitor.warningColor = "#123456";
      coloredData.systemMonitor.criticalColor = "#abcdef";
      Settings.data = coloredData;
      wait(10);
      for (const indicator of indicators) {
        compare(indicator.warningColor, "#123456");
        compare(indicator.criticalColor, "#abcdef");
      }
      configure("top", "compact");
      wait(10);
      for (const indicator of indicators) {
        compare(indicator.height, 34);
        compare(indicator.width, indicator.indicatorWidth + 6);
      }
      configure("right", "comfortable");
      monitor.width = 30;
      wait(10);
      for (const indicator of indicators) {
        compare(indicator.visible, false);
        compare(indicator.height, 46);
        compare(indicator.width, 22);
      }
      monitor.width = 400;
      configure("top", "comfortable");
      wait(10);
      for (const indicator of indicators) {
        compare(indicator.visible, true);
        compare(indicator.height, monitor.pillHeight);
        compare(indicator.width, indicator.indicatorWidth + 6);
      }
      Settings.data = originalData;
      monitor.visible = false;
      compare(FanService.refs, 0);
      for (const metric of ["cpu", "temp", "memory", "disk", "network"])
        compare(SystemStatService.refs[metric], 0);
      monitor.visible = true;
      compare(FanService.refs, 1);
      for (const metric of ["cpu", "temp", "memory", "disk", "network"])
        compare(SystemStatService.refs[metric], 1);
    }
  }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fan-only", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-system-monitor-") as temporary:
        directory = Path(temporary)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
            and key not in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "HOME")
        }
        for key in (
            "HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "XDG_RUNTIME_DIR",
        ):
            path = directory / key
            path.mkdir(mode=0o700)
            environment[key] = str(path)
        environment.update(
            QT_QPA_PLATFORM="offscreen",
            QT_QUICK_BACKEND="software",
            QT_FORCE_STDERR_LOGGING="1",
        )
        settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
        settings.parent.mkdir(mode=0o700, parents=True)
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        settings.touch(mode=0o600)
        settings.write_bytes(original)
        backup = directory / "settings.backup.json"
        backup.touch(mode=0o600)
        backup.write_bytes(original)
        assert backup.read_bytes() == original, "fixture backup bytes differ"
        stage_runtime(directory)
        try:
            result = subprocess.run(
                [
                    "/usr/lib/qt6/bin/qmltestrunner",
                    "-input",
                    str(directory),
                    "-import",
                    str(directory),
                    *(["SystemMonitor::test_fan_contract"] if args.fan_only else []),
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            print(result.stdout + result.stderr, end="")
            assert result.returncode == 0, (
                f"SystemMonitor runtime exit {result.returncode}"
            )
            assert "0 failed" in result.stdout + result.stderr
            assert not re.search(
                r"QWARN|QFATAL|ReferenceError|TypeError", result.stdout + result.stderr
            )
        finally:
            assert settings.read_bytes() == original, "fixture settings changed"
            assert backup.read_bytes() == original, "fixture backup changed"


if __name__ == "__main__":
    main()
