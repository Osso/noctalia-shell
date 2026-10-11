# Local Noctalia Shell Maintenance

Verified: 2026-06-13

## Local Contract

- This repository is Alessio's local desktop shell product.
- Upstream Noctalia v5 and `noctalia-qs` are not the target.
- Supported runtime: stock Arch `quickshell`.
- Supported compositor/session: `niri` on this laptop.
- Shell source: `/syncthing/Sync/Projects/apps/noctalia-shell`.
- Active launch command: `quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell`.
- User config: `/home/osso/.config/noctalia/settings.json`.
- User cache/state: `/home/osso/.cache/noctalia`.

## Current Baseline

```text
quickshell --version
Quickshell 0.3.0 (revision , distributed by Arch Linux)
```

```text
pacman -Qo /usr/bin/quickshell /usr/bin/qs
/usr/bin/quickshell is owned by quickshell 0.3.0-2
/usr/bin/qs is owned by quickshell 0.3.0-2
```

Note: `pacman -Qo` also reported a CachyOS signature warning. Treat package database/signature health as part of general system maintenance before relying on Arch updates.

Current display baseline:

- `HDMI-A-1`: LG Electronics LG ULTRAWIDE, `3440x1440 @ 84.957 Hz`, active.
- `eDP-1`: Lenovo Group Limited N160JCA-GT1, disabled in the current docked layout.

Brightness baseline:

- `/home/osso/.config/noctalia/settings.json` has `brightness.enableDdcSupport = true`.
- LG UltraWide DDC path is `/dev/i2c-4`; `ddcutil -b 4 getvcp 10 --brief` has returned `VCP 10 C 100 100`.
- Laptop panel is non-DDC and should use internal backlight/`brightnessctl` when enabled.

Runtime commands available on 2026-06-13:

- Present: `quickshell`, `ddcutil`, `brightnessctl`, `wlsunset`, `wl-copy`, `magick`, `gpu-screen-recorder`, `notify-send`, `gdbus`, `jq`, `rg`.
- Missing from PATH: `cliphist`, `cava`, `matugen`.

Enabled bar widgets from `/home/osso/.config/noctalia/settings.json`:

- Left: `ControlCenter`, `SystemMonitor`, `ActiveWindow`, `MediaMini`.
- Center: `TaskbarGrouped`.
- Right: `ScreenRecorder`, `Tray`, `NotificationHistory`, `PowerProfile`, `Battery`, `Volume`, `Brightness`, `Clock`.

## Regression Gates

Run the non-invasive gate:

```bash
./run-tests.sh
```

It runs cheap JavaScript helper unit tests, read-only service probes, and checks the active local Quickshell instance log for high-signal QML/runtime failures such as missing imports, `TypeError`, `ReferenceError`, fatal errors, and component load failures.

Run only helper unit tests:

```bash
./run-tests.sh unit
```

Run only read-only service probes:

```bash
./run-tests.sh probes
```

Current probes verify:

- Notification server responds on D-Bus as `quickshell` and exposes body/actions capabilities.
- PipeWire default sink/source volume state is readable through `wpctl`.
- Internal backlight `amdgpu_bl1` is visible through `brightnessctl`.
- LG UltraWide is visible through `ddcutil`, and VCP 10 brightness is readable on bus 4.
- Clipboard MIME type list is readable without reading clipboard contents.
- Active wallpaper paths and color cache keys are coherent.

Run visible notification probes only when interaction is acceptable:

```bash
./run-tests.sh notifications
```

The underlying scripts require `--run` when called directly to avoid accidental visible notification spam.

## Manual Smoke Checklist

