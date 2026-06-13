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

usage() {
    cat <<'USAGE'
Usage: Bin/dev/service-probes.sh [all|notifications|audio|brightness|clipboard|wallpaper-colors]

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
    -h | --help | help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
