"""Exercise overview CLI isolation inside the static checker's outer sandbox."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "Tests/overview-warnings.test.py"


class OverviewIsolationTest(unittest.TestCase):
    def run_case(self, arguments, staged_home=False):
        with tempfile.TemporaryDirectory(prefix="overview-isolation-") as temporary:
            directory = Path(temporary)
            staged = directory / "staged-home"
            staged.mkdir(mode=0o700)
            if staged_home:
                settings = staged / ".config/noctalia/settings.json"
                settings.parent.mkdir(parents=True)
                settings.write_bytes(b"synthetic settings must never be read")
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-net",
                "--ro-bind",
                "/",
                "/",
                "--tmpfs",
                "/home",
                "--dir",
                "/home/osso",
                "--dir",
                "/home/osso/.config",
                "--tmpfs",
                "/tmp",
                "--bind",
                str(ROOT),
                str(ROOT),
                "--bind",
                temporary,
                temporary,
                "--ro-bind",
                str(staged),
                "/tmp/noctalia-home",
                "--dev",
                "/dev",
                "--proc",
                "/proc",
                "--",
                sys.executable,
                str(RUNNER),
                *arguments,
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=dict(
                    os.environ,
                    HOME="/tmp/noctalia-home",
                    TMPDIR=temporary,
                    PYTHONDONTWRITEBYTECODE="1",
                ),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(list(directory.glob("noctalia-overview-*")), [])
            if staged_home:
                self.assertEqual(
                    settings.read_bytes(), b"synthetic settings must never be read"
                )
            else:
                self.assertEqual(list(staged.iterdir()), [])
            output = result.stdout + result.stderr
            print("CASE", arguments, "EXIT", result.returncode, output, flush=True)
            return result.returncode, output

    def assert_denial(self, output):
        for path in (
            "/home/osso/.config/noctalia/settings.json",
            "/tmp/noctalia-home/.config/noctalia/settings.json",
        ):
            self.assertIn("CONFIG_ACCESS_DENIED " + path, output)
        self.assertNotIn("Read-only file system", output)

    def assert_pass(self, arguments, marker, staged_home=False):
        code, output = self.run_case(arguments, staged_home)
        self.assertEqual(code, 0, output)
        self.assertIn(marker, output)
        self.assert_denial(output)

    def test_strict_lint_absent_config(self):
        self.assert_pass(
            ["lint-harness", "--max-warnings", "0"],
            "OVERVIEW_HARNESS_LINT_WARNINGS 0 EXIT 0",
        )

    def test_strict_lint_readonly_staged_config(self):
        self.assert_pass(
            ["lint-harness", "--max-warnings", "0"],
            "OVERVIEW_HARNESS_LINT_WARNINGS 0 EXIT 0",
            staged_home=True,
        )

    def test_warning_rejected(self):
        code, output = self.run_case(
            ["lint-harness", "--max-warnings", "0", "--inject-warning"]
        )
        self.assertNotEqual(code, 0, output)
        self.assertIn("OVERVIEW_HARNESS_LINT_WARNINGS 1 EXIT", output)
        self.assertIn("missingLintProbe", output)
        self.assert_denial(output)

    def test_private_runtime(self):
        self.assert_pass(["runtime"], "5 passed, 0 failed")

    def test_cover_mutation_detected(self):
        self.assert_pass(
            ["runtime", "--mutation", "cover"], "OVERVIEW_NEGATIVE_DETECTED cover"
        )

    def test_visibility_mutation_detected(self):
        self.assert_pass(
            ["runtime", "--mutation", "visibility"],
            "OVERVIEW_NEGATIVE_DETECTED visibility",
        )

    def test_geometry_mutation_detected(self):
        self.assert_pass(
            ["runtime", "--mutation", "geometry"],
            "OVERVIEW_NEGATIVE_DETECTED geometry",
        )


if __name__ == "__main__":
    unittest.main()
