Testing covers local regression gates, structural source-reference guardrails, executable behavior checks, QML lifecycle integration, live host probes, and log filtering used to keep this fork maintainable against current Quickshell. Runtime source lives mainly in `run-tests.sh`, `Tests/source-coverage.test.js`, `Tests/qml-function-inventory.test.js`, and `Bin/dev/quickshell-regression.sh`; implementation notes belong in [docs/wiki/systems/testing.md](../wiki/systems/testing.md).

## What it must do

### Evidence categories

- [x] **Structural reference coverage** uses `code-index` to prove source functions are inventoried and structurally referenced from tests. It does not prove runtime execution, branch coverage, QML lifecycle behavior, or integration behavior.
- [x] **Executable behavior coverage** runs JavaScript/Python/shell logic and extracted QML function bodies with deterministic inputs.
- [x] **QML lifecycle integration** means instantiating real QML/Quickshell objects and exercising signals, bindings, loaders, processes, and destruction ordering; current coverage is feature-specific and incomplete.
- [x] **Live host probes** inspect the active machine or shell and must be reported separately from deterministic unit/static results.
- [x] Runner output labels `deterministic-unit`, `structural-reference`, `qml-static`, `host-probes`, `live-log`, and `visible-notifications` evidence independently.

### Structural reference guardrails

- [x] QML source functions must stay structurally referenced from tests according to `code-index untested`.
- [x] QML source function inventory must stay broad enough to catch structural-reference regressions.
- [x] `code-index` must inventory every QML `function` declaration outside `Tests/`.
- [x] Non-test source functions must stay structurally referenced from tests according to `code-index untested`.
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
- [x] The live Quickshell log gate must identify the canonical runtime shell from Quickshell's running-instance registry by matching `/syncthing/Sync/Projects/apps/noctalia-shell/shell.qml`, independent of the checkout or worktree running the gate and without relying on the process command line.
- [x] The live Quickshell log gate must report a clear no-shell diagnostic when no local shell is running.

### Runner contract

- [x] `./run-tests.sh unit` discovers every `Tests/*.test.js` suite, runs behavior suites under `deterministic-unit`, then runs source inventory/coverage meta-tests under `structural-reference`.
- [x] Adding a JavaScript test suite requires no manual runner-list update; the deterministic runner-completeness test proves discovery and discovery-failure handling.
- [x] `./run-tests.sh qml` runs the focused QML static check.
- [x] `./run-tests.sh probes` runs read-only service probes, injects the deterministic Bluetooth CLI fixture rather than contacting host Bluetooth hardware, and validates launch/IPC contracts against the canonical runtime shell path rather than the invoking worktree.
- [x] `./run-tests.sh log` runs the active Quickshell log regression gate.
- [x] `./run-tests.sh notifications` is isolated from the default gates because it visibly sends notifications.
- [x] `all` and `regression` report visible notifications as explicitly excluded before running deterministic unit, structural reference, QML static, host probes, and live logs.
- [x] Category wrappers preserve fail-closed execution: a failed command cannot continue to a PASS category record.

## How it works

- [docs/wiki/systems/testing.md](../wiki/systems/testing.md)

## Implementation inventory

- `run-tests.sh` - local test runner, fail-closed JavaScript test discovery, and gate grouping.
- `Tests/source-coverage.test.js` - structural source-reference, QML declaration inventory, evidence-category, and test-to-spec mapping guard.
- `Tests/runner-completeness.test.js` - executable runner discovery and discovery-failure coverage.
- `Tests/test-runner-categories.test.sh` - evidence-category mapping, ordering, fail-closed execution, and caller-errexit coverage.
- `Tests/qml-function-inventory.test.js` - explicit QML function anchor inventory for high-risk source files.
- `Tests/qml-test-utils.js` - shared comment-aware QML component and handler extraction used by structural UI contracts.
- `Tests/qml-test-utils.test.js` - lexical-decoy and alternate-brace-format coverage for shared QML extraction.
- `Tests/quickshell-regression.test.sh` - current-reload log filtering fixture.
- `Bin/dev/quickshell-regression.sh` - live Quickshell log regression gate.
- `Bin/dev/qml-static-check.sh` - focused qmllint gate.
- `Bin/dev/service-probes.sh` - read-only runtime/service probes; direct Bluetooth invocation remains a bounded host diagnostic.
- `Tests/fixtures/bluetoothctl` - deterministic Bluetooth CLI fixture selected by automated probe runs.

## Tests asserting this spec

- `Tests/source-coverage.test.js`
- `Tests/qml-function-inventory.test.js`
- `Tests/qml-test-utils.test.js`
- `Tests/quickshell-regression.test.sh`
- `Tests/runner-completeness.test.js`
- `Tests/service-probes-parsing.test.sh`
- `Tests/test-runner-categories.test.sh`

## Known gaps (current cycle)

None for the current registry-selection contract.

## Out of scope

- Feature behavior tested by individual guard suites belongs in that feature's spec.
- Manual visible notification probes belong in [notifications.md](notifications.md).
