Compositor covers backend detection, shared workspace/window state, display-scale cache, backend adapters for Niri, Hyprland, Sway, and Mango, and the Workspace bar widget. Runtime source lives mainly in `Services/Compositor/CompositorService.qml`, backend service files under `Services/Compositor/`, and `Modules/Bar/Widgets/Workspace.qml`; implementation notes belong in [docs/wiki/systems/compositor.md](../wiki/systems/compositor.md).

## What it must do

### Shared compositor service

- [x] Compositor detection inspects Hyprland, Niri, Sway, and desktop environment state, prefers Mango desktop detection, selects matching Niri/Hyprland/Sway backends, and falls back to Niri.
- [x] Display-scale cache loading reads ShellState display data and fails closed when cached state is unavailable.
- [x] Display-scale updates and cache saves mirror backend display data through ShellState.
- [x] Display info lookup returns known display data and returns null for missing displays.
- [x] Shared workspace, window, focused-window, active-workspace, clean-app-name, and workspace-window helpers mirror backend models and fail closed for invalid indexes or missing focus.
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
- `Modules/Bar/Widgets/Taskbar.qml` - window delegate typing covered by compositor-facing type tests.

## Tests asserting this spec

- `Tests/compositor-service-guards.test.js`
- `Tests/niri-service-guards.test.js`
- `Tests/hyprland-service-guards.test.js`
- `Tests/sway-service-guards.test.js`
- `Tests/mango-service-guards.test.js`
- `Tests/workspace-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`

## Known gaps (current cycle)

- [ ] Add executable coverage for active window widget display behavior.
- [ ] Add executable coverage for taskbar compositor actions beyond typed delegate roles.
- [ ] Add executable coverage for backend process failure output parsing.
- [ ] Add live-smoke coverage for one active compositor backend when a shell instance is running.

## Out of scope

- Session menu action selection belongs in a dedicated session/power spec.
- Taskbar grouped notification badge cooldown belongs in [notifications.md](notifications.md) until a taskbar-specific spec exists.
