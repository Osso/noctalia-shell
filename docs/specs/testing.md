Testing covers local regression gates, function-coverage guardrails, and log filtering used to keep this fork maintainable against current Quickshell. Runtime source lives mainly in `run-tests.sh`, `Tests/source-coverage.test.js`, `Tests/qml-function-inventory.test.js`, and `Bin/dev/quickshell-regression.sh`; implementation notes belong in [docs/wiki/systems/testing.md](../wiki/systems/testing.md).

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
- [x] The live Quickshell log gate must report a clear no-shell diagnostic when no local shell is running.

### Runner contract

- [x] `./run-tests.sh unit` runs pure helper, source coverage, QML guard, service guard, parser, and quickshell log-filter tests.
- [x] `./run-tests.sh qml` runs the focused QML static check.
- [x] `./run-tests.sh probes` runs read-only service probes.
- [x] `./run-tests.sh log` runs the active Quickshell log regression gate.
- [x] `./run-tests.sh notifications` is isolated from the default gates because it visibly sends notifications.

## How it works

- [docs/wiki/systems/testing.md](../wiki/systems/testing.md)

## Implementation inventory

- `run-tests.sh` - local test runner and gate grouping.
- `Tests/source-coverage.test.js` - source function coverage and QML declaration inventory guard.
- `Tests/qml-function-inventory.test.js` - explicit QML function anchor inventory for high-risk source files.
- `Tests/quickshell-regression.test.sh` - current-reload log filtering fixture.
- `Bin/dev/quickshell-regression.sh` - live Quickshell log regression gate.
- `Bin/dev/qml-static-check.sh` - focused qmllint gate.
- `Bin/dev/service-probes.sh` - read-only runtime/service probes.

## Tests asserting this spec

- `Tests/source-coverage.test.js`
- `Tests/qml-function-inventory.test.js`
- `Tests/quickshell-regression.test.sh`

## Known gaps (current cycle)

None.

## Out of scope

- Feature behavior tested by individual guard suites belongs in that feature's spec.
- Manual visible notification probes belong in [notifications.md](notifications.md).
