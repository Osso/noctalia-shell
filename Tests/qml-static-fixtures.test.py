#!/usr/bin/env python3
"""Bounded real-qmllint regression for the three behavioral fixture contexts."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPTS = {
    "BatteryTabWarningsHarness.qml": "battery-tab-warnings.test.py",
    "BatteryWidgetWarningsHarness.qml": "battery-widget-warnings.test.py",
    "MediaMiniWarningsHarness.qml": "media-mini-warnings.test.py",
}


class FixtureLintTest(unittest.TestCase):
    def stage_repository(self, root):
        # Real dependencies remain available to behavior staging, but discovery is
        # bounded to these three harnesses, not a full-project lint invocation.
        for directory in (
            "Commons",
            "Modules",
            "Services",
            "Widgets",
            "Assets",
            "Shaders",
        ):
            shutil.copytree(ROOT / directory, root / directory)
        tests = root / "Tests"
        (tests / "Qml").mkdir(parents=True)
        for script in HARNESS_SCRIPTS.values():
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        helper = ROOT / "Tests/qml_fixture_lint.py"
        if helper.exists():
            shutil.copy2(helper, tests / helper.name)
        for harness in HARNESS_SCRIPTS:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        runner = root / "Bin/dev/qml-static-check.sh"
        runner.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
        (runner.parent / "qml-static-exclusions.txt").write_text("")
        (root / ".ignore").write_text(
            "Commons/\nModules/\nServices/\nWidgets/\nAssets/\nShaders/\n"
        )
        return runner

    def run_checker(self, runner, root):
        result = subprocess.run(
            [str(runner)],
            cwd=root,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            timeout=90,
        )
        print(result.stdout + result.stderr, end="")
        return result

    def test_all_three_harnesses_are_checked_without_fixture_type_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-static-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            result = self.run_checker(runner, root)
            warnings = [
                warning
                for line in result.stdout.splitlines()
                if line.startswith('{"files":')
                for file in json.loads(line)["files"]
                for warning in file["warnings"]
                if warning["type"] in ("warning", "error")
            ]
            self.assertFalse(any(w["id"] == "read-only-property" for w in warnings))
            self.assertEqual(warnings, [])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Checked 3 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_real_warning_is_visible_and_fails_static_runner(self):
        for name in HARNESS_SCRIPTS:
            with (
                self.subTest(harness=name),
                tempfile.TemporaryDirectory(prefix="noctalia-fixture-warning-") as temp,
            ):
                root = Path(temp)
                runner = self.stage_repository(root)
                harness = root / "Tests/Qml" / name
                source = harness.read_text()
                harness.write_text(
                    source.replace(
                        "{",
                        "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                        1,
                    )
                )
                # Earlier genuine warnings must not mask this injected failure.
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                result = self.run_checker(runner, root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("missingFixtureValue", result.stdout)
                self.assertIn('"id":"missing-property"', result.stdout)
                self.assertNotIn("ok qmlStaticCheck", result.stdout)
                self.assertNotIn("Checked 3 QML files", result.stdout)


if __name__ == "__main__":
    unittest.main()
