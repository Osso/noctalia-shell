Program Checker covers runtime availability checks for optional tools and themed application clients. Runtime source lives in `Services/System/ProgramCheckerService.qml`; implementation notes belong in [docs/wiki/systems/program-checker.md](../wiki/systems/program-checker.md).

## What it must do

### Client detection

- [x] Discord client detection builds a shell directory probe from TemplateRegistry Discord clients.
- [x] Discord client detection checks theme-folder paths when required and config paths otherwise.
- [x] Discord client detection appends available client names and echoes the available client list.
- [x] Discord client detection starts the detector process.
- [x] Code client detection builds a shell directory probe from TemplateRegistry code clients.
- [x] Code client detection appends available client names and starts the detector process.
- [x] Detector stdout parsing maps whitespace-separated client names to known client metadata, drops unknown names, deduplicates repeated names, and treats blank output as no clients.
- [x] Client detector scripts quote shell-sensitive config paths and emit one detected client name per line so names with spaces are preserved.

### Program queueing

- [x] Program checking advances one queued program at a time.
- [x] Program checking writes the current property, command, and running flag for each queued check.
- [x] Program checking stops without changing state when the queue is exhausted.
- [x] Checking all programs resets completed count, current index, and queue state.
- [x] Checking all programs starts the first queued program immediately.
- [x] Checker exit handling writes availability from the process exit code, stops the process, advances incomplete queues, and emits completion after starting client detection at the end.

### Targeted checks and diagnostics

- [x] Targeted program checks warn and do not start a process for unknown properties.
- [x] Targeted program checks start the checker process for known properties.
- [x] Discord detection diagnostics log the test start, HOME value, and every configured Discord client path.
- [x] Discord detection diagnostics trigger Discord client detection.
- [x] QML program checks and `Bin/dev/service-probes.sh` expected-program checks stay aligned except intentionally optional desktop/client checks.

## How it works

- [docs/wiki/systems/program-checker.md](../wiki/systems/program-checker.md)

## Implementation inventory

- `Services/System/ProgramCheckerService.qml` - optional program availability state, client detectors, check queue, targeted checks, and diagnostic logging.
- `Services/Theming/TemplateRegistry.qml` - Discord and code client metadata consumed by client detection.
- `Bin/dev/service-probes.sh` - runtime probe layer that checks required programs outside QML.

## Tests asserting this spec

- `Tests/program-checker-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [x] Add fixture coverage for client names and paths containing shell-sensitive characters.

## Out of scope

- Template generation behavior is covered by [docs/specs/theming.md](theming.md).
- Probe parser behavior is covered by the service-probes tests until a dedicated probes spec exists.
