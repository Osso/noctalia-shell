#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

run_calendar_script() {
    local script="$1"
    shift

    set +e
    output="$(
        cd "$repo_root"
        python3 "$script" "$@" 2>&1
    )"
    status=$?
    set -e
}

assert_no_traceback() {
    local label="$1"

    if [[ "$output" == *"Traceback"* ]]; then
        echo "$label must not print a traceback" >&2
        echo "$output" >&2
        exit 1
    fi
}

assert_exit_zero() {
    local label="$1"

    if [[ "$status" -ne 0 ]]; then
        echo "$label exited with status $status" >&2
        echo "$output" >&2
        exit 1
    fi
}

run_calendar_script Bin/check-calendar.py
assert_no_traceback "calendar availability check"
assert_exit_zero "calendar availability check"

if [[ "$output" != "available" && "$output" != unavailable:* ]]; then
    echo "unexpected calendar availability output: $output" >&2
    exit 1
fi

run_calendar_script Bin/list-calendars.py
assert_no_traceback "calendar list script"
assert_exit_zero "calendar list script"

if ! printf '%s' "$output" | jq -e 'type == "array"' >/dev/null; then
    echo "calendar list script must output a JSON array" >&2
    echo "$output" >&2
    exit 1
fi

run_calendar_script Bin/calendar-events.py 0 4102444800
assert_no_traceback "calendar events script"
assert_exit_zero "calendar events script"

if ! printf '%s' "$output" | jq -e 'type == "array"' >/dev/null; then
    echo "calendar events script must output a JSON array" >&2
    echo "$output" >&2
    exit 1
fi

echo "ok testCalendarScripts"