- [ ] Bar renders on the active monitor and keeps expected layout.
- [ ] Launcher opens, searches, and launches an app.
- [ ] Taskbar/grouped taskbar shows active apps without cursor flicker after notifications.
- [ ] Tray opens and exposes expected tray items.
- [ ] Notification popup appears, replacement notification updates in place, and notification history opens.
- [ ] Audio controls read and change output volume without UI stalls.
- [ ] Brightness slider controls the LG over DDC when connected.
- [ ] Brightness behavior remains graceful when the LG is disconnected or the laptop panel is enabled.
- [ ] Wallpaper/colors load and settings remain readable.
- [ ] Settings panel opens and changes persist to `/home/osso/.config/noctalia/settings.json`.
- [ ] Lock/session menu opens and offers expected actions.
- [ ] Restarting `quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell` restores the shell without manual state cleanup.

## Deploy Local Source

Run `./deploy.sh` from this checkout after committing changes. It requests a normal QML reload, waits for a new successful configuration load on the same running instance, and checks IPC responsiveness. It does not restart Quickshell or change settings. Missing or ambiguous instances, load failures, and timeouts fail deployment.

### Inline component reload caveat

Verified: 2026-10-11

Isolated `12e49754a` + `12d5902b1` passed exact JSON fixtures, but canonical merge `4c62f6ebf` failed hot auto-reload with `SettingsData.qml:213 AppLauncherSettings is not a type`. Revert `2726fccbe` followed by `./deploy.sh` restored the shell. User-approved reapply `19c55ee7d` then loaded settings and rendered on a fresh canonical `/home/osso/bin/start-quickshell` launch (PID 176660); config SHA remained unchanged.

A second incident followed inline component commit `4fbb9a30f`: canonical auto-reload failed with `SystemMonitor.qml:257 StatusIndicator is not a type`, leaving the old generation running. After edits finished, a controlled canonical `/home/osso/bin/start-quickshell` launch on October 11 at 16:50:19 loaded PID 401960 with zero scene warnings/errors, unchanged settings SHA, and a nonwhite screenshot. This proves clean-start loading, not hot-reload compatibility.

For inline component changes, isolated harness success is not proof of canonical hot-reload compatibility. A controlled fresh launch requires explicit approval and settings preservation; ordinary QML edits still use auto-reload. Reload-time type resolution apparently differs from fresh launch here; a Qt cache root cause is not proven. Retire this caveat when both failing transitions pass representative canonical reload regressions on the supported runtime. Harness coverage: [settings](../specs/settings.md#tests-asserting-this-spec), [testing](../specs/testing.md#evidence-categories).

### Missing palette FileView workaround

Verified: 2026-10-11 (`81049c423` + `d07303648`)

`NColor` defers missing `colors.json` creation with `Qt.callLater(customColorsFile.writeAdapter)`: FileView cleans up its reader after emitting `loadFailed`, so an immediate write inside `onLoadFailed` caused `got operation finished from dropped operation`. Deferral lets the callback return before writing.

Keep deferral limited to missing-file creation; it is not a timed delay or diagnostic suppression. Isolated coverage proves `SAVED → LOADED`, zero warning/error/fatal records in all four modes, custom reload values, and preserved bytes on fresh reload—not canonical hot-reload behavior. Requirements: [theming](../specs/theming.md#project-palette-namespace).

Retire deferral only when the supported Quickshell runtime fixes reader cleanup ordering and the same isolated cases pass with an immediate write, including save/load ordering and byte preservation.

## Update Workflow

After Arch updates `quickshell`, Qt, niri, icon theme packages, or related runtime tools:

1. Start or keep the shell running with `quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell`.
2. Run `./run-tests.sh`.
3. Inspect `quickshell log --pid "$(pgrep -u "$USER" -n quickshell)" --tail 500 --no-color`.
4. Run the manual smoke checklist for the workflows touched by the update.
5. Fix QML compatibility issues in this repo, not by pinning old Quickshell unless a temporary rollback is needed to restore the desktop.
6. Commit one verified fix at a time.

## Recovery

If the shell breaks after an update:

```bash
pkill -u "$USER" quickshell
quickshell -p /syncthing/Sync/Projects/apps/noctalia-shell --no-color -v
```

Read the foreground error, fix the failing QML/runtime assumption, then restart normally.
