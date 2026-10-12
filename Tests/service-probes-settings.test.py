#!/usr/bin/env python3
"""Private fixture coverage for the settings service probe; no host settings mount."""

import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / "Bin/dev/service-probes.sh"
DEFAULTS = REPO / "Assets/settings-default.json"
HOST_SETTINGS = "/home/osso/.config/noctalia/settings.json"


class SettingsProbeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="service-settings-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.defaults_bytes = DEFAULTS.read_bytes()
        self.addCleanup(self.assert_defaults_intact)
        for command in ("bwrap", "strace", "jq"):
            if not shutil.which(command):
                self.fail(f"required private-test command missing: {command}")

    def assert_defaults_intact(self):
        self.assertEqual(DEFAULTS.read_bytes(), self.defaults_bytes)

    def run_private(self, script, *arguments):
        trace = self.root / "file-access.log"
        command = [
            "strace",
            "-f",
            "-e",
            "trace=%file",
            "-o",
            str(trace),
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/bin",
            "/bin",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--ro-bind",
            str(REPO),
            str(REPO),
            "--bind",
            str(self.root),
            str(self.root),
            "--chdir",
            str(REPO),
            "--setenv",
            "HOME",
            str(self.root),
            "--setenv",
            "TMPDIR",
            str(self.root),
            str(script),
            *arguments,
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=20)
        host_accesses = [
            line for line in trace.read_text().splitlines() if HOST_SETTINGS in line
        ]
        self.assertEqual(host_accesses, [], "real settings access attempted")
        return result

    def write_harness(self, body):
        harness = self.root / "harness.sh"
        harness.write_text(
            f'#!/usr/bin/env bash\nset -euo pipefail\nsource "{PROBE}"\n' + body
        )
        harness.chmod(0o700)
        return harness

    def test_entrypoint_validates_private_fixture_and_cleans_up(self):
        result = self.run_private(PROBE, "settings")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "ok probeSettings (private fixture; host settings not checked)",
            result.stdout,
        )
        self.assertEqual(
            sorted(p.name for p in self.root.iterdir()), ["file-access.log"]
        )

    def test_fixture_is_customized_valid_and_unchanged_by_validation(self):
        harness = self.write_harness(
            "umask 077\n"
            'write_settings_probe_fixture "$repo_root/Assets/settings-default.json" "$TMPDIR/settings.json"\n'
            'has_settings_default_keys "$TMPDIR/settings.json" "$repo_root/Assets/settings-default.json"\n'
            'has_settings_value_shape "$TMPDIR/settings.json"\n'
        )
        result = self.run_private(harness)
        self.assertEqual(result.returncode, 0, result.stderr)
        fixture = self.root / "settings.json"
        data = json.loads(fixture.read_bytes())
        self.assertEqual(data["bar"]["position"], "bottom")
        self.assertEqual(
            data["bar"]["widgets"]["left"],
            [{"id": "ControlCenter"}, {"id": "Workspace"}],
        )
        self.assertEqual(
            data["wallpaper"]["monitorDirectories"],
            [{"name": "fixture-monitor", "path": "/fixture/wallpapers"}],
        )
        self.assertEqual(data["templates"]["kitty"], True)
        self.assertNotEqual(data, json.loads(self.defaults_bytes))
        self.assertEqual(stat.S_IMODE(fixture.stat().st_mode), 0o600)
        before = hashlib.sha256(fixture.read_bytes()).hexdigest()
        result = self.run_private(
            self.write_harness(
                'has_settings_default_keys "$TMPDIR/settings.json" "$repo_root/Assets/settings-default.json"\n'
                'has_settings_value_shape "$TMPDIR/settings.json"\n'
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), before)

    def test_missing_and_extra_keys_are_rejected(self):
        cases = (
            "del(.audio)",
            "del(.templates.kitty)",
            ".unexpected = true",
            ".templates.unexpected = true",
        )
        for mutation in cases:
            with self.subTest(mutation=mutation):
                harness = self.write_harness(
                    "umask 077\n"
                    'write_settings_probe_fixture "$repo_root/Assets/settings-default.json" "$TMPDIR/valid.json"\n'
                    f'jq \'{mutation}\' "$TMPDIR/valid.json" >"$TMPDIR/bad.json"\n'
                    'if has_settings_default_keys "$TMPDIR/bad.json" "$repo_root/Assets/settings-default.json"; then\n'
                    '    echo "invalid keys accepted" >&2; exit 1\nfi\n'
                )
                result = self.run_private(harness)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_value_shapes_are_rejected(self):
        cases = (
            '.bar.position = "diagonal"',
            '.bar.widgets.left = [{"id": 42}]',
            ".controlCenter.cards = []",
            ".audio.volumeStep = 0",
            '.wallpaper.monitorDirectories = [{"name": "test", "path": 42}]',
            ".wallpaper.transitionEdgeSmoothness = 2",
            '.templates.kitty = "true"',
            ".osd.enabledTypes = [4]",
        )
        for mutation in cases:
            with self.subTest(mutation=mutation):
                harness = self.write_harness(
                    "umask 077\n"
                    'write_settings_probe_fixture "$repo_root/Assets/settings-default.json" "$TMPDIR/valid.json"\n'
                    f'jq \'{mutation}\' "$TMPDIR/valid.json" >"$TMPDIR/bad.json"\n'
                    'has_settings_default_keys "$TMPDIR/bad.json" "$repo_root/Assets/settings-default.json"\n'
                    'if has_settings_value_shape "$TMPDIR/bad.json"; then\n'
                    '    echo "invalid shape accepted" >&2; exit 1\nfi\n'
                )
                result = self.run_private(harness)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_validation_is_not_skipped_and_cleans_up(self):
        harness = self.write_harness(
            'write_settings_probe_fixture() { printf "{}\\n" >"$2"; }\nprobe_settings\n'
        )
        result = self.run_private(harness)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("ok probeSettings", result.stdout)
        self.assertEqual(
            sorted(p.name for p in self.root.iterdir()),
            ["file-access.log", "harness.sh"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
