#!/usr/bin/env python3
"""Four parent CLIs deny host config and verify fixture integrity before launch."""

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
    ("scheme-downloader-runtime.test.py", ("runtime",), "SCHEME_DOWNLOADER_PASS"),
    ("sound-service-runtime.test.py", (), "SOUND_SERVICE_PASS:"),
    ("system-monitor-runtime.test.py", (), "5 passed, 0 failed"),
    ("taskbar-grouped-warnings.test.py", ("behavior",), "0 failed"),
)
LINT_CASES = (
    ("scheme-downloader-runtime.test.py", "lint"),
    ("scheme-downloader-runtime.test.py", "lint-harness"),
    ("taskbar-grouped-warnings.test.py", "lint"),
    ("taskbar-grouped-warnings.test.py", "lint-harness"),
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
    if event == 'subprocess.Popen' and Path(args[0]).name in ('qmltestrunner', 'quickshell', 'bwrap'):
        command, env = args[1], args[3]
        if Path(args[0]).name == 'bwrap':
            env = {command[i + 1]: command[i + 2] for i, arg in enumerate(command) if arg == '--setenv'}
        assert env['QT_QPA_PLATFORM'] == 'offscreen'
        assert env['QT_QUICK_BACKEND'] == 'software'
        home = Path(env['HOME'])
        assert home.is_relative_to(root)
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


class ParentSettingsIsolationTest(unittest.TestCase):
    def run_case(self, filename, arguments, mode):
        # Keep nested Quickshell IPC paths below the Unix socket path limit.
        with tempfile.TemporaryDirectory(prefix="ds-") as temporary:
            root = Path(temporary)
            home = root / "absent-home"
            self.assertFalse(home.exists())
            result = subprocess.run(
                [
                    "bwrap",
                    "--die-with-parent",
                    "--new-session",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--dev",
                    "/dev",
                    "--proc",
                    "/proc",
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
                    str(root),
                    str(root),
                    "--chdir",
                    str(ROOT),
                    sys.executable,
                    "-c",
                    BOOTSTRAP,
                    str(root),
                    mode,
                    str(ROOT / "Tests" / filename),
                    *arguments,
                ],
                cwd=ROOT,
                env=dict(
                    os.environ,
                    HOME=str(home),
                    XDG_CONFIG_HOME=str(home / ".config"),
                    TMPDIR=str(root),
                    PYTHONDONTWRITEBYTECODE="1",
                ),
                capture_output=True,
                text=True,
                timeout=180,
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
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("SAFE_CHILD_BOUNDARY", output, output)
                else:
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn(marker, output)
                print(filename, output, flush=True)

    def test_mutations_rejected(self):
        for filename, arguments, _ in CASES:
            for mode in ("settings", "backup"):
                with self.subTest(runner=filename, mutation=mode):
                    result, output = self.run_case(filename, arguments, mode)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                    self.assertIn(f"fixture {mode} changed", output, output)
                    self.assertNotIn("blocked settings access", output, output)
                    print("MUTATION_DETECTED", filename, mode, flush=True)

    def test_lint_branches(self):
        for filename, mode in LINT_CASES:
            with self.subTest(runner=filename, mode=mode):
                result, output = self.run_case(filename, (mode,), "normal")
                self.assertEqual(result.returncode, 0, output)
                self.assertNotIn("PRIVATE_FIXTURE_VERIFIED", output)
                self.assertNotIn("blocked settings access", output)
                print(filename, mode, output, flush=True)


if __name__ == "__main__":
    unittest.main()
