# Local Probe Scripts

These scripts are for Alessio's local Noctalia shell fork on stock Arch `quickshell`.

## Default Non-Invasive Gate

```bash
./run-tests.sh
```

Runs:

- JavaScript helper unit tests.
- Read-only service probes from `Bin/dev/service-probes.sh`.
- Active Quickshell log regression gate.

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
