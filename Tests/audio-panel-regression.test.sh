#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="$(mktemp -d)"
runtime_shell="$runtime_dir/shell.qml"

cleanup() {
    quickshell kill --any-display -p "$runtime_shell" >/dev/null 2>&1 || true
    rm -rf "$runtime_dir"
}
trap cleanup EXIT INT TERM

chmod 0700 "$runtime_dir"
mkdir -p "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"
chmod 0700 "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"

# Avoid palette creation racing its own FileView watcher during this short probe.
mkdir -p "$runtime_dir/config/noctalia"
printf '{}\n' >"$runtime_dir/config/noctalia/colors.json"

for source_dir in Assets Commons Helpers Modules Services Widgets; do
    ln -s "$repo_root/$source_dir" "$runtime_dir/$source_dir"
done
ln -s "$repo_root/Tests/Qml/AudioPanelRegressionHarness.qml" "$runtime_shell"
output_log="$runtime_dir/output.log"
success_status=42

set +e
NOCTALIA_CONFIG_DIR="$runtime_dir/config/noctalia/" \
    NOCTALIA_CACHE_DIR="$runtime_dir/cache/noctalia/" \
    NOCTALIA_SETTINGS_FILE="$runtime_dir/config/noctalia/settings.json" \
    XDG_CONFIG_HOME="$runtime_dir/config" \
    XDG_CACHE_HOME="$runtime_dir/cache" \
    XDG_DATA_HOME="$runtime_dir/data" \
    timeout --kill-after=2s 20s \
    quickshell --no-color -p "$runtime_shell" >"$output_log" 2>&1
status=$?
set -e

cat "$output_log"
if rg --quiet '\b(WARN|ERROR|FATAL)\b' "$output_log"; then
    echo "AudioPanel regression process emitted diagnostics" >&2
    exit 1
fi
if [ "$status" -eq "$success_status" ]; then
    echo "PASS AudioPanelRegression"
    exit 0
fi
if [ "$status" -ne 0 ]; then
    exit "$status"
fi

echo "AudioPanel regression did not reach its PASS sentinel" >&2
exit 1
