#!/usr/bin/env python3
"""Exact owner CLI diagnostic fidelity with masked host config and inert fixtures."""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OWNER = "ipc-idle-services-warnings.test.py"
HARNESS = "IpcIdleServicesHarness.qml"


class IpcIdleServicesHarnessLintTest(unittest.TestCase):
    def run_owner(self, injection="", max_warnings=0):
        with tempfile.TemporaryDirectory(prefix="noctalia-ipc-lint-") as temporary:
            root = Path(temporary)
            tests = root / "Tests"
            (tests / "Qml").mkdir(parents=True)
            for name in (OWNER, "workspace-runtime.test.py"):
                shutil.copyfile(ROOT / "Tests" / name, tests / name)
            for target in (
                "Services/Control/IPCService.qml",
                "Services/Power/IdleInhibitorService.qml",
            ):
                destination = root / target
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / target, destination)
            source = (ROOT / "Tests/Qml" / HARNESS).read_text()
            (tests / "Qml" / HARNESS).write_text(
                source.replace("id: testCase", "id: testCase\n" + injection, 1)
            )
            environment = {"PATH": os.environ["PATH"]}
            for key in (
                "HOME",
                "XDG_CONFIG_HOME",
                "XDG_CACHE_HOME",
                "XDG_DATA_HOME",
                "XDG_STATE_HOME",
                "XDG_RUNTIME_DIR",
            ):
                path = root / key
                path.mkdir(mode=0o700)
                environment[key] = str(path)
            artifacts = root / "artifacts"
            result = subprocess.run(
                [
                    "bwrap",
                    "--die-with-parent",
                    "--unshare-all",
                    "--ro-bind",
                    "/",
                    "/",
                    "--tmpfs",
                    "/home",
                    "--tmpfs",
                    "/syncthing",
                    "--tmpfs",
                    "/run",
                    "--tmpfs",
                    "/tmp",
                    "--bind",
                    str(root),
                    str(root),
                    "--dev",
                    "/dev",
                    "--proc",
                    "/proc",
                    "--chdir",
                    str(root),
                    "--",
                    sys.executable,
                    str(tests / OWNER),
                    "lint-harness",
                    "--max-warnings",
                    str(max_warnings),
                    "--artifacts",
                    str(artifacts),
                ],
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            output = result.stdout + result.stderr
            print(
                f"OWNER_CLI injection={injection!r} max_warnings={max_warnings} exit={result.returncode}"
            )
            print(output, end="")
            self.assertTrue((artifacts / "harness.lint.log").exists(), output)
            log = (artifacts / "harness.lint.log").read_text()
            self.assertTrue(result.stdout.startswith(log), output)
            return result, output

    def assert_counts(self, output, expected):
        summary = next(
            line
            for line in output.splitlines()
            if line.startswith("HARNESS_LINT_COUNTS ")
        )
        counts, total = summary.removeprefix("HARNESS_LINT_COUNTS ").rsplit(
            " TOTAL ", 1
        )
        self.assertEqual(ast.literal_eval(counts), expected, output)
        self.assertEqual(int(total), sum(expected.values()), output)

    def test_zero_warning_baseline(self):
        result, output = self.run_owner()
        self.assertEqual(result.returncode, 0, output)
        self.assert_counts(output, {})

    def test_semantic_missing_property_is_visible_and_rejected(self):
        result, output = self.run_owner(
            "property int injectedWarning: testCase.missingLintProbe"
        )
        self.assertIn("missingLintProbe", output)
        self.assertIn("missing-property", output)
        self.assertNotEqual(result.returncode, 0, output)
        self.assert_counts(output, {"missing-property": 1})

    def test_semantic_warning_is_counted_once_at_allowed_limit(self):
        result, output = self.run_owner(
            "property int injectedWarning: testCase.missingLintProbe", max_warnings=1
        )
        self.assertIn("missingLintProbe", output)
        self.assertIn("missing-property", output)
        self.assertEqual(result.returncode, 0, output)
        self.assert_counts(output, {"missing-property": 1})

    def test_syntax_error_is_visible_and_rejected(self):
        result, output = self.run_owner("property int broken: (")
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("syntax", output.lower())
        self.assertIn("Expected token", output)


if __name__ == "__main__":
    unittest.main()
