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

lint_files=(
    "Commons/ThemeIcons.qml"
    "Modules/Bar/Widgets/ActiveWindow.qml"
    "Modules/Panels/Brightness/BrightnessPanel.qml"
    "Modules/Panels/Settings/Tabs/DisplayTab.qml"
)

for file in "${lint_files[@]}"; do
    qmllint "$repo_root/$file"
done

echo "ok qmlStaticCheck"
echo "Checked ${#lint_files[@]} QML files with qmllint."
