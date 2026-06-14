#!/usr/bin/env bash
set -euo pipefail

probe="${1:-all}"

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "missing required command: $name" >&2
        exit 2
    fi
}

probe_notifications() {
    require_command gdbus

    local info capabilities
    info="$(gdbus call --session \
        --dest org.freedesktop.Notifications \
        --object-path /org/freedesktop/Notifications \
        --method org.freedesktop.Notifications.GetServerInformation)"
    capabilities="$(gdbus call --session \
        --dest org.freedesktop.Notifications \
        --object-path /org/freedesktop/Notifications \
        --method org.freedesktop.Notifications.GetCapabilities)"

    if [[ "$info" != *"quickshell"* ]]; then
        echo "notification server is not quickshell: $info" >&2
        exit 1
    fi

    if [[ "$capabilities" != *"body"* || "$capabilities" != *"actions"* ]]; then
        echo "notification capabilities are missing body/actions: $capabilities" >&2
        exit 1
    fi

    echo "ok probeNotifications"
}

probe_audio() {
    require_command wpctl

    local sink source
    sink="$(wpctl get-volume @DEFAULT_AUDIO_SINK@)"
    source="$(wpctl get-volume @DEFAULT_AUDIO_SOURCE@)"

    if [[ ! "$sink" =~ ^Volume:\ [0-9]+(\.[0-9]+)?( \[MUTED\])?$ ]]; then
        echo "unexpected default sink volume output: $sink" >&2
        exit 1
    fi

    if [[ ! "$source" =~ ^Volume:\ [0-9]+(\.[0-9]+)?( \[MUTED\])?$ ]]; then
        echo "unexpected default source volume output: $source" >&2
        exit 1
    fi

    echo "ok probeAudio"
}

probe_brightness() {
    require_command brightnessctl
    require_command ddcutil
    require_command rg

    if ! brightnessctl --list | rg -q "Device 'amdgpu_bl1' of class 'backlight'"; then
        echo "expected internal backlight device amdgpu_bl1 was not found" >&2
        exit 1
    fi

    local ddc_output vcp_output current_bus lg_bus
    ddc_output="$(ddcutil detect 2>&1)"
    current_bus=""
    lg_bus=""

    while IFS= read -r line; do
        if [[ "$line" =~ I2C\ bus:[[:space:]]+/dev/i2c-([0-9]+) ]]; then
            current_bus="${BASH_REMATCH[1]}"
        elif [[ "$line" == *"Model:                LG ULTRAWIDE"* ]]; then
            lg_bus="$current_bus"
        fi
    done <<<"$ddc_output"

    if [ -n "$lg_bus" ]; then
        vcp_output="$(ddcutil -b "$lg_bus" getvcp 10 --brief 2>&1)"
        if [[ ! "$vcp_output" =~ ^VCP\ 10\ C\ [0-9]+\ 100$ ]]; then
            echo "unexpected DDC brightness output for LG ULTRAWIDE on bus $lg_bus: $vcp_output" >&2
            exit 1
        fi
        echo "ok probeBrightnessDdc"
    else
        echo "ok probeBrightnessDdcSkipped"
    fi

    echo "ok probeBrightness"
}

probe_clipboard() {
    require_command wl-paste
    require_command rg

    local types
    types="$(wl-paste --list-types 2>/dev/null || true)"

    if [[ -z "$types" ]]; then
        echo "clipboard type list is empty; clipboard service may be unavailable" >&2
        exit 1
    fi

    if ! printf '%s\n' "$types" | rg -q '^(text/plain|text/plain;charset=utf-8|text/html|image/)'; then
        echo "clipboard has no expected text/html/image MIME types: $types" >&2
        exit 1
    fi

    echo "ok probeClipboard"
}

probe_wallpaper_colors() {
    require_command jq

    local colors_file="/home/osso/.config/noctalia/colors.json"
    local wallpapers_file="/home/osso/.cache/noctalia/wallpapers.json"

    jq -e '.mPrimary and .mSurface and .mOnSurface and .mError' "$colors_file" >/dev/null
    jq -e '.wallpapers and (.wallpapers | type == "object")' "$wallpapers_file" >/dev/null

    local wallpaper_paths
    mapfile -t wallpaper_paths < <(jq -r '.wallpapers[]' "$wallpapers_file")

    if [ "${#wallpaper_paths[@]}" -eq 0 ]; then
        echo "no active wallpaper paths found in $wallpapers_file" >&2
        exit 1
    fi

    local wallpaper_path
    for wallpaper_path in "${wallpaper_paths[@]}"; do
        if [ ! -e "$wallpaper_path" ]; then
            echo "active wallpaper path does not exist: $wallpaper_path" >&2
            exit 1
        fi
    done

    echo "ok probeWallpaperColors"
}

probe_settings() {
    require_command jq

    local settings_file="/home/osso/.config/noctalia/settings.json"

    jq -e '
        .settingsVersion
        and (.general | type == "object")
        and (.ui | type == "object")
        and (.bar | type == "object")
        and (.bar.position | IN("top", "bottom", "left", "right"))
        and (.bar.widgets | type == "object")
        and (.bar.widgets.left | type == "array")
        and (.bar.widgets.center | type == "array")
        and (.bar.widgets.right | type == "array")
        and ([
            .bar.widgets.left[],
            .bar.widgets.center[],
            .bar.widgets.right[]
        ] | all(.id and (.id | type == "string")))
        and (.controlCenter.cards | type == "array")
        and (.controlCenter.cards | length > 0)
        and (.controlCenter.cards | all(.id and (.id | type == "string") and (.enabled | type == "boolean")))
        and (.audio.volumeStep | type == "number")
        and (.audio.volumeStep > 0)
        and (.brightness.brightnessStep | type == "number")
        and (.brightness.brightnessStep > 0)
        and (.notifications.location | type == "string")
        and (.wallpaper.directory | type == "string")
    ' "$settings_file" >/dev/null

    echo "ok probeSettings"
}

