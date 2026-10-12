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
    "TrayWidgetWarningsHarness.qml": "tray-widget-warnings.test.py",
    "WallpaperServiceHarness.qml": "wallpaper-service-warnings.test.py",
    "TaskbarHarness.qml": "taskbar-warnings.test.py",
    "AboutTabWarningsHarness.qml": "about-tab-warnings.test.py",
    "RemainingLayoutGeometryHarness.qml": "remaining-layout-geometry.test.py",
    "BatteryPanelWarningsHarness.qml": "battery-panel-warnings.test.py",
    "ColorSchemeServiceHarness.qml": "color-scheme-service-runtime.test.py",
    "BarWidgetLoaderOwnerHarness.qml": "layer-bar-owner-warnings.test.py",
    "NotificationWarningsHarness.qml": "notification-warnings.test.py",
    "PanelServiceLifecycleHarness.qml": "panel-service-lifecycle.test.sh",
    "CompositorServiceHarness.qml": "compositor-service-warnings.test.py",
    "ShellStateHarness.qml": "shell-state-warnings.test.py",
    "BatterySettingsWarningsHarness.qml": "battery-settings-warnings.test.py",
    "OSDWarningsHarness.qml": "osd-warnings.test.py",
    "SimpleServiceHarness.qml": "simple-service-warnings.test.py",
}
HARNESS_REPORTS = {
    "BatteryTabWarningsHarness.qml": "tst_battery.qml",
    "BatteryWidgetWarningsHarness.qml": "tst_battery.qml",
    "MediaMiniWarningsHarness.qml": "shell.qml",
    "RootServiceHarness.qml": "tst_root.qml",
    "ServiceCohortHarness.qml": "tst_services.qml",
    "BrightnessPanelWarningsHarness.qml": "tst_brightness.qml",
    "TrayWidgetWarningsHarness.qml": "tst_tray_widget.qml",
    "WallpaperServiceHarness.qml": "tst_wallpaper.qml",
    "TaskbarHarness.qml": "tst_taskbar.qml",
    "AboutTabWarningsHarness.qml": "tst_about.qml",
    "RemainingLayoutGeometryHarness.qml": "shell.qml",
    "BatteryPanelWarningsHarness.qml": "tst_battery_panel.qml",
    "ColorSchemeServiceHarness.qml": "shell.qml",
    "BarWidgetLoaderOwnerHarness.qml": "tst_owner.qml",
    "NotificationWarningsHarness.qml": "shell.qml",
    "PanelServiceLifecycleHarness.qml": "shell.qml",
    "CompositorServiceHarness.qml": "tst_service.qml",
    "ShellStateHarness.qml": "tst_shellstate.qml",
    "BatterySettingsWarningsHarness.qml": "tst_battery_settings.qml",
    "OSDWarningsHarness.qml": "shell.qml",
    "SimpleServiceHarness.qml": "tst_services.qml",
}
NEW_HARNESSES = (
    "TrayWidgetWarningsHarness.qml",
    "WallpaperServiceHarness.qml",
    "TaskbarHarness.qml",
    "AboutTabWarningsHarness.qml",
    "RemainingLayoutGeometryHarness.qml",
    "BatteryPanelWarningsHarness.qml",
    "ColorSchemeServiceHarness.qml",
    "BarWidgetLoaderOwnerHarness.qml",
    "NotificationWarningsHarness.qml",
    "PanelServiceLifecycleHarness.qml",
    "CompositorServiceHarness.qml",
    "ShellStateHarness.qml",
    "BatterySettingsWarningsHarness.qml",
    "OSDWarningsHarness.qml",
    "SimpleServiceHarness.qml",
)
ARTIFACT_HARNESSES = (
    "BrightnessPanelWarningsHarness.qml",
    "WallpaperServiceHarness.qml",
    "RemainingLayoutGeometryHarness.qml",
    "BatteryPanelWarningsHarness.qml",
    "ColorSchemeServiceHarness.qml",
    "BarWidgetLoaderOwnerHarness.qml",
    "CompositorServiceHarness.qml",
    "BatterySettingsWarningsHarness.qml",
)


