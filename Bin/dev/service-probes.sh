#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "missing required command: $name" >&2
        exit 2
    fi
}

find_lg_ultrawide_bus() {
    local ddc_output="$1"
    local current_bus=""
    local lg_bus=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^Display[[:space:]]+[0-9]+ ]]; then
            current_bus=""
        elif [[ "$line" =~ I2C\ bus:[[:space:]]+/dev/i2c-([0-9]+) ]]; then
            current_bus="${BASH_REMATCH[1]}"
        elif [[ -n "$current_bus" && "$line" == *"Model:                LG ULTRAWIDE"* ]]; then
            lg_bus="$current_bus"
        fi
    done <<<"$ddc_output"

    printf '%s\n' "$lg_bus"
}

is_ddc_brightness_output() {
    local vcp_output="$1"

    [[ "$vcp_output" =~ ^VCP\ 10\ C\ ([0-9]+)\ 100$ ]] || return 1
    ((${BASH_REMATCH[1]} <= 100))
}

is_wpctl_volume_output() {
    local volume_output="$1"

    [[ "$volume_output" =~ ^Volume:\ [0-9]+(\.[0-9]+)?( \[MUTED\])?$ ]]
}

has_supported_clipboard_mime() {
    local mime_types="$1"
    local mime_type

    while IFS= read -r mime_type; do
        if [[ "$mime_type" =~ ^(text/plain|text/plain\;charset=utf-8|text/html|image/[^[:space:]/]+)$ ]]; then
            return 0
        fi
    done <<<"$mime_types"

    return 1
}

has_clipboard_mime_types() {
    local mime_types="$1"

    [[ -n "${mime_types//[[:space:]]/}" ]]
}

has_lock_key_state_rows() {
    local state_output="$1"

    [[ "$state_output" =~ (^|$'\n')caps:[01]($'\n'|$) ]] \
        && [[ "$state_output" =~ (^|$'\n')num:[01]($'\n'|$) ]] \
        && [[ "$state_output" =~ (^|$'\n')scroll:[01]($'\n'|$) ]]
}

