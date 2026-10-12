#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/Bin/dev/service-probes.sh"

fixture_dir="$(mktemp -d)"
trap 'rm -rf -- "$fixture_dir"' EXIT
export BRIGHTNESS_PROBE_CALLS="$fixture_dir/brightnessctl.calls"
export BRIGHTNESS_PROBE_DEVICE="amdgpu_bl1"
cat >"$fixture_dir/brightnessctl" <<'FIXTURE'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$BRIGHTNESS_PROBE_CALLS"
[[ "$#" == 1 && "$1" == --list ]] || exit 90
printf "Device '%s' of class 'backlight':\n" "$BRIGHTNESS_PROBE_DEVICE"
FIXTURE
chmod +x "$fixture_dir/brightnessctl"
export PATH="$fixture_dir:$PATH"

assert_equal() {
    if [[ "$1" != "$2" ]]; then
        printf '%s: expected <%s>, got <%s>\n' "$3" "$2" "$1" >&2
        exit 1
    fi
}

output="$("$repo_root/Bin/dev/service-probes.sh" brightness 2>&1)" || {
    printf 'brightness probe must succeed without invoking live DDC: %s\n' "$output" >&2
    exit 1
}
assert_equal "$output" $'ok probeBrightnessDdcFixture (private data only; live DDC not tested)\nok probeBrightness' "fixture evidence label"
assert_equal "$(<"$BRIGHTNESS_PROBE_CALLS")" '--list' "read-only backlight command"
echo 'ok brightness probe uses private DDC data and backlight --list'

export BRIGHTNESS_PROBE_DEVICE="other_backlight"
if output="$("$repo_root/Bin/dev/service-probes.sh" brightness 2>&1)"; then
    echo 'missing internal backlight was accepted' >&2
    exit 1
fi
assert_equal "$output" 'expected internal backlight device amdgpu_bl1 was not found' "backlight failure"
echo 'ok missing internal backlight fails'

detect=$'Display 1\n   I2C bus:  /dev/i2c-4\n   EDID synopsis:\n      Model:                LG ULTRAWIDE\n\nDisplay 2\n   I2C bus:  /dev/i2c-7\n      Model:                Other Display'

assert_fixture() {
    local description="$1" expected_status="$2" expected_output="$3"
    local actual_status=0 actual_output
    shift 3
    actual_output="$(validate_ddc_brightness_fixture "$@" 2>&1)" || actual_status="$?"
    assert_equal "$actual_status" "$expected_status" "$description status"
    assert_equal "$actual_output" "$expected_output" "$description output"
    echo "ok $description"
}

assert_fixture 'no display' 1 'DDC fixture has no LG ULTRAWIDE bus' 0 'No displays found' 0 'VCP 10 C 25 100'
assert_fixture 'malformed detect bus' 1 'DDC fixture has no LG ULTRAWIDE bus' 0 $'Display 1\n   I2C bus:  /dev/i2c-4 trailing\n      Model: LG ULTRAWIDE' 0 'VCP 10 C 25 100'
assert_fixture 'stale bus across displays' 1 'DDC fixture has no LG ULTRAWIDE bus' 0 $'Display 1\n   I2C bus: /dev/i2c-3\n      Model: Other Display\nDisplay 2\n      Model: LG ULTRAWIDE' 0 'VCP 10 C 25 100'
assert_fixture 'detect error with valid-looking data' 1 'DDC fixture detect failed with exit status 7' 7 "$detect" 0 'VCP 10 C 25 100'
assert_fixture 'getvcp error with valid-looking data' 1 'DDC fixture getvcp failed with exit status 8' 0 "$detect" 8 'VCP 10 C 25 100'
assert_fixture 'malformed VCP' 1 'unexpected DDC fixture brightness output on bus 4: VCP 10 C unsupported' 0 "$detect" 0 'VCP 10 C unsupported'
assert_fixture 'out-of-range VCP' 1 'unexpected DDC fixture brightness output on bus 4: VCP 10 C 101 100' 0 "$detect" 0 'VCP 10 C 101 100'
assert_fixture 'valid VCP' 0 '' 0 "$detect" 0 'VCP 10 C 25 100'
assert_fixture 'zero VCP' 0 '' 0 "$detect" 0 'VCP 10 C 0 100'
assert_fixture 'maximum VCP' 0 '' 0 "$detect" 0 'VCP 10 C 100 100'
