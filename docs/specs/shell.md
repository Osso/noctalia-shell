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

- `Tests/shell-root-warnings.test.py` and `Tests/Qml/ShellRootWarningsProbe.qml` — at `03d617445`, private cold-start and source reload each pass nine lifecycle cases using fake Settings/services/screens and real Quickshell Loader/Variants. Loader destruction/recreation and exact screen identity provide Bound owner-resolution proof, not compositor rendering/input proof.
- Static shell-only evidence: six `unqualified` warnings → zero; two `block-scope-var-declaration` hoisting warnings remain.
- Reported main-session read-only observation, October 11, 2026 at 22:13 CDT: canonical PID `797384` loaded; wlsunset `manual22` unaffected. This is not whole-shell warning-free acceptance.

## Known gaps (current cycle)

- [ ] Two shell-root hoisting warnings remain; overall QML warnings are not zero.

## Out of scope

- Real Settings persistence, service backends, compositor pixels/input, and whole-shell acceptance: private fixtures do not prove them.
- This documentation update runs no tests, canonical restart, or live settings interaction.
