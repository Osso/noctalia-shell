#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

set +e
output="$(
    cd "$repo_root"
    python3 Bin/check-calendar.py 2>&1
)"
status=$?
set -e

if [[ "$output" == *"Traceback"* ]]; then
    echo "calendar availability check must not print a traceback" >&2
    echo "$output" >&2
    exit 1
fi

if [[ "$status" -ne 0 ]]; then
    echo "calendar availability check exited with status $status" >&2
    echo "$output" >&2
    exit 1
fi

if [[ "$output" != "available" && "$output" != unavailable:* ]]; then
    echo "unexpected calendar availability output: $output" >&2
    exit 1
fi

echo "ok testCalendarAvailabilityScript"
