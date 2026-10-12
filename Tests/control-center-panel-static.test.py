"""Control-center CLI isolation: static and offscreen modes need no host state."""

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

real_config = Path("/home/osso/.config/noctalia")

def deny_runtime_access(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).absolute()
        if path.name == "settings.json" or path.is_relative_to(real_config):
            raise PermissionError(f"blocked settings access: {path}")
    if event == "subprocess.Popen":
        if Path(args[0]).name not in ("qmllint", "qmltestrunner"):
            raise PermissionError(f"blocked live process/registry access: {args[0]}")

sys.addaudithook(deny_runtime_access)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


class ControlCenterIsolationTest(unittest.TestCase):
    def run_mode(self, root, mode, inject_warning=False):
        for relative in (
            "Tests/control-center-panel-warnings.test.py",
            "Tests/about-tab-warnings.test.py",
            "Tests/brightness-panel-warnings.test.py",
            "Tests/qml_fixture_lint.py",
            "Tests/Qml/ControlCenterPanelWarningsHarness.qml",
            "Modules/Panels/ControlCenter/ControlCenterPanel.qml",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        if inject_warning:
            harness = root / "Tests/Qml/ControlCenterPanelWarningsHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "{",
                    "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
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
                str(root / "Tests/control-center-panel-warnings.test.py"),
                mode,
                "--artifacts",
                str(artifacts),
            ],
            cwd=root,
            env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config")),
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = result.stdout + result.stderr
        self.assertNotIn("blocked settings access", output, output)
        self.assertNotIn("blocked live process/registry access", output, output)
        self.assertFalse(settings.exists())
        self.assertFalse((artifacts / "settings.backup.json").exists())
        self.assertFalse((artifacts / "canonical-runtime.txt").exists())
        return result, artifacts

    def lint_report(self, result, artifacts):
        output = result.stdout + result.stderr
        reports = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith('{"files":')
        ]
        self.assertEqual(len(reports), 1, output)
        self.assertEqual(len(reports[0]["files"]), 1, output)
        report = reports[0]["files"][0]
        self.assertEqual(Path(report["filename"]), artifacts / "tst_control_center.qml")
        return report

    def test_static_lint_with_absent_settings_and_denied_real_access(self):
        with tempfile.TemporaryDirectory(prefix="control-center-static-") as temp:
            result, artifacts = self.run_mode(Path(temp), "lint-harness")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.lint_report(result, artifacts)["warnings"], [])
            self.assertFalse((artifacts / "HOME").exists())

    def test_injected_warning_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="control-center-warning-") as temp:
            result, artifacts = self.run_mode(
                Path(temp), "lint-harness", inject_warning=True
            )
            self.assertNotEqual(result.returncode, 0)
            warnings = self.lint_report(result, artifacts)["warnings"]
            self.assertTrue(
                any(
                    warning["id"] == "missing-property"
                    and "missingFixtureValue" in warning["message"]
                    for warning in warnings
                ),
                warnings,
            )

    def test_four_offscreen_cases_use_only_synthetic_settings(self):
        with tempfile.TemporaryDirectory(prefix="control-center-behavior-") as temp:
            result, artifacts = self.run_mode(Path(temp), "behavior")
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            for case in (
                "card_routing_layout_and_owner_heights",
                "reorder_disable_weather_and_reopen",
                "screen_and_position_anchor_bindings",
                "open_close_media_and_vpn_interactions",
            ):
                self.assertIn(
                    f"PASS   : qmltestrunner::ControlCenterPanelWarnings::test_{case}()",
                    output,
                )
            self.assertIn("6 passed, 0 failed", output)
            self.assertTrue((artifacts / "HOME").is_dir())
            self.assertNotRegex(output, r"QWARN|QFATAL|QCRITICAL|Warning:")


if __name__ == "__main__":
    unittest.main()
