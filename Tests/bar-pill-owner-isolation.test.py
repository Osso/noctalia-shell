#!/usr/bin/env python3
"""Exercise bar-pill public owners under a masked host and read-only private HOME."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "Tests/bar-pill-owner-warnings.test.py"
GUARD = r"""import os
from pathlib import Path
import sys

def reject(path):
    if isinstance(path, (str, bytes, os.PathLike)):
        spelling = os.path.abspath(os.fsdecode(path))
        if spelling.startswith("/home/osso/.config"):
            raise AssertionError("PROTECTED_CONFIG_ATTEMPT " + spelling)

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
sys.addaudithook(audit)
"""


class BarPillOwnerIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = Path(tempfile.mkdtemp(prefix="bar-pill-isolation-proof-"))
        print("PROOF", cls.proof, flush=True)

    def run_case(self, runner, arguments, shadow=False, harness_source=None):
        with tempfile.TemporaryDirectory(prefix="bar-pill-isolation-") as temporary:
            directory = Path(temporary)
            directory.chmod(0o700)
            home = directory / "readonly-home"
            home.mkdir(mode=0o700)
            guard = directory / "guard"
            guard.mkdir()
            (guard / "sitecustomize.py").write_text(GUARD)
            script = ROOT / "Tests" / runner
            if shadow:
                script = directory / "shadow-owner.py"
                source = OWNER.read_text().replace(
                    "ROOT = Path(__file__).resolve().parents[1]",
                    f"ROOT = Path({str(ROOT)!r})",
                )
                source = source.replace(
                    "    helper = load_helper()",
                    """    import socket
    assert not Path("/dev/snd").exists(), "host audio devices exposed"
    assert list(Path("/run").iterdir()) == [], "host runtime sockets exposed"
    assert not any(key in os.environ for key in (
        "DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "PULSE_SERVER"
    )), "host desktop environment exposed"
    try:
        socket.create_connection(("203.0.113.1", 9), timeout=1)
    except OSError as error:
        assert error.errno == errno.ENETUNREACH, error
    else:
        raise AssertionError("network accessible")
    print("AUDIO_NETWORK_DESKTOP_DENIED")
    helper = load_helper()""",
                    1,
                )
                script.write_text(source)
            if harness_source is not None:
                harness = directory / "supplied.qml"
                harness.write_text(harness_source)
                arguments = [*arguments, "--harness", str(harness)]
            command = [
                "bwrap",
                "--die-with-parent",
                "--unshare-all",
                "--new-session",
                "--ro-bind",
                "/",
                "/",
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
                "--ro-bind",
                str(home),
                "/tmp/noctalia-home",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--chdir",
                temporary,
                "--",
                "/usr/bin/strace",
                "-f",
                "-e",
                "trace=%file,connect",
                "-o",
                str(directory / "trace.log"),
                sys.executable,
                str(script),
                *arguments,
            ]
            result = subprocess.run(
                command,
                env={
                    "PATH": "/usr/bin",
                    "LANG": "C.UTF-8",
                    "HOME": "/tmp/noctalia-home",
                    "TMPDIR": temporary,
                    "PYTHONPATH": str(guard),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            output = result.stdout + result.stderr
            print(
                "CASE", runner, arguments, "SHADOW", shadow, "EXIT", result.returncode
            )
            print(output, end="", flush=True)
            trace = (directory / "trace.log").read_text()
            (self.proof / (self._testMethodName + ".trace")).write_text(trace)
            (self.proof / (self._testMethodName + ".log")).write_text(output)
            attempts = [
                line
                for line in trace.splitlines()
                if "/home/osso/.config" in line or "/tmp/noctalia-home/.config" in line
            ]
            self.assertEqual(attempts, [], "protected config/metadata attempts")
            print("PROTECTED_CONFIG_METADATA_ATTEMPTS", len(attempts), flush=True)
            self.assertEqual(list(home.iterdir()), [])
            self.assertEqual(list(directory.glob("noctalia-bar-pill-*")), [])
            self.assertNotIn("PROTECTED_CONFIG_ATTEMPT", output)
            return result.returncode, output

    def assert_pass(self, runner, arguments, marker, shadow=False):
        code, output = self.run_case(runner, arguments, shadow)
        self.assertEqual(code, 0, output)
        self.assertIn(marker, output)
        self.assertIn("BAR_PILL_HOST_MASKED", output)
        return output

    def test_primary_private_home(self):
        self.assert_pass(
            "bar-pill-warnings.test.py", ["behavior"], "11 passed, 0 failed"
        )

    def test_horizontal_private_home(self):
        self.assert_pass(
            "bar-pill-horizontal-warnings.test.py", ["behavior"], "14 passed, 0 failed"
        )

    def test_vertical_private_home(self):
        self.assert_pass(
            "bar-pill-vertical-warnings.test.py", ["behavior"], "9 passed, 0 failed"
        )

    def test_shadow_owner_script_survives_private_tmp(self):
        output = self.assert_pass(
            OWNER.name, ["runtime"], "3 passed, 0 failed", shadow=True
        )
        self.assertIn("AUDIO_NETWORK_DESKTOP_DENIED", output)

    def test_negative_owner_control(self):
        code, output = self.run_case(OWNER.name, ["runtime", "--mutation"])
        self.assertNotEqual(code, 0, output)
        self.assertIn("FAIL!", output)
        self.assertIn("BAR_PILL_HOST_MASKED", output)
        self.assertNotIn("BAR_PILL_OWNER_RUNTIME_PASS", output)

    def test_parent_and_qt_child_home_denial(self):
        harness = r"""import QtQuick
