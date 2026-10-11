#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runner="$repo_root/run-tests.sh"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
help_output="$("$runner" --help)"

for category in \
    'deterministic-unit' \
    'structural-reference' \
    'qml-static' \
    'host-probes' \
    'live-log' \
    'visible-notifications'; do
    if ! printf '%s\n' "$help_output" | rg -q "$category"; then
        echo "runner help omitted evidence category: $category" >&2
        exit 1
    fi
done

set +e
unknown_output="$("$runner" unknown 2>&1)"
unknown_status="$?"
set -e
if [ "$unknown_status" -ne 2 ]; then
    echo "unknown runner command returned $unknown_status, expected 2" >&2
    exit 1
fi
if ! printf '%s\n' "$unknown_output" | rg -q 'Usage:'; then
    echo "unknown runner command omitted usage" >&2
    exit 1
fi

# Exercise the real unit runner, stopping before unrelated Python suites.
mkdir -p "$tmp_dir/bin"
printf '#!/bin/sh\nexit 0\n' >"$tmp_dir/bin/node"
cat >"$tmp_dir/bin/python3" <<'PYTHON'
#!/bin/sh
printf '%s\n' "${1##*/}${2:+ $2}${3:+ $3}"
case "${1##*/}" in
    settings-types.test.py | system-monitor-runtime.test.py)
        exit 0
        ;;
    media-mini-warnings.test.py)
        [ "${2:-}" = behavior ] || exit 40
        exit 0
        ;;
    sound-service-runtime.test.py)
        exit "$SOUND_TEST_STATUS"
        ;;
    datetime-tokens-layout-runtime.test.py)
        exit "$DATETIME_TEST_STATUS"
        ;;
    setup-layout-geometry.test.py)
        exit "$SETUP_TEST_STATUS"
        ;;
    calendar-service-runtime.test.py)
        exit "$CALENDAR_TEST_STATUS"
        ;;
    timer-card-runtime.test.py)
        [ "${2:-}" = behavior ] && [ "$#" -eq 2 ] || exit 40
        exit "$TIMER_TEST_STATUS"
        ;;
    file-picker-warnings.test.py)
        [ "${2:-}" = --mode ] && [ "${3:-}" = runtime ] && [ "$#" -eq 3 ] || exit 40
        exit "$PICKER_TEST_STATUS"
        ;;
esac
if [ "${1##*/}" = color-namespace-runtime.test.py ]; then
    exit "$COLOR_TEST_STATUS"
fi
if [ "${1##*/}" = weather-card-effects.test.py ]; then
    exit 0
fi
exit 38
PYTHON
chmod +x "$tmp_dir/bin/node" "$tmp_dir/bin/python3"
cat >"$tmp_dir/unit-driver.sh" <<'DRIVER'
#!/usr/bin/env bash
set -euo pipefail
source "$RUNNER_UNDER_TEST"
run_qml_runtime_tests() { :; }
run_command unit
DRIVER

