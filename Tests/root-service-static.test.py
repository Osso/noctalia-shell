"""Root-service CLI isolation: lint and offscreen behavior never use real settings."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import os
from pathlib import Path
import runpy
import sys

artifacts = Path(sys.argv.pop(1))
fixture_settings = artifacts / "HOME/.config/noctalia/settings.json"
real_config = Path("/home/osso/.config/noctalia")

def deny_real_settings(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        if path.is_relative_to(real_config) or (
            path.name == "settings.json" and path != fixture_settings
        ):
            raise PermissionError(f"blocked settings access: {path}")
    if event == "subprocess.Popen":
        if Path(args[0]).name not in (
            "qmllint", "qmltestrunner", "moc", "pkg-config", "c++"
        ):
            raise PermissionError(f"blocked live process access: {args[0]}")

sys.addaudithook(deny_real_settings)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


class RootServiceIsolationTest(unittest.TestCase):
    def run_mode(self, root, mode, inject_warning=False):
        for relative in ("Tests", "Services", "Helpers", "Assets"):
            shutil.copytree(ROOT / relative, root / relative)
        if inject_warning:
            harness = root / "Tests/Qml/RootServiceHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "TestCase {",
                    "TestCase {\n  property int regressionWarning: Qt.application.missingFixtureValue",
                    1,
                )
            )
        home = root / "home"
        home.mkdir(mode=0o700)
        settings = home / ".config/noctalia/settings.json"
        self.assertFalse(settings.exists())
        artifacts = root / "artifacts"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                BOOTSTRAP,
                str(artifacts),
                str(root / "Tests/root-service-warnings.test.py"),
                mode,
                "--artifacts",
                str(artifacts),
            ],
            cwd=root,
            env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config")),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        self.assertNotIn("blocked settings access", output, output)
        self.assertNotIn("blocked live process access", output, output)
        self.assertFalse(settings.exists())
        self.assertFalse((artifacts / "settings.backup").exists())
        return result, artifacts

    def test_lint_with_absent_settings_and_denied_real_access(self):
        with tempfile.TemporaryDirectory(prefix="root-service-static-") as temp:
            result, artifacts = self.run_mode(Path(temp), "lint-harness")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["files"]), 1)
            self.assertEqual(report["files"][0]["warnings"], [])
            self.assertFalse((artifacts / "HOME").exists())

    def test_injected_warning_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="root-service-warning-") as temp:
            result, _ = self.run_mode(Path(temp), "lint-harness", inject_warning=True)
            self.assertNotEqual(result.returncode, 0)
            warnings = json.loads(result.stdout)["files"][0]["warnings"]
            self.assertTrue(
                any(
                    warning["id"] == "missing-property"
                    and "missingFixtureValue" in warning["message"]
                    for warning in warnings
                ),
                warnings,
            )

    def test_offscreen_behavior_preserves_fixture_owned_settings(self):
        with tempfile.TemporaryDirectory(prefix="root-service-behavior-") as temp:
            result, artifacts = self.run_mode(Path(temp), "behavior")
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            for case in (
                "compositor_events_and_suspend_timer",
                "ipc_screen_callback_and_debounce",
                "brightness_detection_disable_discards_generation",
                "bluetooth_state_and_discovery_events",
                "notification_history_persistence_and_progress_event",
            ):
                self.assertIn(
                    f"PASS   : qmltestrunner::RootServices::test_{case}()", output
                )
            self.assertIn("7 passed, 0 failed", output)
            fixture = artifacts / "HOME/.config/noctalia/settings.json"
            self.assertEqual(
                fixture.read_bytes(),
                (ROOT / "Assets/settings-default.json").read_bytes(),
            )
            self.assertEqual(fixture.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
