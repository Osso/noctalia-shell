#!/usr/bin/env python3
"""Bounded lock UI lint and offscreen behavior; no Wayland lock or PAM.

Production Loader, timers, layouts, password input and signal handlers remain
real. Session-lock transport, authentication and service/leaf dependencies are
inert fixtures. This proves UI routing, not compositor locking or authentication.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path("Modules/LockScreen/LockScreen.qml")


def helper(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT / "Tests" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lint(directory):
    helper("media-mini-warnings.test.py").stage_modules(directory)
    result = subprocess.run(
        [
            "/usr/lib/qt6/bin/qmllint",
            "-I",
            str(directory),
            str(directory / "qs" / TARGET),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(output, end="")
    warnings = [line for line in output.splitlines() if line.startswith("Warning:")]
    counts = Counter(re.findall(r"\[([^]]+)\]", line)[-1] for line in warnings)
    print("LOCK_SCREEN_LINT_COUNTS", dict(counts), "TOTAL", len(warnings))
    # Remaining diagnostics are the unchanged implicit-component context accesses.
    assert counts == {"unqualified": 10}, dict(counts)
    diagnostic_sources = re.findall(r"^Warning:.*\n([^\n]+)", output, re.M)
    assert all("lockContext." in line for line in diagnostic_sources), (
        diagnostic_sources
    )
    assert result.returncode == 255, result.returncode


def stage_runtime(directory, mutation):
    helpers = helper("about-tab-warnings.test.py")
    write, singleton = helpers.write_module, helpers.singleton
    inert = {"Inert": "import QtQuick\nQtObject {}"}
    write(
        directory,
        "Quickshell",
        {"ShellScreen": "import QtQuick\nQtObject { property string name }"},
    )
    for uri in (
        "Quickshell.Io",
        "Quickshell.Services.Pam",
        "Quickshell.Widgets",
        "qs.Services.Networking",
    ):
        write(directory, uri, inert)
    write(
        directory,
        "Quickshell.Wayland",
        {
            "WlSessionLock": "import QtQuick\nItem { property bool locked: false }",
            "WlSessionLockSurface": 'import QtQuick\nimport Quickshell\nItem { width: 1920; height: 1080; property ShellScreen screen: ShellScreen { name: "fixture-screen" } }',
        },
    )
    write(
        directory,
        "Quickshell.Services.UPower",
        {
            "UPowerDevice": "import QtQuick\nQtObject {}",
            "UPower": singleton("property UPowerDevice displayDevice: null"),
            "UPowerDeviceType": singleton("enum DeviceType { Battery = 2 }"),
            "UPowerDeviceState": singleton("enum DeviceState { Charging = 1 }"),
        },
    )
    defaults = json.loads((ROOT / "Assets/settings-default.json").read_text())
    defaults["general"]["showScreenCorners"] = False
    defaults["general"]["avatarImage"] = ""
    defaults["location"]["name"] = "Fixture, Test"
    defaults["location"]["weatherEnabled"] = True
    defaults["audio"]["visualizerType"] = "none"
    style = dict(
        uiScaleRatio=1,
        radiusL=12,
        screenRadius=12,
        marginM=8,
        marginXL=16,
        borderS=1,
        fontSizeS=10,
        fontSizeM=12,
        fontSizeL=14,
        fontSizeXL=16,
        fontSizeXXL=20,
        fontSizeXXXL=24,
        fontWeightMedium=500,
        fontWeightBold=700,
    )
    colors = {
        name: "#808080"
        for name in (
            "mShadow",
            "mSurface",
            "mOutline",
            "mPrimary",
            "mOnSurface",
            "mOnSurfaceVariant",
            "mError",
            "mOnError",
            "mOnPrimary",
            "mHover",
        )
    }
    colors.update(transparent="transparent", black="black")
    write(
        directory,
        "qs.Commons",
        {
            "Settings": singleton(
                "property var data: "
                + json.dumps(defaults)
                + "\nfunction preprocessPath(path) { return path; }"
            ),
            "Style": singleton(
                "\n".join(f"property real {k}: {v}" for k, v in style.items())
            ),
            "NColor": singleton(
                "\n".join(f'property color {k}: "{v}"' for k, v in colors.items())
            ),
            "I18n": singleton(
                'property var locale: Qt.locale("en_US")\nfunction tr(key) { return key; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.UI",
        {
            "PanelService": singleton("property Loader lockScreen: null"),
            "WallpaperService": singleton(
                'function getWallpaper(name) { if (name !== "fixture-screen") throw new Error("Wrong screen"); return ""; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.System",
        {
            "Time": singleton('property date now: new Date("2026-10-11T12:00:00")'),
            "HostService": singleton('property string displayName: "Fixture"'),
        },
    )
    write(
        directory,
        "qs.Services.Hardware",
        {
            "BluetoothService": singleton("property var devices: null"),
            "BatteryService": singleton(
                'function getIcon(percent, charging, ready) { return "battery"; }'
            ),
        },
    )
    write(
        directory,
        "qs.Services.Keyboard",
        {"KeyboardLayoutService": singleton('property string currentLayout: "US"')},
    )
    write(
        directory,
        "qs.Services.Media",
        {
            "MediaService": singleton(
                'property var currentPlayer: null\nproperty bool canPlay: false\nproperty string trackTitle: ""\nproperty string trackArtist: ""\nproperty string trackArtUrl: ""'
            ),
            "CavaService": singleton("property var values: []"),
        },
    )
    weather = dict(
        current_weather=dict(weathercode=1, temperature=20, windspeed=5),
        daily=dict(
            time=["2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14"],
            weathercode=[11, 22, 33, 44],
            temperature_2m_max=[10, 20, 30, 40],
            temperature_2m_min=[1, 2, 3, 4],
        ),
    )
    write(
        directory,
        "qs.Services.Location",
        {
            "LocationService": singleton(
                "property var data: "
                + json.dumps(dict(weather=weather))
                + '\nfunction weatherSymbolFromCode(code) { return "weather-" + code; }\nfunction celsiusToFahrenheit(c) { return c * 1.8 + 32; }'
            )
        },
    )
    write(
        directory,
        "qs.Services.Compositor",
        {
            "CompositorService": singleton(
                "property var events: []\n"
                + "\n".join(
                    f'function {action}() {{ events = events.concat(["{action}"]); }}'
                    for action in (
                        "logout",
                        "suspend",
                        "hibernate",
                        "reboot",
                        "shutdown",
                    )
                )
            )
        },
    )
    write(
        directory,
        "qs.Widgets",
        {
            "NText": "import QtQuick\nText { property real pointSize; font.pointSize: pointSize }",
            "NIcon": "import QtQuick\nText { property string icon; property real pointSize }",
            "NImageRounded": "import QtQuick\nItem { property real radius; property string imagePath; property string fallbackIcon; property real fallbackIconSize; property color borderColor; property real borderWidth }",
            "NClock": "import QtQuick\nItem { property date now; property string clockStyle; property color backgroundColor; property color clockColor; property color secondHandColor; property real hoursFontSize; property real minutesFontSize }",
            "NButton": "import QtQuick\nItem { property string icon; property string text; property bool outlined; property color backgroundColor; property color textColor; property color hoverColor; property real fontSize; property real iconSize; property real fontWeight; property int horizontalAlignment; property real buttonRadius; signal clicked() }",
        },
    )
    write(
        directory,
        "qs.Widgets.AudioSpectrum",
        {
            name: "import QtQuick\nItem { property var values; property color fillColor }"
            for name in ("NLinearSpectrum", "NMirroredSpectrum", "NWaveSpectrum")
        },
    )
    source = (ROOT / TARGET).read_text()
    # Observation labels only, on a disposable copy; no production test hooks.
    source = re.sub(r"(id: (\w+))", r'\1; objectName: "\2"', source)
    if mutation == "visibility":
        source = source.replace(
            "property bool passwordVisible: false",
            "property bool passwordVisible: true",
        )
    if mutation == "unload":
        source = source.replace("interval: 250", "interval: 5000")
    write(
        directory,
        "qs.Modules.LockScreen",
        {
            "LockScreen": source,
            "LockContext": """import QtQuick
