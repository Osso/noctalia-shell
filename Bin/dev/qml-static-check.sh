#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "missing required command: $name" >&2
        exit 2
    fi
}

qmllint=/usr/lib/qt6/bin/qmllint
if [ ! -x "$qmllint" ]; then
    echo "missing required Qt 6 qmllint: $qmllint" >&2
    exit 2
fi
require_command rg
require_command python3

mapfile -t qml_files < <(cd "$repo_root" && rg --files -g '*.qml' | sort)
mapfile -t js_files < <(cd "$repo_root" && rg --files -g '*.js' | sort)
module_root="$(mktemp -d "${TMPDIR:-/tmp}/noctalia-qmllint-modules.XXXXXX")"
trap 'rm -rf -- "$module_root"' EXIT

# Quickshell supplies qs.* virtually; qmllint needs equivalent on-disk modules.
python3 - "$repo_root" "$module_root" "${qml_files[@]}" "${js_files[@]}" <<'PY'
from pathlib import Path
import re
import shutil
import sys

source_root = Path(sys.argv[1])
qs_root = Path(sys.argv[2]) / "qs"
modules = {Path("."): []}
for relative in sorted(sys.argv[3:]):
    path = Path(relative)
    target = qs_root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    source = source_root / path
    # Copies retain qmldir context; qmllint resolves symlinks outside the module.
    shutil.copyfile(source, target)
    if path.suffix != ".qml":
        continue
    directory = path.parent
    for parent in (directory, *directory.parents):
        modules.setdefault(parent, [])
    singleton = bool(
        re.search(r"^\s*pragma\s+Singleton\b", source.read_text(), re.MULTILINE)
    )
    prefix = "singleton " if singleton else ""
    modules[directory].append(f"{prefix}{path.stem} 1.0 {path.name}\n")

for directory, declarations in sorted(modules.items()):
    module = ".".join(("qs", *directory.parts))
    (qs_root / directory / "qmldir").write_text(
        f"module {module}\n" + "".join(declarations)
    )
PY

exclusions_file="$repo_root/Bin/dev/qml-static-exclusions.txt"

declare -A excluded_files=()
while IFS= read -r file || [ -n "$file" ]; do
    if [ -z "$file" ]; then
        continue
    fi
    excluded_files["$file"]=1
done <"$exclusions_file"

checked_count=0
skipped_count=0
scheme_downloader_checked=false

