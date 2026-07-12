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

if ! rg -q 'run_category "deterministic-unit" run_unit_tests' "$runner"; then
    echo "all gate does not label deterministic unit evidence" >&2
    exit 1
fi
if ! rg -q 'run_category "structural-reference" run_structural_tests' "$runner"; then
    echo "all gate does not label structural-reference evidence" >&2
    exit 1
fi
if ! rg -q 'run_category "qml-static" run_qml_static_check' "$runner"; then
    echo "all gate does not label QML static evidence" >&2
    exit 1
fi
if ! rg -q 'run_category "host-probes" run_service_probes' "$runner"; then
    echo "all gate does not label host probe evidence" >&2
    exit 1
fi
if ! rg -q 'run_category "live-log" run_log_gate' "$runner"; then
    echo "all gate does not label live log evidence" >&2
    exit 1
fi
if ! rg -q 'EXCLUDED visible-notifications' "$runner"; then
    echo "all gate does not explicitly report visible notification exclusion" >&2
    exit 1
fi

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
errexit_output="$(set -e; run_command all 2>&1)"
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
