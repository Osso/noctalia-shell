Fan covers hardware fan sensor discovery, RPM readout, label loading, and fan summary helpers used by the system monitor. Runtime source lives mainly in `Services/Hardware/FanService.qml`; implementation notes belong in [docs/wiki/systems/fan.md](../wiki/systems/fan.md).

## What it must do

### Hwmon detection

- [x] Hwmon detection stops after the configured probe range and logs when no supported fan sensor is found.
- [x] Hwmon detection probes `/sys/class/hwmon/hwmonN/name` files.
- [x] Supported sensor names must also expose `fan1_input` before the service selects a hwmon path.
- [x] Failed fan-input checks continue scanning later hwmon paths.
- [x] Successful fan-input verification publishes the sensor name, hwmon path, and detection log.

### Fan read pipeline

- [x] Reading fans no-ops before a hwmon path is detected.
- [x] Reading fans resets pending and collected fan state.
- [x] Reading fans queues the configured fan sensor indices.
- [x] Reading fans starts the read pipeline.
- [x] Reading the next fan finalizes after pending reads are exhausted.
- [x] Reading the next fan peeks the next pending index, loads the matching `fanN_input` path, and reloads the reader.
- [x] Finalizing sorts fans by sensor index.
- [x] Finalizing attempts to load missing labels for collected fans.
- [x] Finalizing reuses cached labels instead of rereading static `fanN_label` files on every RPM refresh.
- [x] Finalizing publishes collected fans after cached labels are applied.

### Fan reader and labels

- [x] Fan reader parses RPM and consumes the pending index together.
- [x] Fan reader collects non-negative readings with cached labels or default `Fan N` labels.
- [x] Fan reader failure stops the pipeline and finalizes collected data.
- [x] Label reader caches labels by fan index and continues the label pipeline.

### Summary helpers and types

- [x] Average RPM helper declares an integer return type.
- [x] Max RPM helper declares an integer return type.
- [x] RPM formatter declares integer input and string output types.
- [x] Average RPM returns zero without fans.
- [x] Average RPM returns the rounded average of collected fan RPM values.
- [x] Max RPM returns zero without fans.
- [x] Max RPM returns the highest collected fan RPM value.
- [x] RPM formatting keeps sub-1000 RPM values literal.
- [x] RPM formatting shortens thousands with one decimal and `k` suffix.

### System Monitor widget

- [x] The bar widget shows fan speed only when the widget setting is enabled and FanService is available.
- [x] The bar widget displays the formatted max fan RPM.
- [x] The bar widget tooltip lists each fan label and RPM on separate lines.
- [x] System Monitor settings hide fan-speed controls when FanService is unavailable.

## How it works

- [docs/wiki/systems/fan.md](../wiki/systems/fan.md)

## Implementation inventory

- `Services/Hardware/FanService.qml` - hwmon detection, fan read pipeline, label loading, fan summaries, and RPM formatting.
- `Modules/Bar/Widgets/SystemMonitor.qml` - bar system-monitor fan display and fan hover area.
- `Modules/Cards/SystemMonitorCard.qml` - control-center/dashboard system monitor card using hardware metrics.
- `Modules/Panels/Settings/Tabs/SystemMonitorTab.qml` - system monitor settings surface.
- `Modules/Panels/Settings/Bar/WidgetSettings/SystemMonitorSettings.qml` - bar widget setting that hides fan options when FanService is unavailable.

## Tests asserting this spec

- `Tests/fan-service-guards.test.js`
- `Tests/fan-widget-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

None.

## Out of scope

- CPU, memory, disk, and network metrics belong in a future system-monitor spec.
- Host hwmon device behavior belongs to Linux sysfs; this spec covers shell discovery and parsing.
