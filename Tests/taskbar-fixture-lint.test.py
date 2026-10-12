#!/usr/bin/env python3
"""Real CLI lint against Taskbar's runtime fixtures, including warning failure."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path("Tests/taskbar-warnings.test.py")
HARNESS = Path("Tests/Qml/TaskbarHarness.qml")


class TaskbarFixtureLintTest(unittest.TestCase):
    def run_lint(self, warning=False):
        with tempfile.TemporaryDirectory(prefix="noctalia-taskbar-lint-test-") as temp:
            root = Path(temp)
            for directory in ("Assets", "Modules", "Services", "Widgets"):
                (root / directory).symlink_to(
                    ROOT / directory, target_is_directory=True
                )
            tests = root / "Tests"
            (tests / "Qml").mkdir(parents=True)
            for name in (
                "taskbar-warnings.test.py",
                "taskbar-grouped-warnings.test.py",
                "workspace-runtime.test.py",
                "media-mini-warnings.test.py",
                "qml_fixture_lint.py",
            ):
                shutil.copy2(ROOT / "Tests" / name, tests / name)
            for name in (
                "TaskbarHarness.qml",
                "TaskbarGroupedHarness.qml",
                "WorkspaceHarness.qml",
            ):
                shutil.copy2(ROOT / "Tests/Qml" / name, tests / "Qml" / name)
            if warning:
                harness = root / HARNESS
                harness.write_text(
                    harness.read_text().replace(
                        "Item {",
                        "Item {\n  property int regressionWarning: Qt.application.missingFixtureValue",
                        1,
                    )
                )
            result = subprocess.run(
                ["python3", str(root / RUNNER), "lint-harness"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=90,
            )
            print(result.stdout + result.stderr, end="")
            return result

    def diagnostics(self, result):
        files = json.loads(result.stdout)["files"]
        self.assertEqual(len(files), 1, result.stdout)
        self.assertEqual(Path(files[0]["filename"]).name, "tst_taskbar.qml")
        return files[0]["warnings"]

    def test_runtime_fixture_lints_without_warnings(self):
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.diagnostics(result), [])

    def test_injected_warning_fails_cli(self):
        result = self.run_lint(warning=True)
        self.assertNotEqual(result.returncode, 0)
        warnings = self.diagnostics(result)
        self.assertEqual([warning["id"] for warning in warnings], ["missing-property"])
        self.assertIn("missingFixtureValue", warnings[0]["message"])


if __name__ == "__main__":
    unittest.main()
