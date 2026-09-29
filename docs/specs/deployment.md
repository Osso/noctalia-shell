Local deployment reloads the running Quickshell instance from this checkout without restarting it. Source lives in `deploy.sh`.

## What it must do

- [x] Require exactly one running instance whose config path matches this checkout; missing or ambiguous instances fail without touching source.
- [x] Request a normal source reload and wait for a new successful configuration load, rather than accepting an earlier startup log.
- [x] Fail on configuration-load errors, timeout, instance replacement, or failed IPC.
- [x] Verify IPC responsiveness on the original instance before reporting success.

## How it works

Run `./deploy.sh` after committing changes. Source already lives in the active checkout; the script touches `shell.qml` to request auto-reload, then checks the instance log and IPC. It neither starts a missing shell nor changes settings.

## Implementation inventory

- `deploy.sh` — bounded reload and same-instance confirmation.
- `run-tests.sh` — includes isolated deployment regressions in the deterministic gate.

## Tests asserting this spec

- `Tests/deploy-source.test.py` — disposable checkout and fake Quickshell exercise successful reload and failure paths without touching the desktop.

## Known gaps (current cycle)

None.

## Out of scope

Remote deployment, binary installation, process restart, and automatic rollback.
