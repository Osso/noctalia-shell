Local deployment installs narrow battery-threshold authorization, then reloads the running Quickshell instance from this checkout without restarting it. Source lives in `deploy.sh`.

## What it must do

- [x] Require exactly one running instance whose config path matches this checkout; missing or ambiguous instances fail without touching source.
- [x] Install the root-owned battery helper and its helper-only, prompt-free wheel policy before requesting reload; installation failures stop deployment before reload.
- [x] Request a normal source reload and wait for a new successful configuration load, rather than accepting an earlier startup log.
- [x] Fail on configuration-load errors, timeout, instance replacement, or failed IPC.
- [x] Verify IPC responsiveness on the original instance before reporting success.

## How it works

Run `./deploy.sh` after committing changes. Source already lives in the active checkout; the script calls `shell reload` over IPC on the matching instance. `ShellReload.qml` defers `Quickshell.reload(false)` until after the IPC response, then the script checks for a new load in that instance's log and verifies IPC responsiveness. It does not touch source, start a missing shell, restart the process, or change settings.

### Battery authorization installation

`./deploy.sh` uses `authsudo install` to install `Bin/noctalia-battery-threshold` as root:root mode `0755` at `/usr/local/libexec/noctalia-battery-threshold`, and `Assets/authd/noctalia-battery.toml` as root:root mode `0644` at `/etc/authd/policies.d/noctalia-battery.toml`. Parent directories are root:root mode `0755`. Installation itself remains subject to existing authorization; prompt-free access applies only to subsequent battery-limit requests.

The policy targets only that installed helper, allows group `wheel`, and sets `auth = "none"`. It does not authorize `bash` or arbitrary commands. Battery settings call `authsudo /usr/local/libexec/noctalia-battery-threshold start|end VALUE`; the helper accepts only integers 0–100 and writes only existing BAT0 threshold files. Battery behavior and validation requirements: [battery](battery.md#settings-and-ipc).

These are deployment requirements and source behavior, not evidence that installation, live authd policy enforcement, or hardware writes have succeeded on the host. Isolated deployment tests use fake authorization/installation; live prompt-free writes require separate host evidence.

## Implementation inventory

- `deploy.sh` — battery helper/policy installation, bounded IPC reload and same-instance confirmation.
- `Bin/noctalia-battery-threshold` and `Assets/authd/noctalia-battery.toml` — installed battery-only authorization artifacts.
- `Services/Control/ShellReload.qml` — in-process reload IPC handler instantiated by `shell.qml`.
- `run-tests.sh` — includes isolated deployment regressions in the deterministic gate.

## Tests asserting this spec

- `Tests/deploy-source.test.py` — fake authorization/installation checks installed bytes, modes, helper-only policy, installation-before-reload ordering and failure paths; private-XDG offscreen Quickshell exercises same-PID reload with unchanged source. No live policy or hardware-write proof.

## Known gaps (current cycle)

None.

## Out of scope

Remote deployment, installations other than the battery helper/policy, process restart, and automatic rollback.
