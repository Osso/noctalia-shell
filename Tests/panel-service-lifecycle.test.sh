#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-behavior}"
if [ "$#" -gt 0 ]; then
    shift
fi
harness="PanelServiceLifecycleHarness.qml"
inject_warning=false
usage() {
    echo "Usage: $0 [behavior|lint-harness] [--harness PanelServiceLifecycleHarness.qml|tst_panel_service_lifecycle.qml] [--inject-warning]" >&2
    exit 2
}
[[ "$mode" = "behavior" || "$mode" = "lint-harness" ]] || usage
while [ "$#" -gt 0 ]; do
    case "$1" in
    --harness)
        [ "$mode" = "lint-harness" ] && [ "$#" -ge 2 ] || usage
        harness="$2"
        shift 2
        ;;
    --inject-warning)
        [ "$mode" = "lint-harness" ] || usage
        inject_warning=true
        shift
        ;;
    *) usage ;;
    esac
done
[[ "$harness" = "PanelServiceLifecycleHarness.qml" || "$harness" = "tst_panel_service_lifecycle.qml" ]] || usage
runtime_dir="$(mktemp -d)"
cleanup() {
    rm -rf "$runtime_dir"
}
trap cleanup EXIT INT TERM

mkdir -p "$runtime_dir/home" "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data" "$runtime_dir/run" "$runtime_dir/tests"
chmod 0700 "$runtime_dir" "$runtime_dir/home" "$runtime_dir/config" "$runtime_dir/cache" "$runtime_dir/data" "$runtime_dir/run"

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
cp "$repo_root/Tests/Qml/PanelServiceLifecycleHarness.qml" "$runtime_dir/shell.qml"
cp "$repo_root/Tests/Qml/tst_panel_service_lifecycle.qml" "$runtime_dir/tests/tst_panel_service_lifecycle.qml"
ln -s "$runtime_dir" "$runtime_dir/qs"

# Both lint and runtime use these exact copies. Bubblewrap masks host config,
# desktop sockets and network; all writable settings stay under private HOME/XDG.
sandbox=(
    bwrap --die-with-parent --unshare-all --new-session
    --ro-bind / / --tmpfs /home --tmpfs /syncthing --tmpfs /tmp --tmpfs /run
    --bind "$runtime_dir" "$runtime_dir" --proc /proc --dev /dev
    --chdir "$runtime_dir" --clearenv
    --setenv PATH /usr/bin --setenv LANG C.UTF-8
    --setenv HOME "$runtime_dir/home"
    --setenv XDG_CONFIG_HOME "$runtime_dir/config"
    --setenv XDG_CACHE_HOME "$runtime_dir/cache"
    --setenv XDG_DATA_HOME "$runtime_dir/data"
    --setenv XDG_RUNTIME_DIR "$runtime_dir/run"
    --setenv NOCTALIA_CONFIG_DIR "$runtime_dir/config/noctalia/"
    --setenv NOCTALIA_CACHE_DIR "$runtime_dir/cache/noctalia/"
    --setenv NOCTALIA_SETTINGS_FILE "$runtime_dir/config/noctalia/settings.json"
    --setenv QT_QPA_PLATFORM offscreen --setenv QT_QUICK_BACKEND software
    --setenv QML_DISABLE_DISK_CACHE 1
)
"${sandbox[@]}" python3 - <<'PY'
import os
from pathlib import Path

for path in ("/home/osso/.config", "/syncthing/Sync", "/run/user"):
    assert not Path(path).exists(), f"host path exposed: {path}"
assert Path.home() == Path(os.environ["HOME"])
assert Path.home().is_dir()
print("LIFECYCLE_ISOLATION_PASS host config/desktop masked; private HOME")
PY

if [ "$mode" = "lint-harness" ]; then
    lint_target="$runtime_dir/shell.qml"
    if [ "$harness" = "tst_panel_service_lifecycle.qml" ]; then
        lint_target="$runtime_dir/tests/$harness"
    fi
    if [ "$inject_warning" = true ]; then
        python3 - "$lint_target" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text()
owner = "testRoot" if path.name == "shell.qml" else "testCase"
source = source.replace(
    f"id: {owner}",
    f"id: {owner}\n  property int injectedWarning: {owner}.missingLintProbe",
    1,
)
path.write_text(source)
PY
    fi
    set +e
    "${sandbox[@]}" /usr/lib/qt6/bin/qmllint --bare \
        -I "$runtime_dir" -I /usr/lib/qt6/qml \
        --max-warnings 0 --json - "$lint_target" >"$runtime_dir/lint.json"
    status=$?
    set -e
    cat "$runtime_dir/lint.json"
    python3 - "$runtime_dir/lint.json" "$harness" "$status" "$inject_warning" <<'PY'
import json
import sys
from pathlib import Path

report, harness, status, injected = sys.argv[1:]
files = json.loads(Path(report).read_text())["files"]
assert len(files) == 1, "expected exactly one linted harness"
warnings = [warning for warning in files[0]["warnings"] if warning["type"] == "warning"]
print("LIFECYCLE_HARNESS_LINT", harness, "FILES", len(files), "WARNINGS", len(warnings), "EXIT", status)
if injected == "true":
    assert any("missingLintProbe" in warning["message"] for warning in warnings), "semantic injection not visible"
    assert int(status) != 0, "semantic injection accepted"
else:
    assert int(status) != 0 or not warnings, "warnings accepted"
PY
    exit "$status"
fi

output_log="$runtime_dir/output.log"
set +e
timeout --kill-after=2s 45s "${sandbox[@]}" \
    --setenv QT_QPA_PLATFORM wayland --setenv WLR_BACKENDS headless \
    --setenv WLR_RENDERER pixman --setenv WLR_LIBINPUT_NO_DEVICES 1 \
    dbus-run-session -- cage -- \
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
if ! rg --quiet 'PASS PanelServiceLifecycle 26 animation/geometry/Loader cases plus output teardown' "$output_log"; then
    echo "PanelService lifecycle did not reach its 26-case PASS sentinel" >&2
    exit 1
fi

set +e
timeout --kill-after=2s 45s "${sandbox[@]}" \
    /usr/lib/qt6/bin/qmltestrunner -input "$runtime_dir/tests" >"$output_log" 2>&1
status=$?
set -e
cat "$output_log"
if [ "$status" -ne 0 ]; then
    exit "$status"
fi
if rg --quiet 'QWARN|QFATAL|QCRITICAL|Warning:|ReferenceError|TypeError' "$output_log" ||
    ! rg --quiet '3 passed, 0 failed' "$output_log"; then
    echo "PanelService captured-key QtTest failed or emitted diagnostics" >&2
    exit 1
fi
