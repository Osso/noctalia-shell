#!/usr/bin/env python3
"""Bounded offscreen JsonAdapter contract and real qmllint type regression."""

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "Tests/fixtures/settings-types-default.json"
MUTATED_GOLDEN = REPO / "Tests/fixtures/settings-types-mutated.json"
GROUPS_GOLDEN = REPO / "Tests/fixtures/settings-types-groups.json"
OSD_ENUM = """import QtQuick
QtObject { enum Type { Volume, InputVolume, Brightness, LockKey } }
"""
SETTINGS_ALIAS = """pragma Singleton
import QtQuick
QtObject {
  readonly property alias data: adapter
  property SettingsData adapter: SettingsData { id: adapter }
}
"""
PROBE = """import QtQuick
import qs.Commons
QtObject {
  property string font: Settings.data.ui.fontDefault
  property string fixed: Settings.data.ui.fontFixed
  property real scale: Settings.data.ui.fontDefaultScale
  property bool tips: Settings.data.ui.tooltipsEnabled
  property var widgets: Settings.data.bar.widgets.left
}
"""
GROUPS_PROBE = PROBE.replace(
    "\n}\n",
    """
  property string barPosition: Settings.data.bar.position
  property var center: Settings.data.bar.widgets.center
  property var right: Settings.data.bar.widgets.right
  property string language: Settings.data.general.language
  property string location: Settings.data.location.name
  property var calendar: Settings.data.calendar.cards
  property int frameRate: Settings.data.screenRecorder.frameRate
  property bool wallpaper: Settings.data.wallpaper.enabled
  property var pinnedExecs: Settings.data.appLauncher.pinnedExecs
  property string controlPosition: Settings.data.controlCenter.position
  property var shortcutsLeft: Settings.data.controlCenter.shortcuts.left
  property var shortcutsRight: Settings.data.controlCenter.shortcuts.right
  property int cpuPolling: Settings.data.systemMonitor.cpuPollingInterval
  property bool dock: Settings.data.dock.enabled
  property bool wifi: Settings.data.network.wifiEnabled
  property var powerOptions: Settings.data.sessionMenu.powerOptions
  property int notificationDuration: Settings.data.notifications.normalUrgencyDuration
  property var osdTypes: Settings.data.osd.enabledTypes
  property int volumeStep: Settings.data.audio.volumeStep
  property int brightnessStep: Settings.data.brightness.brightnessStep
  property bool darkMode: Settings.data.colorSchemes.darkMode
  property bool gtk: Settings.data.templates.gtk
  property string nightTemp: Settings.data.nightLight.nightTemp
  property string lastSeenVersion: Settings.data.changelog.lastSeenVersion
  property bool hooks: Settings.data.hooks.enabled
}
""",
)


def representative_values(value):
    return {
        "barPosition": value["bar"]["position"],
        "language": value["general"]["language"],
        "shortcuts": value["controlCenter"]["shortcuts"],
        "volumeStep": value["audio"]["volumeStep"],
        "wallpaperChange": value["hooks"]["wallpaperChange"],
    }


def assert_fixture_settings_unchanged(path, expected):
    if path.read_bytes() != expected:
        raise AssertionError(f"Fixture settings changed: {path}")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise AssertionError(f"Fixture settings must remain 0600: {path}")


def isolated_environment(root):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for variable in (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "XDG_CONFIG_DIRS",
        "XDG_DATA_DIRS",
    ):
        path = root / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    return environment


def prepare_sources(root):
    for directory in ("Commons", "Helpers", "Modules/OSD"):
        (root / directory).mkdir(parents=True)
    shutil.copy2(REPO / "Commons/SettingsData.qml", root / "Commons/SettingsData.qml")
    shutil.copy2(
        REPO / "Helpers/SettingsDefaults.js", root / "Helpers/SettingsDefaults.js"
    )
    # Only enum values are used by SettingsData; never instantiate desktop OSD/services.
    (root / "Modules/OSD/OSD.qml").write_text(OSD_ENUM)
    (root / "Commons/Settings.qml").write_text(SETTINGS_ALIAS)
    shutil.copy2(REPO / "Tests/Qml/SettingsTypesHarness.qml", root / "shell.qml")


