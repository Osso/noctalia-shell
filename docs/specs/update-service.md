Update Service covers changelog initialization, upgrade-log fetching, release-note parsing, changelog popup scheduling, external links, and persisted changelog-seen state. Runtime source lives in `Services/Noctalia/UpdateService.qml`; implementation notes belong in [docs/wiki/systems/update-service.md](../wiki/systems/update-service.md).

## What it must do

### Initialization and changelog requests

- [x] Initialization is idempotent and marks the service initialized.
- [x] Initialization defers ShellState changelog loading until ShellState is available.
- [x] Changelog requests are suppressed during setup wizard and mark the target version seen.
- [x] Changelog requests ignore empty target versions.
- [x] Changelog requests avoid duplicate scheduled popups and already shown versions.
- [x] Changelog requests store previous and current changelog versions.
- [x] Changelog requests fetch the upgrade log, emit `popupQueued`, and clear pending request state.
- [x] Upgrade-log fetching chooses a stable fallback source version.
- [x] Upgrade-log fetching strips legacy `-dev` suffixes from source and target versions.
- [x] Upgrade-log fetching resets inverted version ranges to the stable fallback source version.
- [x] Upgrade-log fetching builds the request URL from the normalized range and sends a GET request.

### Version and release-note parsing

- [x] Version normalization handles empty values and strips a leading `v`.
- [x] Version-part parsing normalizes first, splits on non-numeric separators, and parses integers.
- [x] Version comparison fast-paths equal strings, compares all parts, defaults missing parts to zero, and reports greater or lesser versions.
- [x] Release-note parsing handles empty bodies, splits on platform line endings, preserves release note lines, and trims trailing blank lines.
- [x] Version-line detection accepts numeric version headings with or without a leading `v`.
- [x] Entry cleaning strips markdown links, parenthesized URLs, commit hashes, and trailing author names.
- [x] Entry cleaning special-cases merge branch entries.
- [x] Ignored-entry detection ignores release headings, autoformat entries, auto-formatting entries, and qmlfmt entries.

### Popup opening and state transitions

- [x] Changelog popup opening only runs for scheduled popups.
- [x] Changelog popup opening waits for Quickshell screens.
- [x] Changelog popup opening targets the changelog panel through PanelService.
- [x] Changelog popup opening waits for panel registration, opens the panel, clears the scheduled flag, and remembers the shown version.
- [x] Discord and feedback opening guard empty URLs and open configured URLs with `xdg-open`.
- [x] Showing the latest changelog guards empty current versions.
- [x] Showing the latest changelog defers until changelog state loads.
- [x] Showing the latest changelog skips already seen versions.
- [x] Showing the latest changelog sets source and target versions, marks a request pending, and dispatches the request.
- [x] Clearing a changelog request clears pending, source, and target state.
- [x] Marking a changelog seen ignores empty versions, stores the seen version, and persists state.

### Changelog state persistence

- [x] Changelog state loading reads ShellState changelog state and restores the last-seen version.
- [x] Changelog state loading logs load failures and marks state loaded even after failure.
- [x] Changelog state loading replays deferred show requests.
- [x] Debounced changelog saving queues a save and restarts the save debouncer.
- [x] Save execution no-ops without a pending save.
- [x] Save execution retries when a save is already running.
- [x] Save execution claims pending saves, persists the last-seen version, and clears the save-in-progress flag.
- [x] Save execution handles saves queued during a save and logs save failures.
- [x] Immediate save compatibility goes through the debounced save path.

## How it works

- [docs/wiki/systems/update-service.md](../wiki/systems/update-service.md)

## Implementation inventory

- `Services/Noctalia/UpdateService.qml` - changelog lifecycle, version parsing, upgrade-log fetches, panel opening, external links, and ShellState persistence.
- `Modules/Panels/Changelog/ChangelogPanel.qml` - changelog panel opened by UpdateService.
- `Services/UI/PanelService.qml` - panel lookup used to open the changelog panel.
- `Commons/ShellState.qml` - persisted changelog last-seen state storage.

## Tests asserting this spec

- `Tests/update-service-guards.test.js`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable fixture coverage for successful and failed upgrade-log HTTP responses.
- [ ] Add executable fixture coverage for release-note parsing output, not only parser structure.
- [ ] Add fake PanelService coverage for delayed changelog panel opening.
- [ ] Add fake ShellState coverage for changelog state load/save success and failure.

## Out of scope

- GitHub metadata fetching is covered by [docs/specs/github.md](github.md).
- Panel registration behavior is covered by [docs/specs/panel-service.md](panel-service.md).