for test_statuses in 0:0:0:0:0:0:0 37:0:0:0:0:0:0 0:39:0:0:0:0:0 0:0:41:0:0:0:0 0:0:0:42:0:0:0 0:0:0:0:43:0:0 0:0:0:0:0:44:0 0:0:0:0:0:0:45; do
    IFS=: read -r color_status sound_status datetime_status setup_status calendar_status timer_status picker_status <<<"$test_statuses"
    set +e
    unit_output="$(PATH="$tmp_dir/bin:$PATH" RUNNER_UNDER_TEST="$runner" COLOR_TEST_STATUS="$color_status" SOUND_TEST_STATUS="$sound_status" DATETIME_TEST_STATUS="$datetime_status" SETUP_TEST_STATUS="$setup_status" CALENDAR_TEST_STATUS="$calendar_status" TIMER_TEST_STATUS="$timer_status" PICKER_TEST_STATUS="$picker_status" \
        bash "$tmp_dir/unit-driver.sh" 2>&1)"
    unit_status="$?"
    set -e
    for runtime_test in \
        'settings-types.test.py' \
        'system-monitor-runtime.test.py' \
        'media-mini-warnings.test.py behavior' \
        'sound-service-runtime.test.py'; do
        if [ "$(printf '%s\n' "$unit_output" | rg -F -x -c "$runtime_test" || true)" != 1 ]; then
            echo "unit runner omitted or repeated runtime regression: $runtime_test" >&2
            exit 1
        fi
    done
    runtime_order='settings-types.test.py.*system-monitor-runtime.test.py.*media-mini-warnings.test.py behavior.*sound-service-runtime.test.py'
    if ! printf '%s\n' "$unit_output" | tr '\n' ' ' | rg -q "$runtime_order"; then
        echo "unit runner runtime regression order is incoherent" >&2
        exit 1
    fi
    if [ "$sound_status" -ne 0 ]; then
        if [ "$unit_status" -ne 39 ] || ! printf '%s\n' "$unit_output" | rg -q 'EVIDENCE FAIL deterministic-unit \(exit 39\)' || printf '%s\n' "$unit_output" | rg -q '^datetime-tokens-layout-runtime.test.py$|^setup-layout-geometry.test.py$|^calendar-service-runtime.test.py$|^timer-card-runtime.test.py behavior$|^file-picker-warnings.test.py --mode runtime$|^color-namespace-runtime.test.py$|^weather-card-effects.test.py$|^calendar-events-safe-get-time.test.py$|EVIDENCE PASS|EVIDENCE START structural-reference'; then
            echo "unit runner did not stop with sound runtime regression failure status" >&2
            exit 1
        fi
        continue
    fi
    for runtime_case in \
        "datetime-tokens-layout-runtime.test.py:$datetime_status" \
        "setup-layout-geometry.test.py:$setup_status" \
        "calendar-service-runtime.test.py:$calendar_status" \
        "timer-card-runtime.test.py behavior:$timer_status" \
        "file-picker-warnings.test.py --mode runtime:$picker_status"; do
        runtime_test="${runtime_case%:*}"
        runtime_status="${runtime_case#*:}"
        if [ "$(printf '%s\n' "$unit_output" | rg -F -x -c "$runtime_test" || true)" != 1 ]; then
            echo "unit runner omitted or repeated runtime regression: $runtime_test" >&2
            exit 1
        fi
        case "$runtime_test" in
            datetime-tokens-layout-runtime.test.py)
                later_tests='^setup-layout-geometry.test.py$|^calendar-service-runtime.test.py$|^timer-card-runtime.test.py behavior$|^file-picker-warnings.test.py --mode runtime$'
                ;;
            setup-layout-geometry.test.py)
                later_tests='^calendar-service-runtime.test.py$|^timer-card-runtime.test.py behavior$|^file-picker-warnings.test.py --mode runtime$'
                ;;
            calendar-service-runtime.test.py)
                later_tests='^timer-card-runtime.test.py behavior$|^file-picker-warnings.test.py --mode runtime$'
                ;;
            'timer-card-runtime.test.py behavior')
                later_tests='^file-picker-warnings.test.py --mode runtime$'
                ;;
            'file-picker-warnings.test.py --mode runtime')
                later_tests=''
                ;;
        esac
        later_tests="${later_tests:+$later_tests|}^color-namespace-runtime.test.py$|^weather-card-effects.test.py$|^calendar-events-safe-get-time.test.py$|EVIDENCE PASS|EVIDENCE START structural-reference"
        if [ "$runtime_status" -ne 0 ]; then
            if [ "$unit_status" -ne "$runtime_status" ] || ! printf '%s\n' "$unit_output" | rg -F -q "=== EVIDENCE FAIL deterministic-unit (exit $runtime_status) ===" || printf '%s\n' "$unit_output" | rg -q "$later_tests"; then
                echo "unit runner did not stop with runtime regression failure: $runtime_test (exit $runtime_status)" >&2
                exit 1
            fi
            continue 2
        fi
    done
    runtime_order='sound-service-runtime.test.py.*datetime-tokens-layout-runtime.test.py.*setup-layout-geometry.test.py.*calendar-service-runtime.test.py.*timer-card-runtime.test.py behavior.*file-picker-warnings.test.py --mode runtime.*color-namespace-runtime.test.py'
    if ! printf '%s\n' "$unit_output" | tr '\n' ' ' | rg -q "$runtime_order"; then
        echo "unit runner runtime regression order or continuation is incoherent" >&2
        exit 1
    fi
    if ! printf '%s\n' "$unit_output" | rg -q '^color-namespace-runtime.test.py$'; then
        echo "unit runner omitted offscreen color regression" >&2
        exit 1
    fi
    if [ "$color_status" -eq 0 ]; then
        if [ "$unit_status" -ne 38 ] || ! printf '%s\n' "$unit_output" | rg -q '^weather-card-effects.test.py$' || ! printf '%s\n' "$unit_output" | rg -q '^calendar-events-safe-get-time.test.py$'; then
            echo "unit runner did not continue after successful color and weather regressions" >&2
            exit 1
        fi
    elif [ "$unit_status" -ne 37 ] || printf '%s\n' "$unit_output" | rg -q '^weather-card-effects.test.py$|^calendar-events-safe-get-time.test.py$'; then
        echo "unit runner did not stop with color regression failure status" >&2
        exit 1
    fi
