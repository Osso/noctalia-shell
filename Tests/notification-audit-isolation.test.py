#!/usr/bin/env python3
"""Notification-only audit, filesystem isolation and warning-gate regressions."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[1]
RUNNER = ROOT / "Tests/notification-warnings.test.py"
PROTECTED = "/home/osso/.config/noctalia/settings.json"
OUTER_GUARD = """import os
from pathlib import Path
import sys

PROTECTED = "/home/osso/.config/noctalia/settings.json"
def reject(path):
    if isinstance(path, (str, bytes, os.PathLike)):
        spelling = "/" + os.path.abspath(os.fsdecode(path)).lstrip("/")
        if spelling == PROTECTED:
            raise AssertionError("OUTER_PROTECTED_METADATA: " + spelling)

original_resolve = Path.resolve
def resolve(path, *args, **kwargs):
    reject(path)
    return original_resolve(path, *args, **kwargs)
Path.resolve = resolve

for name in ("stat", "lstat", "readlink"):
    original = getattr(os, name)
    def guarded(path, *args, _original=original, **kwargs):
        reject(path)
        return _original(path, *args, **kwargs)
    setattr(os, name, guarded)

def audit(event, args):
    if event == "open" and args:
        reject(args[0])
    if event == "socket.connect":
        raise PermissionError("OUTER_NETWORK_DENIED")
sys.addaudithook(audit)
"""
LOAD_RUNNER = f"""import importlib.util
from pathlib import Path
import os
import sys
sys.path.insert(0, {str(ROOT / "Tests")!r})
spec = importlib.util.spec_from_file_location("notification_runner", {str(RUNNER)!r})
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
"""


class NotificationAuditIsolationTest(unittest.TestCase):
    def run_case(self, arguments=None, probe=None, public_entrypoint=False):
        with tempfile.TemporaryDirectory(prefix="notification-audit-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            (directory / "sitecustomize.py").write_text(OUTER_GUARD)
            (directory / "harmless_probe.py").write_text("VALUE = 42\n")
            (directory / "settings-alias").symlink_to(PROTECTED)
            environment = {
                "PATH": "/usr/bin",
                "LANG": "C.UTF-8",
                "HOME": temporary,
                "TMPDIR": temporary,
                "PYTHONPATH": temporary,
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-all",
                "--ro-bind",
                "/",
                "/",
                "--perms",
                "000",
                "--tmpfs",
                "/home",
                "--tmpfs",
                "/syncthing",
                "--ro-bind",
                str(ROOT),
                str(ROOT),
                "--tmpfs",
                "/run",
                "--tmpfs",
                "/tmp",
                "--bind",
                temporary,
                temporary,
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                sys.executable,
            ]
            if probe is not None:
                command += ["-c", LOAD_RUNNER + probe]
            else:
                command += [str(RUNNER), *arguments]
                if not public_entrypoint:
                    command += ["--sandbox", temporary]
            result = subprocess.run(
                command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
            print("CASE", arguments or "audit probe", "EXIT", result.returncode)
            print(output, end="", flush=True)
            self.assertEqual(list(directory.glob("noctalia-notification-*")), [])
            return result.returncode, output

    def test_harmless_import_never_resolves_protected_settings(self):
        code, output = self.run_case(
            probe="""sys.addaudithook(runner.deny_real_settings)
import harmless_probe
assert harmless_probe.VALUE == 42
print("HARMLESS_IMPORT_PASS")
"""
        )
        self.assertEqual(code, 0, output)
        self.assertIn("HARMLESS_IMPORT_PASS", output)

    def test_lexical_denial_precedes_metadata_and_keeps_network_denied(self):
        code, output = self.run_case(
            probe="""runner.install_settings_guard()
protected = "/home/osso/.config/noctalia/settings.json"
spellings = [protected, "/home/osso/.config/noctalia/../noctalia/settings.json",
             "//home/osso/.config/noctalia/settings.json", os.fsencode(protected)]
