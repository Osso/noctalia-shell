"""Context-menu CLI never inspects host settings, even with an absent HOME."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

root = Path(sys.argv.pop(1))
mutate = sys.argv.pop(1) == "mutate"
protected = "/home/osso/.config/noctalia"
script = sys.argv[1]
sys.path.insert(0, str(Path(script).parent))

def deny(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    name = os.path.abspath(os.fsdecode(path))
    if name == protected or name.startswith(protected + "/") or (
        name.endswith("/settings.json") and not name.startswith(str(root) + "/noctalia-context-menu-")
    ):
        raise PermissionError(f"blocked settings access: {name}")

def audit(event, args):
    if event in ("open", "os.listdir", "os.scandir"):
        deny(args[0])
    if event == "subprocess.Popen" and Path(args[0]).name == "bwrap":
        command, environment = args[1], args[3]
        assert "--unshare-net" in command, "network not isolated"
        masks = [command[i + 1] for i, arg in enumerate(command) if arg == "--tmpfs"]
        assert "/home/osso/.config" in masks, "host config unmasked"
        assert "/syncthing" in masks, "Syncthing config unmasked"
        assert environment["QT_QPA_PLATFORM"] == "offscreen"
        assert environment["QT_QUICK_BACKEND"] == "software"
        home = Path(environment["HOME"])
        assert home.is_relative_to(root), "HOME outside fixture"
        settings = home / ".config/noctalia/settings.json"
        backup = home.parent / "settings.backup.json"
        original = (Path(script).parents[1] / "Assets/settings-default.json").read_bytes()
        assert settings.read_bytes() == backup.read_bytes() == original
        assert settings.stat().st_mode & 0o777 == 0o600
        assert backup.stat().st_mode & 0o777 == 0o600
        print("PRIVATE_FIXTURE_VERIFIED", flush=True)
        if mutate:
            settings.write_bytes(b"changed fixture settings")

def guard(function):
    def guarded(path, *args, **kwargs):
        deny(path)
        return function(path, *args, **kwargs)
    return guarded

sys.addaudithook(audit)
with patch("os.stat", guard(os.stat)), patch("os.lstat", guard(os.lstat)), patch("os.readlink", guard(os.readlink)), patch("os.access", guard(os.access)):
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")
"""


class ContextMenuIsolationTest(unittest.TestCase):
    def run_mode(self, mode, mutate=False):
        with tempfile.TemporaryDirectory(prefix="context-isolation-") as temporary:
            root = Path(temporary)
            home = root / "absent-home"
            self.assertFalse(home.exists())
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    BOOTSTRAP,
                    str(root),
                    "mutate" if mutate else "normal",
                    str(ROOT / "Tests/context-menu-warnings.test.py"),
                    mode,
                ],
                cwd=ROOT,
                env=dict(os.environ, HOME=str(home), TMPDIR=str(root)),
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertFalse(home.exists())
            self.assertEqual(list(root.glob("noctalia-context-menu-*")), [])
            return result

    def assert_behavior(self, mode):
        result = self.run_mode(mode)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("PRIVATE_FIXTURE_VERIFIED", output)
        self.assertIn("7 passed, 0 failed", output)
        self.assertNotIn("blocked settings access", output)

    def test_runtime_with_denied_settings_and_absent_home(self):
        self.assert_behavior("runtime")

    def test_behavior_entrypoint_with_denied_settings_and_absent_home(self):
        self.assert_behavior("behavior")

    def test_lint_with_denied_settings_and_absent_home(self):
        result = self.run_mode("lint")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CONTEXT_MENU_LINT_COUNTS {}", result.stdout)
        self.assertNotIn("PRIVATE_FIXTURE_VERIFIED", result.stdout)

    def test_fixture_mutation_fails_integrity_check(self):
        result = self.run_mode("runtime", mutate=True)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PRIVATE_FIXTURE_VERIFIED", output)
        self.assertIn("fixture settings changed", output)
        self.assertNotIn("blocked settings access", output)


if __name__ == "__main__":
    unittest.main()
