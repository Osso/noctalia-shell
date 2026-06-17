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

fake_bin="$(mktemp -d)"
trap 'rm -rf "$fake_bin"' EXIT
printf '#!/usr/bin/env bash\nexit 0\n' >"$fake_bin/quickshell"
printf '#!/usr/bin/env bash\nexit 1\n' >"$fake_bin/pgrep"
chmod +x "$fake_bin/quickshell" "$fake_bin/pgrep"

set +e
no_shell_output="$(PATH="$fake_bin:$PATH" main 2>&1)"
no_shell_status="$?"
set -e

if [ "$no_shell_status" -ne 1 ]; then
    echo "main returned $no_shell_status for missing shell, expected 1" >&2
    exit 1
fi

if ! printf '%s\n' "$no_shell_output" | rg -q "No active local Noctalia shell instance found"; then
    echo "main did not report missing local shell" >&2
    exit 1
fi

if ! printf '%s\n' "$no_shell_output" | rg -q "quickshell -p $repo_root"; then
    echo "main did not report expected launch command" >&2
    exit 1
fi

cat >"$fake_bin/pgrep" <<FAKE_PGREP
#!/usr/bin/env bash
printf '4242 quickshell -p %s\n' '$repo_root'
FAKE_PGREP
cat >"$fake_bin/quickshell" <<'FAKE_QUICKSHELL'
#!/usr/bin/env bash
if [ "${1:-}" = "log" ]; then
    cat <<'LOG'
WARN scene: @Old.qml[1:-1]: TypeError: stale failure
INFO: Reloading configuration...
INFO qml: [20260615-124025] Brightness Detected DDC Monitor
WARN qml: ReferenceError: PanelService is not defined
LOG
fi
FAKE_QUICKSHELL
chmod +x "$fake_bin/quickshell" "$fake_bin/pgrep"

set +e
fatal_output="$(PATH="$fake_bin:$PATH" main 2>&1)"
fatal_status="$?"
set -e

if [ "$fatal_status" -ne 1 ]; then
    echo "main returned $fatal_status for fatal log, expected 1" >&2
    exit 1
fi

if ! printf '%s\n' "$fatal_output" | rg -q "Quickshell regression gate failed for PID 4242"; then
    echo "main did not report failed regression gate" >&2
    exit 1
fi

if ! printf '%s\n' "$fatal_output" | rg -q "PanelService is not defined"; then
    echo "main did not report current fatal log line" >&2
    exit 1
fi

if printf '%s\n' "$fatal_output" | rg -q "stale failure"; then
    echo "main reported stale pre-reload failure" >&2
    exit 1
fi

echo "ok quickshellRegressionLogFiltering"
