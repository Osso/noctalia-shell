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
REQUESTED_HARNESSES = {
    "BluetoothPanelWarningsHarness.qml": "bluetooth-panel-warnings.test.py",
    "IpcIdleServicesHarness.qml": "ipc-idle-services-warnings.test.py",
    "BrightnessKeyboardServicesHarness.qml": "brightness-keyboard-services-warnings.test.py",
    "DockMenuWarningsHarness.qml": "dock-menu-warnings.test.py",
    "WallpaperTabWarningsHarness.qml": "wallpaper-tab-warnings.test.py",
}
REQUESTED_REPORTS = {
    "BluetoothPanelWarningsHarness.qml": "tst_bluetooth_panel.qml",
    "BrightnessKeyboardServicesHarness.qml": "tst_services.qml",
    "DockMenuWarningsHarness.qml": "tst_dock_menu.qml",
    "WallpaperTabWarningsHarness.qml": "tst_wallpaper_tab.qml",
}
STRICT_HARNESSES = {
    "I18nThemeIconsHarness.qml": "i18n-theme-icons-warnings.test.py",
    "VisualizerProfileHarness.qml": "visualizer-profile-warnings.test.py",
    "SimpleWidgetsWarningsHarness.qml": "simple-widgets-warnings.test.py",
    "SetupWallpaperWarningsHarness.qml": "setup-wallpaper-warnings.test.py",
}
STRICT_REPORTS = {
    "I18nThemeIconsHarness.qml": "tst_i18n_icons.qml",
    "VisualizerProfileHarness.qml": "tst_visualizer_profile.qml",
    "SimpleWidgetsWarningsHarness.qml": "tst_simple_widgets.qml",
    "SetupWallpaperWarningsHarness.qml": "shell.qml",
}
STRICT_MARKERS = {
    "I18nThemeIconsHarness.qml": "HARNESS_LINT_COUNTS",
    "VisualizerProfileHarness.qml": "VISUALIZER_PROFILE_HARNESS_LINT_WARNINGS",
    "SimpleWidgetsWarningsHarness.qml": "SIMPLE_WIDGETS_HARNESS_LINT_WARNINGS",
    "SetupWallpaperWarningsHarness.qml": "SETUP_WALLPAPER_HARNESS_LINT_WARNINGS",
}
PANEL_SERVICE_HARNESSES = {
    "NotificationServiceHarness.qml": "notification-service-warnings.test.py",
    "SettingsPanelWarningsHarness.qml": "settings-panel-warnings.test.py",
    "WiFiPanelWarningsHarness.qml": "wifi-panel-warnings.test.py",
    "BarWarningsHarness.qml": "bar-warnings.test.py",
    "ChangelogPanelWarningsHarness.qml": "changelog-panel-warnings.test.py",
}
PANEL_SERVICE_REPORTS = {
    "NotificationServiceHarness.qml": "tst_service.qml",
    "SettingsPanelWarningsHarness.qml": "shell.qml",
    "WiFiPanelWarningsHarness.qml": "tst_wifi.qml",
    "BarWarningsHarness.qml": "tst_bar.qml",
    "ChangelogPanelWarningsHarness.qml": "tst_history.qml",
}
PANEL_SERVICE_MARKERS = {
    "NotificationServiceHarness.qml": "NOTIFICATION_SERVICE_HARNESS_LINT_COUNTS",
    "SettingsPanelWarningsHarness.qml": "SETTINGS_PANEL_HARNESS_WARNINGS",
    "WiFiPanelWarningsHarness.qml": "WIFI_PANEL_HARNESS_LINT_COUNTS",
    "BarWarningsHarness.qml": "BAR_HARNESS_LINT_WARNINGS",
    "ChangelogPanelWarningsHarness.qml": "CHANGELOG_HARNESS_LINT_WARNINGS",
}
GLOBAL_HARNESSES = {
    "ControlCenterPanelWarningsHarness.qml": "control-center-panel-warnings.test.py",
    "LocationServiceHarness.qml": "location-service-runtime.test.py",
    "MainScreenWarningsHarness.qml": "main-screen-warnings.test.py",
    "FilePickerWarningsHarness.qml": "file-picker-warnings.test.py",
}
GLOBAL_REPORTS = {
    "ControlCenterPanelWarningsHarness.qml": "tst_control_center.qml",
    "LocationServiceHarness.qml": "shell.qml",
    "MainScreenWarningsHarness.qml": "tst_main_screen.qml",
    "FilePickerWarningsHarness.qml": "tst_picker.qml",
}
GLOBAL_MARKERS = {
    "ControlCenterPanelWarningsHarness.qml": "CONTROL_CENTER_HARNESS_WARNINGS",
    "LocationServiceHarness.qml": "LOCATION_HARNESS_LINT_COUNTS",
    "MainScreenWarningsHarness.qml": "MAIN_SCREEN_HARNESS_LINT_WARNINGS",
    "FilePickerWarningsHarness.qml": "FILE_PICKER_HARNESS_WARNINGS",
}
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


