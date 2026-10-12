#!/usr/bin/env python3
"""Simple-service runtime fixture lint and fail-closed diagnostic regression."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "Tests/simple-service-warnings.test.py"


class SimpleServiceHarnessLintTest(unittest.TestCase):
    def run_lint(self, runner):
        return subprocess.run(
            [sys.executable, str(runner), "lint-harness"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=runner.parents[1],
        )

    def test_runtime_staged_harness_has_zero_warnings(self):
        result = self.run_lint(RUNNER)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        files = json.loads(result.stdout)["files"]
        self.assertEqual(len(files), 1, files)
        self.assertTrue(files[0]["success"], files)
        self.assertEqual(files[0]["warnings"], [], files)

    def test_injected_warning_is_reported_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-simple-injection-") as temp:
            directory = Path(temp)
            tests = directory / "Tests"
            (tests / "Qml").mkdir(parents=True)
            for name in (
                RUNNER.name,
                "workspace-runtime.test.py",
                "qml_fixture_lint.py",
            ):
                shutil.copyfile(ROOT / "Tests" / name, tests / name)
            for name in ("Services", "Assets"):
                (directory / name).symlink_to(ROOT / name, target_is_directory=True)
            source = (ROOT / "Tests/Qml/SimpleServiceHarness.qml").read_text()
            harness = tests / "Qml/SimpleServiceHarness.qml"
            harness.write_text(
                source.replace(
                    "TestCase {",
                    "TestCase {\n  property int injectedWarning: Settings.missingLintProbe",
                    1,
                )
            )
            result = self.run_lint(tests / RUNNER.name)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            warnings = json.loads(result.stdout)["files"][0]["warnings"]
            self.assertTrue(
                any(
                    warning["type"] == "warning"
                    and warning["id"] == "missing-property"
                    and "missingLintProbe" in warning["message"]
                    for warning in warnings
                ),
                warnings,
            )


if __name__ == "__main__":
    unittest.main()
