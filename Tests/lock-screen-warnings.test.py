#!/usr/bin/env python3
"""Bounded lock UI lint and offscreen behavior; no Wayland lock or PAM.

Production Loader, timers, layouts, password input and signal handlers remain
real. Fake lock transport preserves the native default Component surface and
creation-context boundary, with deferred surface destruction on release. Fake
authentication supplies delayed success/failure; no PAM or native lock type is
loaded. Owner shadow and routing/clear-order/unload/visibility mutations test
binding ownership and lifecycle. Bubblewrap masks real config and runtime
sockets; only software/offscreen Qt runs. No live-lock/authentication proof.
"""

import argparse
from collections import Counter
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
            "--max-warnings",
            "0",
            "--json",
            "-",
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
    files = json.loads(result.stdout)["files"]
    assert len(files) == 1, files
    # Qt's block-scope diagnostics are absent from text output, but count toward
    # --max-warnings. Inspect JSON so strict acceptance cannot miss them.
    warnings = [
        diagnostic
        for diagnostic in files[0]["warnings"]
        if diagnostic["type"] in {"warning", "error"}
    ]
    counts = Counter(diagnostic["id"] for diagnostic in warnings)
    print("LOCK_SCREEN_LINT_COUNTS", dict(counts), "TOTAL", len(warnings))
    assert not warnings, warnings
    assert result.returncode == 0, result.returncode


