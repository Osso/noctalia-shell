# Local Noctalia Shell Fork

This repository is Alessio's local, upstream-independent Noctalia v4/QML desktop shell.

It is maintained for this machine and session:

- OS: Arch Linux
- Compositor: niri
- Runtime: stock Arch `quickshell`
- Launch command: `quickshell -p /home/osso/Repos/noctalia-shell`
- User config: `/home/osso/.config/noctalia/settings.json`
- User cache/state: `/home/osso/.cache/noctalia`

Upstream Noctalia v5 and `noctalia-qs` are not the target. Do not merge upstream
changes by default. Treat upstream remotes as historical/reference material only.

## Test Gate

Run the non-invasive local gate before committing:

```bash
./run-tests.sh
```

This runs:

- Pure JavaScript helper regression tests.
- Read-only service probes for notifications, audio, brightness/DDC, clipboard MIME
  types, and wallpaper/color cache state.
- Active Quickshell log checks for high-signal QML/runtime failures.

Visible notification probes are intentionally separate:

```bash
./run-tests.sh notifications
```

See [Bin/dev/PROBES.md](Bin/dev/PROBES.md) for probe details.

## Runtime Maintenance

After Arch updates `quickshell`, Qt, niri, icon themes, PipeWire, DDC tools, or
related runtime packages:

1. Start or keep the shell running with `quickshell -p /home/osso/Repos/noctalia-shell`.
2. Run `./run-tests.sh`.
3. Inspect `quickshell log --pid "$(pgrep -u "$USER" -n quickshell)" --tail 500 --no-color`.
4. Run the manual smoke checklist from `docs/local/maintenance.md`.
5. Fix compatibility issues in this repo.
6. Commit one verified fix at a time.

`docs/local/` and `PLAN.md` are intentionally local/ignored workspace notes.

## Packaging Notes

The active install is not Nix-based. The tracked Nix files are legacy/reference
packaging only unless they are explicitly updated for this local stock-Quickshell
contract. See [nix/README.md](nix/README.md).

## License

MIT License - see [LICENSE](LICENSE). Original Noctalia credits remain in
[CREDITS.md](CREDITS.md).
