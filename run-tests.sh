#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'USAGE'
Usage: ./run-tests.sh [all|regression|log|unit|qml|probes|notifications]

Commands:
  all            Run non-invasive local regression checks.
  regression     Same as all.
  log            Check the active Quickshell instance log for high-signal errors.
  unit           Run cheap pure JavaScript helper tests.
  qml            Run focused qmllint coverage for currently lint-clean QML files.
  probes         Run read-only service probes for notifications, audio, brightness, battery, Bluetooth, clipboard, lock keys, VPN, screen recorder, program checks, system stats, host/fonts, wallpaper/colors, settings, state cache, network state, and power profile.
  notifications  Run notification probe scripts. This visibly sends notifications.
USAGE
}

run_unit_tests() {
    node "$repo_root/Tests/helpers.test.js"
    node "$repo_root/Tests/widget-registry.test.js"
    node "$repo_root/Tests/settings-references.test.js"
    node "$repo_root/Tests/i18n-references.test.js"
    node "$repo_root/Tests/qml-type-annotations.test.js"
    node "$repo_root/Tests/qml-runtime-guards.test.js"
    node "$repo_root/Tests/launcher-guards.test.js"
    node "$repo_root/Tests/emoji-service-guards.test.js"
    node "$repo_root/Tests/media-service-guards.test.js"
    node "$repo_root/Tests/network-service-guards.test.js"
    node "$repo_root/Tests/idle-inhibitor-service-guards.test.js"
    node "$repo_root/Tests/process-service-guards.test.js"
    node "$repo_root/Tests/github-service-guards.test.js"
    node "$repo_root/Tests/wallpaper-service-guards.test.js"
    node "$repo_root/Tests/clipboard-service-guards.test.js"
    node "$repo_root/Tests/font-service-guards.test.js"
    node "$repo_root/Tests/fan-service-guards.test.js"
    node "$repo_root/Tests/file-picker-guards.test.js"
    node "$repo_root/Tests/view-wrapper-guards.test.js"
    node "$repo_root/Tests/dock-menu-guards.test.js"
    node "$repo_root/Tests/emoji-plugin-guards.test.js"
    node "$repo_root/Tests/i18n-service-guards.test.js"
    node "$repo_root/Tests/location-service-guards.test.js"
    node "$repo_root/Tests/logger-guards.test.js"
    node "$repo_root/Tests/panel-service-guards.test.js"
    node "$repo_root/Tests/mango-service-guards.test.js"
    node "$repo_root/Tests/audio-service-guards.test.js"
    node "$repo_root/Tests/applications-plugin-guards.test.js"
    node "$repo_root/Tests/bar-tab-guards.test.js"
    node "$repo_root/Tests/bar-service-guards.test.js"
    node "$repo_root/Tests/battery-widget-guards.test.js"
    node "$repo_root/Tests/brightness-service-guards.test.js"
    node "$repo_root/Tests/bluetooth-service-guards.test.js"
    node "$repo_root/Tests/calendar-month-card-guards.test.js"
    node "$repo_root/Tests/calendar-service-guards.test.js"
    node "$repo_root/Tests/clipboard-plugin-guards.test.js"
    node "$repo_root/Tests/control-center-tab-guards.test.js"
    node "$repo_root/Tests/color-scheme-service-guards.test.js"
    node "$repo_root/Tests/compositor-service-guards.test.js"
    node "$repo_root/Tests/custom-button-settings-guards.test.js"
    node "$repo_root/Tests/dark-mode-service-guards.test.js"
    node "$repo_root/Tests/hyprland-service-guards.test.js"
    node "$repo_root/Tests/niri-service-guards.test.js"
    node "$repo_root/Tests/notification-history-panel-guards.test.js"
    node "$repo_root/Tests/notification-service-gap-guards.test.js"
    node "$repo_root/Tests/power-profile-service-guards.test.js"
    node "$repo_root/Tests/program-checker-service-guards.test.js"
    node "$repo_root/Tests/popup-context-menu-guards.test.js"
    node "$repo_root/Tests/scheme-downloader-guards.test.js"
    node "$repo_root/Tests/screen-recorder-service-guards.test.js"
    node "$repo_root/Tests/shape-corner-helper-guards.test.js"
    node "$repo_root/Tests/session-menu-guards.test.js"
    node "$repo_root/Tests/settings-service-guards.test.js"
    node "$repo_root/Tests/settings-panel-guards.test.js"
    node "$repo_root/Tests/sway-service-guards.test.js"
    node "$repo_root/Tests/system-stat-service-guards.test.js"
    node "$repo_root/Tests/template-processor-guards.test.js"
    node "$repo_root/Tests/tooltip-guards.test.js"
    node "$repo_root/Tests/update-service-guards.test.js"
    node "$repo_root/Tests/timer-card-guards.test.js"
    node "$repo_root/Tests/time-service-guards.test.js"
    node "$repo_root/Tests/tray-menu-guards.test.js"
    node "$repo_root/Tests/tray-widget-guards.test.js"
    node "$repo_root/Tests/vpn-service-guards.test.js"
    node "$repo_root/Tests/wallhaven-service-guards.test.js"
    node "$repo_root/Tests/workspace-guards.test.js"
    node "$repo_root/Tests/color-schemes.test.js"
    node "$repo_root/Tests/template-registry.test.js"
    node "$repo_root/Tests/shell-state-contract.test.js"
    bash "$repo_root/Tests/i18n-json.test.sh"
    bash "$repo_root/Tests/calendar-scripts.test.sh"
    bash "$repo_root/Tests/service-probes-parsing.test.sh"
    bash "$repo_root/Tests/quickshell-regression.test.sh"
}

run_log_gate() {
    "$repo_root/Bin/dev/quickshell-regression.sh"
}

run_qml_static_check() {
    "$repo_root/Bin/dev/qml-static-check.sh"
}

run_service_probes() {
    "$repo_root/Bin/dev/service-probes.sh"
}

run_notifications() {
    "$repo_root/Bin/dev/notifications-test.sh" --run
    "$repo_root/Bin/dev/notifications-test-replace.sh" --run
}

command="${1:-all}"

case "$command" in
    all | regression)
        run_unit_tests
        run_qml_static_check
        run_service_probes
        run_log_gate
        ;;
    log)
        run_log_gate
        ;;
    unit)
        run_unit_tests
        ;;
    qml)
        run_qml_static_check
        ;;
    probes)
        run_service_probes
        ;;
    notifications)
        run_notifications
        ;;
    -h | --help | help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
