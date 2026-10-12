"""Brightness-only CLI regression: static lint must not touch runtime state."""

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


class BrightnessStaticTest(unittest.TestCase):
    def run_lint(self, root, inject_warning=False):
        for relative in (
            "Tests/brightness-panel-warnings.test.py",
            "Tests/about-tab-warnings.test.py",
            "Tests/qml_fixture_lint.py",
            "Tests/Qml/BrightnessPanelWarningsHarness.qml",
            "Modules/Panels/Brightness/BrightnessPanel.qml",
            "Widgets/NValueSlider.qml",
            "Widgets/NSlider.qml",
            "Widgets/NScrollView.qml",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        if inject_warning:
            harness = root / "Tests/Qml/BrightnessPanelWarningsHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "{",
                    "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                    1,
                )
            )
        home = root / "home"
        home.mkdir(mode=0o700)
        self.assertFalse((home / ".config/noctalia/settings.json").exists())
        artifacts = root / "artifacts"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                BOOTSTRAP,
                str(Path.home() / ".config"),
                str(root / "Tests/brightness-panel-warnings.test.py"),
                "lint-harness",
                "--artifacts",
                str(artifacts),
            ],
            cwd=root,
            env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config")),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        self.assertNotIn("blocked settings access", output, output)
        self.assertNotIn("blocked live process/registry access", output, output)
        self.assertFalse((artifacts / "settings.backup.json").exists())
        self.assertFalse((artifacts / "canonical-runtime.txt").exists())
        self.assertFalse((home / ".config/noctalia/settings.json").exists())
        reports = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.startswith('{"files":')
        ]
        self.assertEqual(len(reports), 1, output)
        self.assertEqual(len(reports[0]["files"]), 1, output)
        file = reports[0]["files"][0]
        self.assertEqual(Path(file["filename"]), artifacts / "tst_brightness.qml")
        return result, file

    def test_static_lint_with_absent_settings_and_blocked_runtime_access(self):
        with tempfile.TemporaryDirectory(prefix="brightness-static-") as temp:
            result, file = self.run_lint(Path(temp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(file["warnings"], [])

    def test_injected_warning_fails_without_runtime_access(self):
        with tempfile.TemporaryDirectory(prefix="brightness-static-warning-") as temp:
            result, file = self.run_lint(Path(temp), inject_warning=True)
            self.assertNotEqual(result.returncode, 0)
            warnings = file["warnings"]
            self.assertTrue(
                any(
                    warning["id"] == "missing-property"
                    and "missingFixtureValue" in warning["message"]
                    for warning in warnings
                ),
                warnings,
            )


if __name__ == "__main__":
    unittest.main()
