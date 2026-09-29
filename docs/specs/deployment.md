Local deployment reloads the running Quickshell instance from this checkout without restarting it. Source lives in `deploy.sh`.

## What it must do

- [x] Require exactly one running instance whose config path matches this checkout; missing or ambiguous instances fail without touching source.
- [x] Request a normal source reload and wait for a new successful configuration load, rather than accepting an earlier startup log.
- [x] Fail on configuration-load errors, timeout, instance replacement, or failed IPC.
- [x] Verify IPC responsiveness on the original instance before reporting success.

## How it works

Run `./deploy.sh` after committing changes. Source already lives in the active checkout; the script calls `shell reload` over IPC on the matching instance. `ShellReload.qml` defers `Quickshell.reload(false)` until after the IPC response, then the script checks for a new load in that instance's log and verifies IPC responsiveness. It does not touch source, start a missing shell, restart the process, or change settings.

## Implementation inventory

- `deploy.sh` — bounded IPC reload and same-instance confirmation.
- `Services/Control/ShellReload.qml` — in-process reload IPC handler instantiated by `shell.qml`.
- `run-tests.sh` — includes isolated deployment regressions in the deterministic gate.

## Tests asserting this spec

- `Tests/deploy-source.test.py` — fake CLI exercises failure paths; private-XDG offscreen Quickshell loads the production handler and proves same-PID reload with unchanged source.

## Known gaps (current cycle)

None.

## Out of scope

Remote deployment, binary installation, process restart, and automatic rollback.
