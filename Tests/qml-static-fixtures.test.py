"""Bounded real-qmllint regression for behavioral fixture contexts."""

from collections import Counter
import json
import os
import re
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
    "IpcIdleServicesHarness.qml": "tst_services.qml",
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
UTILITY_HARNESSES = {
    "EmojiRecorderWarningsHarness.qml": "emoji-recorder-warnings.test.py",
    "WallhavenPowerWarningsHarness.qml": "wallhaven-power-warnings.test.py",
    "CalendarMonthCardWarningsHarness.qml": "calendar-month-card-warnings.test.py",
    "ShortcutsClockWarningsHarness.qml": "shortcuts-clock-warnings.test.py",
    "AllScreensWarningsHarness.qml": "all-screens-warnings.test.py",
}
UTILITY_REPORTS = {
    "EmojiRecorderWarningsHarness.qml": "tst_emoji_recorder.qml",
    "WallhavenPowerWarningsHarness.qml": "tst_bounded.qml",
    "CalendarMonthCardWarningsHarness.qml": "tst_calendar.qml",
    "ShortcutsClockWarningsHarness.qml": "tst_shortcuts_clock.qml",
    "AllScreensWarningsHarness.qml": "shell.qml",
}
UTILITY_MARKERS = {
    "EmojiRecorderWarningsHarness.qml": "EMOJI_RECORDER_HARNESS_WARNINGS",
    "WallhavenPowerWarningsHarness.qml": "WALLHAVEN_POWER_HARNESS_LINT_COUNTS",
    "CalendarMonthCardWarningsHarness.qml": "CALENDAR_CARD_HARNESS_WARNINGS",
    "ShortcutsClockWarningsHarness.qml": "SHORTCUTS_CLOCK_HARNESS_LINT_WARNINGS",
    "AllScreensWarningsHarness.qml": "ALL_SCREENS_HARNESS_LINT_WARNINGS",
}
POPUP_HISTORY_LOCATION_PROCESS_HARNESSES = {
    "ButtonPopupWarningsHarness.qml": "button-popup-warnings.test.py",
    "HistorySimpleToastHarness.qml": "history-simple-toast-warnings.test.py",
    "LocationTabWarningsHarness.qml": "location-tab-warnings.test.py",
    "ProcessPanelWarningsHarness.qml": "process-panel-warnings.test.py",
}
POPUP_HISTORY_LOCATION_PROCESS_REPORTS = {
    "ButtonPopupWarningsHarness.qml": "shell.qml",
    "HistorySimpleToastHarness.qml": "tst_history_toast.qml",
    "LocationTabWarningsHarness.qml": "tst_location.qml",
    "ProcessPanelWarningsHarness.qml": "tst_process.qml",
}
POPUP_HISTORY_LOCATION_PROCESS_MARKERS = {
    "ButtonPopupWarningsHarness.qml": "BUTTON_POPUP_HARNESS_LINT_WARNINGS",
    "HistorySimpleToastHarness.qml": "HISTORY_TOAST_HARNESS_LINT_COUNTS",
    "LocationTabWarningsHarness.qml": "LOCATION_TAB_HARNESS_LINT_WARNINGS",
    "ProcessPanelWarningsHarness.qml": "PROCESS_PANEL_HARNESS_WARNINGS",
}
SHELL_AUDIO_WIFI_WORKSPACE_BAR_HARNESSES = {
    "ShellRootWarningsProbe.qml": "shell-root-warnings.test.py",
    "AudioDockTabsWarningsHarness.qml": "audio-dock-tabs-warnings.test.py",
    "WiFiNetworksListWarningsHarness.qml": "wifi-networks-list-warnings.test.py",
    "WorkspaceHarness.qml": "workspace-runtime.test.py",
    "BarContentWindowWarningsHarness.qml": "bar-content-window-warnings.test.py",
}
SHELL_AUDIO_WIFI_WORKSPACE_BAR_REPORTS = {
    "ShellRootWarningsProbe.qml": "ShellRootWarningsProbe.qml",
    "AudioDockTabsWarningsHarness.qml": "tst_audio_dock.qml",
    "WiFiNetworksListWarningsHarness.qml": "tst_wifi.qml",
    "WorkspaceHarness.qml": "tst_workspace.qml",
    "BarContentWindowWarningsHarness.qml": "tst_bar_content.qml",
}
SHELL_AUDIO_WIFI_WORKSPACE_BAR_MARKERS = {
    "ShellRootWarningsProbe.qml": "SHELL_ROOT_HARNESS_LINT_COUNTS",
    "AudioDockTabsWarningsHarness.qml": "AUDIO_DOCK_TABS_HARNESS_LINT_WARNINGS",
    "WiFiNetworksListWarningsHarness.qml": "WIFI_LIST_HARNESS_LINT_COUNTS",
    "WorkspaceHarness.qml": "WORKSPACE_HARNESS_LINT_WARNINGS",
    "BarContentWindowWarningsHarness.qml": "BAR_CONTENT_HARNESS_LINT_WARNINGS",
}
AUDIO_TAB_HARNESSES = {
    "AudioCardHarness.qml": "audio-card-warnings.test.py",
    "AudioPanelRegressionHarness.qml": "audio-panel-warnings.test.py",
    "BarTabWarningsHarness.qml": "bar-tab-warnings.test.py",
    "ControlCenterTabWarningsHarness.qml": "control-center-tab-warnings.test.py",
}
AUDIO_TAB_REPORTS = {
    "AudioCardHarness.qml": "tst_audio_card.qml",
    "AudioPanelRegressionHarness.qml": "tst_audio_panel.qml",
    "BarTabWarningsHarness.qml": "tst_tab.qml",
    "ControlCenterTabWarningsHarness.qml": "tst_tab.qml",
}
AUDIO_TAB_MARKERS = {
    "AudioCardHarness.qml": "AUDIO_CARD HARNESS_WARNINGS",
    "AudioPanelRegressionHarness.qml": "AUDIO_PANEL HARNESS_WARNINGS",
    "BarTabWarningsHarness.qml": "BAR_TAB_HARNESS_LINT_WARNINGS",
    "ControlCenterTabWarningsHarness.qml": "CONTROL_CENTER_TAB_HARNESS_LINT_WARNINGS",
}
LAUNCHER_MANGO_PROGRAM_VPN_WALLPAPER_ROUTES = {
    "LauncherWarningsHarness.qml": (
        "launcher-warnings.test.py",
        ["lint-harness", "--max-warnings", "0"],
        False,
        "tst_launcher.qml",
        "LAUNCHER_HARNESS_WARNINGS",
    ),
    "MangoServiceHarness.qml": (
        "mango-service-warnings.test.py",
        ["lint-harness"],
        True,
        "tst_mango.qml",
        "MANGO_HARNESS_LINT_COUNT",
    ),
    "ProgramCheckerHarness.qml": (
        "program-checker-warnings.test.py",
        ["lint-harness", "--max-warnings", "0"],
        False,
        "shell.qml",
        "PROGRAM_CHECKER_LINT_COUNTS",
    ),
    "VPNPanelWarningsHarness.qml": (
        "vpn-panel-warnings.test.py",
        ["lint-harness"],
        True,
        "tst_vpn.qml",
        "VPN_PANEL_HARNESS_LINT_COUNTS",
    ),
    "WallpaperPanelWarningsHarness.qml": (
        "wallpaper-panel-warnings.test.py",
        ["--mode", "lint-harness"],
        False,
        "tst_wallpaper.qml",
        "WALLPAPER_PANEL_HARNESS_LINT_COUNTS",
    ),
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


def settings_file_attempts(audit):
    attempts = []
    for line in audit.splitlines():
        paths = re.findall(r'"((?:\\.|[^"\\])*)"', line)
        if re.search(r"\bexecve(?:at)?\(", line):
            # Only the executable is a file path; argv can contain guard source.
            paths = paths[:1]
        if any("settings.json" in path for path in paths):
            attempts.append(line)
    return attempts


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
            "settings-panel-warnings.test.py",
            "settings-singleton-warnings.test.py",
            "wifi-networks-list-warnings.test.py",
            "notification-history-warnings.test.py",
            "brightness-keyboard-services-warnings.test.py",
            "calendar-month-card-warnings.test.py",
            "simple-widgets-warnings.test.py",
        ):
            shutil.copy2(ROOT / "Tests" / script, tests / script)
        if any(
            name in harness_scripts for name in SHELL_AUDIO_WIFI_WORKSPACE_BAR_HARNESSES
        ):
            for script in (
                "audio-notification-settings-warnings.test.py",
                "wifi-panel-warnings.test.py",
            ):
                shutil.copy2(ROOT / "Tests" / script, tests / script)
        if "VPNPanelWarningsHarness.qml" in harness_scripts:
            shutil.copy2(
                ROOT / "Tests/wifi-panel-warnings.test.py",
                tests / "wifi-panel-warnings.test.py",
            )
        if any(name in harness_scripts for name in AUDIO_TAB_HARNESSES):
            for script in (
                "audio-card-warnings.test.py",
                "audio-notification-settings-warnings.test.py",
            ):
                shutil.copy2(ROOT / "Tests" / script, tests / script)
        if any(
            name in harness_scripts
            for name in (
                "HooksAppThemeWarningsHarness.qml",
                "BusyDividerWarningsHarness.qml",
            )
        ):
            for script in (
                "notifications-hooks-warnings.test.py",
                "grouped-osd-settings-warnings.test.py",
            ):
                shutil.copy2(ROOT / "Tests" / script, tests / script)
        if "ShellRootWarningsProbe.qml" in harness_scripts:
            source = root / ".fixture-dependencies/shell.qml"
            source.parent.mkdir(exist_ok=True)
            shutil.copy2(ROOT / "shell.qml", source)
            (root / "shell.qml").symlink_to(source)
        helper = ROOT / "Tests/qml_fixture_lint.py"
        if helper.exists():
            shutil.copy2(helper, tests / helper.name)
        if any(
            name in harness_scripts
            for name in (
                "WallpaperTabWarningsHarness.qml",
                "CalendarMonthCardWarningsHarness.qml",
                "ShortcutsClockWarningsHarness.qml",
            )
        ):
            # Owner audits block directory discovery after installation.
            # Preload the helper their AboutTab writer imports before that boundary.
            for name in (
                "WallpaperTabWarningsHarness.qml",
                "CalendarMonthCardWarningsHarness.qml",
                "ShortcutsClockWarningsHarness.qml",
            ):
                if name in harness_scripts:
                    script = tests / harness_scripts[name]
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
            if name not in harness_scripts:
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
            "PanelServiceLifecycleHarness.qml": ("tst_panel_service_lifecycle.qml",),
            "AudioPanelRegressionHarness.qml": ("AudioCardHarness.qml",),
            "AudioDockTabsWarningsHarness.qml": ("ClockSettingsWarningsHarness.qml",),
            "ButtonPopupWarningsHarness.qml": ("SimpleWidgetsWarningsHarness.qml",),
            "LocationTabWarningsHarness.qml": ("AboutTabWarningsHarness.qml",),
            "ShortcutsClockWarningsHarness.qml": (
                "CalendarMonthCardWarningsHarness.qml",
            ),
            "SettingsPanelWarningsHarness.qml": (
                "SettingsSingletonHarness.qml",
                "SetupLayoutGeometryHarness.qml",
            ),
            "WiFiPanelWarningsHarness.qml": ("WiFiNetworksListWarningsHarness.qml",),
            "VPNPanelWarningsHarness.qml": ("WiFiNetworksListWarningsHarness.qml",),
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
                link = tests / "Qml" / dependency
                link.unlink(missing_ok=True)
                link.symlink_to(staged)
        runner = root / "Bin/dev/qml-static-check.sh"
        runner.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
        (runner.parent / "qml-static-exclusions.txt").write_text("")
        (root / ".ignore").write_text(
            "Commons/\nModules/\nServices/\nWidgets/\nAssets/\nShaders/\nHelpers/\n"
        )
        return runner

    def run_checker(
        self,
        runner,
        root,
        settings_present=True,
        audit_settings=False,
        owner_audits=False,
        mask_audio=False,
        command=None,
        static_only=False,
    ):
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
            trace = self.fixture_tmp / "checker.trace"
            audit_command = (
                [
                    "strace",
                    "-f",
                    "-qq",
                    "-e",
                    "trace=%file,process" if static_only else "trace=%file",
                    "-o",
                    str(trace),
                ]
                if audit_settings and not owner_audits
                else []
            )
            probe_command = (
                [
                    "python3",
                    "-c",
                    "import os, pathlib, sys; "
                    "assert not any(pathlib.Path('/home/osso/.config').iterdir()); "
                    "assert pathlib.Path.home() == pathlib.Path(sys.argv[1]); "
                    + (
                        "assert not any(pathlib.Path('/run').iterdir()); "
                        "assert os.environ['PULSE_SERVER'] == 'unix:/run/no-audio'; "
                        "assert os.environ['PIPEWIRE_REMOTE'] == '/run/no-audio'; "
                        "print('CHECKER_AUDIO_SOCKETS_MASKED', flush=True); "
                        if mask_audio
                        else ""
                    )
                    + "print('CHECKER_PRIVATE_HOME_CONFIG_MASKED', flush=True); "
                    "os.execv(sys.argv[2], sys.argv[2:])",
                    str(home),
                ]
                if audit_settings or mask_audio
                else []
            )
            result = subprocess.run(
                [
                    *audit_command,
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
                    "--dir",
                    "/home/osso/.config",
                    "--tmpfs",
                    "/tmp",
                    *(["--tmpfs", "/run"] if mask_audio else []),
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
                    *probe_command,
                    *(command or [str(runner)]),
                ],
                cwd=root,
                check=False,
                env=dict(
                    os.environ,
                    HOME=str(home),
                    TMPDIR=temp,
                    **(
                        {
                            "XDG_RUNTIME_DIR": "/run/no-runtime",
                            "PULSE_SERVER": "unix:/run/no-audio",
                            "PIPEWIRE_REMOTE": "/run/no-audio",
                            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/no-bus",
                        }
                        if mask_audio
                        else {}
                    ),
                ),
                capture_output=True,
                text=True,
                timeout=90,
            )
            print(result.stdout + result.stderr, end="")
            if mask_audio:
                self.assertIn("CHECKER_AUDIO_SOCKETS_MASKED", result.stdout)
            if audit_settings:
                self.assertIn("CHECKER_PRIVATE_HOME_CONFIG_MASKED", result.stdout)
                if owner_audits:
                    # Nested strace cannot attach to children already traced here.
                    self.assertEqual(result.stdout.count("CHILD_SETTINGS_AUDIT:"), 1)
                    self.assertIn("zero settings attempts", result.stdout)
                    self.assertIn("host home/config not mounted", result.stdout)
                else:
                    audit = trace.read_text()
                    self.assertEqual(settings_file_attempts(audit), [], audit)
                    if static_only:
                        executables = {
                            Path(path).name
                            for path in re.findall(r'execve\("([^\"]+)"', audit)
                        }
                        self.assertIn("qmllint", executables, audit)
                        self.assertLessEqual(
                            executables,
                            {
                                "bwrap",
                                "bash",
                                "qml-static-check.sh",
                                "python3",
                                "dirname",
                                "rg",
                                "sort",
                                "mktemp",
                                "qmllint",
                                "rm",
                            },
                            executables,
                        )
                        print("CHECKER_STATIC_ONLY_AUDIT: no runtime or gamma commands")
                    trace.unlink()
                print("CHECKER_SETTINGS_AUDIT: zero settings attempts")
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

    def test_utility_routes_are_once_only_strict_and_isolated(self):
        guard_exec = (
            '101 execve("/usr/bin/python3", ["python3", "-c", '
            '"deny(\\"settings.json\\")"], 0x1234) = 0'
        )
        self.assertEqual(settings_file_attempts(guard_exec), [])
        file_attempts = [
            '102 openat(AT_FDCWD, "/home/osso/.config/noctalia/settings.json", O_RDONLY) = 3',
            '102 openat(AT_FDCWD, "settings.json", O_RDONLY) = -1 EACCES (Permission denied)',
            '102 newfstatat(AT_FDCWD, "settings.json", 0x1234, 0) = -1 ENOENT (No such file or directory)',
            '102 readlink("settings.json", 0x1234, 4096) = -1 EACCES (Permission denied)',
            '102 readlink("alias", "/home/osso/.config/noctalia/settings.json", 4096) = 40',
            '102 execve("settings.json", ["python3"], 0x1234) = -1 EACCES (Permission denied)',
            '102 execveat(AT_FDCWD, "settings.json", ["python3"], 0x1234, 0) = -1 EACCES (Permission denied)',
        ]
        self.assertEqual(
            settings_file_attempts("\n".join([guard_exec, *file_attempts])),
            file_attempts,
        )
        for name, script in UTILITY_HARNESSES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        UTILITY_REPORTS,
                        UTILITY_MARKERS,
                    )

    def test_popup_history_location_process_routes_are_strict_and_isolated(self):
        artifact_paths = set()
        for name, script in POPUP_HISTORY_LOCATION_PROCESS_HARNESSES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        POPUP_HISTORY_LOCATION_PROCESS_REPORTS,
                        POPUP_HISTORY_LOCATION_PROCESS_MARKERS,
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_shell_audio_wifi_workspace_bar_routes_are_strict_and_isolated(self):
        artifact_paths = set()
        for name, script in SHELL_AUDIO_WIFI_WORKSPACE_BAR_HARNESSES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        SHELL_AUDIO_WIFI_WORKSPACE_BAR_REPORTS,
                        SHELL_AUDIO_WIFI_WORKSPACE_BAR_MARKERS,
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_audio_tab_checker_routes_are_strict_once_only_and_isolated(self):
        artifact_paths = set()
        for name, script in AUDIO_TAB_HARNESSES.items():
            for mode in ("absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_requested_route(
                        name, mode, {name: script}, AUDIO_TAB_REPORTS, AUDIO_TAB_MARKERS
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_control_overview_session_timer_dispatch_is_strict_and_isolated(self):
        routes = {
            "ControlCenterWidgetLoaderHarness.qml": "control-center-widget-loader-warnings.test.py",
            "OverviewWarningsHarness.qml": "overview-warnings.test.py",
            "SessionMenuWarningsHarness.qml": "session-menu-warnings.test.py",
            "TimerCardHarness.qml": "timer-card-runtime.test.py",
        }
        for name, script in routes.items():
            for warning in (False, True):
                with self.subTest(harness=name, warning=warning):
                    self.check_synthetic_strict_dispatch(name, script, warning)

    def test_hooks_busy_checker_dispatch_is_strict_once_only_and_isolated(self):
        for name, script, arguments, report, marker in (
            (
                "HooksAppThemeWarningsHarness.qml",
                "hooks-app-theme-warnings.test.py",
                ["lint-harness"],
                "tst_hooks_app_theme.qml",
                "HOOKS_APP_THEME_HARNESS_LINT",
            ),
            (
                "BusyDividerWarningsHarness.qml",
                "busy-divider-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
                "tst_busy_divider.qml",
                "BUSY_DIVIDER_HARNESS_LINT_WARNINGS",
            ),
        ):
            for warning in (False, True):
                with self.subTest(harness=name, warning=warning, boundary="dispatch"):
                    self.check_synthetic_strict_dispatch(
                        name, script, warning, arguments
                    )
                for owner_cli in (False, True):
                    with (
                        self.subTest(
                            harness=name, warning=warning, owner_cli=owner_cli
                        ),
                        tempfile.TemporaryDirectory(
                            prefix="noctalia-hooks-busy-dispatch-", dir="/var/tmp"
                        ) as temp,
                    ):
                        root = Path(temp)
                        runner = self.stage_repository(root, {name: script})
                        if warning:
                            harness = root / "Tests/Qml" / name
                            harness.write_text(
                                harness.read_text().replace(
                                    "{",
                                    "{\n  property int injectedWarning: Qt.application.missingFixtureValue",
                                    1,
                                )
                            )
                        result = self.run_checker(
                            runner,
                            root,
                            settings_present=False,
                            audit_settings=True,
                            mask_audio=True,
                            command=(
                                [
                                    "/usr/bin/python3",
                                    str(root / "Tests" / script),
                                    *arguments,
                                ]
                                if owner_cli
                                else None
                            ),
                        )
                        output = result.stdout + result.stderr
                        self.assertEqual(output.count(marker), 1, output)
                        reports = lint_reports(result.stdout)
                        self.assertEqual(len(reports), 1, output)
                        self.assertEqual(len(reports[0]["files"]), 1, output)
                        file = reports[0]["files"][0]
                        self.assertEqual(Path(file["filename"]).name, report)
                        self.assert_artifacts_are_isolated(file)
                        if warning:
                            self.assertNotEqual(result.returncode, 0, output)
                            self.assertIn("missingFixtureValue", output)
                            self.assertTrue(
                                any(
                                    w["id"] == "missing-property"
                                    for w in file["warnings"]
                                ),
                                output,
                            )
                            self.assertNotIn("ok qmlStaticCheck", output)
                            self.assertNotIn("Checked ", output)
                        else:
                            self.assertEqual(result.returncode, 0, output)
                            self.assertEqual(file["warnings"], [])
                            self.assertTrue(file["success"], output)
                            if not owner_cli:
                                self.assertEqual(output.count("ok qmlStaticCheck"), 1)
                                self.assertIn("Checked 1 QML files", output)
                                self.assertIn("skipped 0", output)

    def test_settings_tray_weather_clock_color_lifecycle_routes(self):
        routes = {
            "SettingsSingletonHarness.qml": (
                "settings-singleton-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
            ),
            "TrayDrawerWarningsHarness.qml": (
                "tray-drawer-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
            ),
            "WeatherCardWarningsHarness.qml": (
                "weather-card-effects.test.py",
                ["lint-harness", "--max-warnings", "0"],
            ),
            "ClockWarningsHarness.qml": (
                "clock-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
            ),
            "ColorPickerWarningsHarness.qml": (
                "color-picker-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
            ),
            "tst_panel_service_lifecycle.qml": (
                "panel-service-lifecycle.test.sh",
                ["lint-harness", "--harness", "tst_panel_service_lifecycle.qml"],
            ),
            "PanelServiceLifecycleHarness.qml": (
                "panel-service-lifecycle.test.sh",
                ["lint-harness"],
            ),
        }
        artifact_paths = set()
        for name, (script, arguments) in routes.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_synthetic_strict_dispatch(
                        name,
                        script,
                        mode == "warning",
                        arguments,
                        artifacts=name == "SettingsSingletonHarness.qml",
                        settings_present=mode == "present",
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_image_history_display_appearance_checker_routes(self):
        routes = {
            "ImageShadowWarningsHarness.qml": (
                "image-shadow-warnings.test.py",
                ["lint-harness"],
                False,
            ),
            "NotificationHistoryWarningsHarness.qml": (
                "notification-history-warnings.test.py",
                ["lint-harness"],
                False,
            ),
            "DisplayTabWarningsHarness.qml": (
                "display-tab-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
                True,
            ),
            "SetupAppearanceWarningsHarness.qml": (
                "setup-appearance-warnings.test.py",
                ["lint-harness", "--max-warnings", "0"],
                True,
            ),
        }
        artifact_paths = set()
        for name, (script, arguments, artifacts) in routes.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_synthetic_strict_dispatch(
                        name,
                        script,
                        mode == "warning",
                        arguments,
                        artifacts=artifacts,
                        settings_present=mode == "present",
                        static_only=True,
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_launcher_mango_program_vpn_wallpaper_checker_routes(self):
        artifact_paths = set()
        for name, (
            script,
            arguments,
            artifacts,
            _,
            _,
        ) in LAUNCHER_MANGO_PROGRAM_VPN_WALLPAPER_ROUTES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    filename = self.check_synthetic_strict_dispatch(
                        name,
                        script,
                        mode == "warning",
                        arguments,
                        artifacts=artifacts,
                        settings_present=mode == "present",
                        static_only=True,
                    )
                    self.assertNotIn(filename, artifact_paths, "artifact path reused")
                    artifact_paths.add(filename)

    def test_launcher_mango_program_vpn_wallpaper_real_strict_routes(self):
        for name, (
            script,
            _,
            _,
            report,
            marker,
        ) in LAUNCHER_MANGO_PROGRAM_VPN_WALLPAPER_ROUTES.items():
            for mode in ("present", "absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name, mode, {name: script}, {name: report}, {name: marker}
                    )

    def check_synthetic_strict_dispatch(
        self,
        name,
        script,
        warning,
        arguments=None,
        artifacts=False,
        settings_present=False,
        static_only=False,
    ):
        if arguments is None:
            arguments = ["lint-harness", "--max-warnings", "0"]
        # Owner semantics are proved separately; exercise only the dispatch boundary.
        with tempfile.TemporaryDirectory(prefix="noctalia-dispatch-") as temp:
            root = Path(temp)
            runner = root / "Bin/dev/qml-static-check.sh"
            runner.parent.mkdir(parents=True)
            shutil.copy2(ROOT / "Bin/dev/qml-static-check.sh", runner)
            (runner.parent / "qml-static-exclusions.txt").write_text("")
            (root / "Assets").mkdir()
            (root / "Assets/settings-default.json").write_text("{}\n")
            (root / "calls").write_text("")
            harness = root / "Tests/Qml" / name
            harness.parent.mkdir(parents=True)
            harness.write_text(
                "import QtQuick\nQtObject {\n"
                + (
                    "property int probe: Qt.application.missingFixtureValue\n"
                    if warning
                    else "property int probe: 42\n"
                )
                + "}\n"
            )
            # Synthetic executable checks the exact public CLI, then runs real lint.
            # No owner runtime imports or desktop actions can execute here.
            owner = root / "Tests" / script
            owner.write_text(
                "#!/usr/bin/python3\n"
                "import os, pathlib, shutil, subprocess, sys, tempfile\n"
                + (
                    f"assert sys.argv[1:-2] == {arguments!r}, sys.argv\n"
                    "assert sys.argv[-2] == '--artifacts', sys.argv\n"
                    "artifacts = pathlib.Path(sys.argv[-1])\n"
                    "artifacts.relative_to(pathlib.Path(os.environ['TMPDIR']))\n"
                    "assert artifacts.parent.stat().st_mode & 0o777 == 0o700\n"
                    "assert not artifacts.exists(), 'artifact path reused'\n"
                    "artifacts.mkdir(mode=0o700)\n"
                    if artifacts
                    else f"assert sys.argv[1:] == {arguments!r}, sys.argv\n"
                )
                + "sys.stderr.write('dispatch stderr visible\\n')\n"
                "root = pathlib.Path(__file__).resolve().parents[1]\n"
                "with (root / 'calls').open('a') as calls:\n"
                "    calls.write(pathlib.Path(__file__).name + '\\n')\n"
                + (
                    "with tempfile.TemporaryDirectory(prefix='strict-dispatch-', dir=artifacts) as temp:\n"
                    if artifacts
                    else "with tempfile.TemporaryDirectory(prefix='strict-dispatch-') as temp:\n"
                )
                + "    assert pathlib.Path(temp).stat().st_mode & 0o777 == 0o700\n"
                "    harness = pathlib.Path(temp) / 'shell.qml'\n"
                f"    shutil.copy2(root / 'Tests/Qml' / {name!r}, harness)\n"
                "    result = subprocess.run(['/usr/lib/qt6/bin/qmllint', '--bare', "
                "'-I', '/usr/lib/qt6/qml', '--max-warnings', '0', '--json', '-', str(harness)], "
                "capture_output=True, text=True, check=False, timeout=30)\n"
                "    print(result.stdout, end='', flush=True)\n"
                "    print(result.stderr, end='', file=sys.stderr, flush=True)\n"
                "    code = result.returncode\n"
                "sys.exit(code)\n"
            )
            owner.chmod(0o700)
            result = self.run_checker(
                runner,
                root,
                settings_present=settings_present,
                audit_settings=True,
                mask_audio=True,
                static_only=static_only,
            )
            output = result.stdout + result.stderr
            self.assertEqual((root / "calls").read_text().splitlines(), [script])
            self.assertIn("dispatch stderr visible", result.stderr)
            reports = lint_reports(result.stdout)
            self.assertEqual(len(reports), 1, output)
            self.assertEqual(len(reports[0]["files"]), 1, output)
            file = reports[0]["files"][0]
            self.assert_artifacts_are_isolated(file)
            if warning:
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn("missingFixtureValue", output)
                self.assertTrue(
                    any(w["id"] == "missing-property" for w in file["warnings"]), output
                )
                self.assertNotIn("ok qmlStaticCheck", output)
                self.assertNotIn("Checked ", output)
            else:
                self.assertEqual(result.returncode, 0, output)
                self.assertEqual(file["warnings"], [])
                self.assertEqual(output.count("ok qmlStaticCheck"), 1)
                self.assertIn("Checked 1 QML files", output)
                self.assertIn("skipped 0", output)
            return file["filename"]

    def test_audio_tab_owner_clis_reject_injected_semantic_warnings(self):
        for name, script in AUDIO_TAB_HARNESSES.items():
            for mode in ("absent", "warning"):
                with self.subTest(harness=name, mode=mode):
                    self.check_requested_route(
                        name,
                        mode,
                        {name: script},
                        AUDIO_TAB_REPORTS,
                        AUDIO_TAB_MARKERS,
                        owner_cli=True,
                    )

    def check_requested_route(
        self,
        name,
        mode,
        harness_scripts=REQUESTED_HARNESSES,
        harness_reports=REQUESTED_REPORTS,
        harness_markers=STRICT_MARKERS,
        owner_cli=False,
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
                    # Exercise JSON parse diagnostics separately from semantic warnings.
                    harness.write_text(harness.read_text() + "\n}\n")
                elif not owner_cli:
                    harness.write_text(
                        harness.read_text().replace(
                            "{",
                            "{\n  property int regressionWarning: Qt.application.missingFixtureValue",
                            1,
                        )
                    )
            command = None
            if owner_cli:
                command = [
                    "/usr/bin/python3",
                    str(root / "Tests" / harness_scripts[name]),
                    "lint-harness",
                ]
                if name in (
                    "BarTabWarningsHarness.qml",
                    "ControlCenterTabWarningsHarness.qml",
                ):
                    command += ["--max-warnings", "0"]
                if failing:
                    command.append("--inject-warning")
            result = self.run_checker(
                runner,
                root,
                command=command,
                mask_audio=name in AUDIO_TAB_HARNESSES
                or name in LAUNCHER_MANGO_PROGRAM_VPN_WALLPAPER_ROUTES,
                settings_present=mode == "present",
                audit_settings=name in UTILITY_HARNESSES
                or name in POPUP_HISTORY_LOCATION_PROCESS_HARNESSES
                or name in SHELL_AUDIO_WIFI_WORKSPACE_BAR_HARNESSES
                or name in AUDIO_TAB_HARNESSES,
                owner_audits=name
                in (
                    "EmojiRecorderWarningsHarness.qml",
                    "AllScreensWarningsHarness.qml",
                    "ButtonPopupWarningsHarness.qml",
                    "ProcessPanelWarningsHarness.qml",
                    "ShellRootWarningsProbe.qml",
                    "WiFiNetworksListWarningsHarness.qml",
                    "WorkspaceHarness.qml",
                    "BarContentWindowWarningsHarness.qml",
                    "BarTabWarningsHarness.qml",
                    "ControlCenterTabWarningsHarness.qml",
                ),
            )
            output = result.stdout + result.stderr
            reports = lint_reports(result.stdout)
            if name in harness_markers:
                self.assertEqual(output.count(harness_markers[name]), 1, output)
            if failing:
                self.assertNotEqual(result.returncode, 0, output)
                self.assertTrue(result.stderr.startswith(diagnostic), result.stderr)
                if mode == "warning":
                    self.assertIn(
                        "missingLintProbe" if owner_cli else "missingFixtureValue",
                        output,
                    )
                self.assertNotIn("ok qmlStaticCheck", output)
                self.assertNotIn("Checked ", output)
            else:
                self.assertEqual(result.returncode, 0, output)
                if not owner_cli:
                    self.assertEqual(output.count("ok qmlStaticCheck"), 1)
                    self.assertIn("Checked 1 QML files", output)
                    self.assertIn("skipped 0", output)
            self.assertEqual(len(reports), 1, output)
            self.assertEqual(len(reports[0]["files"]), 1)
            file = reports[0]["files"][0]
            self.assertEqual(Path(file["filename"]).name, harness_reports[name])
            if name == "IpcIdleServicesHarness.qml":
                self.assertEqual(file["success"], not failing)
                expected_counts = {}
                if failing:
                    warning_id = "syntax" if mode == "syntax" else "missing-property"
                    self.assertEqual(
                        [(w["id"], w["type"]) for w in file["warnings"]],
                        [(warning_id, "warning")],
                    )
                    self.assertEqual(
                        file["warnings"][0]["message"],
                        "Unexpected token `}'"
                        if mode == "syntax"
                        else 'Member "missingFixtureValue" not found on type "QQmlApplication"',
                    )
                    expected_counts = {warning_id: 1}
                else:
                    self.assertEqual(file["warnings"], [])
                self.assertEqual(output.count("HARNESS_LINT_COUNTS"), 1)
                self.assertIn(
                    f"HARNESS_LINT_COUNTS {expected_counts} TOTAL {sum(expected_counts.values())}",
                    output.splitlines(),
                )
            elif mode == "warning":
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
                self.assertEqual(output.count("FILE_PICKER_CONFIG_NETWORK_MASKED"), 1)
            elif name == "MangoServiceHarness.qml":
                self.assertEqual(file["filename"], "/fixture/tst_mango.qml")
            elif name == "ProgramCheckerHarness.qml":
                self.assertEqual(file["filename"], "/fixture/shell.qml")
            elif name == "WallhavenPowerWarningsHarness.qml":
                self.assertEqual(file["filename"], "/fixture/tst_bounded.qml")
            elif name == "BrightnessKeyboardServicesHarness.qml":
                self.assertEqual(file["filename"], "/fixture/tst_services.qml")
            else:
                self.assert_artifacts_are_isolated(file)
            return file["filename"]

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
                self.assertIn(diagnostic, result.stderr)
                if name in (
                    "BatteryPanelWarningsHarness.qml",
                    "BarWidgetLoaderOwnerHarness.qml",
                    "BatterySettingsWarningsHarness.qml",
                ):
                    self.assertTrue(result.stderr.startswith(diagnostic), result.stderr)
                    self.assertIn("AssertionError", result.stderr)
                else:
                    self.assertNotRegex(
                        result.stderr,
                        r"Traceback|AssertionError|cp:|cannot stat|No such file or directory|"
                        r"ModuleNotFoundError|ImportError",
                    )
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
                self.assertTrue(
                    any(
                        warning["type"] == "warning"
                        and warning["id"] == "missing-property"
                        and "missingFixtureValue" in warning["message"]
                        for warning in report["files"][0]["warnings"]
                    ),
                    report,
                )
                if name in ARTIFACT_HARNESSES:
                    self.assert_artifacts_are_isolated(report["files"][0])
                self.assertEqual(
                    Path(report["files"][0]["filename"]).name,
                    HARNESS_REPORTS[name],
                )


if __name__ == "__main__":
    unittest.main()
