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

This is intentionally a curated baseline, not a whole-tree claim. Expand
`lint_files` in `Bin/dev/qml-static-check.sh` as parser/tooling issues are fixed
or as high-risk QML files become lint-clean.

## Read-Only Service Probes

```bash
./run-tests.sh probes
Bin/dev/service-probes.sh notifications
Bin/dev/service-probes.sh audio
Bin/dev/service-probes.sh brightness
Bin/dev/service-probes.sh clipboard
Bin/dev/service-probes.sh wallpaper-colors
```

These probes do not change shell state. They verify that the notification server,
PipeWire volume state, brightness/DDC state, clipboard MIME type list, and
wallpaper/color cache are readable and coherent for this machine.

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
