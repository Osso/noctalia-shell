#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

source "$repo_root/Bin/dev/service-probes.sh"

assert_equal() {
    local actual="$1"
    local expected="$2"
    local message="$3"

    if [[ "$actual" != "$expected" ]]; then
        echo "$message: expected '$expected', got '$actual'" >&2
        exit 1
    fi
}

ddc_detect_fixture='Display 1
   I2C bus:  /dev/i2c-4
   DRM_connector:           card1-HDMI-A-1
   EDID synopsis:
      Mfg id:               GSM - LG Electronics
      Model:                LG ULTRAWIDE

Display 2
   I2C bus:  /dev/i2c-7
   EDID synopsis:
      Model:                Other Display'

assert_equal "$(find_lg_ultrawide_bus "$ddc_detect_fixture")" "4" "LG ULTRAWIDE bus parse failed"

ddc_detect_without_lg='Display 1
   I2C bus:  /dev/i2c-9
   EDID synopsis:
      Model:                Other Display'

assert_equal "$(find_lg_ultrawide_bus "$ddc_detect_without_lg")" "" "non-LG display must not select a DDC bus"

is_ddc_brightness_output "VCP 10 C 25 100"

if is_ddc_brightness_output "VCP 10 C unsupported"; then
    echo "invalid DDC brightness output was accepted" >&2
    exit 1
fi

is_wpctl_volume_output "Volume: 0.42"
is_wpctl_volume_output "Volume: 1 [MUTED]"

if is_wpctl_volume_output "Volume: muted"; then
    echo "invalid wpctl volume output was accepted" >&2
    exit 1
fi

has_supported_clipboard_mime $'application/x-special\ntext/html'
has_supported_clipboard_mime $'image/png\napplication/octet-stream'

if has_supported_clipboard_mime $'application/x-special\napplication/octet-stream'; then
    echo "unsupported clipboard MIME list was accepted" >&2
    exit 1
fi

has_lock_key_state_rows $'caps:0\nnum:1\nscroll:0'

if has_lock_key_state_rows $'caps:0\nnum:1'; then
    echo "incomplete lock-key state rows were accepted" >&2
    exit 1
fi

is_bluetooth_controller_row "Controller AA:BB:CC:DD:EE:FF aso [default]"
has_bluetooth_toggle_state $'Powered: yes\nDiscovering: no'
is_bluetooth_device_row "Device 11:22:33:44:55:66 Keyboard"

if is_bluetooth_controller_row "Controller missing-address"; then
    echo "invalid Bluetooth controller row was accepted" >&2
    exit 1
fi

if has_bluetooth_toggle_state $'Powered: maybe\nDiscovering: no'; then
    echo "invalid Bluetooth toggle state was accepted" >&2
    exit 1
fi

if is_bluetooth_device_row "Device not-a-mac Keyboard"; then
    echo "invalid Bluetooth device row was accepted" >&2
    exit 1
fi

is_gpu_screen_recorder_monitor_row "HDMI-A-1|3440x1440"
has_gpu_screen_recorder_capture_option $'HDMI-A-1|3440x1440@165hz|card1\nportal'

if is_gpu_screen_recorder_monitor_row "HDMI-A-1 3440x1440"; then
    echo "invalid gpu-screen-recorder monitor row was accepted" >&2
    exit 1
fi

if has_gpu_screen_recorder_capture_option $'   '; then
    echo "invalid gpu-screen-recorder capture option was accepted" >&2
    exit 1
fi

is_power_profile_name "balanced"
has_power_profile_entries $'performance:\n* balanced:\npower-saver:'
has_active_power_profile_marker $'performance:\n* balanced:\npower-saver:' "balanced"

if is_power_profile_name "turbo"; then
    echo "invalid power profile name was accepted" >&2
    exit 1
fi

if has_power_profile_entries $'performance:\n* balanced:'; then
    echo "incomplete power profile list was accepted" >&2
    exit 1
