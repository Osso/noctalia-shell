VPN covers NetworkManager VPN discovery, connection state, connect/disconnect commands, refresh scheduling, and VPN panel/widget entry points. Runtime source lives mainly in `Services/Networking/VPNService.qml` and `Modules/Panels/VPN/`; implementation notes belong in [docs/wiki/systems/vpn.md](../wiki/systems/vpn.md).

## What it must do

### Refresh lifecycle

- [x] Refresh requests during an active refresh are marked pending without clearing the existing error or starting another process.
- [x] Refresh requests when idle mark the service refreshing, clear the last error, and start the refresh process.
- [x] Delayed refresh scheduling updates the timer interval and restarts the timer.
- [x] Refresh-process stdout parsing keeps `vpn` and `wireguard` rows, handles connection names containing colons, marks devices other than `--` as active, and ignores non-VPN or malformed rows.

### Connect and disconnect

- [x] Connect rejects empty UUIDs and missing connections.
- [x] Connect starts only when no connection process is already running.
- [x] Connect records connecting state, target UUID, clears the last error, stores the target connection name, and starts the connect process.
- [x] Disconnect rejects empty UUIDs and missing connections.
- [x] Disconnect starts only when no disconnect process is already running.
- [x] Disconnect records disconnecting state, target UUID, clears the last error, stores the target connection name, and starts the disconnect process.
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

## How it works

- [docs/wiki/systems/vpn.md](../wiki/systems/vpn.md)

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
- `Tests/service-probes-parsing.test.sh`
- `Tests/source-coverage.test.js`

## Known gaps (current cycle)

- [ ] Add executable coverage for connect/disconnect process exit and toast handling.
- [ ] Add executable coverage for VPN panel rendered active/available sections.
- [ ] Add executable coverage for bar and Control Center VPN entry-point interactions.

## Out of scope

- Wi-Fi and general NetworkManager connection behavior belongs in [network.md](network.md).
- Host VPN backend behavior belongs to NetworkManager; this spec covers the shell boundary.
