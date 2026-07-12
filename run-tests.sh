#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export repo_root

usage() {
    cat <<'USAGE'
Usage: ./run-tests.sh [all|regression|log|unit|structural|qml|probes|notifications]

Commands:
  all            Run non-invasive local regression checks.
  regression     Same as all.
  log            Check the active Quickshell instance log for high-signal errors.
  unit           Run deterministic tests, then structural-reference meta-tests.
  structural     Run structural-reference inventory and coverage meta-tests.
  qml            Run focused qmllint coverage for currently lint-clean QML files.
  probes         Run read-only service probes for notifications, audio, brightness, battery, Bluetooth, clipboard, lock keys, VPN, screen recorder, program checks, system stats, host/fonts, wallpaper/colors, settings, state cache, network state, and power profile.
  notifications  Run notification probe scripts. This visibly sends notifications.

Evidence categories:
  deterministic-unit     Executable JavaScript, Python, and shell behavior tests.
  structural-reference   Source inventory and structural-reference meta-tests.
  qml-static             Static qmllint coverage.
  host-probes            Read-only host and service observations.
  live-log               Active local Quickshell log inspection.
  visible-notifications  Visible notification probes; excluded from all/regression.
USAGE
}

run_unit_tests() {
    local javascript_tests
    if ! javascript_tests="$(cd "$repo_root" && rg --files Tests --glob '*.test.js' | LC_ALL=C sort)"; then
        echo "Failed to discover JavaScript tests" >&2
        return 1
    fi
    if [ -z "$javascript_tests" ]; then
        echo "Failed to discover JavaScript tests: no suites found" >&2
        return 1
    fi

    while IFS= read -r test_file; do
        case "$test_file" in
            Tests/qml-function-inventory.test.js | Tests/source-coverage.test.js)
                continue
                ;;
        esac
        node "$repo_root/$test_file"
    done <<<"$javascript_tests"

    python3 "$repo_root/Tests/calendar-events-safe-get-time.test.py"
    bash "$repo_root/Tests/i18n-json.test.sh"
    bash "$repo_root/Tests/calendar-scripts.test.sh"
    bash "$repo_root/Tests/service-probes-parsing.test.sh"
    bash "$repo_root/Tests/quickshell-regression.test.sh"
    bash "$repo_root/Tests/test-runner-categories.test.sh"
}

run_structural_tests() {
    node "$repo_root/Tests/qml-function-inventory.test.js"
    node "$repo_root/Tests/source-coverage.test.js"
}

run_log_gate() {
    "$repo_root/Bin/dev/quickshell-regression.sh"
}

run_qml_static_check() {
    "$repo_root/Bin/dev/qml-static-check.sh"
}

run_service_probes() {
    NOCTALIA_BLUETOOTHCTL="$repo_root/Tests/fixtures/bluetoothctl" \
        "$repo_root/Bin/dev/service-probes.sh"
}

run_notifications() {
    "$repo_root/Bin/dev/notifications-test.sh" --run
    "$repo_root/Bin/dev/notifications-test-replace.sh" --run
}

run_category() {
    local category="$1"
    local runner="$2"
    echo "=== EVIDENCE START $category ==="
    export -f "$runner"
    local status
    if bash -euo pipefail -c "$runner"; then
        status=0
    else
        status="$?"
    fi
    if [ "$status" -eq 0 ]; then
        echo "=== EVIDENCE PASS $category ==="
        return 0
    fi
    echo "=== EVIDENCE FAIL $category (exit $status) ===" >&2
    return "$status"
}

run_command() {
    local command="${1:-all}"
    case "$command" in
        all | regression)
            echo "=== EVIDENCE EXCLUDED visible-notifications (explicit opt-in) ==="
            run_category "deterministic-unit" run_unit_tests
            local status="$?"
            [ "$status" -eq 0 ] || return "$status"
            run_category "structural-reference" run_structural_tests
            status="$?"
            [ "$status" -eq 0 ] || return "$status"
            run_category "qml-static" run_qml_static_check
            status="$?"
            [ "$status" -eq 0 ] || return "$status"
            run_category "host-probes" run_service_probes
            status="$?"
            [ "$status" -eq 0 ] || return "$status"
            run_category "live-log" run_log_gate
            status="$?"
            [ "$status" -eq 0 ] || return "$status"
            echo "=== REGRESSION PASS ==="
            ;;
        log)
            run_category "live-log" run_log_gate
            ;;
        unit)
            run_category "deterministic-unit" run_unit_tests
            local status="$?"
            [ "$status" -eq 0 ] || return "$status"
            run_category "structural-reference" run_structural_tests
            status="$?"
            [ "$status" -eq 0 ] || return "$status"
            ;;
        structural)
            run_category "structural-reference" run_structural_tests
            ;;
        qml)
            run_category "qml-static" run_qml_static_check
            ;;
        probes)
            run_category "host-probes" run_service_probes
            ;;
        notifications)
            run_category "visible-notifications" run_notifications
            ;;
        -h | --help | help)
            usage
            ;;
        *)
            usage >&2
            return 2
            ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    run_command "${1:-all}"
fi