fi

if has_active_power_profile_marker $'performance:\nbalanced:\npower-saver:' "balanced"; then
    echo "unmarked active power profile was accepted" >&2
    exit 1
fi

is_vpn_connection_type "vpn"
is_vpn_connection_type "wireguard"
is_nm_uuid "123e4567-e89b-12d3-a456-426614174000"
is_active_nm_device "wg0"

if is_vpn_connection_type "802-11-wireless"; then
    echo "non-VPN NetworkManager type was accepted" >&2
    exit 1
fi

if is_nm_uuid "not-a-uuid"; then
    echo "malformed NetworkManager UUID was accepted" >&2
    exit 1
fi

if is_active_nm_device "--"; then
    echo "inactive NetworkManager device placeholder was accepted" >&2
    exit 1
fi

is_proc_cpu_aggregate_row "cpu  123 0 456 789 0 0 0 0 0 0"
has_meminfo_kb_row $'MemTotal:       32768000 kB\nMemAvailable:   12345678 kB' "MemTotal"
is_ps_process_row " 1234  1.5  0.4  65536 quickshell"

if is_proc_cpu_aggregate_row "cpu not-numbers"; then
    echo "invalid /proc/stat CPU row was accepted" >&2
    exit 1
fi

if has_meminfo_kb_row $'MemTotal: none kB' "MemAvailable"; then
    echo "missing /proc/meminfo row was accepted" >&2
    exit 1
fi

if is_ps_process_row "pid cpu mem rss args"; then
    echo "invalid ps process row was accepted" >&2
    exit 1
fi

has_upower_percentage "percentage:          87%"
has_upower_battery_state "state:               discharging"
has_physical_upower_battery_details $'native-path:          BAT0\nrechargeable:        yes'

if has_upower_percentage "percentage: unknown"; then
    echo "invalid UPower percentage was accepted" >&2
    exit 1
fi

if has_upower_battery_state "state:               broken"; then
    echo "invalid UPower battery state was accepted" >&2
    exit 1
fi

if has_physical_upower_battery_details $'native-path:          BAT0\nrechargeable:        no'; then
    echo "incomplete UPower battery details were accepted" >&2
    exit 1
fi

is_network_connection_type "802-11-wireless"
is_network_connection_type "802-3-ethernet"
has_connected_wifi_device_status "wlan0:wifi:connected:Home WiFi" "Home WiFi"

if is_network_connection_type "bridge"; then
    echo "unsupported NetworkManager connection type was accepted" >&2
    exit 1
fi

if has_connected_wifi_device_status "wlan0:wifi:disconnected:Home WiFi" "Home WiFi"; then
    echo "disconnected Wi-Fi device status was accepted" >&2
    exit 1
fi

is_passwd_row "osso:x:1000:1000:Alessio:/home/osso:/usr/bin/zsh"
has_readable_font_family $'JetBrains Mono\nNoto Sans Mono'

if is_passwd_row "osso:x:not-a-uid:1000:Alessio:/home/osso:/usr/bin/zsh"; then
    echo "invalid passwd row was accepted" >&2
    exit 1
fi

if has_readable_font_family $'   \n12345'; then
    echo "font output without readable family names was accepted" >&2
    exit 1
fi

ipc_fixture=$'target launcher\n  function toggle(): void\ntarget settings\n  function toggle(): void\n  function open(): void'

has_ipc_target "$ipc_fixture" "launcher"
has_ipc_toggle_handler "$ipc_fixture"
has_ipc_target_function "$ipc_fixture" "settings" "open"

if has_ipc_target "$ipc_fixture" "missing"; then
    echo "missing IPC target was accepted" >&2
    exit 1
fi

if has_ipc_target_function "$ipc_fixture" "launcher" "open"; then
    echo "missing IPC target function was accepted" >&2
    exit 1
fi

echo "ok testServiceProbeParsing"
