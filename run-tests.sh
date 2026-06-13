#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'USAGE'
Usage: ./run-tests.sh [all|regression|log|unit|notifications]

Commands:
  all            Run non-invasive local regression checks.
  regression     Same as all.
  log            Check the active Quickshell instance log for high-signal errors.
  unit           Run cheap pure JavaScript helper tests.
  notifications  Run notification probe scripts. This visibly sends notifications.
USAGE
}

run_unit_tests() {
    node "$repo_root/Tests/helpers.test.js"
}

run_log_gate() {
    "$repo_root/Bin/dev/quickshell-regression.sh"
}

run_notifications() {
    "$repo_root/Bin/dev/notifications-test.sh"
    "$repo_root/Bin/dev/notifications-test-replace.sh"
}

command="${1:-all}"

case "$command" in
    all | regression)
        run_unit_tests
        run_log_gate
        ;;
    log)
        run_log_gate
        ;;
    unit)
        run_unit_tests
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