class FixtureLintTest(unittest.TestCase):
    def stage_repository(self, root):
        # Real dependencies remain available to behavior staging, but discovery is
        # bounded to these harnesses, not a full-project lint invocation.
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
            "clock-settings-warnings.test.py",
            "workspace-runtime.test.py",
            "taskbar-grouped-warnings.test.py",
            "setup-layout-geometry.test.py",
            "process-panel-warnings.test.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        helper = ROOT / "Tests/qml_fixture_lint.py"
        if helper.exists():
            shutil.copy2(helper, tests / helper.name)
        for harness in HARNESS_SCRIPTS:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        # Runtime staging copies these dependencies; rg skips symlinks.
        for name in (
            "ClockSettingsWarningsHarness.qml",
            "TaskbarGroupedHarness.qml",
            "WorkspaceHarness.qml",
            "ProcessPanelWarningsHarness.qml",
        ):
            (tests / "Qml" / name).symlink_to(ROOT / "Tests/Qml" / name)
        # Redirect the owner's hardcoded guard to synthetic settings only.
        for name in (
            "remaining-layout-geometry.test.py",
            "color-scheme-service-runtime.test.py",
        ):
            script = tests / name
            script.write_text(
                script.read_text().replace(
                    'Path("/home/osso/.config/noctalia/settings.json")',
                    'Path.home() / ".config/noctalia/settings.json"',
                )
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

    def run_checker(self, runner, root, settings_present=True):
        home = root / ".fixture-home"
        settings = home / ".config/noctalia/settings.json"
        settings.parent.mkdir(parents=True, mode=0o700)
        original = (root / "Assets/settings-default.json").read_bytes()
        if settings_present:
            settings.touch(mode=0o600)
            settings.write_bytes(original)
        # Keep runtime staging outside the repository's inherited .ignore rules.
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-artifacts-") as temp:
            self.fixture_tmp = Path(temp)
            result = subprocess.run(
                [str(runner)],
                cwd=root,
                check=False,
                env=dict(os.environ, HOME=str(home), TMPDIR=temp),
                capture_output=True,
                text=True,
                timeout=90,
            )
            print(result.stdout + result.stderr, end="")
            self.assertEqual(self.fixture_tmp.stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                list(self.fixture_tmp.iterdir()), [], "fixture artifacts leaked"
            )
        if settings_present:
            self.assertEqual(settings.read_bytes(), original)
        else:
            self.assertFalse(settings.exists(), "lint created settings")
        return result

    def assert_artifacts_are_isolated(self, file):
        harness = Path(file["filename"])
        harness.relative_to(self.fixture_tmp)
        self.assertFalse(harness.parent.exists(), "fixture artifacts leaked")

    def test_all_harnesses_are_checked_without_fixture_type_warnings(self):
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
                Counter(
                    report
                    for name, report in HARNESS_REPORTS.items()
                    if name != "RemainingLayoutGeometryHarness.qml"
                ),
            )
            for file in files:
                if Path(file["filename"]).name in {
                    HARNESS_REPORTS[name] for name in ARTIFACT_HARNESSES
                }:
                    self.assert_artifacts_are_isolated(file)
            self.assertEqual(
                result.stdout.count("REMAINING_LAYOUT_HARNESS_LINT_WARNINGS 0"), 1
            )
            self.assertIn(f"Checked {len(HARNESS_SCRIPTS)} QML files", result.stdout)
            self.assertIn("skipped 0", result.stdout)

    def test_new_routes_each_count_once_without_other_harnesses(self):
        for name in (
            "ServiceCohortHarness.qml",
            "BrightnessPanelWarningsHarness.qml",
            *NEW_HARNESSES,
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
                if name == "RemainingLayoutGeometryHarness.qml":
                    self.assertEqual(reports, [])
                    self.assertEqual(
                        result.stdout.count("REMAINING_LAYOUT_HARNESS_LINT_WARNINGS 0"),
                        1,
                    )
                    self.assertIn("Checked 1 QML files", result.stdout)
                    self.assertIn("skipped 0", result.stdout)
                    continue
                self.assertEqual(len(reports), 1, result.stdout)
                self.assertEqual(len(reports[0]["files"]), 1)
                file = reports[0]["files"][0]
                self.assertEqual(Path(file["filename"]).name, HARNESS_REPORTS[name])
                self.assertEqual(file["warnings"], [])
                if name in ARTIFACT_HARNESSES:
                    self.assert_artifacts_are_isolated(file)
                self.assertIn("Checked 1 QML files", result.stdout)
                self.assertIn("skipped 0", result.stdout)

    def test_new_routes_do_not_require_settings(self):
        for name in NEW_HARNESSES:
            with (
                self.subTest(harness=name),
                tempfile.TemporaryDirectory(prefix="noctalia-fixture-absent-") as temp,
            ):
                root = Path(temp)
                runner = self.stage_repository(root)
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                result = self.run_checker(runner, root, settings_present=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Checked 1 QML files", result.stdout)

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
                if name == "RemainingLayoutGeometryHarness.qml":
                    harness.write_text(
                        source.replace(
                            "width: 1000",
                            "width: Qt.application.missingFixtureValue",
                            1,
                        )
                    )
                else:
                    harness.write_text(
                        source.replace(
                            "{",
                            "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                            1,
                        )
                    )
                diagnostic = f"fixture stderr: {name}\n"
                script = root / "Tests" / HARNESS_SCRIPTS[name]
                if script.suffix == ".sh":
                    source = script.read_text()
                    shebang, body = source.split("\n", 1)
                    script.write_text(
                        shebang
                        + f"\nprintf '%s\\n' 'fixture stderr: {name}' >&2\n"
                        + body
                    )
                else:
                    script.write_text(
                        "import sys\nsys.stderr.write("
                        + repr(diagnostic)
                        + ")\n"
                        + script.read_text()
                    )
                # Earlier genuine warnings must not mask this injected failure.
                for other in HARNESS_SCRIPTS:
                    if other != name:
                        (root / "Tests/Qml" / other).unlink()
                result = self.run_checker(runner, root)
                self.assertNotEqual(result.returncode, 0)
                if name in (
                    "BatteryPanelWarningsHarness.qml",
                    "BarWidgetLoaderOwnerHarness.qml",
                    "BatterySettingsWarningsHarness.qml",
                ):
                    self.assertTrue(result.stderr.startswith(diagnostic), result.stderr)
                    self.assertIn("AssertionError", result.stderr)
                else:
                    self.assertEqual(result.stderr, diagnostic)
                if name != "RemainingLayoutGeometryHarness.qml":
                    self.assertIn("missingFixtureValue", result.stdout)
                    self.assertIn('"id":"missing-property"', result.stdout)
                self.assertNotIn("ok qmlStaticCheck", result.stdout)
                self.assertNotIn("Checked ", result.stdout)
                reports = [
                    json.loads(line)
                    for line in result.stdout.splitlines()
                    if line.startswith('{"files":')
                ]
                if name == "RemainingLayoutGeometryHarness.qml":
                    self.assertEqual(reports, [])
                    self.assertEqual(
                        result.stdout.count("REMAINING_LAYOUT_HARNESS_LINT_WARNINGS "),
                        1,
                    )
                    # Owner CLI uses --max-warnings 0: diagnostics are silent,
                    # but qmllint's failing exit status must reach the checker.
                    continue
                self.assertEqual(len(reports), 1, result.stdout)
                report = reports[0]
                self.assertEqual(len(report["files"]), 1)
                if name in ARTIFACT_HARNESSES:
                    self.assert_artifacts_are_isolated(report["files"][0])
                self.assertEqual(
                    Path(report["files"][0]["filename"]).name,
                    HARNESS_REPORTS[name],
                )


if __name__ == "__main__":
    unittest.main()
