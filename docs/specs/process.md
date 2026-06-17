Process covers process monitoring, process-list parsing/sorting, process actions, display formatting, and the process panel's typed delegate fields. Runtime source lives mainly in `Services/System/ProcessService.qml` and `Modules/Panels/Process/ProcessPanel.qml`; implementation notes belong in [docs/wiki/systems/process.md](../wiki/systems/process.md).

## What it must do

### Lifecycle and commands

- [x] Adding a reference increments the reference count and starts monitoring on the first reference.
- [x] Removing a reference clamps the reference count at zero and logs deactivation when no references remain.
- [x] Updating processes does no work without active references.
- [x] Updating processes starts the `ps` process when monitoring is active.
- [x] Changing the sort key resorts only when the key changes.
- [x] Toggling sort direction flips direction and resorts.
- [x] Normal process kill runs `kill` only for positive pids.
- [x] Force kill runs `kill -9` only for positive pids.
- [x] Sort-key, process-id, formatter, and process-icon helper inputs are typed.

### Formatting and icons

- [x] CPU formatting renders one decimal percent values.
- [x] Memory formatting renders KB, MB, and GB values with unit-appropriate precision.
- [x] Process icon lookup normalizes command names.
- [x] Process icon lookup recognizes browsers, editors, terminals, music players, video players, chat apps, container runtimes, and kernel workers.
- [x] Process icon lookup falls back to a generic process icon.

### Parsing

- [x] Empty process output is ignored.
- [x] Process output is split by line and each row is split by whitespace.
- [x] Malformed rows are skipped.
- [x] Rows parse pid, CPU usage, memory percentage, RSS memory, and command text.
- [x] Command arguments are preserved while executable display names are reduced to basenames.
- [x] Kernel thread display names are normalized.
- [x] Long display names are truncated.
- [x] Parsed process lists publish process count and aggregate CPU/memory usage.
- [x] Aggregate CPU and memory percentages are capped at 100.
- [x] Parsed processes are sorted before publication.

### Sorting

- [x] Empty process lists are ignored.
- [x] Sorting copies the source process list before sorting.
- [x] Sorting supports CPU, memory, name, and pid keys.
- [x] Unknown sort keys keep process order unchanged.
- [x] Numeric sorts honor ascending and descending direction.
- [x] Name sorting uses locale order.
- [x] Published process lists honor the configured process limit.

### Panel types

- [x] Process panel delegates declare typed aliases for command, display name, CPU, memory, pid, CPU color, icon, formatted CPU, formatted memory, and pid text.
- [x] Process panel delegates use the typed aliases after declaration instead of repeatedly reading dynamic `modelData` fields.

## How it works

- [docs/wiki/systems/process.md](../wiki/systems/process.md)

## Implementation inventory

- `Services/System/ProcessService.qml` - process monitor lifecycle, `ps` parsing, sorting, kill commands, formatting, and process icons.
- `Modules/Panels/Process/ProcessPanel.qml` - process list panel, sort controls, process actions, and typed process delegates.
- `Modules/Bar/Widgets/SystemMonitor.qml` - bar widget entry point that can open the process panel.
- `Modules/Cards/SystemMonitorCard.qml` - dashboard card that displays system-monitor summaries alongside process-related system state.

## Tests asserting this spec

- `Tests/process-service-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for ProcessPanel open/close reference ownership.
- [ ] Add executable coverage for ProcessPanel sort button interactions.
- [ ] Add executable coverage for rendered process action buttons.
- [ ] Add executable coverage for ps process exit/error handling.

## Out of scope

- CPU, memory, disk, network, and fan metric collection belongs in a future system-monitor spec.
- Backend kernel/process semantics belong to the host `ps` and `kill` commands; this spec covers the shell boundary.
