#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="$(mktemp -d)"
cleanup() {
    local status=$?
    local instances
    quickshell kill --any-display -p "$runtime_dir/shell.qml" >/dev/null 2>&1 || true
    if ! instances="$(quickshell list --all 2>&1)"; then
        printf 'Failed to verify Quickshell cleanup: %s\n' "$instances" >&2
        status=1
    elif [[ "$instances" == *"$runtime_dir/shell.qml"* ]]; then
        printf 'Test shell remains registered: %s\n' "$runtime_dir/shell.qml" >&2
        status=1
    fi
    rm -rf "$runtime_dir"
    return "$status"
}
trap cleanup EXIT INT TERM

mkdir -p "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data" "$runtime_dir/bin"
chmod 0700 "$runtime_dir" "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"
for source_dir in Assets Commons Helpers Modules Services Widgets; do
    ln -s "$repo_root/$source_dir" "$runtime_dir/$source_dir"
done
ln -s "$repo_root/Tests/Qml/ScreenRecorderDiscoveryHarness.qml" "$runtime_dir/shell.qml"
printf 'old\n' > "$runtime_dir/phase"
cat > "$runtime_dir/bin/gpu-screen-recorder" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
phase="$(cat "$DISCOVERY_PHASE_FILE")"
case "$phase:$1" in
    old:--list-capture-options) printf 'DP-4|2560x1440\nregion\n';;
    old:--list-monitors) sleep 0.15; printf 'DP-4|2560x1440\n';;
    new:--list-capture-options) sleep 0.15; printf 'eDP-1|1920x1200\nregion\n';;
    new:--list-monitors) printf 'eDP-1|1920x1200\n';;
    *) exit 2;;
esac
STUB
chmod +x "$runtime_dir/bin/gpu-screen-recorder"

PATH="$runtime_dir/bin:$PATH" \
DISCOVERY_PHASE_FILE="$runtime_dir/phase" \
NOCTALIA_CONFIG_DIR="$runtime_dir/config/noctalia" \
NOCTALIA_CACHE_DIR="$runtime_dir/cache/noctalia" \
XDG_CONFIG_HOME="$runtime_dir/config" \
XDG_CACHE_HOME="$runtime_dir/cache" \
XDG_DATA_HOME="$runtime_dir/data" \
QT_QPA_PLATFORM=wayland \
timeout --kill-after=2s 12s quickshell --no-color -p "$runtime_dir/shell.qml"
