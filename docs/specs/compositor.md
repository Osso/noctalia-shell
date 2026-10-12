Compositor covers backend detection, shared workspace/window state, display-scale cache, backend adapters for Niri, Hyprland, Sway, and Mango, and the Workspace bar widget. Runtime source lives mainly in `Services/Compositor/CompositorService.qml`, backend service files under `Services/Compositor/`, and `Modules/Bar/Widgets/Workspace.qml`; implementation notes belong in [docs/wiki/systems/compositor.md](../wiki/systems/compositor.md).

## What it must do

### Shared compositor service

- [x] Compositor detection inspects Hyprland, Niri, Sway, and desktop environment state, prefers Mango desktop detection, selects matching Niri/Hyprland/Sway backends, and falls back to Niri.
- [x] Display-scale cache loading reads ShellState display data and fails closed when cached state is unavailable.
- [x] Display-scale updates and cache saves mirror backend display data through ShellState.
- [x] Display info lookup returns known display data and returns null for missing displays.
- [x] Shared workspace, window, focused-window, active-workspace, clean-app-name, and workspace-window helpers mirror backend models and fail closed for invalid indexes or missing focus.
- [x] Each backend `windowListChanged` event replaces the facade model and emits one facade `windowListChanged` signal; backend `activeWindowChanged` handling also resyncs the facade model and emits the same signal, so a backend sequence that emits both signals produces one facade window-list signal per backend signal.
- [x] Clean app-name helper types app-id and fallback-title string inputs.
- [x] Backend delegate functions fail closed when no backend object is available.
- [x] Session commands delegate to the active backend while lock/suspend fallback paths use system commands when needed.

### Niri backend

- [x] Niri initialization connects event and command sockets, starts event streaming, and queries initial workspaces, windows, and display scales.
- [x] Niri socket commands write newline-delimited JSON and flush the socket.
- [x] Niri update commands request EventStream, Workspaces, Windows, and Outputs from the right sockets.
- [x] Niri output, workspace, and window recollection normalizes backend data, tracks focus/active state, and sorts windows.
- [x] Niri window event handlers maintain window state for open/change/close/focus/layout events.
- [x] Niri overview and keyboard layout handlers mirror overview state, store layout names, and publish active layout changes.
- [x] Niri workspace/window/logout actions execute the expected `niri msg action` commands.

### Hyprland backend

- [x] Hyprland initialization is idempotent, refreshes workspaces/toplevels, defers initial cache refreshes, queries display scales and keyboard layout, marks initialization, and logs failures.
- [x] Hyprland workspace refresh clears stale rows, resets cache, guards unavailable workspace data, and derives occupied workspace ids.
- [x] Hyprland window normalization guards app id, title, address, workspace, focus, output, and sorting data.
- [x] Hyprland keyboard layout parsing handles parenthesized metadata, derives the comma-delimited layout suffix, forwards the selected layout, and logs parse failures.
- [x] Hyprland workspace, focus, close, and logout actions dispatch through Hyprland/hyprctl and log failures.

### Sway backend

- [x] Sway initialization is idempotent, refreshes workspaces, subscribes to input events, defers initial cache refreshes, queries display scales and keyboard layout, marks initialization, and logs failures.
- [x] Sway workspace/window refresh clears stale rows, guards unavailable backend data, normalizes app/window fields, and safely reads backend properties.
- [x] Sway input layout parsing handles parenthesized metadata, derives the comma-delimited layout suffix, forwards the selected layout, and logs parse failures.
- [x] Sway workspace, focus, close, and logout actions use backend handles or `swaymsg exit` and log failures.

### Mango backend

- [x] Mango tag parsing handles newline-separated `mmsg` output, detailed tags, binary tag fallbacks, active/urgent bits, focused window metadata, layout symbol, keyboard layout changes, selected monitor, and state merging.
- [x] Mango workspace/window guards normalize tag, monitor, focus, urgency, title, app id, output, and layout data.
- [x] Mango scale and lifecycle guards maintain monitor scales and startup/update flows.
- [x] Mango command guards build safe `mmsg` command paths for workspace/window/logout behavior.
- [x] Mango workspace switching prefers original tag indexes and explicit outputs, falls back to selected monitor, and omits output for single-monitor state.
- [x] Mango focus/close commands prefer direct handles, fall back to workspace switching or focused-client kill, and logout requests compositor quit.

