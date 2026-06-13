# Nix Packaging Status

The active local shell is not installed through Nix.

Current runtime contract:

- Launch command: `quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell`
- Runtime binary: stock Arch `/usr/bin/quickshell`
- Config path: `/home/osso/.config/noctalia/settings.json`

The files in this directory are retained as legacy/reference packaging. Do not use
them as evidence for the active install path unless they are explicitly updated and
verified against the local stock-Quickshell workflow.

Before reviving Nix packaging:

- Make the wrapper use stock `quickshell`, not `noctalia-qs`.
- Make runtime dependencies match the local probe baseline in `docs/local/maintenance.md`.
- Run `./run-tests.sh` against the resulting launched shell.
- Update this note with the verified install path.
