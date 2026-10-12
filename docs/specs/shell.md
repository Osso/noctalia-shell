Shell bootstrap in `shell.qml` gates full-shell loading, routes settings errors per screen, and opens setup on an attached screen.

## What it must do

- [x] Keep the full-shell Loader inactive until translations, Settings readiness, and shell state are ready; unload/recreate it when readiness changes and initialize services once per creation.
- [x] Create settings-error delegates for exact screen identities, update diagnostic/path bindings, route retry to Settings, and remove delegates when screens detach or bootstrap recovers.
- [x] Resolve root signal handlers, Loader completion, and setup timer to their owner; open setup on the first attached screen across screen attachment changes.

## How it works

- Ownership and isolation evidence: [testing](testing.md#shell-root-isolated-lifecycle).

## Implementation inventory

- `shell.qml` — bootstrap gates, error-screen delegates, service initialization, and setup routing; `ComponentBehavior: Bound` with qualified root references, no inline types introduced.

## Tests asserting this spec

- `Tests/shell-root-warnings.test.py` and `Tests/Qml/ShellRootWarningsProbe.qml` — through `f4f157c81`, reported private cold-start and source reload each pass nine lifecycle cases using fake Settings/services/screens and real Quickshell Loader/Variants. Loader destruction/recreation and exact screen identity provide Bound owner-resolution proof, not compositor rendering/input proof.
- Static shell-only evidence: six `unqualified` warnings → zero at `03d617445`; at `f4f157c81`, two `block-scope-var-declaration` hoisting warnings → zero. Strict source lint uses `--max-warnings 0` and JSON warning/error diagnostics. Three synthetic-fixture unused-import informational notices are not source warnings.
- Reported main-session read-only observation, October 11, 2026 at 22:13 CDT: canonical PID `797384` loaded; wlsunset `manual22` unaffected. This prior observation is not a current live test or whole-shell warning-free acceptance.

## Known gaps (current cycle)

- [ ] Whole-shell warning-free acceptance remains unproven; zero strict source warnings applies only to `shell.qml`.

## Out of scope

- Real Settings persistence, service backends, compositor pixels/input, and whole-shell acceptance: private fixtures do not prove them.
- This documentation update runs no tests, canonical restart, or live settings interaction.
