#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "missing required command: $name" >&2
        exit 2
    fi
}

qmllint=/usr/lib/qt6/bin/qmllint
if [ ! -x "$qmllint" ]; then
    echo "missing required Qt 6 qmllint: $qmllint" >&2
    exit 2
fi
require_command rg
require_command python3

mapfile -t qml_files < <(cd "$repo_root" && rg --files -g '*.qml' | sort)
mapfile -t js_files < <(cd "$repo_root" && rg --files -g '*.js' | sort)
module_root="$(mktemp -d "${TMPDIR:-/tmp}/noctalia-qmllint-modules.XXXXXX")"
trap 'rm -rf -- "$module_root"' EXIT

# Quickshell supplies qs.* virtually; qmllint needs equivalent on-disk modules.
python3 - "$repo_root" "$module_root" "${qml_files[@]}" "${js_files[@]}" <<'PY'
from pathlib import Path
import re
import shutil
import sys

source_root = Path(sys.argv[1])
qs_root = Path(sys.argv[2]) / "qs"
modules = {Path("."): []}
for relative in sorted(sys.argv[3:]):
    path = Path(relative)
    target = qs_root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    source = source_root / path
    # Copies retain qmldir context; qmllint resolves symlinks outside the module.
    shutil.copyfile(source, target)
    if path.suffix != ".qml":
        continue
    directory = path.parent
    for parent in (directory, *directory.parents):
        modules.setdefault(parent, [])
    singleton = bool(
        re.search(r"^\s*pragma\s+Singleton\b", source.read_text(), re.MULTILINE)
    )
    prefix = "singleton " if singleton else ""
    modules[directory].append(f"{prefix}{path.stem} 1.0 {path.name}\n")

for directory, declarations in sorted(modules.items()):
    module = ".".join(("qs", *directory.parts))
    (qs_root / directory / "qmldir").write_text(
        f"module {module}\n" + "".join(declarations)
    )
PY

exclusions_file="$repo_root/Bin/dev/qml-static-exclusions.txt"

declare -A excluded_files=()
while IFS= read -r file || [ -n "$file" ]; do
    if [ -z "$file" ]; then
        continue
    fi
    excluded_files["$file"]=1
done <"$exclusions_file"

checked_count=0
skipped_count=0

for file in "${qml_files[@]}"; do
    if [ -n "${excluded_files[$file]:-}" ]; then
        skipped_count=$((skipped_count + 1))
        continue
    fi

    "$qmllint" -I "$module_root" "$module_root/qs/$file"
    checked_count=$((checked_count + 1))
done

for file in "${!excluded_files[@]}"; do
    if [ ! -f "$repo_root/$file" ]; then
        echo "excluded QML file does not exist: $file" >&2
        exit 1
    fi

    if "$qmllint" -I "$module_root" "$module_root/qs/$file" >/dev/null 2>&1; then
        echo "excluded QML file now passes qmllint; remove it from $exclusions_file: $file" >&2
        exit 1
    fi
done

echo "ok qmlStaticCheck"
echo "Checked $checked_count QML files with qmllint; skipped $skipped_count documented exclusions."
