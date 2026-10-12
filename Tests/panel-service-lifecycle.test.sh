#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-behavior}"
if [ "$#" -gt 1 ] || [[ "$mode" != "behavior" && "$mode" != "lint-harness" ]]; then
    echo "Usage: $0 [behavior|lint-harness]" >&2
    exit 2
fi
runtime_dir="$(mktemp -d)"

cleanup() {
    if [ "$mode" = "behavior" ]; then
        quickshell kill --any-display -p "$runtime_dir/shell.qml" >/dev/null 2>&1 || true
    fi
    rm -rf "$runtime_dir"
}
trap cleanup EXIT INT TERM

mkdir -p "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"
chmod 0700 "$runtime_dir" "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data"

# Avoid palette creation racing its own FileView watcher during this short probe.
mkdir -p "$runtime_dir/config/noctalia"
printf '{}\n' >"$runtime_dir/config/noctalia/colors.json"

python3 - "$repo_root" "$runtime_dir" <<'PY'
import re
import shutil
import sys
from pathlib import Path

root, runtime = map(Path, sys.argv[1:])
for name in ("Assets", "Commons", "Helpers", "Modules", "Services", "Widgets"):
    shutil.copytree(root / name, runtime / name)
modules = {}
for path in sorted(runtime.rglob("*.qml")):
    relative = path.relative_to(runtime)
    for parent in (relative.parent, *relative.parent.parents):
        modules.setdefault(parent, [])
    singleton = bool(
        re.search(r"^\s*pragma\s+Singleton\b", path.read_text(), re.MULTILINE)
    )
    prefix = "singleton " if singleton else ""
    modules[relative.parent].append(f"{prefix}{path.stem} 1.0 {path.name}\n")
for parent, declarations in modules.items():
    module = ".".join(("qs", *parent.parts))
    (runtime / parent / "qmldir").write_text(
        f"module {module}\n" + "".join(declarations)
    )
PY
ln -s "$repo_root/Tests/Qml/PanelServiceLifecycleHarness.qml" "$runtime_dir/shell.qml"
ln -s "$runtime_dir" "$runtime_dir/qs"

if [ "$mode" = "lint-harness" ]; then
    /usr/lib/qt6/bin/qmllint --bare \
        -I "$runtime_dir" -I /usr/lib/qt6/qml \
        --max-warnings 0 --json - "$runtime_dir/shell.qml"
    exit "$?"
fi

output_log="$runtime_dir/output.log"
set +e
NOCTALIA_CONFIG_DIR="$runtime_dir/config/noctalia/" \
    NOCTALIA_CACHE_DIR="$runtime_dir/cache/noctalia/" \
    NOCTALIA_SETTINGS_FILE="$runtime_dir/config/noctalia/settings.json" \
    XDG_CONFIG_HOME="$runtime_dir/config" \
    XDG_CACHE_HOME="$runtime_dir/cache" \
    XDG_DATA_HOME="$runtime_dir/data" \
    timeout --kill-after=2s 45s \
    quickshell --no-color -p "$runtime_dir/shell.qml" >"$output_log" 2>&1
status=$?
set -e

cat "$output_log"
if rg --quiet '\b(WARN|ERROR|FATAL)\b' "$output_log"; then
    echo "PanelService lifecycle process emitted diagnostics" >&2
    exit 1
fi
if [ "$status" -ne 0 ]; then
    exit "$status"
fi
if ! rg --quiet 'PASS PanelServiceLifecycle' "$output_log"; then
    echo "PanelService lifecycle did not reach its PASS sentinel" >&2
    exit 1
fi
