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

    local ddc_output vcp_output
    ddc_output="$(ddcutil detect)"
    if [[ "$ddc_output" != *"Model:                LG ULTRAWIDE"* ]]; then
        echo "expected LG ULTRAWIDE DDC display was not detected" >&2
        exit 1
    fi

    vcp_output="$(ddcutil -b 4 getvcp 10 --brief)"
    if [[ ! "$vcp_output" =~ ^VCP\ 10\ C\ [0-9]+\ 100$ ]]; then
        echo "unexpected DDC brightness output: $vcp_output" >&2
        exit 1
    fi

    echo "ok probeBrightness"
}

usage() {
    cat <<'USAGE'
Usage: Bin/dev/service-probes.sh [all|notifications|audio|brightness]

Runs read-only probes for services used by the local shell.
USAGE
}

case "$probe" in
    all)
        probe_notifications
        probe_audio
        probe_brightness
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
    -h | --help | help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
