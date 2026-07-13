#!/usr/bin/env bash
set -euo pipefail

ssid="${1:-}"
if [ -z "$ssid" ]; then
    echo "SSID is required" >&2
    exit 2
fi

profiles="$(nmcli -t --escape no -f NAME connection show)"
deleted=false

is_target_profile() {
    local profile="$1"
    if [ "$profile" = "$ssid" ] || [ "$profile" = "Auto $ssid" ]; then
        return 0
    fi

    local prefix="$ssid "
    if [[ "$profile" != "$prefix"* ]]; then
        return 1
    fi
    local suffix="${profile#"$prefix"}"
    [[ "$suffix" =~ ^[0-9]+$ ]]
}

while IFS= read -r profile; do
    if is_target_profile "$profile"; then
        nmcli connection delete id "$profile" >/dev/null
        echo "Deleted profile: $profile"
        deleted=true
    fi
done <<<"$profiles"

if [ "$deleted" = false ]; then
    echo "No profiles found for SSID: $ssid"
fi
