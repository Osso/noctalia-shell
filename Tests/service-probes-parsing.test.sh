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

echo "ok testServiceProbeParsing"
