Testing covers local regression gates, structural source-reference guardrails, executable behavior checks, QML lifecycle integration, live host probes, and log filtering used to keep this fork maintainable against current Quickshell. Runtime source lives mainly in `run-tests.sh`, `Tests/source-coverage.test.js`, `Tests/qml-function-inventory.test.js`, and `Bin/dev/quickshell-regression.sh`.

## What it must do

### Evidence categories

- [x] **Structural reference coverage** uses `code-index` to prove source functions are inventoried and structurally referenced from tests. It does not prove runtime execution, branch coverage, QML lifecycle behavior, or integration behavior.
- [x] **Executable behavior coverage** runs JavaScript/Python/shell logic and extracted QML function bodies with deterministic inputs.
- [x] **QML lifecycle integration** means instantiating real QML/Quickshell objects and exercising signals, bindings, loaders, processes, and destruction ordering; current coverage is feature-specific and incomplete.
- [x] Headless QML lifecycle suites run with `qmltestrunner` on `QT_QPA_PLATFORM=offscreen` and isolated temporary XDG config/cache/data directories.
- [x] Production QML lifecycle harnesses run non-visibly with isolated temporary config/cache/data paths and explicit process cleanup. Night-light gamma tests use a private Wayland server, never the active display.
- [x] **Live host probes** inspect the active machine or shell and must be reported separately from deterministic unit/static results.
- [x] Runner output labels `deterministic-unit`, `structural-reference`, `qml-static`, `host-probes`, `live-log`, and `visible-notifications` evidence independently.

### Structural reference guardrails

- [x] The structural runner explicitly refreshes the incremental `code-index` graph before inventory or reference queries and fails without running them if indexing fails.
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

- [x] `./run-tests.sh all` (the default) and `./run-tests.sh regression` run deterministic unit tests, structural-reference checks, QML static checks, read-only host probes, and the active Quickshell log gate; they do not run visible notification probes.
- [x] `./run-tests.sh unit` discovers every `Tests/*.test.js` suite, runs behavior suites and discovered `Tests/Qml/tst_*.qml` lifecycle suites under `deterministic-unit`, then runs source inventory/coverage meta-tests under `structural-reference`.
- [x] Adding a JavaScript test suite requires no manual runner-list update; the deterministic runner-completeness test proves discovery and discovery-failure handling.
- [ ] The deterministic gate also runs isolated [deployment](deployment.md) and [night-light](night-light.md) process regressions. Night-light fixtures require a C compiler, `pkg-config`, Wayland server development files, `wayland-scanner`, Quickshell, and `wlsunset`; these are test-only dependencies beyond the shell's existing runtime programs.
- [x] `./run-tests.sh qml` runs the focused QML static check using the installed Qt 6 `/usr/lib/qt6/bin/qmllint` for checked and documented-exclusion files; it does not fall back to a PATH-resolved Qt 5 tool.
- [x] `./run-tests.sh probes` runs read-only service probes, injects the deterministic Bluetooth CLI fixture rather than contacting host Bluetooth hardware, validates launch/IPC contracts against the canonical runtime shell path, and runs the isolated non-visible production QML lifecycle harness.
- [x] `./run-tests.sh log` runs the active Quickshell log regression gate.
- [x] `./run-tests.sh notifications` runs visible notification probes and is isolated from the default gates.
- [x] `all` and `regression` report visible notifications as explicitly excluded before running deterministic unit, structural reference, QML static, host probes, and live logs.
- [x] Category wrappers preserve fail-closed execution: a failed command cannot continue to a PASS category record.

## How it works

- Runtime behavior is implemented in `run-tests.sh` and the test/probe files listed below.

## Implementation inventory

- `run-tests.sh` - local test runner, fail-closed JavaScript and headless QML test discovery, QML runtime isolation, and gate grouping.
- `Tests/source-coverage.test.js` - structural source-reference, QML declaration inventory, evidence-category, and test-to-spec mapping guard.
- `Tests/Qml/tst_panel_service_lifecycle.qml` - headless Qt QObject destruction regression for captured panel registration keys.
- `Tests/Qml/PanelServiceLifecycleHarness.qml` - production SmartPanel and PanelService lifecycle assertions.
- `Tests/panel-service-lifecycle.test.sh` - isolated non-visible Quickshell harness runner and cleanup.
- `Tests/runner-completeness.test.js` - executable runner discovery and discovery-failure coverage.
- `Tests/test-runner-categories.test.sh` - evidence-category mapping, ordering, fail-closed execution, and caller-errexit coverage.
- `Tests/qml-function-inventory.test.js` - explicit QML function anchor inventory for high-risk source files.
- `Tests/qml-test-utils.js` - shared comment-aware QML component and handler extraction used by structural UI contracts.
- `Tests/qml-test-utils.test.js` - lexical-decoy and alternate-brace-format coverage for shared QML extraction.
- `Tests/quickshell-regression.test.sh` - current-reload log filtering fixture.
- `Bin/dev/quickshell-regression.sh` - live Quickshell log regression gate.
- `Bin/dev/qml-static-check.sh` - focused Qt 6 qmllint gate.
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
