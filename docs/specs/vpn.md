VPN covers NetworkManager VPN discovery, connection state, connect/disconnect commands, refresh scheduling, and VPN panel/widget entry points. Runtime source lives mainly in `Services/Networking/VPNService.qml` and `Modules/Panels/VPN/`.

## What it must do

### Refresh lifecycle

- [x] VPN refresh polling is ref-counted by visible consumers.
- [x] The periodic refresh timer runs only while at least one consumer holds a polling reference.
- [x] The service does not start `nmcli` refresh polling at startup before a consumer appears.
- [x] Starting a polling reference immediately refreshes VPN state.
- [x] Ending a polling reference clamps the reference count at zero.
- [x] The bar VPN widget, Control Center panel with a VPN shortcut, and VPN panel hold polling references only while visible/open.
- [x] Refresh requests during an active refresh are marked pending without clearing the existing error or starting another process.
- [x] Refresh requests when idle mark the service refreshing, clear the last error, and start the refresh process.
- [x] Delayed refresh scheduling updates the timer interval and restarts the timer.
- [x] Refresh-process stdout parsing keeps `vpn` and `wireguard` rows, handles connection names containing colons, marks devices other than `--` as active, and ignores non-VPN or malformed rows.
- [x] Refresh output and errors are buffered until process exit determines success or failure.
- [x] Nonzero and failed-to-start `nmcli` refreshes clear busy state, preserve the previous connection map, expose a concrete error, and avoid normal-exit double finalization.
- [x] A pending refresh drains after completion with a short success delay or longer failure delay.

### Connect and disconnect

- [x] Connect rejects empty UUIDs and missing connections.
- [x] Connect starts only when no connection process is already running.
- [x] Connect records connecting state, target UUID, clears the last error, stores the target connection name, and starts the connect process.
- [x] Disconnect rejects empty UUIDs and missing connections.
- [x] Disconnect starts only when no disconnect process is already running.
- [x] Disconnect records disconnecting state, target UUID, clears the last error, stores the target connection name, and starts the disconnect process.
- [x] Connect and disconnect buffer stdout/stderr until exit status determines success or failure.
- [x] Successful actions update connection state, clear busy/error state, show a notice, and schedule refresh without depending on localized stdout text.
- [x] Nonzero exits and failed process starts preserve connection state, clear busy state, expose stderr/stdout diagnostics or a concrete fallback, show a warning, and avoid normal-exit double finalization.
- [x] Action completion is UUID-identity-safe and clears the prior UUID before notifying busy-state observers, so stale or reentrant completion cannot clobber a newer action.
- [x] Toggle ignores missing connections.
- [x] Toggle disconnects active connections.
- [x] Toggle connects inactive connections.

### Connection state

- [x] Setting a connection rejects empty UUIDs and unknown connections.
- [x] Setting a known connection replaces the connection map instead of mutating it in place.
- [x] Setting a known connection preserves existing fields and merges new state such as active flag and device name.

### Probe predicates

- [x] VPN type detection accepts NetworkManager `vpn` and `wireguard` types.
- [x] VPN type detection rejects non-VPN NetworkManager types.
- [x] NetworkManager UUID validation accepts UUID-shaped values and rejects malformed values.
- [x] Active device validation accepts device names such as `wg0` and rejects inactive placeholders, blank values, and malformed values.
- [x] Connected-state validation accepts connected and connecting states and rejects disconnected or malformed connected strings.

### Panel and widget interactions

- [x] The VPN panel owns polling while open, refreshes on request, and renders active and inactive connection groups separately.
- [x] A connection row disables its single action while busy and routes active rows to disconnect and inactive rows to connect.
- [x] The Control Center shortcut resolves and toggles the VPN panel for its screen.
- [x] The bar context menu exposes connect, disconnect, and widget-settings actions and opens from both primary and secondary clicks.

### Panel row typing

- [x] VPN connection-list delegates type connection UUID, name, and active state roles and pass those scalars into each row item.
- [x] VPN connection row items use typed connection properties instead of dynamic `connection.*` field reads.

## How it works

- Runtime behavior is implemented in `Services/Networking/VPNService.qml` and the VPN panel/widget entry points.

## Implementation inventory

- `Services/Networking/VPNService.qml` - NetworkManager VPN discovery, connection map state, refresh scheduling, connect/disconnect processes, and active/inactive connection lists.
- `Modules/Panels/VPN/VPNPanel.qml` - VPN SmartPanel shell and active/available connection sections.
- `Modules/Panels/VPN/VPNConnectionsList.qml` - grouped VPN connection list.
- `Modules/Panels/VPN/VPNConnectionItem.qml` - per-connection status and connect/disconnect action row.
- `Modules/Bar/Widgets/VPN.qml` - bar widget and context menu entry point.
- `Modules/Panels/ControlCenter/Widgets/VPN.qml` - Control Center VPN panel launcher.
- `Modules/Panels/Settings/Bar/WidgetSettings/VPNSettings.qml` - VPN bar widget display-mode settings.

## Tests asserting this spec

- `Tests/vpn-service-guards.test.js`
- `Tests/vpn-ui-guards.test.js`
- `Tests/qml-type-annotations.test.js`
- `Tests/service-probes-parsing.test.sh`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

None.

## Out of scope

- Wi-Fi and general NetworkManager connection behavior belongs in [network.md](network.md).
- Host VPN backend behavior belongs to NetworkManager; this spec covers the shell boundary.