### Workspace widget

- [x] Workspace dimensions respect label mode, active state, base dimensions, character count, spacing, and padding.
- [x] Aggregate workspace dimensions include per-workspace sizes, spacing, and padding.
- [x] Focused workspace lookup returns the focused local index, switching by offset wraps/clamps through local workspaces, and empty workspace lists fail closed.
- [x] Workspace refresh filters by screen, follow-focused-screen mode, and occupied state, updates repeater models, and refreshes focus state.

### Grouped taskbar

- [x] Grouped taskbar filters workspace groups by screen and preserves normalized workspace/window order through launches, model clears, and screen reassignment.
- [x] Window left-click focuses that window; empty-group left-click switches workspace. Window context actions appear in activate/close/settings order; empty groups expose settings only. Actions clear selection and retain widget settings context.
- [x] Delegate ownership qualification preserves icon sizing and leaves notification/toast input regions unchanged.

### Ungrouped taskbar

- [x] Window order follows normalized Niri state; output and active-workspace filters control visible icons, and left-click records the selected window's focus command.
- [x] Workspace changes and window moves refresh visible windows; context actions preserve activate/close/settings order, command arguments, settings context, and selection reset.
- [x] Horizontal and vertical layouts handle launches, output reassignment, model clears, and repopulation while updating `hasWindow`.

### Types and probes

- [x] Compositor backend references are typed.
- [x] Taskbar window delegate roles are typed.
- [x] Service probes validate Niri IPC extraction and reject malformed function suffixes.

## How it works

- [docs/wiki/systems/compositor.md](../wiki/systems/compositor.md)

## Implementation inventory

- `Services/Compositor/CompositorService.qml` - backend detection, shared state, display-scale cache, and backend delegation.
- `Services/Compositor/NiriService.qml` - Niri IPC sockets, state recollection, events, and actions.
- `Services/Compositor/HyprlandService.qml` - Hyprland state refresh, normalization, keyboard handling, and actions.
- `Services/Compositor/SwayService.qml` - Sway/i3 state refresh, input handling, and actions.
- `Services/Compositor/MangoService.qml` - Mango tag parsing, monitor/window state, and `mmsg` actions.
- `Modules/Bar/Widgets/Workspace.qml` - bar workspace dimensions, filtering, focus, and switching.
- `Modules/Bar/Widgets/Taskbar.qml` - ungrouped window filtering, activation, context actions, and delegate typing.

## Tests asserting this spec

- `Tests/root-service-static.test.py` — root-service lint/behavior entrypoint isolation and warning rejection with inert I/O; includes compositor/IPC, [brightness](brightness.md), [audio](audio.md), [Bluetooth](bluetooth.md) and [notifications](notifications.md).

