#!/usr/bin/env python3
"""Three parent CLIs deny host config before staging or child execution."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = "--probe" in sys.argv
if PROBE:
    sys.argv.remove("--probe")
CASES = (
    ("weather-card-effects.test.py", (), "WEATHER_EFFECTS_PASS"),
    ("wifi-networks-list-warnings.test.py", ("behavior",), "WIFI_LIST_BEHAVIOR_PASS"),
    ("workspace-runtime.test.py", (), "0 failed"),
)
BOOTSTRAP = """
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
root = Path(sys.argv.pop(1))
mode = sys.argv.pop(1)
script = sys.argv[1]
sys.path.insert(0, str(Path(script).parent))

def deny(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    name = os.path.abspath(os.fsdecode(path))
    if name == '/home/osso/.config' or name.startswith('/home/osso/.config/') or (
        name.endswith('/settings.json') and not name.startswith(str(root) + '/noctalia-')
    ):
        raise RuntimeError(f'blocked settings access: {name}')

def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir'):
        deny(args[0])
    if event in ('socket.connect', 'socket.getaddrinfo'):
        raise RuntimeError('blocked network access')
    if event == 'subprocess.Popen':
        if Path(args[0]).name == 'rg':
            return
        env = args[3]
        assert env['QT_QPA_PLATFORM'] == 'offscreen'
        assert env['QT_QUICK_BACKEND'] == 'software'
        home = Path(env['HOME'])
        assert home.is_relative_to(root)
        if Path(args[0]).name == 'qmllint':
            print('PRIVATE_LINT_VERIFIED', flush=True)
            return
        assert Path(args[0]).name in ('quickshell', 'qmltestrunner')
        settings = home / '.config/noctalia/settings.json'
        backup = home.parent / 'settings.backup.json'
        original = (Path(script).parents[1] / 'Assets/settings-default.json').read_bytes()
        assert settings.read_bytes() == backup.read_bytes() == original
        for path in (settings, backup):
            assert path.stat().st_mode & 0o777 == 0o600
        assert home.parent.stat().st_mode & 0o777 == 0o700
        print('PRIVATE_FIXTURE_VERIFIED', flush=True)
        if mode == 'probe':
            raise RuntimeError('SAFE_CHILD_BOUNDARY')
        if mode in ('settings', 'backup'):
            (settings if mode == 'settings' else backup).write_bytes(b'changed fixture')
            raise RuntimeError('mutation injected before child launch')

def guard(function):
    def guarded(path, *args, **kwargs):
        deny(path)
        return function(path, *args, **kwargs)
    return guarded

sys.addaudithook(audit)
with patch('os.stat', guard(os.stat)), patch('os.lstat', guard(os.lstat)), patch('os.readlink', guard(os.readlink)), patch('os.access', guard(os.access)):
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name='__main__')
"""


class ParentIsolationTest(unittest.TestCase):
    def run_case(self, filename, arguments, mode):
        with tempfile.TemporaryDirectory(prefix="ww-") as temporary:
            root = Path(temporary)
            home = root / "absent-home"
            self.assertFalse(home.exists())
            command = [
                sys.executable,
                "-c",
                BOOTSTRAP,
                str(root),
                mode,
                str(ROOT / "Tests" / filename),
                *arguments,
            ]
            if mode != "probe":
                command = [
                    "bwrap",
                    "--die-with-parent",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--bind",
                    str(root),
                    str(root),
                    "--tmpfs",
                    "/home/osso/.config",
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "--",
                    *command,
                ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=dict(
                    os.environ,
                    HOME=str(home),
                    XDG_CONFIG_HOME=str(home / ".config"),
                    TMPDIR=str(root),
                ),
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertFalse(home.exists())
            self.assertEqual(list(root.iterdir()), [], "fixture leaked")
            return result, result.stdout + result.stderr

    def test_runtime_denied_config_absent_home(self):
        for filename, arguments, marker in CASES:
            with self.subTest(runner=filename):
                result, output = self.run_case(
                    filename, arguments, "probe" if PROBE else "normal"
                )
                self.assertNotIn("blocked settings access", output, output)
                self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                if PROBE:
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertIn("SAFE_CHILD_BOUNDARY", output, output)
                else:
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn(marker, output)
                print(filename, output, flush=True)

    @unittest.skipIf(PROBE, "RED stops at guarded runtime boundary")
    def test_mutations_rejected(self):
        for filename, arguments, _ in CASES:
            for mode in ("settings", "backup"):
                with self.subTest(runner=filename, mutation=mode):
                    result, output = self.run_case(filename, arguments, mode)
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                    self.assertIn(f"fixture {mode} changed", output, output)
                    self.assertNotIn("blocked settings access", output, output)
                    print("MUTATION_DETECTED", filename, mode)

    @unittest.skipIf(PROBE, "RED stops before lint child")
    def test_wifi_lint_denied_config_absent_home(self):
        result, output = self.run_case(
            "wifi-networks-list-warnings.test.py", ("lint",), "normal"
        )
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PRIVATE_LINT_VERIFIED", output, output)
        self.assertIn("WIFI_LIST_LINT_COUNTS {}", output, output)
        self.assertNotIn("PRIVATE_FIXTURE_VERIFIED", output)
        print(output, end="")


if __name__ == "__main__":
    unittest.main()
