#!/usr/bin/env python3
"""Timer parent owns fixtures outside the denied offscreen child config."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = r"""
import os
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch

root = Path(sys.argv.pop(1))
mutation = sys.argv.pop(1)
script = sys.argv[1]
original_run = subprocess.run

def deny(path):
    if isinstance(path, (str, bytes, os.PathLike)):
        name = os.path.abspath(os.fsdecode(path))
        if name == '/home/osso/.config' or name.startswith('/home/osso/.config/'):
            raise AssertionError('protected config access: ' + name)
        if name.endswith('/settings.json') and not name.startswith(str(root) + '/'):
            raise AssertionError('non-fixture settings access: ' + name)

def audit(event, args):
    if event in ('open', 'os.listdir', 'os.scandir'):
        deny(args[0])

sys.addaudithook(audit)

def guarded(function):
    def call(path, *args, **kwargs):
        deny(path)
        return function(path, *args, **kwargs)
    return call

CHILD_PROBE = '''
from pathlib import Path
import os
for config in (Path(os.environ['HOME']) / '.config', Path(os.environ['XDG_CONFIG_HOME'])):
    assert config.stat().st_mode & 0o777 == 0
    try:
        (config / 'noctalia/settings.json').read_bytes()
    except PermissionError:
        print('CHILD_CONFIG_DENIED', config)
    else:
        raise AssertionError('child config readable')
assert not Path('/home/osso/.config').exists()
print('CHILD_HOST_CONFIG_MASKED')
'''

def run(command, **kwargs):
    if Path(command[0]).name == 'bwrap':
        env = kwargs['env']
        directory = Path(env['HOME']).parent
        settings = directory / 'settings.json'
        backup = directory / 'settings.backup.json'
        expected = (Path(script).parents[1] / 'Assets/settings-default.json').read_bytes()
        assert directory.stat().st_mode & 0o777 == 0o700
        for config in (Path(env['HOME']) / '.config', Path(env['XDG_CONFIG_HOME'])):
            assert config.stat().st_mode & 0o777 == 0
            try:
                (config / 'noctalia/settings.json').read_bytes()
            except PermissionError:
                pass
            else:
                raise AssertionError('parent config readable')
        assert env['QT_QPA_PLATFORM'] == 'offscreen'
        assert env['QT_QUICK_BACKEND'] == 'software'
        probe = original_run(command[:command.index('--') + 1] +
                             [sys.executable, '-c', CHILD_PROBE], **kwargs)
        assert probe.returncode == 0, probe.stdout + probe.stderr
        print(probe.stdout, end='', flush=True)
        if 'quickshell' in command:
            for path in (settings, backup):
                assert path.read_bytes() == expected
                assert path.stat().st_mode & 0o777 == 0o600
            print('PRIVATE_FIXTURE_VERIFIED', flush=True)
            if mutation != 'normal':
                target = settings if mutation.startswith('settings') else backup
                if mutation.endswith('-mode'):
                    target.chmod(0o644)
                else:
                    target.write_bytes(b'changed fixture')
                raise RuntimeError('mutation injected before child launch')
    return original_run(command, **kwargs)

with patch('os.stat', guarded(os.stat)), patch('os.lstat', guarded(os.lstat)), \
     patch('os.access', guarded(os.access)), patch('subprocess.run', run):
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name='__main__')
"""


class TimerIsolationTest(unittest.TestCase):
    def run_case(self, arguments, mutation="normal"):
        with tempfile.TemporaryDirectory(prefix="ti-") as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            home = root / "absent-home"
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    BOOTSTRAP,
                    str(root),
                    mutation,
                    str(ROOT / "Tests/timer-card-runtime.test.py"),
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
                timeout=90,
            )
            self.assertFalse(home.exists())
            self.assertEqual(list(root.iterdir()), [])
            output = result.stdout + result.stderr
            self.assertNotIn("protected config access", output, output)
            self.assertNotIn("non-fixture settings access", output, output)
            return result, output

    def test_behavior_with_denied_config(self):
        result, output = self.run_case(["behavior"])
        print(output, end="", flush=True)
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PRIVATE_FIXTURE_VERIFIED", output)
        self.assertEqual(output.count("CHILD_CONFIG_DENIED"), 2)
        self.assertIn("CHILD_HOST_CONFIG_MASKED", output)
        self.assertIn("TIMER_CARD_BEHAVIOR_PASS", output)

    def test_integrity_mutations(self):
        for mutation in ("settings", "backup", "settings-mode", "backup-mode"):
            with self.subTest(mutation=mutation):
                result, output = self.run_case(["behavior"], mutation)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn("PRIVATE_FIXTURE_VERIFIED", output, output)
                target = mutation.split("-")[0]
                kind = "mode " if mutation.endswith("-mode") else ""
                self.assertIn(f"fixture {target} {kind}changed", output, output)
                print("TIMER_MUTATION_DETECTED", mutation, flush=True)

    def test_lint_harness(self):
        for injected in (False, True):
            with self.subTest(injected=injected):
                arguments = ["lint-harness", "--max-warnings", "0"]
                if injected:
                    arguments.append("--inject-warning")
                result, output = self.run_case(arguments)
                print(output, end="", flush=True)
                self.assertEqual(output.count("CHILD_CONFIG_DENIED"), 2, output)
                self.assertIn("CHILD_HOST_CONFIG_MASKED", output)
                if injected:
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertIn("missingLintProbe", output)
                else:
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn("TIMER_CARD_HARNESS_LINT_WARNINGS 0 EXIT 0", output)


if __name__ == "__main__":
    unittest.main()
