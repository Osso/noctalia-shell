"""Exercise loader CLI isolation inside the static checker's outer sandbox."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "Tests/control-center-widget-loader-warnings.test.py"


class LoaderIsolationTest(unittest.TestCase):
    def run_case(self, arguments, staged_home=False):
        with tempfile.TemporaryDirectory(prefix="loader-isolation-") as temporary:
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
            self.assertEqual(list(directory.glob("noctalia-loader-proof-*")), [])
            if staged_home:
                self.assertEqual(
                    settings.read_bytes(), b"synthetic settings must never be read"
                )
            else:
                self.assertEqual(list(staged.iterdir()), [])
            output = result.stdout + result.stderr
            print("CASE", arguments, "EXIT", result.returncode, output, flush=True)
            return result.returncode, output

    def assert_pass(self, arguments, marker, staged_home=False):
        code, output = self.run_case(arguments, staged_home)
        self.assertEqual(code, 0, output)
        self.assertIn(marker, output)
        self.assertIn("CONFIG_AUDIT_PASS", output)
        self.assertNotIn("Read-only file system", output)

    def test_strict_lint_absent_config(self):
        self.assert_pass(
            ["lint-harness", "--max-warnings", "0"],
            "LOADER_HARNESS_LINT_WARNINGS 0 EXIT 0",
        )

    def test_strict_lint_readonly_staged_config(self):
        self.assert_pass(
            ["lint-harness", "--max-warnings", "0"],
            "LOADER_HARNESS_LINT_WARNINGS 0 EXIT 0",
            staged_home=True,
        )

    def test_warning_rejected(self):
        code, output = self.run_case(
            ["lint-harness", "--max-warnings", "0", "--inject-warning"]
        )
        self.assertNotEqual(code, 0, output)
        self.assertIn("LOADER_HARNESS_LINT_WARNINGS 1 EXIT", output)
        self.assertIn("CONFIG_AUDIT_PASS", output)

    def test_normal_runtime(self):
        self.assert_pass(["runtime"], "8 passed, 0 failed")

    def test_owner_runtime(self):
        self.assert_pass(["runtime", "--owner-shadow"], "8 passed, 0 failed")

    def test_production_lint(self):
        self.assert_pass(["lint"], "LOADER_WARNINGS 2 {'missing-property': 2}")

    def test_bar_normal_runtime(self):
        self.assert_pass(["runtime", "--bar"], "8 passed, 0 failed")

    def test_bar_owner_runtime(self):
        self.assert_pass(["runtime", "--bar", "--owner-shadow"], "8 passed, 0 failed")

    def test_bar_strict_harness_lint(self):
        self.assert_pass(
            ["lint-harness", "--bar"], "LOADER_HARNESS_LINT_WARNINGS 0 EXIT 0"
        )

    def test_bar_production_lint(self):
        self.assert_pass(["lint", "--bar"], "LOADER_WARNINGS 3 {'missing-property': 3}")

    def test_owner_and_order_mutations_rejected(self):
        for loader in ([], ["--bar"]):
            for mutation in (["--owner-shadow", "--mutation"], ["--callback-first"]):
                with self.subTest(loader=loader, mutation=mutation):
                    code, output = self.run_case(["runtime", *loader, *mutation])
                    self.assertNotEqual(code, 0, output)
                    self.assertIn("FAIL!", output)
                    self.assertIn("CONFIG_AUDIT_PASS", output)

    def test_optional_member_mutations_rejected(self):
        for loader, members in (
            ([], ("screen", "onLoaded")),
            (["--bar"], ("screen", "scaling", "onLoaded")),
        ):
            for member in members:
                with self.subTest(loader=loader, member=member):
                    code, output = self.run_case(
                        ["runtime", *loader, "--required-member", member]
                    )
                    self.assertNotEqual(code, 0, output)
                    expected = (
                        "TypeError"
                        if member == "onLoaded"
                        else f'Cannot assign to non-existent property "{member}"'
                    )
                    self.assertIn(expected, output)
                    self.assertIn("CONFIG_AUDIT_PASS", output)


class SettingsAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("loader_runner", RUNNER)
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def test_zero_attempts_safe(self):
        self.runner.audit_config_access("", "/tmp/noctalia-home/.config")

    def test_denied_attempts_safe(self):
        trace = '42 openat(AT_FDCWD, "/home/osso/.config/noctalia/settings.json", O_RDONLY) = -1 EACCES (Permission denied)'
        self.runner.audit_config_access(trace, "/tmp/noctalia-home/.config")

    def test_successful_attempt_rejected(self):
        for path in (
            "/home/osso/.config/noctalia/settings.json",
            "/tmp/noctalia-home/.config/noctalia/settings.json",
        ):
            for call in ("open", "openat", "openat2"):
                with self.subTest(path=path, call=call):
                    trace = f'42 {call}(AT_FDCWD, "{path}", O_RDONLY) = 3'
                    with self.assertRaises(AssertionError):
                        self.runner.audit_config_access(
                            trace, "/tmp/noctalia-home/.config"
                        )


if __name__ == "__main__":
    unittest.main()