probe_state_cache() {
    require_command jq

    local cache_dir="/home/osso/.cache/noctalia"
    local shell_state_file="$cache_dir/shell-state.json"
    local network_file="$cache_dir/network.json"
    local location_file="$cache_dir/location.json"
    local notifications_file="$cache_dir/notifications.json"

    jq -e '
        (.notificationsState | type == "object")
        and (.changelogState | type == "object")
        and (.colorSchemesList | type == "object")
        and (.display | type == "object")
        and (.display | to_entries | all(
            (.value.name | type == "string")
            and (.value.width | type == "number")
            and (.value.height | type == "number")
            and (.value.scale | type == "number")
        ))
    ' "$shell_state_file" >/dev/null

    jq -e '
        (.knownNetworks | type == "object")
        and (.knownNetworks | to_entries | all(
            (.value.profileName | type == "string")
            and (.value.lastConnected | type == "number")
        ))
        and ((.lastConnected | type == "string") or (.lastConnected == null))
    ' "$network_file" >/dev/null

    jq -e '
        (.name | type == "string")
        and (.latitude | type == "string")
        and (.longitude | type == "string")
        and (.weatherLastFetch | type == "number")
        and ((.weather | type == "object") or (.weather == null))
    ' "$location_file" >/dev/null

    jq -e '
        (.notifications | type == "array")
        and (.notifications | all(
            (.id | type == "string")
            and (.summary | type == "string")
            and (.timestamp | type == "number")
            and (.urgency | type == "number")
        ))
    ' "$notifications_file" >/dev/null

    echo "ok probeStateCache"
}

probe_network() {
    require_command nmcli
    require_command jq

    local cache_file="${XDG_CACHE_HOME:-$HOME/.cache}/noctalia/network.json"
    if [ ! -r "$cache_file" ]; then
        echo "network cache is not readable: $cache_file" >&2
        exit 1
    fi

    local state connectivity active_connections device_status
    state="$(nmcli -t -f STATE general)"
    connectivity="$(nmcli -t -f CONNECTIVITY general)"
    active_connections="$(nmcli -t -f NAME,TYPE,DEVICE connection show --active)"
    device_status="$(nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status)"

    if [[ "$state" != "connected" && "$state" != "connecting" ]]; then
        echo "NetworkManager is not connected or connecting: $state" >&2
        exit 1
    fi

    if [[ "$state" == "connected" && "$connectivity" == "none" ]]; then
        echo "NetworkManager reports connected state with no connectivity" >&2
        exit 1
    fi

    local has_network_connection=false
    local active_wifi_name=""
    while IFS=: read -r name type device; do
        if [[ -z "$name" || -z "$type" || -z "$device" ]]; then
            echo "malformed active NetworkManager connection row: $name:$type:$device" >&2
            exit 1
        fi

        case "$type" in
            802-11-wireless)
                has_network_connection=true
                active_wifi_name="$name"
                ;;
            802-3-ethernet)
                has_network_connection=true
                ;;
        esac
    done <<<"$active_connections"

    if [[ "$has_network_connection" != true ]]; then
        echo "no active Wi-Fi or ethernet NetworkManager connection found" >&2
        exit 1
    fi

    if [[ -n "$active_wifi_name" ]]; then
        if ! jq -e --arg ssid "$active_wifi_name" '
            (.knownNetworks[$ssid] | type == "object")
            and (.knownNetworks[$ssid].profileName | type == "string")
            and (.lastConnected == $ssid)
        ' "$cache_file" >/dev/null; then
            echo "active Wi-Fi connection is missing from network cache: $active_wifi_name" >&2
            exit 1
        fi

        if [[ "$device_status" != *":wifi:connected:$active_wifi_name"* ]]; then
            echo "active Wi-Fi connection is not reflected in device status: $active_wifi_name" >&2
            exit 1
        fi
    fi

    echo "ok probeNetwork"
}

probe_power_profile() {
    require_command powerprofilesctl

    local current profiles
    current="$(powerprofilesctl get)"
    profiles="$(powerprofilesctl list)"

    case "$current" in
        performance | balanced | power-saver)
            ;;
        *)
            echo "unexpected active power profile: $current" >&2
            exit 1
            ;;
    esac

    for profile in performance balanced power-saver; do
        if [[ "$profiles" != *"$profile:"* ]]; then
            echo "power profile is missing from list: $profile" >&2
            exit 1
        fi
    done

    if [[ "$profiles" != *"* $current:"* ]]; then
        echo "active power profile is not marked in profile list: $current" >&2
        exit 1
    fi

    echo "ok probePowerProfile"
}

usage() {
    cat <<'USAGE'
Usage: Bin/dev/service-probes.sh [all|notifications|audio|brightness|clipboard|wallpaper-colors|settings|state-cache|network|power-profile]

Runs read-only probes for services used by the local shell.
USAGE
}

case "$probe" in
    all)
        probe_notifications
        probe_audio
        probe_brightness
        probe_clipboard
        probe_wallpaper_colors
        probe_settings
        probe_state_cache
        probe_network
        probe_power_profile
        ;;
    notifications)
        probe_notifications
        ;;
    audio)
        probe_audio
        ;;
    brightness)
        probe_brightness
        ;;
    clipboard)
        probe_clipboard
        ;;
    wallpaper-colors)
        probe_wallpaper_colors
        ;;
    settings)
        probe_settings
        ;;
    state-cache)
        probe_state_cache
        ;;
    network)
        probe_network
        ;;
    power-profile)
        probe_power_profile
        ;;
    -h | --help | help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
