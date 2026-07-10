#!/usr/bin/env bash
set -euo pipefail

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "missing required command: $name" >&2
        exit 2
    fi
}

current_reload_log() {
    awk '
        {
            buffer = buffer $0 ORS
            if ($0 ~ /INFO: Reloading configuration\.\.\./ || $0 ~ /Noctalia Hello!/) {
                buffer = $0 ORS
            }
        }
        END {
            printf "%s", buffer
        }
    ' <<<"$1"
}

fatal_log_pattern() {
    printf '%s\n' '(^|\b)(CRITICAL|FATAL|TypeError|ReferenceError|SyntaxError|Error:.*(module|import|component|property)|Cannot assign|Cannot read property|Cannot call method|is not a function|is not defined|module .* is not installed|module .* is not found|failed to load component|segmentation fault|core dumped)(\b|:)'
}

find_instance_pid() {
    local instances_json="$1"
    local expected_config="$2"

    jq -r --arg expected_config "$expected_config" '
        [.[] | select(.config_path == $expected_config)]
        | max_by(.launch_time)
        | .pid // empty
    ' <<<"$instances_json"
}

main() {
    local repo_root expected_command expected_config tail_lines instances_json pid log current_log fatal_pattern
    repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
    expected_command="quickshell -p $repo_root"
    expected_config="$repo_root/shell.qml"
    tail_lines="${QUICKSHELL_LOG_TAIL:-500}"

    require_command quickshell
    require_command jq
    require_command rg

    instances_json="$(quickshell list --all --json 2>/dev/null || true)"
    pid="$(find_instance_pid "$instances_json" "$expected_config" 2>/dev/null || true)"

    if [ -z "$pid" ]; then
        echo "No active local Noctalia shell instance found." >&2
        echo "Expected config path: $expected_config" >&2
        echo "Start it with: $expected_command" >&2
        exit 1
    fi

    log="$(quickshell log --pid "$pid" --tail "$tail_lines" --no-color 2>&1 || true)"
    current_log="$(current_reload_log "$log")"

    fatal_pattern="$(fatal_log_pattern)"

    if printf '%s\n' "$current_log" | rg -i "$fatal_pattern" >/tmp/noctalia-quickshell-regression-errors.txt; then
        echo "Quickshell regression gate failed for PID $pid." >&2
        echo "Matched high-signal log errors:" >&2
        cat /tmp/noctalia-quickshell-regression-errors.txt >&2
        exit 1
    fi

    echo "Quickshell regression gate passed for PID $pid."
    echo "Checked current reload window from last $tail_lines log lines for QML load/runtime failures."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
