#!/usr/bin/env python3
"""Four parent CLIs deny host config and preserve private fixture integrity."""

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
    ("timer-card-runtime.test.py", ("behavior",), "TIMER_CARD_BEHAVIOR_PASS"),
    ("tray-drawer-warnings.test.py", ("--mode", "runtime"), "TRAY_DRAWER_RUNTIME_PASS"),
    ("tray-widget-warnings.test.py", ("--mode", "runtime"), "TRAY_WIDGET_RUNTIME_PASS"),
    (
        "wallpaper-panel-warnings.test.py",
        ("--mode", "runtime"),
        "WALLPAPER_PANEL_RUNTIME_PASS",
    ),
)
LINT_CASES = (
    ("timer-card-runtime.test.py", ("lint",)),
    ("tray-drawer-warnings.test.py", ("--mode", "lint")),
    ("tray-widget-warnings.test.py", ("--mode", "lint")),
    ("wallpaper-panel-warnings.test.py", ("--mode", "lint")),
    ("tray-widget-warnings.test.py", ("lint-harness",)),
    ("tray-widget-warnings.test.py", ("lint-harness-regression",)),
)
BOOTSTRAP = """
import os
from pathlib import Path
import runpy
import subprocess
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
    if event == 'subprocess.Popen' and Path(args[0]).name == 'bwrap':
        command, env = args[1], args[3]
        assert '--unshare-net' in command
        masks = [command[i + 1] for i, arg in enumerate(command) if arg == '--tmpfs']
        assert '/home/osso/.config' in masks and '/syncthing' in masks
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
        if mode != 'normal':
            target = settings if mode.startswith('settings') else backup
            if mode.endswith('-mode'):
                target.chmod(0o644)
            else:
                target.write_bytes(b'changed fixture')
            raise RuntimeError('mutation injected before child launch')

def guard(function):
    def guarded(path, *args, **kwargs):
        deny(path)
        return function(path, *args, **kwargs)
    return guarded

original_run = subprocess.run
def isolated_run(command, **kwargs):
    if Path(command[0]).name in ('quickshell', 'qmltestrunner'):
        command = ['bwrap', '--die-with-parent', '--unshare-net', '--ro-bind', '/', '/',
                   '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/home/osso/.config',
                   '--tmpfs', '/syncthing', '--bind', str(root), str(root),
                   '--chdir', str(root), '--', *command]
        kwargs['cwd'] = root
    return original_run(command, **kwargs)

sys.addaudithook(audit)
with patch('os.stat', guard(os.stat)), patch('os.lstat', guard(os.lstat)), patch('os.readlink', guard(os.readlink)), patch('os.access', guard(os.access)), patch('subprocess.run', isolated_run):
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name='__main__')
"""


class SettingsIsolationTest(unittest.TestCase):
    def run_case(self, filename, arguments, mode):
        # Keep Quickshell IPC paths within Unix socket length limits.
        with tempfile.TemporaryDirectory(prefix="tw-") as temporary:
            root = Path(temporary)
            home = root / "absent-home"
            self.assertFalse(home.exists())
            result = subprocess.run(
                [
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
            self.assertEqual(list(root.iterdir()), [])
            return result, result.stdout + result.stderr

    def test_runtime_denied_config_absent_home(self):
        for filename, arguments, marker in CASES:
            with self.subTest(runner=filename):
                result, output = self.run_case(
                    filename, arguments, "probe" if PROBE else "normal"
                )
                print(filename, output, flush=True)
                self.assertNotIn("blocked settings access", output, output)
                self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                if PROBE:
                    self.assertIn("SAFE_CHILD_BOUNDARY", output, output)
                else:
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn(marker, output)

    def test_mutations_rejected(self):
        for filename, arguments, _ in CASES:
            for mode in ("settings", "backup", "settings-mode", "backup-mode"):
                with self.subTest(runner=filename, mutation=mode):
                    result, output = self.run_case(filename, arguments, mode)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                    target = mode.split("-")[0]
                    self.assertIn(
                        f"fixture {target} {'mode ' if mode.endswith('-mode') else ''}changed",
                        output,
                        output,
                    )
                    self.assertNotIn("blocked settings access", output, output)
                    print(f"MUTATION_DETECTED {filename} {mode}")

    def test_lint_modes(self):
        for filename, arguments in LINT_CASES:
            with self.subTest(runner=filename, arguments=arguments):
                result, output = self.run_case(filename, arguments, "normal")
                self.assertEqual(result.returncode, 0, output)
                self.assertNotIn("PRIVATE_FIXTURE_VERIFIED", output)
                self.assertNotIn("blocked settings access", output)
                print(f"LINT_MODE_PASS {filename} {arguments}", output, flush=True)


if __name__ == "__main__":
    unittest.main()