def run_contract(value, mutate=False):
    with tempfile.TemporaryDirectory(prefix="noctalia-settings-types-") as temporary:
        root = Path(temporary)
        prepare_sources(root)
        environment = isolated_environment(root)
        fixture_path = Path(environment["HOME"]) / ".config/noctalia/settings.json"
        fixture_path.parent.mkdir(mode=0o700, parents=True)
        fixture_bytes = json.dumps(value).encode("utf-8")
        fixture_path.touch(mode=0o600)
        fixture_path.write_bytes(fixture_bytes)
        assert_fixture_settings_unchanged(fixture_path, fixture_bytes)
        settings_path = root / "xdg_config_home/settings.json"
        settings_path.touch(mode=0o600)
        settings_path.write_bytes(fixture_bytes)
        environment.update(
            SETTINGS_TYPES_PATH=str(settings_path),
            SETTINGS_TYPES_MUTATE="1" if mutate else "0",
        )
        if "WAYLAND_DISPLAY" in environment or "DISPLAY" in environment:
            raise AssertionError("Desktop connection not isolated")
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(root / "shell.qml")],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout + result.stderr
            if result.returncode or "SETTINGS_TYPES_PASS" not in output:
                raise AssertionError(output)
            if " WARN " in output or " ERROR " in output:
                raise AssertionError(output)
            loaded = {}
            for name in ("UI", "WIDGETS", "OTHER"):
                match = re.search(r"LOADED_" + name + r" (\{.*\})", output)
                if not match:
                    raise AssertionError(output)
                loaded[name.lower()] = json.loads(match[1])
            return settings_path.read_bytes(), loaded
        except subprocess.TimeoutExpired as error:
            raise AssertionError(
                f"Offscreen harness timed out: {error.stdout!r} {error.stderr!r}"
            ) from error
        finally:
            assert_fixture_settings_unchanged(fixture_path, fixture_bytes)


