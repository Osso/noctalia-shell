#!/usr/bin/env python3
"""Bounded offscreen JsonAdapter contract and real qmllint type regression."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
REAL_SETTINGS = Path("/home/osso/.config/noctalia/settings.json")
SETTINGS_HASH = "bc53e7cae6f456d443ba79ccee688802f18fb38abd6cbfc695ae331885b841e4"
GOLDEN = REPO / "Tests/fixtures/settings-types-default.json"
MUTATED_GOLDEN = REPO / "Tests/fixtures/settings-types-mutated.json"
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


def assert_real_settings_unchanged():
    actual = hashlib.sha256(REAL_SETTINGS.read_bytes()).hexdigest()
    if actual != SETTINGS_HASH:
        raise AssertionError(f"Real settings changed: {actual}")


def isolated_environment(root):
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
    for variable in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                     "XDG_STATE_HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_DIRS", "XDG_DATA_DIRS"):
        path = root / variable.lower()
        path.mkdir(mode=0o700)
        environment[variable] = str(path)
    environment.update(QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
    return environment


def prepare_sources(root):
    for directory in ("Commons", "Helpers", "Modules/OSD"):
        (root / directory).mkdir(parents=True)
    shutil.copy2(REPO / "Commons/SettingsData.qml", root / "Commons/SettingsData.qml")
    shutil.copy2(REPO / "Helpers/SettingsDefaults.js", root / "Helpers/SettingsDefaults.js")
    # Only enum values are used by SettingsData; never instantiate desktop OSD/services.
    (root / "Modules/OSD/OSD.qml").write_text(OSD_ENUM)
    (root / "Commons/Settings.qml").write_text(SETTINGS_ALIAS)
    shutil.copy2(REPO / "Tests/Qml/SettingsTypesHarness.qml", root / "shell.qml")


def run_contract(value, mutate=False):
    assert_real_settings_unchanged()
    with tempfile.TemporaryDirectory(prefix="noctalia-settings-types-") as temporary:
        root = Path(temporary)
        prepare_sources(root)
        environment = isolated_environment(root)
        settings_path = root / "xdg_config_home/settings.json"
        settings_path.write_text(json.dumps(value))
        environment.update(SETTINGS_TYPES_PATH=str(settings_path),
                           SETTINGS_TYPES_MUTATE="1" if mutate else "0")
        if "WAYLAND_DISPLAY" in environment or "DISPLAY" in environment:
            raise AssertionError("Desktop connection not isolated")
        try:
            result = subprocess.run(
                ["quickshell", "--no-color", "-p", str(root / "shell.qml")],
                cwd=root, env=environment, capture_output=True, text=True, timeout=15,
            )
            output = result.stdout + result.stderr
            if result.returncode or "SETTINGS_TYPES_PASS" not in output:
                raise AssertionError(output)
            if " WARN " in output or " ERROR " in output:
                raise AssertionError(output)
            loaded = {}
            for name in ("UI", "WIDGETS"):
                match = re.search(r"LOADED_" + name + r" (\{.*\})", output)
                if not match:
                    raise AssertionError(output)
                loaded[name.lower()] = json.loads(match[1])
            return settings_path.read_bytes(), loaded
        except subprocess.TimeoutExpired as error:
            raise AssertionError(f"Offscreen harness timed out: {error.stdout!r} {error.stderr!r}") from error
        finally:
            assert_real_settings_unchanged()


class SettingsContractTest(unittest.TestCase):
    def test_exact_default_serialization(self):
        actual, loaded = run_contract({})
        self.assertEqual(actual, GOLDEN.read_bytes())
        expected = json.loads(actual)
        self.assertEqual(loaded["ui"], expected["ui"])
        self.assertEqual(loaded["widgets"], expected["bar"]["widgets"])
        print(f"default bytes={len(actual)} sha256={hashlib.sha256(actual).hexdigest()}")

    def test_load_mutate_save_unknown_keys_nested_arrays_and_reload(self):
        defaults = json.loads(GOLDEN.read_bytes())
        left = [{"id": "CustomButton", "extra": {"arrays": [["x"], [1, False, None]]}}]
        incoming = {
            "ui": {"fontDefault": "Loaded Sans", "fontFixed": "Loaded Mono", "unknownUi": 17},
            "bar": {"widgets": {"left": left, "unknownWidgets": ["discard"]}, "unknownBar": True},
            "unknownRoot": {"discard": True},
        }
        actual, loaded = run_contract(incoming, mutate=True)
        loaded_ui = dict(defaults["ui"], fontDefault="Loaded Sans", fontFixed="Loaded Mono")
        self.assertEqual(loaded["ui"], loaded_ui)
        self.assertEqual(loaded["widgets"], dict(defaults["bar"]["widgets"], left=left))
        expected = copy.deepcopy(defaults)
        expected["ui"].update(fontDefault="Mutated Sans", fontFixed="Loaded Mono",
                              fontDefaultScale=1.25, tooltipsEnabled=False)
        expected["bar"]["widgets"] = {
            "left": [{"id": "Clock", "options": {"labels": ["a", "b"], "enabled": True}}],
            "center": [], "right": [{"id": "Tray", "items": [[1, 2], [3]]}],
        }
        self.assertEqual(json.loads(actual), expected)
        # Full serialized external contract, including formatting and every unrelated field.
        expected_bytes = MUTATED_GOLDEN.read_bytes()
        self.assertEqual(json.loads(expected_bytes), expected)
        self.assertEqual(actual, expected_bytes)
        reloaded, observed = run_contract(expected)
        self.assertEqual(reloaded, actual)
        self.assertEqual(observed, {"ui": expected["ui"], "widgets": expected["bar"]["widgets"]})
        print(f"mutated bytes={len(actual)} sha256={hashlib.sha256(actual).hexdigest()}; exact reload")


class SettingsStaticTest(unittest.TestCase):
    def test_settings_alias_ui_fields_resolve_without_suppressing_bar_warning(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-settings-types-lint-") as temporary:
            root = Path(temporary)
            source = root / "qs"
            source.mkdir()
            prepare_sources(source)
            (source / "Probe.qml").write_text(PROBE)
            for directory, entries in {
                "Commons": "SettingsData 1.0 SettingsData.qml\nsingleton Settings 1.0 Settings.qml\n",
                "Modules/OSD": "OSD 1.0 OSD.qml\n",
            }.items():
                module = "qs." + directory.replace("/", ".")
                (source / directory / "qmldir").write_text(f"module {module}\n{entries}")
            result = subprocess.run(
                ["/usr/lib/qt6/bin/qmllint", "-I", str(root), str(source / "Probe.qml")],
                cwd=root, capture_output=True, text=True, timeout=30,
            )
            diagnostics = result.stdout + result.stderr
            print(diagnostics, end="")
            self.assertNotIn("Failed to import", diagnostics)
            self.assertNotIn("was not found", diagnostics)
            missing = re.findall(r'^Warning:.*\[missing-property\]$', diagnostics, re.MULTILINE)
            print(f"targeted missing-property warnings: {len(missing)}")
            self.assertEqual(len(missing), 1, diagnostics)
            self.assertIn('Member "widgets" not found', diagnostics)
            for name in ("fontDefault", "fontFixed", "fontDefaultScale", "tooltipsEnabled"):
                self.assertNotIn(f'Member "{name}" not found', diagnostics)


if __name__ == "__main__":
    unittest.main()
