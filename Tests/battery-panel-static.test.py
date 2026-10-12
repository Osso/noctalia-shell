"""BatteryPanel CLI regression: fixture lint must not touch runtime state."""

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

real_config = Path(sys.argv.pop(1))

def deny_runtime_access(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0]))
        if path.name == "settings.json" or path.is_relative_to(real_config):
            raise PermissionError(f"blocked settings access: {path}")
    if event == "subprocess.Popen":
        if Path(args[0]).name != "qmllint":
            raise PermissionError(f"blocked live process/registry access: {args[0]}")

sys.addaudithook(deny_runtime_access)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


class BatteryPanelStaticTest(unittest.TestCase):
    def run_lint(self, root, mode="lint-harness", blocked=True, inject_warning=False):
        for relative in (
            "Tests/battery-panel-warnings.test.py",
            "Tests/battery-widget-warnings.test.py",
            "Tests/process-panel-warnings.test.py",
            "Tests/about-tab-warnings.test.py",
            "Tests/qml_fixture_lint.py",
            "Tests/Qml/BatteryPanelWarningsHarness.qml",
            "Tests/Qml/ProcessPanelWarningsHarness.qml",
            "Modules/Panels/Battery/BatteryPanel.qml",
            "Modules/Panels/Process/ProcessPanel.qml",
            "Services/Hardware/BatteryService.qml",
            "Widgets/NText.qml",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        if inject_warning:
            harness = root / "Tests/Qml/BatteryPanelWarningsHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "id: suite",
                    "id: suite\n  property int regressionWarning: suite.missingFixtureValue",
                    1,
                )
            )
        home = root / "home"
        home.mkdir(mode=0o700)
        settings = home / ".config/noctalia/settings.json"
        self.assertFalse(settings.exists())
        artifacts = root / "artifacts"
        script = str(root / "Tests/battery-panel-warnings.test.py")
        command = [sys.executable]
        if blocked:
            command.extend(["-c", BOOTSTRAP, "/home/osso/.config"])
        command.extend([script, mode, "--artifacts", str(artifacts)])
        result = subprocess.run(
            command,
            cwd=root,
            env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config")),
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = result.stdout + result.stderr
        self.assertNotIn("blocked settings access", output, output)
        self.assertNotIn("blocked live process/registry access", output, output)
        self.assertFalse((artifacts / "settings.backup.json").exists())
        self.assertFalse(settings.exists())
        reports = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith('{"files":')
        ]
        self.assertEqual(
            len(reports), 2 if mode == "lint-harness-regression" else 1, output
        )
        for report in reports:
            self.assertEqual(len(report["files"]), 1, output)
        return result, [report["files"][0] for report in reports]

    def test_static_lint_with_absent_settings(self):
        for blocked in (False, True):
            with (
                self.subTest(blocked=blocked),
                tempfile.TemporaryDirectory(prefix="battery-panel-static-") as temp,
            ):
                result, files = self.run_lint(Path(temp), blocked=blocked)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(files[0]["warnings"], [])

    def test_injected_warning_fails_without_runtime_access(self):
        with tempfile.TemporaryDirectory(
            prefix="battery-panel-static-warning-"
        ) as temp:
            result, files = self.run_lint(Path(temp), inject_warning=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(
                any(
                    warning["id"] == "missing-property"
                    and "missingFixtureValue" in warning["message"]
                    for warning in files[0]["warnings"]
                ),
                files,
            )

    def test_warning_regression_mode_without_runtime_access(self):
        with tempfile.TemporaryDirectory(
            prefix="battery-panel-static-regression-"
        ) as temp:
            result, files = self.run_lint(Path(temp), mode="lint-harness-regression")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(files[0]["warnings"], [])
            self.assertTrue(
                any(
                    warning["id"] == "missing-property"
                    and "missingLintProbe" in warning["message"]
                    for warning in files[1]["warnings"]
                ),
                files,
            )
            self.assertIn("BATTERY_PANEL_HARNESS_WARNING_REJECTED", result.stdout)


if __name__ == "__main__":
    unittest.main()
