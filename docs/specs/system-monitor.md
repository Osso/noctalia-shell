System Monitor covers CPU, memory, network, and CPU-temperature metric collection plus speed formatting for system-monitor surfaces. Runtime source lives mainly in `Services/System/SystemStatService.qml`; implementation notes belong in [docs/wiki/systems/system-monitor.md](../wiki/systems/system-monitor.md).

## What it must do

### Memory and interval handling

- [x] Sampling interval normalization clamps falsy and too-short intervals.
- [x] Memory parsing ignores empty input.
- [x] Memory parsing reads line-oriented `/proc/meminfo`.
- [x] Memory parsing safely reads `MemTotal` and `MemAvailable`.
- [x] Memory parsing computes usage only with valid total memory.
- [x] Memory parsing exposes used memory in GiB and rounded memory percentage.
- [x] Empty memory input leaves previous memory values unchanged.

### CPU and network metrics

- [x] CPU usage ignores empty input and requires the aggregate `cpu` line.
- [x] CPU usage parses all aggregate CPU counters.
- [x] CPU usage includes iowait in idle time.
- [x] CPU usage compares current samples against previous samples.
- [x] CPU usage avoids divide-by-zero and publishes usage percentage.
- [x] CPU usage stores the latest sample.
- [x] Network speed ignores empty input.
- [x] Network speed timestamps samples in seconds.
- [x] Network speed skips `/proc/net/dev` headers, malformed rows, and loopback.
- [x] Network speed parses RX and TX byte counters.
- [x] Network speed requires a previous sample and clamps counter resets to zero.

### Polling lifecycle

- [x] CPU, temperature, memory, disk, and network timers remain stopped unless a visible consumer holds a polling reference.
- [x] Starting a polling reference immediately refreshes the requested metric instead of waiting for the next interval.
- [x] Polling references are ref-counted and ending a reference clamps at zero.
- [x] The bar system monitor registers only the metrics that are visible and configured.
- [x] The process panel registers CPU and memory metrics only while open.

### Bar widget

- [x] Compact density selects compact text and pill sizing; changing density or bar orientation updates sizing, and vertical metric text scales down to fit without enlarging.
- [x] Left click opens the system monitor panel; right click opens the context menu, whose settings action targets the widget instance.
- [x] Disk and fan hover show their current path/RPM tooltips; hover updates text and icon colors.
- [x] Horizontal CPU status indicators update severity, color, and scale with CPU usage; vertical bars hide status indicators.
- [x] Hiding the widget releases system-stat and fan polling references; showing it restores them.

### Speed formatting

- [x] Full speed formatting keeps sub-megabyte values in KB.
- [x] Full speed formatting shows one decimal for small KB values and rounded values for larger KB values.
- [x] Full speed formatting renders MB and GB values with one decimal.
- [x] Compact speed formatting collapses empty or negative rates to `0`.
- [x] Compact speed formatting uses compact unit suffixes.
- [x] Compact speed formatting promotes through binary units and promotes crowded three-digit values.
- [x] Compact speed formatting returns rounded compact strings.

### CPU temperature

- [x] Temperature sensor probing stops after unsupported hwmon paths and logs a warning.
- [x] Temperature sensor probing reads the next hwmon name file.
- [x] CPU temperature recognizes AMD `k10temp` and `zenpower` sensors.
- [x] AMD CPU temperature reads `temp1_input`.
- [x] Intel CPU temperature resets averaging state before probing.
- [x] Intel CPU temperature stops after configured probes.
- [x] Intel CPU temperature averages collected temperatures.
- [x] Intel CPU temperature fails closed to zero when no sensors load.
- [x] Intel CPU temperature probes the next `tempN_input` file.

## How it works

- [docs/wiki/systems/system-monitor.md](../wiki/systems/system-monitor.md)

## Implementation inventory

- `Services/System/SystemStatService.qml` - CPU, memory, network, disk, and temperature metrics plus speed formatting helpers.
- `Modules/Cards/SystemMonitorCard.qml` - dashboard card displaying system monitor summaries.
- `Modules/Bar/Widgets/SystemMonitor.qml` - bar widget for CPU, memory, network, disk, fan, and temperature summaries.
- `Modules/Panels/Settings/Tabs/SystemMonitorTab.qml` - settings surface for system monitor behavior.
- `Modules/Panels/Settings/Bar/WidgetSettings/SystemMonitorSettings.qml` - bar widget settings for system monitor display.

## Tests asserting this spec

- `Tests/widget-settings-cohort-warnings.test.py` / `Tests/Qml/WidgetSettingsCohortHarness.qml` — SystemMonitorSettings: eight toggles, memory-percent and disk-selector visibility, fixture disk keys `/` and `/data`, and saved `/data` selection. No live metric/disk discovery or SystemMonitorTab coverage. Each editor also exercises fixture defaults, save-copy isolation, cancel/reopen, and apply-close. Completed isolated assertions do not close the RED shared-control runtime warning gate. Cohort counts/lint evidence: [bar](bar.md#tests-asserting-this-spec); isolation and limits: [testing](testing.md#widget-settings-cohort).

- `Tests/system-stat-service-guards.test.js`
- `Tests/system-monitor-runtime.test.py` - standalone offscreen production-widget coverage with fixture services for density/orientation sizing, interactions, CPU critical indicator updates, and polling visibility.
- `Tests/remaining-layout-geometry.test.py behavior` - four offscreen production SystemMonitorCard geometry/content cases at widths 480/1000 and scales 1/1.25, compared exactly with tracked pre-cleanup fixtures. Fixed CPU/temperature/memory/disk values 37/52/64/28 assert gauge text, 68-wide gauges, scaled heights, and content scale 0.8; not live sampling or threshold-transition proof. Shared isolation and lint limits: [testing](testing.md).
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable fixture coverage for CPU and network parser outputs.
- [ ] Add fake FileView coverage for AMD and Intel temperature file reads.
- [ ] Extend widget coverage beyond the CPU critical indicator to all metric warning/critical thresholds and display modes.
- [ ] Add settings-level coverage for SystemMonitorTab; bar widget editor assertions exist in the cohort, but strict no-warning runtime acceptance remains RED ([testing](testing.md#widget-settings-cohort)).

## Out of scope

- Process list parsing and aggregate process metrics are covered by [docs/specs/process.md](process.md).
- Fan speed collection is covered by [docs/specs/fan.md](fan.md).
