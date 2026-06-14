# Local Probe Scripts

These scripts are for Alessio's local Noctalia shell fork on stock Arch `quickshell`.

## Default Non-Invasive Gate

```bash
./run-tests.sh
```

Runs:

- JavaScript helper unit tests.
- Focused `qmllint` coverage for QML files that are lint-clean on current Arch
  Quickshell/Qt tooling.
- Read-only service probes from `Bin/dev/service-probes.sh`.
- Active Quickshell log regression gate.

## QML Static Check

```bash
./run-tests.sh qml
Bin/dev/qml-static-check.sh
```

This lints every QML file except the documented parser/tooling debt in
`Bin/dev/qml-static-exclusions.txt`. The gate also checks that every excluded
file still fails `qmllint`; if one becomes lint-clean, remove it from the
exclusion file so coverage ratchets upward.

## Read-Only Service Probes

```bash
./run-tests.sh probes
Bin/dev/service-probes.sh notifications
Bin/dev/service-probes.sh audio
Bin/dev/service-probes.sh brightness
Bin/dev/service-probes.sh clipboard
Bin/dev/service-probes.sh wallpaper-colors
Bin/dev/service-probes.sh settings
Bin/dev/service-probes.sh state-cache
```

These probes do not change shell state. They verify that the notification server,
PipeWire volume state, internal brightness state, optional LG DDC state when the
display is detected, clipboard MIME type list, and wallpaper/color cache are
readable and coherent for this machine. The settings probe validates the local
settings file shape for the bar, control center, audio, brightness,
notifications, and wallpaper sections that the shell reads at runtime. The
state-cache probe validates persisted shell state, network cache, location
weather cache, and notification history shape.

## Visible Manual Notification Probes

```bash
./run-tests.sh notifications
```

Equivalent explicit scripts:

```bash
Bin/dev/notifications-test.sh --run
Bin/dev/notifications-test-replace.sh --run
```

These intentionally send visible notifications. Use them only when it is okay to
exercise popup display, icon/image handling, actions, and replacement behavior.
