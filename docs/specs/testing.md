Testing covers local regression gates, function-coverage guardrails, and log filtering used to keep this fork maintainable against current Quickshell. Runtime source lives mainly in `run-tests.sh`, `Tests/source-coverage.test.js`, `Tests/qml-function-inventory.test.js`, and `Bin/dev/quickshell-regression.sh`.

## What it must do

### Function coverage guardrails

- [x] QML source function coverage must stay complete according to `code-index untested`.
- [x] QML source function inventory must stay broad enough to catch regressions.
- [x] `code-index` must inventory every QML `function` declaration outside `Tests/`.
- [x] Non-test source functions must have code-index coverage.
- [x] QML function inventory anchors must keep required high-risk QML functions discoverable.
- [x] Every executable test file must be named by at least one `docs/specs` contract.
- [x] Every non-meta executable test file must be named by at least one feature spec, not only by the testing spec.
- [x] The meta-test allowlist must stay explicit and must be the only set of tests allowed to skip feature specs.

### Quickshell regression log gate

- [x] Current-reload log filtering must drop stale errors that appeared before the latest reload marker.
- [x] Current-reload log filtering must keep the reload marker.
- [x] Current-reload log filtering must keep log lines from the current reload window.
- [x] Fatal-pattern fixture coverage must match high-signal QML load/runtime failures and avoid normal informational log lines.
- [x] The live Quickshell log gate must fail when the current reload window contains high-signal QML load/runtime failures.
- [x] The live Quickshell log gate must identify the local shell from Quickshell's running-instance registry by matching this repository's `shell.qml`, without relying on the process command line.
- [x] The live Quickshell log gate must report a clear no-shell diagnostic when no local shell is running.

### Runner contract

- [x] `./run-tests.sh all` (the default) and `./run-tests.sh regression` run the explicit deterministic unit list, structural QML static check, read-only service probes, and active Quickshell log gate; they do not run visible notification probes.
- [x] `./run-tests.sh unit` runs the explicit deterministic test list: JavaScript unit, guard, and contract tests plus Python/Bash parser and log-filter fixtures, without host probes or visible notifications. It does not auto-discover every executable test file.
- [x] `./run-tests.sh qml` runs the structural QML static check.
- [x] `./run-tests.sh probes` runs read-only service probes and injects the deterministic Bluetooth CLI fixture rather than contacting host Bluetooth hardware.
- [x] `./run-tests.sh log` runs the active Quickshell log regression gate.
- [x] `./run-tests.sh notifications` runs the visible notification probes and is isolated from the default gates.
- [x] The runner keeps deterministic tests (`unit`), structural QML lint (`qml`), host/read-only probes (`probes`), active log checks (`log`), and visible notification probes (`notifications`) as separate command paths; `all` and `regression` compose only the first four.
- [x] Runner and helper gates fail closed: `set -euo pipefail` stops composed commands on non-zero subcommands; commands with explicit dependency checks and unknown commands return status 2; failed or malformed probes, a missing local shell, and fatal current-reload log matches return status 1. Documented optional states are limited to unavailable/unsupported clipboard MIME data and an absent LG DDC monitor.

## How it works

- Runtime behavior is implemented in `run-tests.sh` and the test/probe files listed below.

## Implementation inventory

- `run-tests.sh` - local test runner and gate grouping.
- `Tests/source-coverage.test.js` - source function coverage and QML declaration inventory guard.
- `Tests/qml-function-inventory.test.js` - explicit QML function anchor inventory for high-risk source files.
- `Tests/quickshell-regression.test.sh` - current-reload log filtering fixture.
- `Bin/dev/quickshell-regression.sh` - live Quickshell log regression gate.
- `Bin/dev/qml-static-check.sh` - focused qmllint gate.
- `Bin/dev/service-probes.sh` - read-only runtime/service probes; direct Bluetooth invocation remains a bounded host diagnostic.
- `Tests/fixtures/bluetoothctl` - deterministic Bluetooth CLI fixture selected by automated probe runs.

## Tests asserting this spec

- `Tests/source-coverage.test.js`
- `Tests/qml-function-inventory.test.js`
- `Tests/quickshell-regression.test.sh`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] The registry fixture does not yet assert selection of the newest matching `shell.qml` instance when multiple local registrations exist.
- [ ] Add the spec-mapped executable guard tests currently omitted from `run_unit_tests`: `Tests/audio-ui-guards.test.js`, `Tests/background-resource-guards.test.js`, `Tests/battery-service-guards.test.js`, `Tests/clock-widget-guards.test.js`, `Tests/control-center-panel-guards.test.js`, `Tests/control-center-widget-registry-guards.test.js`, `Tests/fan-widget-guards.test.js`, `Tests/image-widget-resource-guards.test.js`, `Tests/keyboard-layout-widget-guards.test.js`, `Tests/lock-keys-service-guards.test.js`, `Tests/main-screen-lazy-panels.test.js`, `Tests/runtime-warning-guards.test.js`, and `Tests/simple-toast-guards.test.js`.
- [ ] Normalize missing direct command dependencies in `run-tests.sh unit` and `run-tests.sh notifications`; currently those paths can return shell status 127 instead of the documented status 2.

## Out of scope

- Feature behavior tested by individual guard suites belongs in that feature's spec.
- Manual visible notification probes belong in [notifications.md](notifications.md).
