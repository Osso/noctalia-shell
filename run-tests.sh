#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'USAGE'
Usage: ./run-tests.sh [all|regression|log|unit|probes|notifications]

Commands:
  all            Run non-invasive local regression checks.
  regression     Same as all.
  log            Check the active Quickshell instance log for high-signal errors.
  unit           Run cheap pure JavaScript helper tests.
  probes         Run read-only service probes for notifications, audio, brightness, clipboard, and wallpaper/colors.
  notifications  Run notification probe scripts. This visibly sends notifications.
USAGE
}

run_unit_tests() {
    node "$repo_root/Tests/helpers.test.js"
}

run_log_gate() {
    "$repo_root/Bin/dev/quickshell-regression.sh"
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
        run_service_probes
        run_log_gate
        ;;
    log)
        run_log_gate
        ;;
    unit)
        run_unit_tests
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