for file in "${qml_files[@]}"; do
    if [ -n "${excluded_files[$file]:-}" ]; then
        skipped_count=$((skipped_count + 1))
        continue
    fi

    case "$file" in
    Tests/Qml/BatteryTabWarningsHarness.qml)
        python3 "$repo_root/Tests/battery-tab-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BatteryWidgetWarningsHarness.qml)
        python3 "$repo_root/Tests/battery-widget-warnings.test.py" lint-harness
        ;;
    Tests/Qml/MediaMiniWarningsHarness.qml)
        python3 "$repo_root/Tests/media-mini-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BarWidgetMetadataHarness.qml)
        python3 "$repo_root/Tests/bar-widget-metadata-runtime.test.py" lint-harness
        ;;
    Tests/Qml/TaskbarGroupedHarness.qml)
        python3 "$repo_root/Tests/taskbar-grouped-warnings.test.py" lint-harness
        ;;
    Tests/Qml/SetupLayoutGeometryHarness.qml)
        python3 "$repo_root/Tests/setup-layout-geometry.test.py" lint-harness
        ;;
    Tests/Qml/SchemeDownloaderHarness.qml | Tests/Qml/SchemeDownloaderTransport.qml)
        # Owner lint checks both exact staged runtime files in one invocation.
        if [ "$scheme_downloader_checked" = false ]; then
            python3 "$repo_root/Tests/scheme-downloader-runtime.test.py" lint-harness
            scheme_downloader_checked=true
        fi
        ;;
    Tests/Qml/ResidualSingletonOwnersHarness.qml)
        python3 "$repo_root/Tests/residual-singleton-owners.test.py" lint-harness
        ;;
    Tests/Qml/ClipboardPreviewWarningsHarness.qml)
        python3 "$repo_root/Tests/clipboard-preview-warnings.test.py" lint-harness
        ;;
    Tests/Qml/RootServiceHarness.qml)
        python3 "$repo_root/Tests/root-service-warnings.test.py" lint-harness
        ;;
    Tests/Qml/ServiceCohortHarness.qml)
        python3 "$repo_root/Tests/service-cohort-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BrightnessPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/brightness-panel-warnings.test.py" lint-harness \
            --artifacts "$module_root/brightness-panel"
        ;;
    Tests/Qml/ActiveWindowWarningsHarness.qml)
        python3 "$repo_root/Tests/active-window-warnings.test.py" lint-harness
        ;;
    Tests/Qml/TrayWidgetWarningsHarness.qml)
        python3 "$repo_root/Tests/tray-widget-warnings.test.py" lint-harness
        ;;
    Tests/Qml/WallpaperServiceHarness.qml)
        python3 "$repo_root/Tests/wallpaper-service-warnings.test.py" lint-harness \
            --artifacts "$module_root/wallpaper-service"
        ;;
    Tests/Qml/TaskbarHarness.qml)
        python3 "$repo_root/Tests/taskbar-warnings.test.py" lint-harness
        ;;
    Tests/Qml/AboutTabWarningsHarness.qml)
        python3 "$repo_root/Tests/about-tab-warnings.test.py" lint-harness
        ;;
    Tests/Qml/RemainingLayoutGeometryHarness.qml)
        python3 "$repo_root/Tests/remaining-layout-geometry.test.py" lint-harness \
            --artifacts "$module_root/remaining-layout"
        ;;
    Tests/Qml/BatteryPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/battery-panel-warnings.test.py" lint-harness \
            --artifacts "$module_root/battery-panel"
        ;;
    Tests/Qml/ColorSchemeServiceHarness.qml)
        python3 "$repo_root/Tests/color-scheme-service-runtime.test.py" lint-harness \
            --artifacts "$module_root/color-scheme-service"
        ;;
    Tests/Qml/BarWidgetLoaderOwnerHarness.qml)
        python3 "$repo_root/Tests/layer-bar-owner-warnings.test.py" loader lint-harness \
            --artifacts "$module_root/bar-widget-loader-owner"
        ;;
    Tests/Qml/NotificationWarningsHarness.qml)
        python3 "$repo_root/Tests/notification-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/CompositorServiceHarness.qml)
        python3 "$repo_root/Tests/compositor-service-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/compositor-service"
        ;;
    Tests/Qml/ShellStateHarness.qml)
        python3 "$repo_root/Tests/shell-state-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/BatterySettingsWarningsHarness.qml)
        python3 "$repo_root/Tests/battery-settings-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/battery-settings"
        ;;
    Tests/Qml/OSDWarningsHarness.qml)
        python3 "$repo_root/Tests/osd-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SimpleServiceHarness.qml)
        python3 "$repo_root/Tests/simple-service-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BluetoothPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/bluetooth-panel-warnings.test.py" lint-harness
        ;;
    Tests/Qml/IpcIdleServicesHarness.qml)
        python3 "$repo_root/Tests/ipc-idle-services-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/ipc-idle-services"
        ;;
    Tests/Qml/BrightnessKeyboardServicesHarness.qml)
        python3 "$repo_root/Tests/brightness-keyboard-services-warnings.test.py" lint-harness \
            --artifacts "$module_root/brightness-keyboard-services"
        ;;
    Tests/Qml/DockMenuWarningsHarness.qml)
        python3 "$repo_root/Tests/dock-menu-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/WallpaperTabWarningsHarness.qml)
        python3 "$repo_root/Tests/wallpaper-tab-warnings.test.py" lint-harness
        ;;
    Tests/Qml/I18nThemeIconsHarness.qml)
        python3 "$repo_root/Tests/i18n-theme-icons-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/VisualizerProfileHarness.qml)
        python3 "$repo_root/Tests/visualizer-profile-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SimpleWidgetsWarningsHarness.qml)
        python3 "$repo_root/Tests/simple-widgets-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SetupWallpaperWarningsHarness.qml)
        python3 "$repo_root/Tests/setup-wallpaper-warnings.test.py" lint-harness
        ;;
    Tests/Qml/NotificationServiceHarness.qml)
        python3 "$repo_root/Tests/notification-service-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SettingsPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/settings-panel-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/settings-panel"
        ;;
    Tests/Qml/WiFiPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/wifi-panel-warnings.test.py" lint-harness \
            --artifacts "$module_root/wifi-panel"
        ;;
    Tests/Qml/BarWarningsHarness.qml)
        python3 "$repo_root/Tests/bar-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ChangelogPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/changelog-panel-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ControlCenterPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/control-center-panel-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/control-center-panel"
        ;;
    Tests/Qml/LocationServiceHarness.qml)
        python3 "$repo_root/Tests/location-service-runtime.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/MainScreenWarningsHarness.qml)
        python3 "$repo_root/Tests/main-screen-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/FilePickerWarningsHarness.qml)
        python3 "$repo_root/Tests/file-picker-warnings.test.py" --mode lint-harness --max-warnings 0
        ;;
    Tests/Qml/EmojiRecorderWarningsHarness.qml)
        python3 "$repo_root/Tests/emoji-recorder-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/WallhavenPowerWarningsHarness.qml)
        python3 "$repo_root/Tests/wallhaven-power-warnings.test.py" lint-harness
        ;;
    Tests/Qml/CalendarMonthCardWarningsHarness.qml)
        python3 "$repo_root/Tests/calendar-month-card-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ShortcutsClockWarningsHarness.qml)
        python3 "$repo_root/Tests/shortcuts-clock-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/AllScreensWarningsHarness.qml)
        python3 "$repo_root/Tests/all-screens-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ButtonPopupWarningsHarness.qml)
        python3 "$repo_root/Tests/button-popup-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/HistorySimpleToastHarness.qml)
        python3 "$repo_root/Tests/history-simple-toast-warnings.test.py" lint-harness
        ;;
    Tests/Qml/LocationTabWarningsHarness.qml)
        python3 "$repo_root/Tests/location-tab-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ProcessPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/process-panel-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/process-panel"
        ;;
    Tests/Qml/ShellRootWarningsProbe.qml)
        python3 "$repo_root/Tests/shell-root-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/AudioDockTabsWarningsHarness.qml)
        python3 "$repo_root/Tests/audio-dock-tabs-warnings.test.py" lint-harness
        ;;
    Tests/Qml/WiFiNetworksListWarningsHarness.qml)
        python3 "$repo_root/Tests/wifi-networks-list-warnings.test.py" lint-harness
        ;;
    Tests/Qml/WorkspaceHarness.qml)
        python3 "$repo_root/Tests/workspace-runtime.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/BarContentWindowWarningsHarness.qml)
        python3 "$repo_root/Tests/bar-content-window-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/AudioCardHarness.qml)
        python3 "$repo_root/Tests/audio-card-warnings.test.py" lint-harness
        ;;
    Tests/Qml/AudioPanelRegressionHarness.qml)
        python3 "$repo_root/Tests/audio-panel-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BarTabWarningsHarness.qml)
        python3 "$repo_root/Tests/bar-tab-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ControlCenterTabWarningsHarness.qml)
        python3 "$repo_root/Tests/control-center-tab-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ControlCenterWidgetLoaderHarness.qml)
        python3 "$repo_root/Tests/control-center-widget-loader-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/OverviewWarningsHarness.qml)
        python3 "$repo_root/Tests/overview-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SessionMenuWarningsHarness.qml)
        python3 "$repo_root/Tests/session-menu-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/TimerCardHarness.qml)
        python3 "$repo_root/Tests/timer-card-runtime.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/HooksAppThemeWarningsHarness.qml)
        python3 "$repo_root/Tests/hooks-app-theme-warnings.test.py" lint-harness
        ;;
    Tests/Qml/BusyDividerWarningsHarness.qml)
        python3 "$repo_root/Tests/busy-divider-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/SettingsSingletonHarness.qml)
        python3 "$repo_root/Tests/settings-singleton-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/settings-singleton"
        ;;
    Tests/Qml/TrayDrawerWarningsHarness.qml)
        python3 "$repo_root/Tests/tray-drawer-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/WeatherCardWarningsHarness.qml)
        python3 "$repo_root/Tests/weather-card-effects.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ClockWarningsHarness.qml)
        python3 "$repo_root/Tests/clock-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ColorPickerWarningsHarness.qml)
        python3 "$repo_root/Tests/color-picker-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/ImageShadowWarningsHarness.qml)
        python3 "$repo_root/Tests/image-shadow-warnings.test.py" lint-harness
        ;;
    Tests/Qml/NotificationHistoryWarningsHarness.qml)
        python3 "$repo_root/Tests/notification-history-warnings.test.py" lint-harness
        ;;
    Tests/Qml/DisplayTabWarningsHarness.qml)
        python3 "$repo_root/Tests/display-tab-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/display-tab"
        ;;
    Tests/Qml/SetupAppearanceWarningsHarness.qml)
        python3 "$repo_root/Tests/setup-appearance-warnings.test.py" lint-harness \
            --max-warnings 0 --artifacts "$module_root/setup-appearance"
        ;;
    Tests/Qml/LauncherWarningsHarness.qml)
        python3 "$repo_root/Tests/launcher-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/MangoServiceHarness.qml)
        python3 "$repo_root/Tests/mango-service-warnings.test.py" lint-harness \
            --artifacts "$module_root/mango-service"
        ;;
    Tests/Qml/ProgramCheckerHarness.qml)
        python3 "$repo_root/Tests/program-checker-warnings.test.py" lint-harness --max-warnings 0
        ;;
    Tests/Qml/VPNPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/vpn-panel-warnings.test.py" lint-harness \
            --artifacts "$module_root/vpn-panel"
        ;;
    Tests/Qml/WallpaperPanelWarningsHarness.qml)
        python3 "$repo_root/Tests/wallpaper-panel-warnings.test.py" --mode lint-harness
        ;;
    Tests/Qml/tst_panel_service_lifecycle.qml)
        "$repo_root/Tests/panel-service-lifecycle.test.sh" lint-harness \
            --harness tst_panel_service_lifecycle.qml
        printf '\n'
        ;;
    Tests/Qml/PanelServiceLifecycleHarness.qml)
        "$repo_root/Tests/panel-service-lifecycle.test.sh" lint-harness
        printf '\n'
        ;;
    Tests/network-service/shell.qml)
        python3 "$repo_root/Tests/network-service-warnings.test.py" lint-harness
        ;;
    *)
        "$qmllint" -I "$module_root" "$module_root/qs/$file"
        ;;
    esac
    checked_count=$((checked_count + 1))
done

for file in "${!excluded_files[@]}"; do
    if [ ! -f "$repo_root/$file" ]; then
        echo "excluded QML file does not exist: $file" >&2
        exit 1
    fi

    if "$qmllint" -I "$module_root" "$module_root/qs/$file" >/dev/null 2>&1; then
        echo "excluded QML file now passes qmllint; remove it from $exclusions_file: $file" >&2
        exit 1
    fi
done

echo "ok qmlStaticCheck"
echo "Checked $checked_count QML files with qmllint; skipped $skipped_count documented exclusions."
