#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

cat >"$tmp_dir/nmcli" <<'NMCLI'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "-t" ]; then
    if [ "$*" != "-t --escape no -f NAME connection show" ]; then
        echo "unexpected list arguments: $*" >&2
        exit 98
    fi
    if [ "${NMCLI_MODE:-}" = "list-fail" ]; then
        echo "list denied" >&2
        exit 10
    fi
    if [ "${NMCLI_MODE:-}" = "none" ]; then
        printf '%s\n' "Other"
    elif [ "${NMCLI_MODE:-}" = "colon" ]; then
        printf '%s\n' "Cafe:Guest" "Other"
    elif [ "${NMCLI_MODE:-}" = "backslash" ]; then
        printf '%s\n' 'Lab\Net' "Other"
    else
        printf '%s\n' "Home" "Auto Home" "Home 2" "Home 4" "Home 123" "Home 12x" "Other"
    fi
    exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "delete" ] && [ "${3:-}" = "id" ]; then
    printf '%s\n' "$4" >>"$NMCLI_DELETE_LOG"
    if [ "${NMCLI_MODE:-}" = "delete-fail" ] && [ "$4" = "Home" ]; then
        echo "delete denied" >&2
        exit 20
    fi
    echo "deleted $4"
    exit 0
fi
exit 99
NMCLI
chmod +x "$tmp_dir/nmcli"

export PATH="$tmp_dir:$PATH"
export NMCLI_DELETE_LOG="$tmp_dir/deleted"

output="$(bash "$repo_root/Bin/network-forget-profiles.sh" "Home")"
printf '%s\n' "$output" | rg -q 'Deleted profile: Home'
printf '%s\n' "$output" | rg -q 'Deleted profile: Auto Home'
printf '%s\n' "$output" | rg -q 'Deleted profile: Home 2'
printf '%s\n' "$output" | rg -q 'Deleted profile: Home 4'
printf '%s\n' "$output" | rg -q 'Deleted profile: Home 123'
if printf '%s\n' "$output" | rg -q 'Home 12x'; then
    echo "forget helper accepted a nonnumeric suffix" >&2
    exit 1
fi
if ! diff -u <(printf '%s\n' "Home" "Auto Home" "Home 2" "Home 4" "Home 123") "$NMCLI_DELETE_LOG"; then
    echo "forget helper deleted the wrong profile set" >&2
    exit 1
fi

: >"$NMCLI_DELETE_LOG"
colon_output="$(NMCLI_MODE=colon bash "$repo_root/Bin/network-forget-profiles.sh" "Cafe:Guest")"
printf '%s\n' "$colon_output" | rg -q 'Deleted profile: Cafe:Guest'
if ! diff -u <(printf '%s\n' "Cafe:Guest") "$NMCLI_DELETE_LOG"; then
    echo "forget helper did not match unescaped punctuation" >&2
    exit 1
fi

: >"$NMCLI_DELETE_LOG"
backslash_output="$(NMCLI_MODE=backslash bash "$repo_root/Bin/network-forget-profiles.sh" 'Lab\Net')"
printf '%s\n' "$backslash_output" | rg -Fq 'Deleted profile: Lab\Net'
if ! diff -u <(printf '%s\n' 'Lab\Net') "$NMCLI_DELETE_LOG"; then
    echo "forget helper did not match an unescaped backslash" >&2
    exit 1
fi

: >"$NMCLI_DELETE_LOG"
NMCLI_MODE=none output="$(NMCLI_MODE=none bash "$repo_root/Bin/network-forget-profiles.sh" "Home")"
printf '%s\n' "$output" | rg -q 'No profiles found for SSID: Home'
if [ -s "$NMCLI_DELETE_LOG" ]; then
    echo "forget helper deleted an unrelated profile" >&2
    exit 1
fi

set +e
NMCLI_MODE=list-fail bash "$repo_root/Bin/network-forget-profiles.sh" "Home" >"$tmp_dir/list.out" 2>"$tmp_dir/list.err"
list_status="$?"
NMCLI_MODE=delete-fail bash "$repo_root/Bin/network-forget-profiles.sh" "Home" >"$tmp_dir/delete.out" 2>"$tmp_dir/delete.err"
delete_status="$?"
set -e
if [ "$list_status" -ne 10 ] || ! rg -q 'list denied' "$tmp_dir/list.err"; then
    echo "forget helper swallowed profile-list failure" >&2
    exit 1
fi
if [ "$delete_status" -ne 20 ] || ! rg -q 'delete denied' "$tmp_dir/delete.err"; then
    echo "forget helper swallowed profile-delete failure" >&2
    exit 1
fi

echo "ok testNetworkForgetProfiles"