def stage_runtime(directory, mutation, owner_shadow):
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
            "WlSessionLock": """import QtQuick
Item {
  id: transport
  default property Component surface
  property bool locked: false
  property Item surfaceInstance: null
  Component.onCompleted: {
    surfaceInstance = surface.createObject(transport);
  }
  onLockedChanged: {
    if (!locked && surfaceInstance !== null) {
      surfaceInstance.destroy();
      surfaceInstance = null;
    }
  }
}""",
            "WlSessionLockSurface": """import QtQuick
import Quickshell
import qs.Modules.LockScreen
Item {
  width: 1920
  height: 1080
  property ShellScreen screen: ShellScreen { name: "fixture-screen" }
  property LockContext shadowContext: LockContext { objectName: "shadowContext" }
"""
            + (
                "  property LockContext lockContext: shadowContext\n"
                if owner_shadow
                else ""
            )
            + "}",
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
    if mutation == "routing":
        source = source.replace("pragma ComponentBehavior: Bound\n", "")
    if mutation == "clear-order":
        source = source.replace(
            'lockSession.locked = false;\n          root.scheduleUnloadAfterUnlock();\n          lockContext.currentText = "";',
            'lockContext.currentText = "";\n          lockSession.locked = false;\n          root.scheduleUnloadAfterUnlock();',
        )
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
  property var submissions: []
  property bool nextSuccess: false
  onCurrentTextChanged: {
    if (currentText !== "") {
      showFailure = false;
      errorMessage = "";
    }
  }
  function tryUnlock() {
    submissions = submissions.concat([currentText]);
    attempts++;
    unlockInProgress = true;
    showFailure = false;
    errorMessage = "";
  }
  function finish(success) {
    nextSuccess = success;
    completion.start();
  }
  Timer {
    id: completion
    interval: 40
    onTriggered: {
      if (parent.nextSuccess) {
        parent.unlocked();
      } else {
        parent.errorMessage = "Fixture authentication failed";
        parent.showFailure = true;
        parent.failed();
      }
      parent.unlockInProgress = false;
    }
  }
}""",
        },
    )
    (directory / "tst_lock.qml").write_text(HARNESS)


HARNESS = """import QtQuick
import QtTest
import qs.Commons
import qs.Modules.LockScreen
import qs.Services.Hardware
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
      compare(context.submissions, ["aBc42"]);
      context.finish(false);
      compare(input.text, "aBc42");
      tryCompare(input, "text", "");
      compare(input.enabled, true);
      compare(lock.active, true);
      compare(named("lockSession").locked, true);
      compare(named("unloadAfterUnlockTimer").running, false);
      const failureText = descendants(lock.item, child => child.text === "Fixture authentication failed");
      compare(failureText.length, 1);
      compare(failureText[0].parent.parent.visible, true);
      compare(failureText[0].parent.parent.color, NColor.mError);
      input.insert(0, "retry7");
      compare(context.showFailure, false);
      compare(failureText[0].parent.parent.visible, false);
      input.forceActiveFocus();
      compare(input.activeFocus, true);
      keyClick(Qt.Key_Return);
      compare(context.submissions, ["aBc42", "retry7"]);
      compare(input.enabled, false);
      context.finish(false);
      tryCompare(input, "text", "");
      input.insert(0, "enter8");
      input.forceActiveFocus();
      keyClick(Qt.Key_Enter);
      compare(context.submissions, ["aBc42", "retry7", "enter8"]);
      compare(input.enabled, false);
      const shadow = named("shadowContext");
      compare(shadow.currentText, "");
      compare(shadow.attempts, 0);
      compare(shadow.showFailure, false);
    }
    function test_unlock_release_then_delayed_unload_and_reactivation() {
      const context = named("lockContext");
      const session = named("lockSession");
      const input = named("passwordInput");
      const unload = named("unloadAfterUnlockTimer");
      compare(unload.interval, 250);
      input.insert(0, "secret");
      named("submitButtonArea").clicked(null);
      compare(context.submissions, ["secret"]);
      let releaseText = null;
      let clearState = null;
      let releaseAt = 0;
      let unloadedAt = 0;
      session.lockedChanged.connect(() => {
        if (!session.locked) {
          releaseText = context.currentText;
          releaseAt = Date.now();
        }
      });
      context.currentTextChanged.connect(() => {
        if (context.currentText === "")
          clearState = [session.locked, unload.running, lock.active, lock.item !== null, input.text];
      });
      lock.activeChanged.connect(() => {
        if (!lock.active)
          unloadedAt = Date.now();
      });
      context.finish(true);
      compare(session.locked, true);
      compare(unload.running, false);
      compare(context.currentText, "secret");
      tryCompare(session, "locked", false);
      compare(releaseText, "secret");
      compare(clearState, [false, true, true, true, ""]);
      compare(context.currentText, "");
      compare(session.surfaceInstance, null);
      compare(lock.active, true);
      verify(lock.item !== null);
      wait(150);
      compare(lock.active, true);
      tryCompare(lock, "active", false, 750);
      verify(unloadedAt - releaseAt >= 225, "unloaded before 250ms boundary");
      verify(unloadedAt - releaseAt < 750, "unloaded too late");
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
    function verify_bluetooth_battery_selection() {
      const indicator = named("batteryIndicator");
      const first = { label: "first", connected: true, batteryAvailable: true, battery: 0 };
      const second = { label: "second", connected: true, batteryAvailable: true, battery: 0.75 };
      const cases = [
        [null, null],
        [{}, null],
        [{ values: [] }, null],
        [{ values: [null, { connected: false, batteryAvailable: true, battery: 1 }, { connected: true, batteryAvailable: false, battery: 1 }, { connected: true, batteryAvailable: true }] }, null],
        [{ values: [null, first, second] }, "first"],
        [{ values: [{ connected: false }, second] }, "second"],
        [{ values: [second, first] }, "second"],
        [{ values: [] }, null]
      ];
      for (const fixture of cases) {
        const before = JSON.stringify(fixture[0]);
        BluetoothService.devices = fixture[0];
        const selected = indicator.findBluetoothBatteryDevice();
        compare(selected === null ? null : selected.label, fixture[1]);
        compare(indicator.bluetoothDevice === null ? null : indicator.bluetoothDevice.label, fixture[1]);
        compare(JSON.stringify(BluetoothService.devices), before);
      }
      BluetoothService.devices = null;
    }
    function test_forecast_indices_and_screen() {
      verify_bluetooth_battery_selection();
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


def runtime(directory, mutation, owner_shadow):
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
    stage_runtime(directory, mutation, owner_shadow)
    result = subprocess.run(
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
            "python3",
            "-c",
            "import os, pathlib, sys; "
            "assert not pathlib.Path('/home/osso/.config/noctalia/settings.json').exists(); "
            "assert os.environ['QT_QPA_PLATFORM'] == 'offscreen'; "
            "assert 'WAYLAND_DISPLAY' not in os.environ and 'DISPLAY' not in os.environ; "
            "print('LOCK_SCREEN_REAL_CONFIG_MASKED', flush=True); "
            "os.execv(sys.argv[1], sys.argv[1:])",
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
    assert not re.search(
        r"QWARN|QFATAL|QCRITICAL|ReferenceError|TypeError|Binding loop|Warning:",
        output,
    ), output
    assert result.returncode == 0, result.returncode
    assert "6 passed, 0 failed" in output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lint", "runtime"))
    parser.add_argument(
        "--mutation", choices=("visibility", "unload", "routing", "clear-order")
    )
    parser.add_argument("--owner-shadow", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="noctalia-lock-screen-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        if args.mode == "lint":
            lint(directory)
        else:
            runtime(directory, args.mutation, args.owner_shadow)
