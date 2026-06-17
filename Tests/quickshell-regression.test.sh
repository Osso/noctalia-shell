#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/Bin/dev/quickshell-regression.sh"

sample_log='WARN scene: @Old.qml[1:-1]: TypeError: Cannot read property '\''name'\'' of null
INFO: Reloading configuration...
INFO qml: [20260615-124024] Shell Service started
INFO qml: [20260615-124025] Brightness Detected DDC Monitor'

filtered="$(current_reload_log "$sample_log")"

if printf '%s\n' "$filtered" | rg -q "Old.qml"; then
    echo "current_reload_log kept a stale pre-reload error" >&2
    exit 1
fi

if ! printf '%s\n' "$filtered" | rg -q "Reloading configuration"; then
    echo "current_reload_log dropped the reload marker" >&2
    exit 1
fi

if ! printf '%s\n' "$filtered" | rg -q "Detected DDC Monitor"; then
    echo "current_reload_log dropped current reload lines" >&2
    exit 1
fi

fatal_pattern="$(fatal_log_pattern)"

for sample in \
    'WARN qml: TypeError: Cannot read property name of null' \
    'WARN qml: ReferenceError: PanelService is not defined' \
    'WARN qml: module QtQuick.Controls is not installed' \
    'ERROR qml: failed to load component' \
    'CRITICAL: core dumped'; do
    if ! printf '%s\n' "$sample" | rg -i "$fatal_pattern" >/dev/null; then
        echo "fatal_log_pattern missed: $sample" >&2
        exit 1
    fi
done

for sample in \
    'INFO qml: [20260615-124024] Shell Service started' \
    'INFO qml: [20260615-124025] Brightness Detected DDC Monitor'; do
    if printf '%s\n' "$sample" | rg -i "$fatal_pattern" >/dev/null; then
        echo "fatal_log_pattern matched non-fatal line: $sample" >&2
        exit 1
    fi
done

echo "ok quickshellRegressionLogFiltering"
