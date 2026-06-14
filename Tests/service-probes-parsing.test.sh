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

ddc_detect_lg_without_bus='Display 1
   I2C bus:  /dev/i2c-3
   EDID synopsis:
      Model:                Other Display

Display 2
   EDID synopsis:
      Model:                LG ULTRAWIDE'

assert_equal "$(find_lg_ultrawide_bus "$ddc_detect_lg_without_bus")" "" "LG display without its own I2C bus must not reuse previous display bus"

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
has_clipboard_mime_types $'application/octet-stream'

if has_supported_clipboard_mime $'application/x-special\napplication/octet-stream'; then
    echo "unsupported clipboard MIME list was accepted" >&2
    exit 1
fi

if has_supported_clipboard_mime $'text/plain-bad\nimage/'; then
    echo "malformed clipboard MIME list was accepted" >&2
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

if has_bluetooth_toggle_state $'NotPowered: yes\nNotDiscovering: no'; then
    echo "prefixed Bluetooth toggle state rows were accepted" >&2
    exit 1
fi

if has_bluetooth_toggle_state $'Powered: yes trailing\nDiscovering: no'; then
    echo "malformed Bluetooth toggle state rows were accepted" >&2
    exit 1
fi

if is_bluetooth_device_row "Device not-a-mac Keyboard"; then
    echo "invalid Bluetooth device row was accepted" >&2
    exit 1
fi

if is_bluetooth_controller_row "Controller AAAAAAAAAAAAAAAAA aso [default]"; then
    echo "malformed Bluetooth controller MAC row was accepted" >&2
    exit 1
fi

if is_bluetooth_device_row "Device AAAAAAAAAAAAAAAAA Keyboard"; then
    echo "malformed Bluetooth device MAC row was accepted" >&2
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

if has_gpu_screen_recorder_capture_option "portal trailing"; then
    echo "malformed gpu-screen-recorder capture option line was accepted" >&2
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

if has_power_profile_entries $'notperformance:\n* balanced:\npower-saver:'; then
    echo "prefixed power profile name was accepted" >&2
    exit 1
fi

if has_active_power_profile_marker $'performance:\nbalanced:\npower-saver:' "balanced"; then
    echo "unmarked active power profile was accepted" >&2
    exit 1
fi

if has_active_power_profile_marker $'performance:\n* balanced: extra\npower-saver:' "balanced"; then
    echo "malformed active power profile row was accepted" >&2
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

if is_proc_cpu_aggregate_row "cpu  123 0 456 789 trailing"; then
    echo "truncated /proc/stat CPU row was accepted" >&2
    exit 1
fi

if has_meminfo_kb_row $'MemTotal: none kB' "MemAvailable"; then
    echo "missing /proc/meminfo row was accepted" >&2
    exit 1
fi

if has_meminfo_kb_row $'MemAvailable: 12345678 kB trailing' "MemAvailable"; then
    echo "malformed /proc/meminfo row was accepted" >&2
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

if has_upower_percentage "notpercentage:          87%"; then
    echo "prefixed UPower percentage row was accepted" >&2
    exit 1
fi

if has_upower_percentage "percentage:          87% trailing"; then
    echo "malformed UPower percentage row was accepted" >&2
    exit 1
fi

if has_upower_battery_state "state:               broken"; then
    echo "invalid UPower battery state was accepted" >&2
    exit 1
fi

if has_upower_battery_state "notstate:               discharging"; then
    echo "prefixed UPower battery state row was accepted" >&2
    exit 1
fi

if has_upower_battery_state "state:               discharging trailing"; then
    echo "malformed UPower battery state row was accepted" >&2
    exit 1
fi

if has_physical_upower_battery_details $'native-path:          BAT0\nrechargeable:        no'; then
    echo "incomplete UPower battery details were accepted" >&2
    exit 1
fi

if has_physical_upower_battery_details $'notnative-path:          BAT0\nnotrechargeable:        yes'; then
    echo "prefixed physical UPower battery details were accepted" >&2
    exit 1
fi

if has_physical_upower_battery_details $'native-path:          BAT0\nrechargeable:        yes trailing'; then
    echo "malformed physical UPower battery details were accepted" >&2
    exit 1
fi

if has_physical_upower_battery_details $'native-path:          \nrechargeable:        yes'; then
    echo "empty physical UPower native path was accepted" >&2
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

if has_connected_wifi_device_status "wlan0:wifi:connected:Home WiFi Guest" "Home WiFi"; then
    echo "prefixed Wi-Fi connection name was accepted" >&2
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

