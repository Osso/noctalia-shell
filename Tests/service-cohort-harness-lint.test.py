#!/usr/bin/env python3
"""Service cohort fixture lint acceptance and real diagnostic rejection."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "Tests/service-cohort-warnings.test.py"


class ServiceCohortHarnessLintTest(unittest.TestCase):
    def test_lint_harness_dispatch_accepts_runtime_fixtures(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "lint-harness"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["files"])
        for file in report["files"]:
            self.assertEqual(file["warnings"], [], file)

    def test_injected_warning_is_reported_and_rejected(self):
        with tempfile.TemporaryDirectory(
            prefix="noctalia-cohort-injection-"
        ) as temporary:
            directory = Path(temporary)
            tests = directory / "Tests"
            (tests / "Qml").mkdir(parents=True)
            for name in (
                RUNNER.name,
                "workspace-runtime.test.py",
                "qml_fixture_lint.py",
            ):
                shutil.copyfile(ROOT / "Tests" / name, tests / name)
            (directory / "Services").symlink_to(
                ROOT / "Services", target_is_directory=True
            )
            harness = tests / "Qml/ServiceCohortHarness.qml"
            source = (ROOT / "Tests/Qml/ServiceCohortHarness.qml").read_text()
            harness.write_text(
                source.replace(
                    "id: testCase",
                    "id: testCase\n  property int injectedWarning: testCase.missingLintProbe",
                    1,
                )
            )
            result = subprocess.run(
                [sys.executable, str(tests / RUNNER.name), "lint-harness"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=directory,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            diagnostics = json.loads(result.stdout)["files"][0]["warnings"]
            self.assertTrue(
                any(
                    warning["type"] == "warning"
                    and warning["id"] == "missing-property"
                    and "missingLintProbe" in warning["message"]
                    for warning in diagnostics
                ),
                diagnostics,
            )


if __name__ == "__main__":
    unittest.main()