done

# Run the real QML category in an isolated checkout with bounded fixture commands.
qml_root="$tmp_dir/qml"
mkdir -p "$qml_root/Tests" "$qml_root/Bin/dev"
cp "$runner" "$qml_root/run-tests.sh"
cat >"$qml_root/Tests/qml-static-imports.test.py" <<'PYTHON'
import os
import sys

print("import-regression")
sys.exit(int(os.environ["IMPORT_TEST_STATUS"]))
PYTHON
printf '#!/bin/sh\nprintf "static-checker\\n"\n' >"$qml_root/Bin/dev/qml-static-check.sh"
chmod +x "$qml_root/Bin/dev/qml-static-check.sh"

for import_status in 0 37; do
    set +e
    qml_output="$(IMPORT_TEST_STATUS="$import_status" "$qml_root/run-tests.sh" qml 2>&1)"
    qml_status="$?"
    set -e
    if ! printf '%s\n' "$qml_output" | rg -q '^import-regression$'; then
        echo "QML runner omitted import-resolution regression" >&2
        exit 1
    fi
    if [ "$import_status" -eq 0 ]; then
        if [ "$qml_status" -ne 0 ] || ! printf '%s\n' "$qml_output" | tr '\n' ' ' | rg -q 'import-regression.*static-checker.*EVIDENCE PASS qml-static'; then
            echo "QML runner did not run static checker after successful import regression" >&2
            exit 1
        fi
    elif [ "$qml_status" -ne 37 ] || printf '%s\n' "$qml_output" | rg -q 'static-checker|EVIDENCE PASS'; then
        echo "QML runner did not stop with import regression failure status" >&2
        exit 1
    fi
done

source "$runner"
run_unit_tests() { echo "unit-body"; }
run_structural_tests() { echo "structural-body"; }
run_qml_static_check() { echo "qml-body"; }
run_service_probes() { echo "probes-body"; }
run_log_gate() { echo "log-body"; }

success_file="$tmp_dir/success.out"
set +e
run_command all >"$success_file" 2>&1
success_status="$?"
success_caller_errexit=false
if [[ $- == *e* ]]; then
    success_caller_errexit=true