is_bluetooth_controller_row() {
    local controller_row="$1"

    [[ "$controller_row" =~ ^Controller[[:space:]]+([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}[[:space:]]+[^[:space:]].* ]]
}

has_bluetooth_toggle_state() {
    local controller_info="$1"

    [[ "$controller_info" =~ (^|$'\n')[[:space:]]*Powered:[[:space:]]+(yes|no)[[:space:]]*($'\n'|$) ]] \
        && [[ "$controller_info" =~ (^|$'\n')[[:space:]]*Discovering:[[:space:]]+(yes|no)[[:space:]]*($'\n'|$) ]]
}

is_bluetooth_device_row() {
    local device_row="$1"

    [[ "$device_row" =~ ^Device[[:space:]]+([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}[[:space:]]+[^[:space:]].* ]]
}

is_gpu_screen_recorder_monitor_row() {
    local monitor_row="$1"

    [[ "$monitor_row" =~ ^[^|[:space:]][^|]*[|][0-9]+x[0-9]+$ ]]
}

has_gpu_screen_recorder_capture_option() {
    local capture_options="$1"
    local capture_option

    while IFS= read -r capture_option; do
        if [[ "$capture_option" =~ ^[^|[:space:]][^|]*[|][0-9]+x[0-9]+@[0-9]+hz[|][A-Za-z0-9_-]+$ ]] \
            || [[ "$capture_option" =~ ^[^|[:space:]]+$ ]]; then
            return 0
        fi
    done <<<"$capture_options"

    return 1
}

is_power_profile_name() {
    local profile="$1"

    [[ "$profile" == "performance" || "$profile" == "balanced" || "$profile" == "power-saver" ]]
}

has_power_profile_row() {
    local profiles="$1"
    local profile="$2"
    local line

    while IFS= read -r line; do
        line="${line#"${line%%[![:space:]]*}"}"
        if [[ "$line" == "* "* ]]; then
            line="${line#\* }"
        fi
        if [[ "$line" == "$profile:" ]]; then
            return 0
        fi
    done <<<"$profiles"

    return 1
}

has_power_profile_entries() {
    local profiles="$1"

    has_power_profile_row "$profiles" "performance" \
        && has_power_profile_row "$profiles" "balanced" \
        && has_power_profile_row "$profiles" "power-saver"
}

has_active_power_profile_marker() {
    local profiles="$1"
    local current="$2"

    [[ "$profiles" =~ (^|$'\n')[[:space:]]*[*][[:space:]]+$current:[[:space:]]*($'\n'|$) ]]
}

is_vpn_connection_type() {
    local connection_type="$1"

    [[ "$connection_type" == "vpn" || "$connection_type" == "wireguard" ]]
}

is_nm_uuid() {
    local uuid="$1"

    [[ "$uuid" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

is_active_nm_device() {
    local device="$1"

    [[ "$device" =~ ^[^[:space:]]+$ && "$device" != "--" ]]
}

is_proc_cpu_aggregate_row() {
    local cpu_line="$1"

    [[ "$cpu_line" =~ ^cpu[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+$ ]]
}

has_meminfo_kb_row() {
    local meminfo="$1"
    local key="$2"

    [[ "$meminfo" =~ (^|$'\n')${key}:[[:space:]]+[0-9]+[[:space:]]+kB($'\n'|$) ]]
}

is_ps_process_row() {
    local ps_row="$1"

    [[ "$ps_row" =~ ^[[:space:]]*[0-9]+[[:space:]]+[0-9]+(\.[0-9]+)?[[:space:]]+[0-9]+(\.[0-9]+)?[[:space:]]+[0-9]+[[:space:]]+[^[:space:]].* ]]
}

has_upower_percentage() {
    local device_info="$1"

    [[ "$device_info" =~ (^|$'\n')[[:space:]]*percentage:[[:space:]]+[0-9]+%[[:space:]]*($'\n'|$) ]]
}

has_upower_battery_state() {
    local device_info="$1"

    [[ "$device_info" =~ (^|$'\n')[[:space:]]*state:[[:space:]]+(charging|discharging|empty|fully-charged|pending-charge|pending-discharge|unknown)[[:space:]]*($'\n'|$) ]]
}

has_physical_upower_battery_details() {
    local battery_info="$1"

    [[ "$battery_info" =~ (^|$'\n')[[:blank:]]*native-path:[[:blank:]]+[^[:space:]].*($'\n'|$) ]] \
        && [[ "$battery_info" =~ (^|$'\n')[[:blank:]]*rechargeable:[[:blank:]]+yes[[:blank:]]*($'\n'|$) ]]
}

is_network_connection_type() {
    local connection_type="$1"

    [[ "$connection_type" == "802-11-wireless" || "$connection_type" == "802-3-ethernet" ]]
}

has_connected_wifi_device_status() {
    local device_status="$1"
    local wifi_name="$2"
    local status_row device type state connection

    while IFS= read -r status_row; do
        IFS=: read -r device type state connection <<<"$status_row"
        if [[ -n "$device" && "$type" == "wifi" && "$state" == "connected" && "$connection" == "$wifi_name" ]]; then
            return 0
        fi
    done <<<"$device_status"

    return 1
}

is_passwd_row() {
    local passwd_row="$1"

    [[ "$passwd_row" =~ ^[^:]+:[^:]*:[0-9]+:[0-9]+:[^:]*:/[^:]+:/[^:]+$ ]]
}

has_readable_font_family() {
    local fontconfig_fonts="$1"
    local font_line

    if [[ -z "${fontconfig_fonts//[[:space:]]/}" ]]; then
        return 1
    fi

    while IFS= read -r font_line; do
        if [[ "$font_line" =~ [[:alpha:]] ]]; then
            return 0
        fi
    done <<<"$fontconfig_fonts"

    return 1
}

has_ipc_target() {
    local ipc_output="$1"
    local target="$2"

    [[ "$ipc_output" =~ (^|$'\n')target[[:space:]]+$target($'\n'|$) ]]
}

has_ipc_toggle_handler() {
    local ipc_output="$1"

    [[ "$ipc_output" =~ (^|$'\n')[[:blank:]]*function[[:blank:]]+toggle\(\):[[:blank:]]+void[[:blank:]]*($'\n'|$) ]]
}

has_ipc_target_function() {
    local ipc_output="$1"
    local target="$2"
    local function_name="$3"
    local in_target=false
    local line

    while IFS= read -r line; do
        if [[ "$line" =~ ^target[[:space:]]+(.+)$ ]]; then
            [[ "${BASH_REMATCH[1]}" == "$target" ]] && in_target=true || in_target=false
            continue
        fi

        if [[ "$in_target" == true && "$line" =~ ^[[:blank:]]+function[[:blank:]]+$function_name\(\):[[:blank:]]+void[[:blank:]]*$ ]]; then
            return 0
        fi
    done <<<"$ipc_output"

    return 1
}

has_quickshell_launch_path() {
    local launcher_config="$1"
    local repo_path="$2"

    [[ "$launcher_config" =~ quickshell[[:blank:]]+-p[[:blank:]]+\"?$repo_path(\"|[[:blank:]]|$) ]]
}

has_niri_start_wrapper() {
    local niri_config="$1"

    [[ "$niri_config" =~ (^|$'\n')[[:blank:]]*spawn-at-startup[[:blank:]]+\"/home/osso/bin/start-quickshell\"[[:blank:]]*($'\n'|$) ]]
}

has_quickshell_ipc_call() {
    local niri_config="$1"
    local repo_path="$2"
    local target="$3"
    local function_name="$4"
    local normalized_config="${niri_config//\"/}"
    local line

    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:blank:]]*(//|#) ]]; then
            continue
        fi
        if [[ "$line" =~ quickshell[[:blank:]]+ipc[[:blank:]]+-p[[:blank:]]+$repo_path[[:blank:]]+call[[:blank:]]+$target[[:blank:]]+$function_name($|[[:space:]]|[;}]) ]]; then
            return 0
        fi
    done <<<"$normalized_config"

    return 1
}

has_stale_launch_path() {
    local launch_config="$1"
    shift
    local stale_path

    for stale_path in "$@"; do
        if [[ "$launch_config" =~ $stale_path($|[[:space:]]|[\";}]) ]]; then
            return 0
        fi
    done

    return 1
}

list_quickshell_ipc_calls() {
    local niri_config="$1"
    local normalized_config="${niri_config//\"/}"
    local line

    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:blank:]]*(//|#) ]]; then
            continue
        fi
        if [[ "$line" =~ quickshell[[:blank:]]+ipc[[:blank:]] ]] \
            && [[ "$line" =~ call[[:space:]]+([A-Za-z0-9_]+)[[:space:]]+([A-Za-z0-9_]+) ]]; then
            printf '%s %s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
        fi
    done <<<"$normalized_config"
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

    if ! is_wpctl_volume_output "$sink"; then
        echo "unexpected default sink volume output: $sink" >&2
        exit 1
    fi

    if ! is_wpctl_volume_output "$source"; then
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

    local ddc_output vcp_output lg_bus
    ddc_output="$(ddcutil detect 2>&1)"
    lg_bus="$(find_lg_ultrawide_bus "$ddc_output")"

    if [ -n "$lg_bus" ]; then
        vcp_output="$(ddcutil -b "$lg_bus" getvcp 10 --brief 2>&1)"
        if ! is_ddc_brightness_output "$vcp_output"; then
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

    local types
    types="$(wl-paste --list-types 2>/dev/null || true)"

    if ! has_clipboard_mime_types "$types"; then
        echo "clipboard type list is empty; clipboard service may be unavailable" >&2
        exit 1
    fi

    if ! has_supported_clipboard_mime "$types"; then
        echo "ok probeClipboardUnsupported"
        return
    fi

    echo "ok probeClipboard"
}

probe_lock_keys() {
    require_command grep

    local has_led_input=false
    local lock_name brightness_file
    for lock_name in capslock numlock scrolllock; do
        for brightness_file in /sys/class/leds/input*::"$lock_name"/brightness; do
            if [[ -r "$brightness_file" ]]; then
                has_led_input=true
                break 2
            fi
        done
    done

    if [[ "$has_led_input" != true ]]; then
        echo "no readable lock-key LED brightness inputs found" >&2
        exit 1
    fi

    local state_output
    state_output="$(sh -c 'caps=0; cat /sys/class/leds/input*::capslock/brightness 2>/dev/null | grep -q 1 && caps=1; echo "caps:${caps}"; num=0; cat /sys/class/leds/input*::numlock/brightness 2>/dev/null | grep -q 1 && num=1; echo "num:${num}"; scroll=0; cat /sys/class/leds/input*::scrolllock/brightness 2>/dev/null | grep -q 1 && scroll=1; echo "scroll:${scroll}"')"

    if ! has_lock_key_state_rows "$state_output"; then
        echo "lock-key state output is missing or malformed: $state_output" >&2
        exit 1
    fi

    echo "ok probeLockKeys"
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
    local defaults_file="$repo_root/Assets/settings-default.json"

    jq -e --slurp '
        .[0] as $settings
        | .[1] as $defaults
        | (($settings | keys | sort) == ($defaults | keys | sort))
        and (($settings.templates | keys | sort) == ($defaults.templates | keys | sort))
    ' "$settings_file" "$defaults_file" >/dev/null

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
        and (.wallpaper.enabled | type == "boolean")
        and (.wallpaper.overviewEnabled | type == "boolean")
        and (.wallpaper.enableMultiMonitorDirectories | type == "boolean")
        and (.wallpaper.recursiveSearch | type == "boolean")
        and (.wallpaper.setWallpaperOnAllMonitors | type == "boolean")
        and (.wallpaper.fillMode | IN("center", "crop", "fit", "stretch"))
        and (.wallpaper.fillColor | test("^#[0-9a-fA-F]{6}$"))
        and (.wallpaper.randomEnabled | type == "boolean")
        and (.wallpaper.randomIntervalSec | type == "number")
        and (.wallpaper.randomIntervalSec > 0)
        and (.wallpaper.transitionDuration | type == "number")
        and (.wallpaper.transitionDuration >= 0)
        and (.wallpaper.transitionType | IN("none", "random", "fade", "disc", "stripes", "wipe"))
        and (.wallpaper.transitionEdgeSmoothness | type == "number")
        and (.wallpaper.transitionEdgeSmoothness >= 0)
        and (.wallpaper.transitionEdgeSmoothness <= 1)
        and (.wallpaper.panelPosition | IN("follow_bar", "center", "top", "bottom", "left", "right"))
        and (.wallpaper.monitorDirectories | type == "array")
        and (.wallpaper.monitorDirectories | all(
            (.name | type == "string")
            and (.path | type == "string")
        ))
        and (.wallpaper.useWallhaven | type == "boolean")
        and (.wallpaper.wallhavenSorting | IN("date_added", "relevance", "random", "views", "favorites", "toplist"))
        and (.wallpaper.wallhavenOrder | IN("desc", "asc"))
        and (.wallpaper.wallhavenResolutionMode | IN("atleast", "exact"))
        and (.osd | type == "object")
        and (.osd.enabled | type == "boolean")
        and (.osd.autoHideMs | type == "number")
        and (.osd.autoHideMs > 0)
        and (.osd.enabledTypes | type == "array")
        and (.osd.enabledTypes | all(type == "number" and . >= 0 and . <= 3))
        and (.osd.monitors | type == "array")
        and (.osd.monitors | all(type == "string"))
        and (.templates | type == "object")
        and (.templates | to_entries | all(.value | type == "boolean"))
        and (.dock | type == "object")
        and (.dock.enabled | type == "boolean")
        and (.dock.displayMode | IN("always_visible", "auto_hide", "dodges_windows"))
        and (.dock.monitors | type == "array")
        and (.dock.pinnedApps | type == "array")
        and (.appLauncher | type == "object")
        and (.appLauncher.position | IN("center", "top", "bottom"))
        and (.appLauncher.viewMode | IN("list", "grid"))
        and (.appLauncher.terminalCommand | type == "string")
        and (.screenRecorder | type == "object")
        and (.screenRecorder.frameRate | type == "number")
        and (.screenRecorder.frameRate > 0)
        and (.screenRecorder.videoCodec | type == "string")
        and (.screenRecorder.audioCodec | type == "string")
        and (.network.wifiEnabled | type == "boolean")
        and (.nightLight | type == "object")
        and (.nightLight.enabled | type == "boolean")
        and (.nightLight.autoSchedule | type == "boolean")
        and (.nightLight.nightTemp | test("^[0-9]+$"))
        and (.nightLight.dayTemp | test("^[0-9]+$"))
        and (.colorSchemes | type == "object")
        and (.colorSchemes.darkMode | type == "boolean")
        and (.colorSchemes.useWallpaperColors | type == "boolean")
        and (.colorSchemes.schedulingMode | IN("off", "manual", "location"))
        and (.colorSchemes.predefinedScheme | type == "string")
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

        if ! is_network_connection_type "$type"; then
            continue
        fi

        has_network_connection=true

        if [[ "$type" == "802-11-wireless" ]]; then
            active_wifi_name="$name"
        fi
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

        if ! has_connected_wifi_device_status "$device_status" "$active_wifi_name"; then
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

    if ! is_power_profile_name "$current"; then
        echo "unexpected active power profile: $current" >&2
        exit 1
    fi

    if ! has_power_profile_entries "$profiles"; then
        echo "power profile list is missing expected entries" >&2
        exit 1
    fi

    if ! has_active_power_profile_marker "$profiles" "$current"; then
        echo "active power profile is not marked in profile list: $current" >&2
        exit 1
    fi

    echo "ok probePowerProfile"
}

probe_battery() {
    require_command upower

    local devices display_device battery_device display_info battery_info
    devices="$(upower -e)"
    display_device="/org/freedesktop/UPower/devices/DisplayDevice"
    battery_device=""

    if [[ "$devices" != *"$display_device"* ]]; then
        echo "UPower display device was not found" >&2
        exit 1
    fi

    while IFS= read -r device; do
        if [[ "$device" == *"/battery_"* ]]; then
            battery_device="$device"
            break
        fi
    done <<<"$devices"

    if [[ -z "$battery_device" ]]; then
        echo "no physical UPower battery device was found" >&2
        exit 1
    fi

    display_info="$(upower -i "$display_device")"
    battery_info="$(upower -i "$battery_device")"

    if [[ "$display_info" != *"battery"* ]]; then
        echo "UPower display device is not reporting battery details" >&2
        exit 1
    fi

    if [[ "$display_info" != *"present:             yes"* ]]; then
        echo "UPower display battery is not present" >&2
        exit 1
    fi

    if ! has_upower_percentage "$display_info"; then
        echo "UPower display battery percentage is missing or malformed" >&2
        exit 1
    fi

    if ! has_upower_battery_state "$display_info"; then
        echo "UPower display battery state is missing or unexpected" >&2
        exit 1
    fi

    if ! has_physical_upower_battery_details "$battery_info"; then
        echo "physical UPower battery details are incomplete: $battery_device" >&2
        exit 1
    fi

    echo "ok probeBattery"
}

probe_bluetooth() {
    require_command bluetoothctl

    local controllers controller_info connected_devices
    controllers="$(bluetoothctl list)"
    controller_info="$(bluetoothctl show)"
    connected_devices="$(bluetoothctl devices Connected)"

    if [[ "$controllers" != *"[default]"* ]] || ! is_bluetooth_controller_row "$controllers"; then
        echo "default Bluetooth controller was not found: $controllers" >&2
        exit 1
    fi

    if ! is_bluetooth_controller_row "$controller_info"; then
        echo "Bluetooth controller details are missing" >&2
        exit 1
    fi

    if ! has_bluetooth_toggle_state "$controller_info"; then
        echo "Bluetooth powered/discovering state is missing or unexpected" >&2
        exit 1
    fi

    if [[ -n "$connected_devices" ]] && ! is_bluetooth_device_row "$connected_devices"; then
        echo "Bluetooth connected device list is malformed: $connected_devices" >&2
        exit 1
    fi

    echo "ok probeBluetooth"
}

probe_vpn() {
    require_command nmcli

    local rows vpn_count active_count
    rows="$(nmcli -t -f NAME,UUID,TYPE,DEVICE connection show)"
    vpn_count=0
    active_count=0

    while IFS= read -r row; do
        if [[ -z "$row" ]]; then
            continue
        fi

        local device remaining type uuid name
        device="${row##*:}"
        remaining="${row%:*}"
        type="${remaining##*:}"
        remaining="${remaining%:*}"
        uuid="${remaining##*:}"
        name="${remaining%:*}"

        if ! is_vpn_connection_type "$type"; then
            continue
        fi

        vpn_count=$((vpn_count + 1))

        if [[ -z "$name" ]]; then
            echo "VPN connection row is missing a name: $row" >&2
            exit 1
        fi

        if ! is_nm_uuid "$uuid"; then
            echo "VPN connection row has malformed UUID: $row" >&2
            exit 1
        fi

        if is_active_nm_device "$device"; then
            active_count=$((active_count + 1))
        fi
    done <<<"$rows"

    if [[ "$vpn_count" -eq 0 ]]; then
        echo "no NetworkManager VPN or WireGuard profiles found" >&2
        exit 1
    fi

    echo "ok probeVpn ($vpn_count profiles, $active_count active)"
}

probe_screen_recorder() {
    require_command gpu-screen-recorder
    require_command pidof

    local monitors capture_options
    monitors="$(gpu-screen-recorder --list-monitors 2>/dev/null)"
    capture_options="$(gpu-screen-recorder --list-capture-options 2>/dev/null)"

    if ! is_gpu_screen_recorder_monitor_row "$monitors"; then
        echo "gpu-screen-recorder monitor list is missing or malformed: $monitors" >&2
        exit 1
    fi

    if ! has_gpu_screen_recorder_capture_option "$capture_options"; then
        echo "gpu-screen-recorder capture options are missing or malformed: $capture_options" >&2
        exit 1
    fi

    if ! pidof xdg-desktop-portal >/dev/null; then
        echo "xdg-desktop-portal is not running" >&2
        exit 1
    fi

    if ! pidof xdg-desktop-portal-wlr xdg-desktop-portal-hyprland xdg-desktop-portal-gnome xdg-desktop-portal-kde xdg-desktop-portal-gtk >/dev/null; then
        echo "no supported xdg-desktop-portal backend is running" >&2
        exit 1
    fi

    echo "ok probeScreenRecorder"
}

probe_programs() {
    require_command rg

    local service_file="$repo_root/Services/System/ProgramCheckerService.qml"
    if [[ ! -r "$service_file" ]]; then
        echo "ProgramCheckerService.qml is not readable" >&2
        exit 1
    fi

    local expected_programs=(
        matugen
        pywalfox
        alacritty
        kitty
        ghostty
        foot
        wezterm
        fuzzel
        walker
        app2unit
        gpu-screen-recorder
        wlsunset
        code
        gnome-calendar
        spicetify
        cava
        niri
    )

    for program in "${expected_programs[@]}"; do
        if ! rg -q "$program" "$service_file"; then
            echo "ProgramCheckerService no longer checks expected program: $program" >&2
            exit 1
        fi
    done

    local required_available=(kitty ghostty gpu-screen-recorder wlsunset niri)
    for program in "${required_available[@]}"; do
        if ! command -v "$program" >/dev/null 2>&1; then
            echo "expected local program is missing: $program" >&2
            exit 1
        fi
    done

    if ! command -v vicinae >/dev/null 2>&1; then
        local found_appimage=false
        local dir candidate
        IFS=: read -ra path_dirs <<<"$PATH"
        for dir in "${path_dirs[@]}"; do
            for candidate in "$dir"/vicinae*.appimage "$dir"/Vicinae*.AppImage; do
                if [[ -x "$candidate" ]]; then
                    found_appimage=true
                    break 2
                fi
            done
        done

        if [[ "$found_appimage" != false ]]; then
            echo "vicinae AppImage fallback is available"
        fi
    fi

    echo "ok probePrograms"
}

probe_launch_contract() {
    local start_wrapper="/home/osso/bin/start-quickshell"
    local niri_config="/home/osso/.config/niri/config.kdl"
    local stale_repo_path="/home/osso/Repos/noctalia-shell"
    local stale_tilde_path="~/Repos/noctalia-shell"

    if [[ ! -x "$start_wrapper" ]]; then
        echo "Noctalia start wrapper is missing or not executable: $start_wrapper" >&2
        exit 1
    fi

    if [[ ! -r "$niri_config" ]]; then
        echo "Niri config is not readable: $niri_config" >&2
        exit 1
    fi

    local start_wrapper_source niri_config_source launch_sources
    start_wrapper_source="$(cat "$start_wrapper")"
    niri_config_source="$(cat "$niri_config")"
    launch_sources="$start_wrapper_source"$'\n'"$niri_config_source"

    if ! has_quickshell_launch_path "$start_wrapper_source" "$repo_root"; then
        echo "Noctalia start wrapper does not launch the canonical repo path: $repo_root" >&2
        exit 1
    fi

    if ! has_niri_start_wrapper "$niri_config_source"; then
        echo "Niri config does not autostart the Noctalia wrapper" >&2
        exit 1
    fi

    if ! has_quickshell_ipc_call "$niri_config_source" "$repo_root" "launcher" "toggle"; then
        echo "Niri launcher keybind does not target the canonical Noctalia path: $repo_root" >&2
        exit 1
    fi

    if ! has_quickshell_ipc_call "$niri_config_source" "$repo_root" "sessionMenu" "toggle"; then
        echo "Niri session menu keybind does not target the canonical Noctalia path: $repo_root" >&2
        exit 1
    fi

    if ! has_quickshell_ipc_call "$niri_config_source" "$repo_root" "settings" "toggle"; then
        echo "Niri settings keybind does not target the canonical Noctalia path: $repo_root" >&2
        exit 1
    fi

    if has_stale_launch_path "$launch_sources" "$stale_repo_path"; then
        echo "launch contract still references stale repo path: $stale_repo_path" >&2
        exit 1
    fi

    if has_stale_launch_path "$launch_sources" "$stale_tilde_path"; then
        echo "launch contract still references stale repo path: $stale_tilde_path" >&2
        exit 1
    fi

    echo "ok probeLaunchContract"
}

probe_ipc_targets() {
    require_command quickshell

    local niri_config="/home/osso/.config/niri/config.kdl"
    local ipc_output required_targets
    ipc_output="$(quickshell ipc -p "$repo_root" show)"
    required_targets=(
        launcher
        sessionMenu
        settings
        brightness
        volume
        notifications
        state
    )

    if [[ -z "$ipc_output" ]]; then
        echo "Quickshell IPC target list is empty for: $repo_root" >&2
        exit 1
    fi

    if [[ ! -r "$niri_config" ]]; then
        echo "Niri config is not readable: $niri_config" >&2
        exit 1
    fi

    local target
    for target in "${required_targets[@]}"; do
        if ! has_ipc_target "$ipc_output" "$target"; then
            echo "Quickshell IPC target is missing: $target" >&2
            exit 1
        fi
    done

    if ! has_ipc_toggle_handler "$ipc_output"; then
        echo "Quickshell IPC target list is missing toggle handlers" >&2
        exit 1
    fi

    local ipc_calls target_name function_name
    ipc_calls="$(list_quickshell_ipc_calls "$(cat "$niri_config")")"
    if [[ -z "$ipc_calls" ]]; then
        echo "Niri config has no Quickshell IPC calls to validate" >&2
        exit 1
    fi

    while read -r target_name function_name; do
        if ! has_ipc_target_function "$ipc_output" "$target_name" "$function_name"; then
            echo "Niri IPC call target/function is missing from live Quickshell IPC: $target_name $function_name" >&2
            exit 1
        fi
    done <<<"$ipc_calls"

    echo "ok probeIpcTargets"
}

probe_system_stats() {
    require_command ps

    local cpu_line meminfo ps_output
    cpu_line="$(awk '/^cpu / { print; exit }' /proc/stat)"
    meminfo="$(cat /proc/meminfo)"
    ps_output="$(ps -eo pid,%cpu,%mem,rss,args --sort=-%cpu --no-headers)"

    if ! is_proc_cpu_aggregate_row "$cpu_line"; then
        echo "/proc/stat CPU aggregate row is missing or malformed: $cpu_line" >&2
        exit 1
    fi

    if ! has_meminfo_kb_row "$meminfo" "MemTotal"; then
        echo "/proc/meminfo is missing MemTotal" >&2
        exit 1
    fi

    if ! has_meminfo_kb_row "$meminfo" "MemAvailable"; then
        echo "/proc/meminfo is missing MemAvailable" >&2
        exit 1
    fi

    if ! is_ps_process_row "$ps_output"; then
        echo "ps output for ProcessService is missing or malformed" >&2
        exit 1
    fi

    echo "ok probeSystemStats"
}

read_os_release_value() {
    local wanted="$1"
    local os_release_content="${2:-}"
    local key value

    while IFS='=' read -r key value; do
        if [[ "$key" != "$wanted" ]]; then
            continue
        fi

        value="${value%\"}"
        value="${value#\"}"
        printf '%s\n' "$value"
        return 0
    done < <(
        if [[ -n "$os_release_content" ]]; then
            printf '%s\n' "$os_release_content"
        else
            cat /etc/os-release
        fi
    )

    return 1
}

find_host_logo_path() {
    local logo_name="$1"
    local sizes=(512x512 256x256 128x128 64x64 48x48 32x32 24x24 22x22 16x16)
    local exts=(svg png)
    local ext size candidate

    for ext in "${exts[@]}"; do
        candidate="/usr/share/pixmaps/${logo_name}.${ext}"
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    candidate="/usr/share/icons/hicolor/scalable/apps/${logo_name}.svg"
    if [[ -f "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
    fi

    for size in "${sizes[@]}"; do
        for ext in "${exts[@]}"; do
            candidate="/usr/share/icons/hicolor/${size}/apps/${logo_name}.${ext}"
            if [[ -f "$candidate" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done
    done

    candidate="/run/current-system/sw/share/icons/hicolor/scalable/apps/${logo_name}.svg"
    if [[ -f "$candidate" ]]; then
        printf '%s\n' "$candidate"
        return 0
    fi

    for size in "${sizes[@]}"; do
        for ext in "${exts[@]}"; do
            candidate="/run/current-system/sw/share/icons/hicolor/${size}/apps/${logo_name}.${ext}"
            if [[ -f "$candidate" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done
    done

    for ext in "${exts[@]}"; do
        for candidate in \
            "/usr/share/icons/${logo_name}.${ext}" \
            "/usr/share/icons/${logo_name}/${logo_name}.${ext}" \
            "/usr/share/icons/${logo_name}/apps/${logo_name}.${ext}"; do
            if [[ -f "$candidate" ]]; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done
    done

    return 1
}

probe_host_fonts() {
    require_command getent
    require_command fc-list

    if [[ ! -r /etc/os-release ]]; then
        echo "/etc/os-release is not readable" >&2
        exit 1
    fi

    local os_name os_id os_logo logo_path passwd_row fontconfig_fonts
    os_name="$(read_os_release_value PRETTY_NAME || read_os_release_value NAME || true)"
    os_id="$(read_os_release_value ID || true)"
    os_logo="$(read_os_release_value LOGO || true)"

    if [[ -z "$os_name" ]]; then
        echo "/etc/os-release is missing PRETTY_NAME and NAME" >&2
        exit 1
    fi

    if [[ -z "$os_id" ]]; then
        echo "/etc/os-release is missing ID" >&2
        exit 1
    fi

    if [[ -n "$os_logo" ]]; then
        logo_path="$(find_host_logo_path "$os_logo" || true)"
        if [[ -z "$logo_path" ]]; then
            echo "host logo listed in /etc/os-release is not resolvable: $os_logo" >&2
            exit 1
        fi
    fi

    if [[ -z "${USER:-}" ]]; then
        echo "USER is not set for HostService passwd lookup" >&2
        exit 1
    fi

    passwd_row="$(getent passwd "$USER" || true)"
    if ! is_passwd_row "$passwd_row"; then
        echo "passwd row for USER is missing or malformed: $passwd_row" >&2
        exit 1
    fi

    fontconfig_fonts="$(fc-list :mono family)"
    if ! has_readable_font_family "$fontconfig_fonts"; then
        echo "fc-list monospace output has no readable family names" >&2
        exit 1
    fi

    echo "ok probeHostFonts"
}

usage() {
    cat <<'USAGE'
Usage: Bin/dev/service-probes.sh [all|notifications|audio|brightness|clipboard|lock-keys|wallpaper-colors|settings|state-cache|network|power-profile|battery|bluetooth|vpn|screen-recorder|programs|launch-contract|ipc-targets|system-stats|host-fonts]

Runs read-only probes for services used by the local shell.
USAGE
}

main() {
    local probe="${1:-all}"

    case "$probe" in
        all)
            probe_notifications
            probe_audio
            probe_brightness
            probe_clipboard
            probe_lock_keys
            probe_wallpaper_colors
            probe_settings
            probe_state_cache
            probe_network
            probe_power_profile
            probe_battery
            probe_bluetooth
            probe_vpn
            probe_screen_recorder
            probe_programs
            probe_launch_contract
            probe_ipc_targets
            probe_system_stats
            probe_host_fonts
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
        lock-keys)
            probe_lock_keys
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
        battery)
            probe_battery
            ;;
        bluetooth)
            probe_bluetooth
            ;;
        vpn)
            probe_vpn
            ;;
        screen-recorder)
            probe_screen_recorder
            ;;
        programs)
            probe_programs
            ;;
        launch-contract)
            probe_launch_contract
            ;;
        ipc-targets)
            probe_ipc_targets
            ;;
        system-stats)
            probe_system_stats
            ;;
        host-fonts)
            probe_host_fonts
            ;;
        -h | --help | help)
            usage
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
