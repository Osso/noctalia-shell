"""Setup geometry CLI runs against fixture settings, never protected host state."""

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
mutate = sys.argv.pop(1) == "mutate"
real_config = Path("/home/osso/.config/noctalia")

def audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        if path.is_relative_to(real_config) or (
            path.name == "settings.json" and not path.is_relative_to(artifacts)
        ):
            raise PermissionError(f"blocked settings access: {path}")
    if event == "subprocess.Popen":
        program = Path(args[0]).name
        if program not in ("qmllint", "quickshell"):
            raise PermissionError(f"blocked process access: {args[0]}")
        if program == "quickshell":
            environment = args[3]
            settings = Path(environment["HOME"]) / ".config/noctalia/settings.json"
            backup = artifacts / "settings.backup.json"
            assert settings.read_bytes() == backup.read_bytes(), "backup bytes differ"
            assert backup.stat().st_mode & 0o777 == 0o600, "backup not private"
            assert settings.stat().st_mode & 0o777 == 0o600, "settings not private"
            assert environment["QT_QPA_PLATFORM"] == "offscreen"
            if mutate:
                settings.write_bytes(b"changed fixture settings")

sys.addaudithook(audit)
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
"""


class SetupLayoutIsolationTest(unittest.TestCase):
    def run_mode(self, root, arguments=(), warning=False, mutate=False):
        for relative in (
            "Commons",
            "Helpers",
            "Widgets",
            "Assets",
            "Modules/Panels/SetupWizard",
            "Modules/MainScreen/SmartPanel.qml",
            "Tests/setup-layout-geometry.test.py",
            "Tests/Qml/SetupLayoutGeometryHarness.qml",
            "Tests/fixtures/setup-layout-geometry.json",
        ):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copyfile(source, target)
        if warning:
            harness = root / "Tests/Qml/SetupLayoutGeometryHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "{",
                    "{\n  property int regressionWarning: Qt.missingFixtureValue",
                    1,
                )
            )
        home = root / "absent-home"
        self.assertFalse(home.exists())
        artifacts = root / "artifacts"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                BOOTSTRAP,
                str(artifacts),
                "mutate" if mutate else "normal",
                str(root / "Tests/setup-layout-geometry.test.py"),
                *arguments,
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
        self.assertNotIn("blocked process access", output, output)
        self.assertFalse(home.exists())
        return result, artifacts

    def assert_fixture(self, artifacts):
        settings = artifacts / "fixture/home/.config/noctalia/settings.json"
        backup = artifacts / "settings.backup.json"
        original = (ROOT / "Assets/settings-default.json").read_bytes()
        self.assertEqual(settings.read_bytes(), original)
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(settings.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_geometry_with_absent_home_and_denied_real_settings(self):
        with tempfile.TemporaryDirectory(prefix="setup-isolation-") as temp:
            result, artifacts = self.run_mode(Path(temp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("20 offscreen cases", result.stdout)
            self.assertEqual(
                len(json.loads((artifacts / "geometry.json").read_text())), 20
            )
            self.assert_fixture(artifacts)

    def test_wizard_transitions_preserve_fixture(self):
        with tempfile.TemporaryDirectory(prefix="setup-transitions-") as temp:
            result, artifacts = self.run_mode(Path(temp), ("--wizard-transitions",))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("52 offscreen transition snapshots", result.stdout)
            self.assert_fixture(artifacts)

    def test_lint_without_settings_access(self):
        with tempfile.TemporaryDirectory(prefix="setup-lint-") as temp:
            result, artifacts = self.run_mode(Path(temp), ("lint-harness",))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("SETUP_HARNESS_LINT_WARNINGS 0", result.stdout)
            self.assertFalse(artifacts.exists())

    def test_injected_runtime_warning_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="setup-runtime-warning-") as temp:
            result, artifacts = self.run_mode(Path(temp), warning=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Offscreen component load/runtime failed", result.stderr)
            self.assertIn(
                "missingFixtureValue", (artifacts / "runtime.log").read_text()
            )
            self.assert_fixture(artifacts)

    def test_fixture_mutation_fails_integrity_check(self):
        with tempfile.TemporaryDirectory(prefix="setup-integrity-") as temp:
            result, _ = self.run_mode(Path(temp), mutate=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Fixture settings changed during isolated test", result.stderr
            )


if __name__ == "__main__":
    unittest.main()
