#!/usr/bin/env python3
"""Four unit parents must never inspect host settings, even before child isolation."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("bar-widget-metadata-runtime.test.py", "behavior", "BAR_WIDGET_METADATA_PASS"),
    ("battery-tab-warnings.test.py", "behavior", "BATTERY_TAB_BEHAVIOR_PASS"),
    ("battery-widget-warnings.test.py", "behavior", "BATTERY_WIDGET_BEHAVIOR_PASS"),
    (
        "bluetooth-devices-list-runtime.test.py",
        "runtime",
        "BLUETOOTH_DEVICES_LIST_PASS",
    ),
)
LINT_CASES = (
    ("bar-widget-metadata-runtime.test.py", "lint-harness"),
    ("battery-tab-warnings.test.py", "lint"),
    ("battery-tab-warnings.test.py", "lint-harness"),
    ("battery-widget-warnings.test.py", "lint"),
    ("battery-widget-warnings.test.py", "lint-harness"),
    ("bluetooth-devices-list-runtime.test.py", "lint"),
)
BOOTSTRAP = """
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

root = Path(sys.argv.pop(1))
mutation = sys.argv.pop(1)
script = sys.argv[1]
sys.path.insert(0, str(Path(script).parent))
protected = "/home/osso/.config/noctalia"

def deny(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    name = os.path.abspath(os.fsdecode(path))
    if name == protected or name.startswith(protected + "/") or (
        name.endswith("/settings.json") and not name.startswith(str(root) + "/noctalia-")
    ):
        raise RuntimeError(f"blocked settings access: {name}")

def audit(event, args):
    if event in ("open", "os.listdir", "os.scandir"):
        deny(args[0])
    if event == "subprocess.Popen" and Path(args[0]).name in ("quickshell", "qmltestrunner"):
        environment = args[3]
        assert environment["QT_QPA_PLATFORM"] == "offscreen"
        assert environment["QT_QUICK_BACKEND"] == "software"
        assert environment["DBUS_SESSION_BUS_ADDRESS"].startswith("unix:path=/nonexistent/")
        assert environment["DBUS_SYSTEM_BUS_ADDRESS"].startswith("unix:path=/nonexistent/")
        home = Path(environment["HOME"])
        assert home.is_relative_to(root), "HOME outside fixture"
        settings = home / ".config/noctalia/settings.json"
        backup = home.parents[1] / "settings.backup.json"
        original = (Path(script).parents[1] / "Assets/settings-default.json").read_bytes()
        assert settings.read_bytes() == backup.read_bytes() == original, "fixture bytes differ"
        assert settings.stat().st_mode & 0o777 == 0o600, "settings not private"
        assert backup.stat().st_mode & 0o777 == 0o600, "backup not private"
        assert home.parents[1].stat().st_mode & 0o777 == 0o700, "fixture root not private"
        print("PRIVATE_FIXTURE_VERIFIED", flush=True)
        if mutation != "normal":
            (settings if mutation == "settings" else backup).write_bytes(b"mutated fixture")

def guard(function):
    def guarded(path, *args, **kwargs):
        deny(path)
        return function(path, *args, **kwargs)
    return guarded

sys.addaudithook(audit)
with patch("os.stat", guard(os.stat)), patch("os.lstat", guard(os.lstat)), patch("os.readlink", guard(os.readlink)), patch("os.access", guard(os.access)):
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")
"""


class UnitParentSettingsIsolationTest(unittest.TestCase):
    def run_mode(self, script, mode, mutation="normal"):
        with tempfile.TemporaryDirectory(prefix="unit-parent-isolation-") as temporary:
            root = Path(temporary)
            home = root / "absent-home"
            self.assertFalse(home.exists())
            arguments = [str(ROOT / "Tests" / script), mode]
            snapshot = root / "snapshot.json"
            if script == "battery-tab-warnings.test.py" and mode == "behavior":
                arguments.extend(("--snapshot", str(snapshot)))
            result = subprocess.run(
                [sys.executable, "-c", BOOTSTRAP, str(root), mutation, *arguments],
                cwd=ROOT,
                env=dict(
                    os.environ,
                    HOME=str(home),
                    XDG_CONFIG_HOME=str(home / ".config"),
                    TMPDIR=str(root),
                ),
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertFalse(home.exists())
            self.assertEqual(list(root.glob("noctalia-*")), [], "fixture leaked")
            if result.returncode == 0 and snapshot.exists():
                golden = json.loads(
                    (ROOT / "Tests/fixtures/battery-tab-geometry.json").read_text()
                )
                self.assertEqual(json.loads(snapshot.read_text()), golden)
            return result

    def assert_behavior(self, script, mode, marker):
        result = self.run_mode(script, mode)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PRIVATE_FIXTURE_VERIFIED", output)
        self.assertIn(marker, output)
        self.assertNotIn("blocked settings access", output)
        print(f"ISOLATED_CASE_PASS {script} {mode}")
        print(output, end="")

    def test_four_unit_modes_with_denied_settings_and_absent_home(self):
        for script, mode, marker in CASES:
            with self.subTest(script=script, mode=mode):
                self.assert_behavior(script, mode, marker)

    def test_bluetooth_concrete_devices(self):
        self.assert_behavior(
            "bluetooth-devices-list-runtime.test.py",
            "devices",
            "BLUETOOTH_DEVICES_LIST_PASS",
        )

    def test_lint_modes_with_denied_settings_and_absent_home(self):
        for script, mode in LINT_CASES:
            with self.subTest(script=script, mode=mode):
                result = self.run_mode(script, mode)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertNotIn("PRIVATE_FIXTURE_VERIFIED", output)
                self.assertNotIn("blocked settings access", output)
                print(f"ISOLATED_CASE_PASS {script} {mode}")

    def test_settings_and_backup_mutation_fail_integrity_check(self):
        for script, mode, _ in CASES:
            for mutation in ("settings", "backup"):
                with self.subTest(script=script, mutation=mutation):
                    result = self.run_mode(script, mode, mutation)
                    output = result.stdout + result.stderr
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertIn("PRIVATE_FIXTURE_VERIFIED", output)
                    self.assertIn(f"fixture {mutation} changed", output)
                    self.assertNotIn("blocked settings access", output)
                    print(f"MUTATION_DETECTED {script} {mutation}")


if __name__ == "__main__":
    unittest.main()