class SettingsContractTest(unittest.TestCase):
    def test_exact_default_serialization(self):
        actual, loaded = run_contract({})
        self.assertEqual(actual, GOLDEN.read_bytes())
        expected = json.loads(actual)
        self.assertEqual(loaded["ui"], expected["ui"])
        self.assertEqual(loaded["widgets"], expected["bar"]["widgets"])
        self.assertEqual(loaded["other"], representative_values(expected))
        print(
            f"default bytes={len(actual)} sha256={hashlib.sha256(actual).hexdigest()}"
        )

    def test_load_mutate_save_unknown_keys_nested_arrays_and_reload(self):
        defaults = json.loads(GOLDEN.read_bytes())
        left = [{"id": "CustomButton", "extra": {"arrays": [["x"], [1, False, None]]}}]
        incoming = {
            "ui": {
                "fontDefault": "Loaded Sans",
                "fontFixed": "Loaded Mono",
                "unknownUi": 17,
            },
            "bar": {
                "widgets": {"left": left, "unknownWidgets": ["discard"]},
                "unknownBar": True,
            },
            "unknownRoot": {"discard": True},
        }
        actual, loaded = run_contract(incoming, mutate=True)
        loaded_ui = dict(
            defaults["ui"], fontDefault="Loaded Sans", fontFixed="Loaded Mono"
        )
        self.assertEqual(loaded["ui"], loaded_ui)
        self.assertEqual(loaded["widgets"], dict(defaults["bar"]["widgets"], left=left))
        expected = copy.deepcopy(defaults)
        expected["ui"].update(
            fontDefault="Mutated Sans",
            fontFixed="Loaded Mono",
            fontDefaultScale=1.25,
            tooltipsEnabled=False,
        )
        expected["bar"]["widgets"] = {
            "left": [
                {"id": "Clock", "options": {"labels": ["a", "b"], "enabled": True}}
            ],
            "center": [],
            "right": [{"id": "Tray", "items": [[1, 2], [3]]}],
        }
        self.assertEqual(json.loads(actual), expected)
        # Full serialized external contract, including formatting and every unrelated field.
        expected_bytes = MUTATED_GOLDEN.read_bytes()
        self.assertEqual(json.loads(expected_bytes), expected)
        self.assertEqual(actual, expected_bytes)
        reloaded, observed = run_contract(expected)
        self.assertEqual(reloaded, actual)
        self.assertEqual(
            observed,
            {
                "ui": expected["ui"],
                "widgets": expected["bar"]["widgets"],
                "other": representative_values(expected),
            },
        )
        print(
            f"mutated bytes={len(actual)} sha256={hashlib.sha256(actual).hexdigest()}; exact reload"
        )

    def test_other_groups_nested_shortcuts_and_fresh_process_reload(self):
        expected = json.loads(GOLDEN.read_bytes())
        incoming = {
            "bar": {"position": "left"},
            "general": {"language": "fr", "unknownGeneral": 17},
            "controlCenter": {
                "shortcuts": {
                    "left": [
                        {"id": "WiFi", "options": {"values": [[1], [False, None]]}}
                    ],
                    "right": [],
                    "unknownShortcuts": True,
                }
            },
            "audio": {"volumeStep": 7},
            "hooks": {"wallpaperChange": "printf wallpaper"},
        }
        for group, values in incoming.items():
            for key, value in values.items():
                if key in expected[group]:
                    expected[group][key] = copy.deepcopy(value)
        del expected["controlCenter"]["shortcuts"]["unknownShortcuts"]
        actual, loaded = run_contract(incoming)
        self.assertEqual(json.loads(actual), expected)
        self.assertEqual(actual, GROUPS_GOLDEN.read_bytes())
        self.assertEqual(loaded["other"], representative_values(expected))
        reloaded, observed = run_contract(expected)
        self.assertEqual(reloaded, actual)
        self.assertEqual(observed, loaded)
        print(
            f"groups bytes={len(actual)} sha256={hashlib.sha256(actual).hexdigest()}; exact reload"
        )


class SettingsStaticTest(unittest.TestCase):
    def assert_probe_resolves(self, probe):
        with tempfile.TemporaryDirectory(
            prefix="noctalia-settings-types-lint-"
        ) as temporary:
            root = Path(temporary)
            source = root / "qs"
            source.mkdir()
            prepare_sources(source)
            (source / "Probe.qml").write_text(probe)
            for directory, entries in {
                "Commons": "SettingsData 1.0 SettingsData.qml\nsingleton Settings 1.0 Settings.qml\n",
                "Modules/OSD": "OSD 1.0 OSD.qml\n",
            }.items():
                module = "qs." + directory.replace("/", ".")
                (source / directory / "qmldir").write_text(
                    f"module {module}\n{entries}"
                )
            result = subprocess.run(
                [
                    "/usr/lib/qt6/bin/qmllint",
                    "-I",
                    str(root),
                    str(source / "Probe.qml"),
                ],
                cwd=root,
                env=isolated_environment(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            diagnostics = result.stdout + result.stderr
            print(diagnostics, end="")
            self.assertNotIn("Failed to import", diagnostics)
            self.assertNotIn("was not found", diagnostics)
            missing = re.findall(
                r"^Warning:.*\[missing-property\]$", diagnostics, re.MULTILINE
            )
            print(f"targeted missing-property warnings: {len(missing)}")
            self.assertEqual(len(missing), 0, diagnostics)
            self.assertEqual(result.returncode, 0, diagnostics)

    def test_original_ui_and_nested_widgets_probe(self):
        self.assert_probe_resolves(PROBE)

    def test_all_groups_and_nested_shortcuts_resolve(self):
        self.assert_probe_resolves(GROUPS_PROBE)


if __name__ == "__main__":
    unittest.main()