import QtTest
Item {
    Image {
        id: probe
        source: "file:///home/bar-pill-isolation-probe"
    }
    TestCase {
        name: "HomeDenial"
        when: windowShown
        function test_denied() {
            tryCompare(probe, "status", Image.Error);
            console.log("QT_CHILD_HOME_DENIED");
        }
    }
}
"""
        code, output = self.run_case(OWNER.name, ["runtime"], harness_source=harness)
        self.assertEqual(code, 0, output)
        trace = (self.proof / (self._testMethodName + ".trace")).read_text()
        self.assertTrue(
            any(
                '"/home/bar-pill-isolation-probe"' in line
                and "EACCES" in line
                and "openat(" in line
                for line in trace.splitlines()
            ),
            trace,
        )
        self.assertIn(
            "CONFIG_ACCESS_DENIED /home/bar-pill-isolation-probe EACCES", output
        )
        self.assertIn("QT_CHILD_HOME_DENIED", output)
        self.assertIn("3 passed, 0 failed", output)

    def test_strict_fixture_warning_rejected(self):
        harness = (
            (ROOT / "Tests/Qml/BarPillOwnerHarness.qml")
            .read_text()
            .replace(
                "id: scene",
                "id: scene\n    property int lintProbe: scene.missingLintProbe",
                1,
            )
        )
        code, output = self.run_case(
            OWNER.name, ["lint-harness"], harness_source=harness
        )
        self.assertNotEqual(code, 0, output)
        self.assertIn("missingLintProbe", output)
        results = [
            json.loads(line) for line in output.splitlines() if line.startswith("{")
        ]
        self.assertFalse(results[0]["files"][0]["success"], output)
        self.assertEqual(len(results[0]["files"][0]["warnings"]), 1, output)

    def test_strict_fixture_lint(self):
        output = self.assert_pass(
            OWNER.name, ["lint-harness"], "BAR_PILL_FIXTURE_LINT_PASS"
        )
        results = [
            json.loads(line) for line in output.splitlines() if line.startswith("{")
        ]
        self.assertEqual(len(results), 1, output)
        self.assertTrue(results[0]["files"][0]["success"], output)
        self.assertEqual(results[0]["files"][0]["warnings"], [], output)


if __name__ == "__main__":
    unittest.main()
