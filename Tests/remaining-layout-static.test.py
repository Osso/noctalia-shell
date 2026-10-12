"""Remaining-layout CLI regression: fixture lint must not touch runtime state."""

import os
from pathlib import Path
import shutil
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

real_config = Path(sys.argv.pop(1))

def deny_runtime_access(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0]))
        if path.name == "settings.json" or path.is_relative_to(real_config):
            raise PermissionError(f"blocked settings access: {path}")
    if event == "subprocess.Popen":
        if Path(args[0]).name != "qmllint":
            raise PermissionError(f"blocked live process/registry access: {args[0]}")

sys.addaudithook(deny_runtime_access)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


class RemainingLayoutStaticTest(unittest.TestCase):
    def run_lint(self, root, inject_warning=False):
        for relative in ("Commons", "Widgets", "Helpers", "Assets"):
            shutil.copytree(ROOT / relative, root / relative)
        for relative in (
            "Tests/remaining-layout-geometry.test.py",
            "Tests/setup-layout-geometry.test.py",
            "Tests/Qml/RemainingLayoutGeometryHarness.qml",
            "Modules/Cards/CalendarHeaderCard.qml",
            "Modules/Cards/SystemMonitorCard.qml",
            "Modules/Panels/Settings/Bar/WidgetSettings/ClockSettings.qml",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        if inject_warning:
            harness = root / "Tests/Qml/RemainingLayoutGeometryHarness.qml"
            harness.write_text(
                harness.read_text().replace(
                    "ShellRoot {",
                    "ShellRoot {\n  property int regressionWarning: Qt.application.missingFixtureValue",
                    1,
                )
            )
        home = root / "home"
        home.mkdir(mode=0o700)
        settings = home / ".config/noctalia/settings.json"
        self.assertFalse(settings.exists())
        artifacts = root / "artifacts"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                BOOTSTRAP,
                "/home/osso/.config",
                str(root / "Tests/remaining-layout-geometry.test.py"),
                "lint-harness",
                "--artifacts",
                str(artifacts),
            ],
            cwd=root,
            env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config")),
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = result.stdout + result.stderr
        self.assertNotIn("blocked settings access", output, output)
        self.assertNotIn("blocked live process/registry access", output, output)
        self.assertFalse((artifacts / "settings.backup.json").exists())
        self.assertFalse(settings.exists())
        log = artifacts / "harness-lint.log"
        self.assertTrue(log.exists(), output)
        self.assertIn(log.read_text(), output)
        return result, log.read_text()

    def test_static_lint_with_absent_settings_and_blocked_runtime_access(self):
        with tempfile.TemporaryDirectory(prefix="remaining-layout-static-") as temp:
            result, diagnostics = self.run_lint(Path(temp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Warning:", diagnostics)
            self.assertIn("REMAINING_LAYOUT_HARNESS_LINT_WARNINGS 0", result.stdout)

    def test_injected_warning_fails_without_runtime_access(self):
        with tempfile.TemporaryDirectory(
            prefix="remaining-layout-static-warning-"
        ) as temp:
            result, _ = self.run_lint(Path(temp), inject_warning=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
