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

require_command qmllint
require_command rg

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

while IFS= read -r file; do
    if [ -n "${excluded_files[$file]:-}" ]; then
        skipped_count=$((skipped_count + 1))
        continue
    fi

    qmllint "$repo_root/$file"
    checked_count=$((checked_count + 1))
done < <(cd "$repo_root" && rg --files -g '*.qml' | sort)

for file in "${!excluded_files[@]}"; do
    if [ ! -f "$repo_root/$file" ]; then
        echo "excluded QML file does not exist: $file" >&2
        exit 1
    fi

    if qmllint "$repo_root/$file" >/dev/null 2>&1; then
        echo "excluded QML file now passes qmllint; remove it from $exclusions_file: $file" >&2
        exit 1
    fi
done

echo "ok qmlStaticCheck"
echo "Checked $checked_count QML files with qmllint; skipped $skipped_count documented exclusions."
