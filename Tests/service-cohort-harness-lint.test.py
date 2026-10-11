#!/usr/bin/env python3
"""Service cohort fixture lint acceptance and real diagnostic rejection."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from qml_fixture_lint import check_harness

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
        spec = importlib.util.spec_from_file_location("service_cohort", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory(
            prefix="noctalia-cohort-injection-"
        ) as temporary:
            directory = Path(temporary)
            runner.stage_runtime(directory)
            harness = directory / "tst_services.qml"
            source = harness.read_text()
            harness.write_text(
                source.replace(
                    "id: testCase",
                    "id: testCase\n  property int injectedWarning: testCase.missingLintProbe",
                    1,
                )
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = check_harness(directory, harness)
            self.assertNotEqual(status, 0, output.getvalue())
            diagnostics = json.loads(output.getvalue())["files"][0]["warnings"]
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
