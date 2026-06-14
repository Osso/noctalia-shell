#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

translations_dir="$tmp_dir/Translations"
mkdir -p "$translations_dir"

cat >"$translations_dir/en.json" <<'JSON'
{
  "common": {
    "hello": "Hello",
    "goodbye": "Goodbye"
  },
  "nested": {
    "title": "Title"
  }
}
JSON

cat >"$translations_dir/fr.json" <<'JSON'
{
  "common": {
    "hello": "Bonjour"
  },
  "nested": {
    "title": "Titre"
  },
  "obsolete": "Supprimer"
}
JSON

output="$(
  cd "$repo_root"
  FOLDER_PATH="$translations_dir" REFERENCE_FILE="en.json" Bin/dev/i18n-json.sh fr 2>&1
)"

assert_contains() {
  local needle="$1"
  if [[ "$output" != *"$needle"* ]]; then
    echo "expected i18n-json output to contain: $needle" >&2
    echo "$output" >&2
    exit 1
  fi
}

assert_contains "Folder: $translations_dir"
assert_contains "File: $translations_dir/fr.json"
assert_contains "Total keys in reference (en): 3"
assert_contains "Total keys in fr: 3"
assert_contains "Translation completion:"
assert_contains "66%"
assert_contains "- Missing keys (exist in English but not in fr): 1"
assert_contains "- Extra keys (exist in fr but not in English): 1"
assert_contains "common.goodbye"
assert_contains "obsolete"

echo "ok testI18nJsonReport"
