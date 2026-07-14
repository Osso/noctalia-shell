#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="$(mktemp -d)"

cleanup() {
    quickshell kill --any-display -p "$runtime_dir/shell.qml" >/dev/null 2>&1 || true
    rm -rf "$runtime_dir"
}
trap cleanup EXIT INT TERM

mkdir -p "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"
chmod 0700 "$runtime_dir" "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"

for source_dir in Assets Commons Helpers Modules Services Widgets; do
    ln -s "$repo_root/$source_dir" "$runtime_dir/$source_dir"
done
ln -s "$repo_root/Tests/Qml/PanelServiceLifecycleHarness.qml" "$runtime_dir/shell.qml"

XDG_CONFIG_HOME="$runtime_dir/config" \
    XDG_CACHE_HOME="$runtime_dir/cache" \
    XDG_DATA_HOME="$runtime_dir/data" \
    timeout --kill-after=2s 20s \
    quickshell --no-color -p "$runtime_dir/shell.qml"