os.chdir("/usr")
spellings.append("../home/osso/.config/noctalia/settings.json")
for spelling in spellings:
    runner.deny_real_settings("open", ("/usr/lib/python3.14/os.py", "r", 0))
    operations = [lambda: runner.deny_real_settings("open", (spelling, "r", 0)),
                  lambda: Path(os.fsdecode(spelling)).resolve(),
                  lambda: os.stat(spelling), lambda: os.lstat(spelling),
                  lambda: os.readlink(spelling)]
    for operation in operations:
        try:
            operation()
        except PermissionError as error:
            assert "real settings access denied" in str(error), str(error)
        else:
            raise AssertionError("protected operation accepted")
try:
    runner.deny_real_settings("socket.connect", (None, ("127.0.0.1", 9)))
except PermissionError as error:
    assert "network access denied" in str(error)
else:
    raise AssertionError("network accepted")
print("LEXICAL_DENIAL_PASS 25 operations; NETWORK_DENIED")
"""
        )
        self.assertEqual(code, 0, output)
        self.assertIn("LEXICAL_DENIAL_PASS", output)

    def test_alias_cannot_cross_host_home_mask(self):
        code, output = self.run_case(
            probe="""runner.install_settings_guard()
alias = Path(os.environ["TMPDIR"]) / "settings-alias"
try:
    alias.read_bytes()
except PermissionError:
    print("MASKED_ALIAS_DENIED")
else:
    raise AssertionError("host settings alias accessible")
"""
        )
        self.assertEqual(code, 0, output)
        self.assertIn("MASKED_ALIAS_DENIED", output)

    def assert_runner_pass(self, mode, marker=None):
        code, output = self.run_case([mode, "--max-warnings", "0"])
        self.assertEqual(code, 0, output)
        self.assertIn("NOTIFICATION_REAL_SETTINGS_AUDIT_DENIED", output)
        self.assertIn("NOTIFICATION_HOST_CONFIG_MASKED", output)
        if marker:
            self.assertIn(marker, output)
        self.assertNotIn("OUTER_PROTECTED_METADATA", output)
        return output

    def lint_results(self, output):
        return [
            file
            for line in output.splitlines()
            if line.startswith("{")
            for file in json.loads(line)["files"]
        ]

    def assert_clean_lint(self, output):
        results = self.lint_results(output)
        self.assertEqual(len(results), 1, output)
        self.assertTrue(results[0]["success"], output)
        self.assertEqual(results[0]["warnings"], [], output)

    def test_strict_harness_zero_warnings(self):
        self.assert_clean_lint(self.assert_runner_pass("lint-harness"))

    def test_injected_warning_is_visible_and_rejected(self):
        output = self.assert_runner_pass(
            "lint-harness-regression", "NOTIFICATION_HARNESS_WARNING_REJECTED"
        )
        results = self.lint_results(output)
        self.assertEqual(len(results), 2, output)
        self.assertTrue(results[0]["success"], output)
        self.assertEqual(results[0]["warnings"], [], output)
        self.assertFalse(results[1]["success"], output)
        self.assertEqual(len(results[1]["warnings"]), 1, output)
        warning = results[1]["warnings"][0]
        self.assertEqual(warning["id"], "missing-property")
        self.assertIn("missingLintProbe", warning["message"])

    def test_isolated_notification_behavior(self):
        self.assert_runner_pass("behavior", "NOTIFICATION_BEHAVIOR_PASS")

    def test_public_entrypoint_creates_host_mask(self):
        code, output = self.run_case(
            ["lint-harness", "--max-warnings", "0"], public_entrypoint=True
        )
        self.assertEqual(code, 0, output)
        self.assertIn("NOTIFICATION_HOST_CONFIG_MASKED", output)
        self.assert_clean_lint(output)


if __name__ == "__main__":
    unittest.main()
