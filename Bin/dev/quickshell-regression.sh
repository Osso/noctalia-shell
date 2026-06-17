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

main() {
    local repo_root expected_command tail_lines pid log current_log fatal_pattern
    repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
    expected_command="quickshell -p $repo_root"
    tail_lines="${QUICKSHELL_LOG_TAIL:-500}"

    require_command quickshell
    require_command pgrep
    require_command rg

    mapfile -t instances < <(pgrep -a -u "${USER:-$(id -un)}" quickshell | rg -F "$expected_command" || true)

    if [ "${#instances[@]}" -eq 0 ]; then
        echo "No active local Noctalia shell instance found." >&2
        echo "Expected command substring: $expected_command" >&2
        echo "Start it with: $expected_command" >&2
        exit 1
    fi

    pid="$(printf '%s\n' "${instances[@]}" | tail -n 1 | awk '{print $1}')"

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