Item {
  property string currentText: ""
  property bool unlockInProgress: false
  property bool showFailure: false
  property string errorMessage: ""
  property int attempts: 0
  signal unlocked()
  signal failed()
  function tryUnlock() { attempts++; unlockInProgress = true; }
}""",
        },
    )
    (directory / "tst_lock.qml").write_text(HARNESS)


HARNESS = """import QtQuick
import QtTest
import qs.Commons
import qs.Modules.LockScreen
import qs.Services.Media
import qs.Services.UI

Item {
  id: scene
  Component {
    id: factory
    LockScreen {}
  }
  TestCase {
    name: "LockScreenWarnings"
    when: true
    property var lock
    function named(name) {
      const found = findChild(lock, name);
      verify(found !== null, name);
      return found;
    }
    function descendants(parent, predicate) {
      let found = [];
      for (const child of parent.children) {
        if (predicate(child))
          found.push(child);
        found = found.concat(descendants(child, predicate));
      }
      return found;
    }
    function init() {
      lock = factory.createObject(scene);
      compare(PanelService.lockScreen, lock);
      compare(lock.active, false);
      compare(lock.item, null);
      lock.active = true;
      tryVerify(() => lock.item !== null);
    }
    function cleanup() {
      lock.destroy();
      lock = null;
      wait(0);
    }
    function test_password_mask_toggle_and_routing() {
      const input = named("passwordInput");
      const context = named("lockContext");
      compare(input.echoMode, TextInput.Password);
      input.insert(0, "aBc42");
      compare(context.currentText, "aBc42");
      named("eyeButtonArea").clicked(null);
      compare(input.echoMode, TextInput.Normal);
      const revealed = descendants(lock.item, child => child.text === "aBc42" && child !== input);
      compare(revealed.length, 1);
      compare(revealed[0].visible, true);
      named("eyeButtonArea").clicked(null);
      compare(input.echoMode, TextInput.Password);
      compare(revealed[0].visible, false);
      named("submitButtonArea").clicked(null);
      compare(context.attempts, 1);
      compare(input.enabled, false);
      compare(named("eyeButtonArea").parent.enabled, false);
      compare(named("submitButtonArea").parent.enabled, false);
      context.failed();
      compare(input.text, "");
      compare(lock.active, true);
    }
    function test_unlock_release_then_delayed_unload_and_reactivation() {
      const context = named("lockContext");
      const session = named("lockSession");
      context.currentText = "secret";
      context.unlocked();
      compare(session.locked, false);
      compare(context.currentText, "");
      compare(lock.active, true);
      verify(lock.item !== null);
      wait(100);
      compare(lock.active, true);
      tryCompare(lock, "active", false, 1000);
      compare(lock.item, null);
      lock.active = true;
      tryVerify(() => lock.item !== null);
      compare(named("lockSession").locked, true);
      compare(named("passwordInput").echoMode, TextInput.Password);
      compare(named("lockContext").currentText, "");
    }
    function test_destroy_pending_unload_does_not_affect_new_instance() {
      lock.scheduleUnloadAfterUnlock();
      lock.destroy();
      lock = factory.createObject(scene);
      compare(PanelService.lockScreen, lock);
      lock.active = true;
      tryVerify(() => lock.item !== null);
      wait(350);
      compare(lock.active, true);
      compare(named("lockSession").locked, true);
    }
    function test_forecast_indices_and_screen() {
      compare(named("lockBgImage").source.toString(), "");
      const weekdays = descendants(lock.item, child => child.text !== undefined && /^(Sun|Mon|Tue|Wed)$/.test(child.text));
      compare(weekdays.map(child => child.text), ["Sun", "Mon", "Tue", "Wed"]);
      const symbols = descendants(lock.item, child => child.icon !== undefined && /^weather-(11|22|33|44)$/.test(child.icon));
      compare(symbols.map(child => child.icon), ["weather-11", "weather-22", "weather-33", "weather-44"]);
      const temperatures = descendants(lock.item, child => child.text !== undefined && /^\\d+°\\/\\d+°$/.test(child.text));
      compare(temperatures.map(child => child.text), ["10°/1°", "20°/2°", "30°/3°", "40°/4°"]);
      MediaService.currentPlayer = {};
      MediaService.canPlay = true;
      wait(0);
      const reduced = descendants(lock.item, child => child.icon !== undefined && /^weather-(11|22|33|44)$/.test(child.icon));
      compare(reduced.map(child => child.icon), ["weather-11", "weather-22", "weather-33"]);
      MediaService.currentPlayer = null;
      MediaService.canPlay = false;
    }
  }
}
"""


def runtime(directory, mutation):
    settings = Path.home() / ".config/noctalia/settings.json"
    original = settings.read_bytes()
    backup = directory / "settings.backup.json"
    backup.touch(mode=0o600)
    backup.write_bytes(original)
    sha = hashlib.sha256(original).hexdigest()
    assert backup.stat().st_mode & 0o777 == 0o600
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == sha
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("XDG_", "WAYLAND_", "QT_", "QML_", "NOCTALIA_"))
        and k
        not in {
            "DISPLAY",
            "DBUS_SESSION_BUS_ADDRESS",
            "HOME",
            "NIRI_SOCKET",
            "HYPRLAND_INSTANCE_SIGNATURE",
            "SWAYSOCK",
        }
    }
    for key in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "NOCTALIA_CONFIG_DIR",
        "NOCTALIA_CACHE_DIR",
    ):
        path = directory / key
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    stage_runtime(directory, mutation)
    try:
        result = subprocess.run(
            [
                "/usr/lib/qt6/bin/qmltestrunner",
                "-input",
                str(directory / "tst_lock.qml"),
                "-import",
                str(directory),
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout + result.stderr
        print(output, end="")
        assert not re.search(r"QWARN|QFATAL|ReferenceError|TypeError", output), output
        assert result.returncode == 0, result.returncode
        assert "0 failed" in output
    finally:
        assert settings.read_bytes() == original, "real settings changed"
        print("LOCK_SCREEN_SETTINGS_SHA_UNCHANGED", sha)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument("--mutation", choices=("visibility", "unload"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-lock-screen-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory, args.mutation)
