"""Bounded real-qmllint regression for behavioral fixture contexts."""

from collections import Counter
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPTS = {
    "BatteryTabWarningsHarness.qml": "battery-tab-warnings.test.py",
    "BatteryWidgetWarningsHarness.qml": "battery-widget-warnings.test.py",
    "MediaMiniWarningsHarness.qml": "media-mini-warnings.test.py",
    "RootServiceHarness.qml": "root-service-warnings.test.py",
    "ServiceCohortHarness.qml": "service-cohort-warnings.test.py",
    "BrightnessPanelWarningsHarness.qml": "brightness-panel-warnings.test.py",
}
HARNESS_REPORTS = {
    "BatteryTabWarningsHarness.qml": "tst_battery.qml",
    "BatteryWidgetWarningsHarness.qml": "tst_battery.qml",
    "MediaMiniWarningsHarness.qml": "shell.qml",
    "RootServiceHarness.qml": "tst_root.qml",
    "ServiceCohortHarness.qml": "tst_services.qml",
    "BrightnessPanelWarningsHarness.qml": "tst_brightness.qml",
}


class FixtureLintTest(unittest.TestCase):
    def stage_repository(self, root):
        # Real dependencies remain available to behavior staging, but discovery is
        # bounded to these six harnesses, not a full-project lint invocation.
        for directory in (
            "Commons",
            "Modules",
            "Services",
            "Widgets",
            "Assets",
            "Shaders",
            "Helpers",
        ):
            shutil.copytree(ROOT / directory, root / directory)
        tests = root / "Tests"
        (tests / "Qml").mkdir(parents=True)
        for script in (
            *HARNESS_SCRIPTS.values(),
            "simple-service-warnings.test.py",
            "workspace-runtime.test.py",
            "about-tab-warnings.test.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        helper = ROOT / "Tests/qml_fixture_lint.py"
        if helper.exists():
            shutil.copy2(helper, tests / helper.name)
        for harness in HARNESS_SCRIPTS:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        # Runtime staging copies this dependency; rg discovery skips symlinks.
        (tests / "Qml/SimpleServiceHarness.qml").symlink_to(
            ROOT / "Tests/Qml/SimpleServiceHarness.qml"
        )
        (tests / "fixtures").mkdir()
        shutil.copy2(
            ROOT / "Tests/fixtures/root-services-wayland.cpp",
            tests / "fixtures/root-services-wayland.cpp",
        )
        runner = root / "Bin/dev/qml-static-check.sh"
        runner.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
        (runner.parent / "qml-static-exclusions.txt").write_text("")
        (root / ".ignore").write_text(
            "Commons/\nModules/\nServices/\nWidgets/\nAssets/\nShaders/\nHelpers/\n"
        )
        return runner

    def run_checker(self, runner, root):
        home = root / ".fixture-home"
        settings = home / ".config/noctalia/settings.json"
        settings.parent.mkdir(parents=True, mode=0o700)
        settings.touch(mode=0o600)
        settings.write_bytes((root / "Assets/settings-default.json").read_bytes())
        result = subprocess.run(
            [str(runner)],
            cwd=root,
            check=False,
            env=dict(os.environ, HOME=str(home)),
            capture_output=True,
            text=True,
            timeout=90,
        )
        print(result.stdout + result.stderr, end="")
        return result

    def test_all_six_harnesses_are_checked_without_fixture_type_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-static-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            result = self.run_checker(runner, root)
            files = [
                file
                for line in result.stdout.splitlines()
                if line.startswith('{"files":')
                for file in json.loads(line)["files"]
            ]
            warnings = [
                warning
                for file in files
                for warning in file["warnings"]
                if warning["type"] in ("warning", "error")
            ]
            self.assertFalse(any(w["id"] == "read-only-property" for w in warnings))
            self.assertEqual(warnings, [])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                Counter(Path(file["filename"]).name for file in files),
                Counter(HARNESS_REPORTS.values()),
            )
            self.assertIn("Checked 6 QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_new_routes_each_count_once_without_other_harnesses(self):
        for name in (
            "ServiceCohortHarness.qml",
            "BrightnessPanelWarningsHarness.qml",
        ):
            with (
                self.subTest(harness=name),
                tempfile.TemporaryDirectory(prefix="noctalia-fixture-count-") as temp,
            ):
                root = Path(temp)
                runner = self.stage_repository(root)
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                result = self.run_checker(runner, root)
                self.assertEqual(result.returncode, 0, result.stderr)
                reports = [
                    json.loads(line)
                    for line in result.stdout.splitlines()
                    if line.startswith('{"files":')
                ]
                self.assertEqual(len(reports), 1, result.stdout)
                self.assertEqual(len(reports[0]["files"]), 1)
                file = reports[0]["files"][0]
                self.assertEqual(Path(file["filename"]).name, HARNESS_REPORTS[name])
                self.assertEqual(file["warnings"], [])
                self.assertIn("Checked 1 QML files", result.stdout)
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
                self.assertNotIn("Checked ", result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(len(report["files"]), 1)
                self.assertEqual(
                    Path(report["files"][0]["filename"]).name,
                    HARNESS_REPORTS[name],
                )


if __name__ == "__main__":
    unittest.main()
