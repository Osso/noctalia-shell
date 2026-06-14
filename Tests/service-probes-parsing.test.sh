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

echo "ok testServiceProbeParsing"