os_release_fixture=$'PRETTY_NAME="Noctalia Test OS"\nNAME=NoctaliaTest\nID=noctalia-test\nLOGO=noctalia-test-logo'
assert_equal "$(read_os_release_value PRETTY_NAME "$os_release_fixture")" "Noctalia Test OS" "quoted os-release value parse failed"
assert_equal "$(read_os_release_value ID "$os_release_fixture")" "noctalia-test" "unquoted os-release value parse failed"

if read_os_release_value MISSING_KEY "$os_release_fixture" >/dev/null; then
    echo "missing os-release key was accepted" >&2
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

if has_ipc_target_function $'target settings\n  function open(): void trailing' "settings" "open"; then
    echo "malformed IPC target function was accepted" >&2
    exit 1
fi

if has_ipc_toggle_handler $'target launcher\n  notfunction toggle(): void'; then
    echo "malformed IPC toggle handler was accepted" >&2
    exit 1
fi

canonical_repo="/syncthing/Sync/Projects/apps/noctalia-shell"
start_wrapper_fixture=$'#!/usr/bin/env bash\nexec quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell "$@"'
niri_config_fixture=$'spawn-at-startup "/home/osso/bin/start-quickshell"\nbinds {\n    Mod+Space { spawn "quickshell" "ipc" "-p" "/syncthing/Sync/Projects/apps/noctalia-shell" "call" "launcher" "toggle"; }\n    Mod+Shift+S { spawn "quickshell" "ipc" "-p" "/syncthing/Sync/Projects/apps/noctalia-shell" "call" "settings" "toggle"; }\n}'

has_quickshell_launch_path "$start_wrapper_fixture" "$canonical_repo"
has_niri_start_wrapper "$niri_config_fixture"
has_quickshell_ipc_call "$niri_config_fixture" "$canonical_repo" "launcher" "toggle"
has_quickshell_ipc_call "$niri_config_fixture" "$canonical_repo" "settings" "toggle"

spawn_sh_niri_fixture=$'Mod+Space { spawn-sh "quickshell ipc -p /syncthing/Sync/Projects/apps/noctalia-shell call launcher toggle"; }\nMod+P { spawn-sh "quickshell ipc -p /syncthing/Sync/Projects/apps/noctalia-shell call sessionMenu toggle"; }'
assert_equal "$(list_quickshell_ipc_calls "$spawn_sh_niri_fixture")" $'launcher toggle\nsessionMenu toggle' "spawn-sh IPC call extraction failed"
assert_equal "$(list_quickshell_ipc_calls "$niri_config_fixture")" $'launcher toggle\nsettings toggle' "quoted spawn IPC call extraction failed"
assert_equal "$(list_quickshell_ipc_calls 'spawn not-quickshell call launcher toggle')" "" "non-Quickshell IPC call extraction failed"

if has_quickshell_launch_path "$start_wrapper_fixture" "/home/osso/Repos/noctalia-shell"; then
    echo "stale wrapper launch path was accepted" >&2
    exit 1
fi

if has_quickshell_launch_path "exec quickshell -p ${canonical_repo}-old" "$canonical_repo"; then
    echo "prefixed wrapper launch path was accepted" >&2
    exit 1
fi

if has_niri_start_wrapper '// spawn-at-startup "/home/osso/bin/start-quickshell"'; then
    echo "commented Niri start wrapper was accepted" >&2
    exit 1
fi

if has_quickshell_ipc_call "$niri_config_fixture" "$canonical_repo" "sessionMenu" "toggle"; then
    echo "missing Niri IPC call was accepted" >&2
    exit 1
fi

if has_quickshell_ipc_call "spawn quickshell ipc -p $canonical_repo call launcher toggleExtra" "$canonical_repo" "launcher" "toggle"; then
    echo "prefixed Niri IPC function was accepted" >&2
    exit 1
fi

if has_stale_launch_path "$start_wrapper_fixture"$'\n'"$niri_config_fixture" "/home/osso/Repos/noctalia-shell" "~/Repos/noctalia-shell"; then
    echo "stale-free launch fixtures were flagged as stale" >&2
    exit 1
fi

if has_stale_launch_path "quickshell -p /home/osso/Repos/noctalia-shell-old" "/home/osso/Repos/noctalia-shell"; then
    echo "prefixed stale launch path was detected" >&2
    exit 1
fi

if ! has_stale_launch_path "quickshell -p /home/osso/Repos/noctalia-shell" "/home/osso/Repos/noctalia-shell" "~/Repos/noctalia-shell"; then
    echo "stale launch path was not detected" >&2
    exit 1
fi

echo "ok testServiceProbeParsing"