fi
set -e
success_output="$(<"$success_file")"
if [ "$success_status" -ne 0 ] || [ "$success_caller_errexit" = true ]; then
    echo "successful all gate changed caller state or failed" >&2
    exit 1
fi
expected_order='EVIDENCE EXCLUDED visible-notifications.*EVIDENCE START deterministic-unit.*unit-body.*EVIDENCE PASS deterministic-unit.*EVIDENCE START structural-reference.*structural-body.*EVIDENCE PASS structural-reference.*EVIDENCE START qml-static.*qml-body.*EVIDENCE PASS qml-static.*EVIDENCE START host-probes.*probes-body.*EVIDENCE PASS host-probes.*EVIDENCE START live-log.*log-body.*EVIDENCE PASS live-log.*REGRESSION PASS'
if ! printf '%s\n' "$success_output" | tr '\n' ' ' | rg -q "$expected_order"; then
    echo "successful all gate evidence order is incoherent" >&2
    exit 1
fi
run_command all >/dev/null 2>&1
if [[ $- != *e* ]]; then
    echo "successful all gate disabled caller errexit" >&2
    exit 1
fi

run_unit_tests() {
    false
    echo "internal deterministic command continued after failure"
}
run_structural_tests() {
    echo "structural should not run after deterministic failure"
}
run_qml_static_check() {
    echo "qml should not run after deterministic failure"
}
run_service_probes() {
    echo "probes should not run after deterministic failure"
}
run_log_gate() {
    echo "log should not run after deterministic failure"
}

failure_file="$tmp_dir/failure.out"
set +e
run_command all >"$failure_file" 2>&1
failure_status="$?"
caller_errexit_after_failure=false
if [[ $- == *e* ]]; then
    caller_errexit_after_failure=true
fi
set -e
failure_output="$(<"$failure_file")"
if [ "$failure_status" -ne 1 ]; then
    echo "failing category returned $failure_status, expected 1" >&2
    exit 1
fi
if ! printf '%s\n' "$failure_output" | rg -q 'EVIDENCE EXCLUDED visible-notifications'; then
    echo "failed regression omitted visible notification exclusion" >&2
    exit 1
fi
if ! printf '%s\n' "$failure_output" | rg -q 'EVIDENCE FAIL deterministic-unit \(exit 1\)'; then
    echo "failed category omitted exact failure status" >&2
    exit 1
fi
if printf '%s\n' "$failure_output" | rg -q 'internal deterministic command continued|EVIDENCE PASS deterministic-unit|structural should not run|REGRESSION PASS'; then
    echo "failed regression continued or reported success" >&2
    exit 1
fi
if [ "$caller_errexit_after_failure" = true ]; then
    echo "run_category enabled errexit for a caller that had it disabled" >&2
    exit 1
fi

set +e
errexit_output="$(
    set -e
    run_command all 2>&1
)"
errexit_status="$?"
set -e
if [ "$errexit_status" -ne 1 ]; then
    echo "errexit caller received $errexit_status, expected 1" >&2
    exit 1
fi
if printf '%s\n' "$errexit_output" | rg -q 'internal deterministic command continued|structural should not run|REGRESSION PASS'; then
    echo "errexit caller continued after internal category failure" >&2
    exit 1
fi

conditional_output="$(
    if run_category "conditional-test" run_unit_tests 2>&1; then
        echo "conditional-success"
    else
        echo "conditional-failure:$?"
    fi
)"
if ! printf '%s\n' "$conditional_output" | tr '\n' ' ' | rg -q 'EVIDENCE FAIL conditional-test \(exit 1\).*conditional-failure:1'; then
    echo "conditional caller lost category failure status" >&2
    exit 1
fi
if printf '%s\n' "$conditional_output" | rg -q 'internal deterministic command continued|EVIDENCE PASS|conditional-success'; then
    echo "conditional caller suppressed internal fail-closed execution" >&2
    exit 1
fi

echo "ok testRunnerEvidenceCategories"
