#!/usr/bin/env python3
"""Settings type entrypoint must never open host settings, even for safeguards."""

import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).with_name("settings-types.test.py")
AUDITED_ENTRYPOINT = r"""
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys

protected = '/home/osso/.config/noctalia/settings.json'
def deny_host_settings(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.abspath(os.fsdecode(args[0]))
        if path == protected:
            raise PermissionError('HOST_SETTINGS_ACCESS_DENIED: ' + path)
sys.addaudithook(deny_host_settings)

# Prove denial without reading any real bytes.
try:
    open(protected, 'rb')
except PermissionError as error:
    assert 'HOST_SETTINGS_ACCESS_DENIED' in str(error)
else:
    raise AssertionError('audit denial failed')

original_run = subprocess.run
children = 0
def run_isolated(*args, **kwargs):
    global children
    environment = kwargs['env']
    root = Path(kwargs['cwd'])
    assert Path(environment['HOME']).is_relative_to(root)
    assert 'DISPLAY' not in environment and 'WAYLAND_DISPLAY' not in environment
    fixture = Path(environment['HOME']) / '.config/noctalia/settings.json'
    if 'SETTINGS_TYPES_PATH' in environment:
        before = fixture.read_bytes()
        assert stat.S_IMODE(fixture.stat().st_mode) == 0o600
        runtime = Path(environment['SETTINGS_TYPES_PATH'])
        assert runtime != fixture and runtime.is_relative_to(root)
        assert runtime.read_bytes() == before
        assert stat.S_IMODE(runtime.stat().st_mode) == 0o600
    result = original_run(*args, **kwargs)
    if 'SETTINGS_TYPES_PATH' in environment:
        assert fixture.read_bytes() == before
        assert stat.S_IMODE(fixture.stat().st_mode) == 0o600
    children += 1
    return result
subprocess.run = run_isolated
sys.argv = [sys.argv[1], '-v']
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit as error:
    if error.code:
        raise
assert children == 7, children
print('ISOLATED_SUBPROCESSES=7; host audit denial active; fixture bytes/mode intact')
"""


def load_runner():
    spec = importlib.util.spec_from_file_location("settings_types", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SettingsTypesIsolationTest(unittest.TestCase):
    def test_full_entrypoint_with_synthetic_home_and_audit_denial(self):
        with tempfile.TemporaryDirectory(prefix="settings-types-audit-") as temporary:
            root = Path(temporary)
            environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8"}
            for name in (
                "HOME",
                "XDG_CONFIG_HOME",
                "XDG_CACHE_HOME",
                "XDG_DATA_HOME",
                "XDG_STATE_HOME",
                "XDG_RUNTIME_DIR",
                "XDG_CONFIG_DIRS",
                "XDG_DATA_DIRS",
            ):
                directory = root / name.lower()
                directory.mkdir(mode=0o700)
                environment[name] = str(directory)
            result = subprocess.run(
                [sys.executable, "-B", "-c", AUDITED_ENTRYPOINT, str(RUNNER)],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout + result.stderr
            print(output, end="")
            self.assertEqual(result.returncode, 0, output)
            self.assertIn("ISOLATED_SUBPROCESSES=7", output)
            self.assertFalse((root / "home/.config/noctalia/settings.json").exists())

    def test_fixture_safeguard_rejects_changed_bytes_and_permissions(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory(
            prefix="settings-types-integrity-"
        ) as temporary:
            fixture = Path(temporary) / "settings.json"
            expected = b'{"fixture": "synthetic only"}\n'
            fixture.touch(mode=0o600)
            fixture.write_bytes(expected)
            runner.assert_fixture_settings_unchanged(fixture, expected)
            fixture.write_bytes(b'{"fixture": "changed"}\n')
            with self.assertRaisesRegex(AssertionError, "Fixture settings changed"):
                runner.assert_fixture_settings_unchanged(fixture, expected)
            fixture.write_bytes(expected)
            fixture.chmod(0o644)
            with self.assertRaisesRegex(AssertionError, "0600"):
                runner.assert_fixture_settings_unchanged(fixture, expected)
            self.assertEqual(stat.S_IMODE(fixture.stat().st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