- `Tests/widget-settings-cohort-warnings.test.py` / `Tests/Qml/WidgetSettingsCohortHarness.qml` — WorkspaceSettings: two toggles, label-mode selection, character-count bounds 1–10, and count-control visibility for name versus index labels. No live workspace/compositor IPC proof. Each editor also exercises fixture defaults, save-copy isolation, cancel/reopen, and apply-close. Completed isolated assertions do not close the RED shared-control runtime warning gate. Cohort counts/lint evidence: [bar](bar.md#tests-asserting-this-spec); isolation and limits: [testing](testing.md#widget-settings-cohort).

- `Tests/root-service-warnings.test.py behavior` / `Tests/Qml/RootServiceHarness.qml` — production CompositorService facade receives fixture backend workspace/window events, mirrors focused-window state, and completes the real lock/suspend polling timer with recorded suspend dispatch. One of five behavioral cases (seven passes including QtTest init/cleanup) at `8b1de9d34`; no real backend IPC, lock, or suspend occurs. Root-only lint leaves five `unqualified`, nineteen `missing-property`, and seven `block-scope-var-declaration` warnings in this service. Cohort gates and limits: [testing](testing.md#root-service-cohort).
- `Tests/compositor-service-warnings.test.py` / `Tests/Qml/CompositorServiceHarness.qml` — at `daf1b4339`/`392ff8e19`, facade-only warnings drop 12→7 in deduplicated text and 31→19 in JSON. Remaining diagnostics are concrete backend API members absent from shared `Item` metadata, retained without suppression; this is not zero-warning lint. Ten behavioral rows plus QtTest init/cleanup yield twelve reported offscreen cases: five backend-selection/replacement rows assert priority, initialization, one live fixture backend, mirrored startup models and delegated action arguments; one cache-loaded event case checks restored display data without writes; one event-ordering case checks model replacement before forwarding, repeated window-list notification on active change, title cleanup and empty models; three real-timer rows check confirmed lock, component timeout and activation timeout, timer stop/count reset and exactly one recorded suspend dispatch. Backend services, environment, ShellState, lock screen and commands are fixtures; no real compositor, IPC, lock, suspend or persistence proof. Isolation and runner gates: [testing](testing.md#compositor-facade-isolated-runtime).
- `Tests/compositor-service-guards.test.js`
- `Tests/shell-state-consumer-roundtrip.test.js`
- `Tests/service-cohort-warnings.test.py` with `Tests/Qml/ServiceCohortHarness.qml` — standalone `behavior` instantiates actual Niri/Sway/Hyprland services offscreen. Niri covers connected socket write order, injected command/event parsing, workspace/window normalization, window-before-active signal order, focus/close/layout/overview events, output refresh requests, model clearing, socket disposal, and disconnected recreation. Separate Sway/Hyprland rows cover pre-initialize connection gating, workspace/window state, split output accumulation/reset, empty outputs, keyboard parsing, workspace-model rebinding with old-model silence, raw output/layout events, and silence after disposal. Together with LockKeys these are four behavioral rows plus QtTest initialization/cleanup (six total). I/O, backend models, compositor facade, and keyboard consumer are fixtures: no real socket/process/compositor IPC or command execution proof. Shared safety and acceptance gates: [testing](testing.md). Standalone `lint` requires exit status zero and zero warnings per service (Niri 15→0, Sway 9→0, Hyprland 9→0 at `aeb28001c`); no runner integration or whole-shell acceptance is claimed.
- `Tests/niri-service-guards.test.js`
- `Tests/hyprland-service-guards.test.js`
- `Tests/sway-service-guards.test.js`
- `Tests/mango-service-warnings.test.py` / `Tests/Qml/MangoServiceHarness.qml` — through `528a11c89`/`e29920f48`, MangoService warnings drop two text/eight JSON→0 by resolving regex members through the actual `patterns` object ID, including the stream frame delimiter. Two behavioral tests plus QtTest init/cleanup yield four reported offscreen passes: initial-exit buffering, detailed/binary tag merging, urgency/occupancy, keyboard/layout state, focused-window mapping and retained unfocused tags across outputs; scale-query exit ordering, exact display records, retained monitor scales and update signals. Process, toplevel, keyboard and facade boundaries are fixtures; no real compositor, commands or config access. Tag/scale mutations are rejected negative controls. Gates and isolation: [testing](testing.md#mango-service-isolated-runtime).
- `Tests/mango-service-guards.test.js`
- `Tests/qml-runtime-guards.test.js` — through `885c72d81`, private Workspace QtTest extension reports 4/4 passes (two orientation rows plus init/cleanup): urgent background/foreground survive cleared urgency and delegate recreation, remain urgent before five-second expiry, then restore settled colors across another rebuild. TaskbarGrouped's invoked private harness reports 8/8 including init/cleanup, with corresponding cooldown/rebuild behavior alongside existing grouping/actions/layout cases. Reported timing/restoration mutations fail; no real config or live compositor is exercised. Aggregate evidence and limits: [testing](testing.md#qml-runtime-guards-behavioral-replacement).
- `Tests/workspace-guards.test.js` — at `ff8a3270a`, production dimension, focused-index/switching and screen/occupancy refresh helpers execute with owner-bound fixture models/services; not regex proof or real compositor switching.
- `Tests/workspace-runtime.test.py` with `Tests/Qml/WorkspaceHarness.qml` — isolated offscreen production Workspace/Niri normalization coverage: eight behavioral cases plus QtTest initialization/cleanup (ten total). Covers initial geometry, output reassignment and click-command order, vertical labels/active sizing, offset switching, occupied/focused-output filtering, and Loader model context; both orientations additionally cover model clear/reassignment/destruction/recreation, label geometry/colors, urgency changes, and effect inputs. Desktop/process/settings boundaries are fixtures; activation commands are recorded, not sent to Niri. Rejects QWARN/QFATAL/ReferenceError/TypeError and verifies real settings remain unchanged. Runs in the deterministic unit gate; no live IPC coverage.
- `Tests/taskbar-grouped-warnings.test.py` with `Tests/Qml/TaskbarGroupedHarness.qml` — standalone `lint` audits only production TaskbarGrouped; `behavior` runs the production widget and Niri normalization offscreen. Covers concrete shuffled window groups, launch events, focus/close/workspace command arguments, menu order/reset/settings context, icon dimensions, and clear/output reassignment in horizontal/vertical layouts. Desktop commands, popup surfaces, icons, settings and compositor facade are fixtures; no live Wayland IPC or notification-flicker coverage. Synthetic private settings/backup are checked unchanged; real config is not accessed.
- `Tests/taskbar-warnings.test.py` with `Tests/Qml/TaskbarHarness.qml` — standalone `lint` requires zero production Taskbar warnings and exit status zero after `60c64807d` (37→0). `behavior` exercises production Taskbar, Niri normalization, and copied facade synchronization/active-workspace helpers offscreen: five behavioral cases plus QtTest initialization/cleanup (seven total). Covers order/filter/activation, workspace transitions, context actions/reset/settings context, and horizontal/vertical launch/clear/output reassignment. Mouse clicks target production MouseAreas; commands are recorded, not sent to Niri. Settings, icons, popup surfaces, and the remaining facade are fixtures; HOME/XDG paths are isolated and real settings are backed up and checked unchanged. Rejects QWARN/QFATAL/ReferenceError/TypeError/binding loops. No runner integration or whole-shell acceptance is claimed; icon sizing and input regions were untouched.
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

### Grouped taskbar settings isolated evidence

- Through `871d9128c`, `TaskbarGroupedSettings.qml` warnings drop 4→0. Shared lint/runtime counts and isolation: [testing](testing.md#grouped-taskbarosd-settings-isolated-runtime).
- `Tests/Qml/GroupedOsdSettingsWarningsHarness.qml` checks grouped defaults, all four label modes, three toggles, pending edits, copy-save preserving unrelated fields and source data, reactive controls, and independent editor instances. Baseline and owner-shadow runs each report seven passes across both editors, including QtTest init/cleanup; not seven grouped-only cases.
- Pre-existing runtime warning when grouped `labelMode` is omitted remains; passing fixtures explicitly supply it. No real persistence, live taskbar/compositor interaction, or notification cursor-flicker fix is proven.

## Known gaps (current cycle)

- [ ] Define a concrete backend API metadata contract to resolve the facade's seven text/nineteen JSON `missing-property` diagnostics; shared `Item` typing does not expose those members.
- [ ] Add executable coverage for active window widget display behavior.
- [ ] Reproduce and verify Firefox/grouped-taskbar cursor flicker triggered per notification at the notification/toast layer-surface input-region boundary. Neither taskbar offscreen harness proves a fix; `60c64807d` changes neither input regions nor icon sizing.
- [ ] Add executable coverage for backend process failure output parsing.
- [ ] Add live-smoke coverage for one active compositor backend when a shell instance is running; the isolated Workspace/Niri and four-service cohort harnesses do not exercise live IPC or compositor activation.

## Out of scope

- Session menu action selection belongs in a dedicated session/power spec.
- Taskbar grouped notification badge cooldown belongs in [notifications.md](notifications.md) until a taskbar-specific spec exists.