def lint_reports(output):
    decoder = json.JSONDecoder()
    return [
        decoder.raw_decode(line)[0]
        for line in output.splitlines()
        if line.startswith('{"files":')
    ]


class FixtureLintTest(unittest.TestCase):
    def bound_discovery(self, root, name, harness_scripts=HARNESS_SCRIPTS):
        for other in harness_scripts:
            if other != name:
                harness = root / "Tests/Qml" / other
                harness.unlink()
                # Owner staging still needs dependencies; rg skips symlinks.
                harness.symlink_to(ROOT / "Tests/Qml" / other)

    def stage_repository(self, root, harness_scripts=HARNESS_SCRIPTS):
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
            *harness_scripts.values(),
            "grid-list-warnings.test.py",
            "clock-settings-warnings.test.py",
            "workspace-runtime.test.py",
            "taskbar-grouped-warnings.test.py",
            "setup-layout-geometry.test.py",
            "process-panel-warnings.test.py",
            "bar-status-warnings.test.py",
            "bar-controls-warnings.test.py",
            "bar-pill-warnings.test.py",
            "wallpaper-panel-warnings.test.py",
            "wallpaper-tab-warnings.test.py",
            "settings-singleton-warnings.test.py",
            "wifi-networks-list-warnings.test.py",
            "notification-history-warnings.test.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        helper = ROOT / "Tests/qml_fixture_lint.py"
        if helper.exists():
            shutil.copy2(helper, tests / helper.name)
        if "WallpaperTabWarningsHarness.qml" in harness_scripts:
            # Wallpaper's audit blocks directory discovery after installation.
            # Preload the helper its AboutTab writer imports before that boundary.
            script = tests / "wallpaper-tab-warnings.test.py"
            script.write_text("import qml_fixture_lint\n" + script.read_text())
        for harness in harness_scripts:
            shutil.copy2(ROOT / "Tests/Qml" / harness, tests / "Qml" / harness)
        # Runtime staging copies these dependencies; rg skips symlinks.
        for name in (
            "ClockSettingsWarningsHarness.qml",
            "TaskbarGroupedHarness.qml",
            "WorkspaceHarness.qml",
            "ProcessPanelWarningsHarness.qml",
            "BarStatusHarness.qml",
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
        if "LocationServiceHarness.qml" in harness_scripts:
            fixtures = tests / "Fixtures"
            fixtures.mkdir()
            shutil.copy2(
                ROOT / "Tests/Fixtures/LocationNetworkPlugin.cpp",
                fixtures / "LocationNetworkPlugin.cpp",
            )
        dependencies = {
            "SettingsPanelWarningsHarness.qml": (
                "SettingsSingletonHarness.qml",
                "SetupLayoutGeometryHarness.qml",
            ),
            "WiFiPanelWarningsHarness.qml": ("WiFiNetworksListWarningsHarness.qml",),
            "ChangelogPanelWarningsHarness.qml": (
                "NotificationHistoryWarningsHarness.qml",
            ),
        }
        for owner, names in dependencies.items():
            if owner not in harness_scripts:
                continue
            for dependency in names:
                # Copy inside the sandbox; symlinks keep dependencies undiscovered.
                staged = root / ".fixture-dependencies" / dependency
                staged.parent.mkdir(exist_ok=True)
                shutil.copy2(ROOT / "Tests/Qml" / dependency, staged)
                (tests / "Qml" / dependency).symlink_to(staged)
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
        original = (root / "Assets/settings-default.json").read_bytes()
        if settings_present:
            settings.parent.mkdir(parents=True, mode=0o700)
            settings.touch(mode=0o600)
            settings.write_bytes(original)
        # Keep runtime staging outside the repository's inherited .ignore rules.
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-artifacts-") as temp:
            self.fixture_tmp = Path(temp)
            result = subprocess.run(
                [
                    "bwrap",
                    "--die-with-parent",
                    "--unshare-net",
                    "--ro-bind",
                    "/",
                    "/",
                    "--tmpfs",
                    "/home",
                    # Nested owner sandboxes mount over this empty directory.
                    "--dir",
                    "/home/osso",
                    "--tmpfs",
                    "/tmp",
                    "--bind",
                    str(root),
                    str(root),
                    "--bind",
                    temp,
                    temp,
                    "--dev",
                    "/dev",
                    "--proc",
                    "/proc",
                    "--",
                    str(runner),
                ],
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
            self.assertFalse(home.exists(), "lint created synthetic HOME")
        return result

    def assert_artifacts_are_isolated(self, file):
        harness = Path(file["filename"])
        harness.relative_to(self.fixture_tmp)
        self.assertFalse(harness.parent.exists(), "fixture artifacts leaked")

    def test_requested_routes_are_once_only_strict_and_isolated(self):
        for name in REQUESTED_HARNESSES:
            modes = ("present", "absent", "warning")
            if name == "IpcIdleServicesHarness.qml":
                modes += ("syntax",)
            for mode in modes:
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(name, mode)

    def test_strict_routes_are_once_only_strict_and_isolated(self):
        for name in STRICT_HARNESSES:
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name, mode, STRICT_HARNESSES, STRICT_REPORTS
                    )

    def test_panel_service_routes_are_once_only_strict_and_isolated(self):
        for name, script in PANEL_SERVICE_HARNESSES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        PANEL_SERVICE_REPORTS,
                        PANEL_SERVICE_MARKERS,
                    )

    def test_global_routes_are_once_only_strict_and_isolated(self):
        for name, script in GLOBAL_HARNESSES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        GLOBAL_REPORTS,
                        GLOBAL_MARKERS,
                    )

    def check_requested_route(
        self,
        name,
        mode,
        harness_scripts=REQUESTED_HARNESSES,
        harness_reports=REQUESTED_REPORTS,
        harness_markers=STRICT_MARKERS,
    ):
        # Visualizer's nested sandbox masks /tmp; keep staged owner code outside it.
        with tempfile.TemporaryDirectory(
            prefix="noctalia-fixture-dispatch-", dir="/var/tmp"
        ) as temp:
            root = Path(temp)
            runner = self.stage_repository(root, harness_scripts)
            self.bound_discovery(root, name, harness_scripts)
            diagnostic = f"fixture stderr: {name}\n"
            failing = mode in ("warning", "syntax")
            if failing:
                script = root / "Tests" / harness_scripts[name]
                script.write_text(
                    "import sys\nsys.stderr.write("
                    + repr(diagnostic)
                    + ")\n"
                    + script.read_text()
                )
                harness = root / "Tests/Qml" / name
                if mode == "syntax":
                    # IPC hides semantic warning text; parse diagnostics remain visible.
                    harness.write_text(harness.read_text() + "\n}\n")
                else:
                    harness.write_text(
                        harness.read_text().replace(
                            "{",
                            "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                            1,
                        )
                    )
            result = self.run_checker(runner, root, settings_present=mode == "present")
            output = result.stdout + result.stderr
            reports = lint_reports(result.stdout)
            if name in harness_markers:
                self.assertEqual(output.count(harness_markers[name]), 1, output)
            if failing:
                self.assertNotEqual(result.returncode, 0, output)
                self.assertTrue(result.stderr.startswith(diagnostic), result.stderr)
                if mode == "syntax":
                    self.assertIn("Unexpected token", result.stdout)
                    self.assertIn("[syntax]", result.stdout)
                    self.assertIn("tst_services.qml", result.stdout)
                elif name != "IpcIdleServicesHarness.qml":
                    self.assertIn("missingFixtureValue", output)
                self.assertNotIn("ok qmlStaticCheck", output)
                self.assertNotIn("Checked ", output)
            else:
                self.assertEqual(result.returncode, 0, output)
                self.assertEqual(output.count("ok qmlStaticCheck"), 1)
                self.assertIn("Checked 1 QML files", output)
                self.assertIn("skipped 0", output)
            if name == "IpcIdleServicesHarness.qml":
                self.assertEqual(reports, [])
                self.assertEqual(output.count("HARNESS_LINT_COUNTS"), 1)
                if not failing:
                    self.assertIn("HARNESS_LINT_COUNTS {} TOTAL 0", output)
            else:
                self.assertEqual(len(reports), 1, output)
                self.assertEqual(len(reports[0]["files"]), 1)
                file = reports[0]["files"][0]
                self.assertEqual(Path(file["filename"]).name, harness_reports[name])
                if mode == "warning":
                    self.assertTrue(file["warnings"], output)
                elif name == "LocationServiceHarness.qml":
                    # Unused-import info is not a warning under the strict CLI.
                    self.assertEqual(
                        [w for w in file["warnings"] if w["type"] != "info"], []
                    )
                else:
                    self.assertEqual(file["warnings"], [])
                if name == "FilePickerWarningsHarness.qml":
                    # Owner re-executes with a fresh /tmp in its nested sandbox.
                    harness = Path(file["filename"])
                    harness.relative_to("/tmp")
                    self.assertFalse(harness.parent.exists(), "picker artifacts leaked")
                    self.assertEqual(
                        output.count("FILE_PICKER_CONFIG_NETWORK_MASKED"), 1
                    )
                elif name == "BrightnessKeyboardServicesHarness.qml":
                    self.assertEqual(file["filename"], "/fixture/tst_services.qml")
                else:
                    self.assert_artifacts_are_isolated(file)

    def test_all_harnesses_are_checked_without_fixture_type_warnings(self):
        with tempfile.TemporaryDirectory(prefix="noctalia-fixture-static-") as temp:
            root = Path(temp)
            runner = self.stage_repository(root)
            result = self.run_checker(runner, root)
            files = [
                file
                for report in lint_reports(result.stdout)
                for file in report["files"]
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
                self.bound_discovery(root, name)
                result = self.run_checker(runner, root)
                self.assertEqual(result.returncode, 0, result.stderr)
                reports = lint_reports(result.stdout)
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
                self.bound_discovery(root, name)
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
                self.bound_discovery(root, name)
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
                reports = lint_reports(result.stdout)
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
