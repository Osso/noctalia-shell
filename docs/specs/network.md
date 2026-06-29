Network covers Wi-Fi radio state, scan scheduling, NetworkManager connection commands, cached known networks, connection status updates, and Wi-Fi icon/security helpers. Runtime source lives mainly in `Services/Networking/NetworkService.qml`; implementation notes belong in [docs/wiki/systems/network.md](../wiki/systems/network.md).

## What it must do

### Cache, Wi-Fi state, and idle polling

- [x] Cache saves are debounced.
- [x] Wi-Fi state sync queries the live radio state.
- [x] On-demand network status refresh queries Ethernet, connected Wi-Fi, and connectivity state.
- [x] Setting Wi-Fi enabled updates settings first and starts the nmcli radio command.
- [x] Startup does not perform a background Wi-Fi scan.
- [x] Idle Ethernet/connectivity timers run only while an active network UI consumer is open.
- [x] Wi-Fi panel opening starts active polling and Wi-Fi scanning through NetworkService.
- [x] Wi-Fi panel closing releases active polling.
- [x] Delayed scan timers do not rescan while idle.

### Scanning

- [x] Scan no-ops while Wi-Fi is disabled.
- [x] Scan queues a pending rescan and ignores in-flight results instead of racing an active scan.
- [x] Scan resets stale errors and scan state before launching.
- [x] Scan refreshes known profiles before scanning networks.
- [x] nmcli scan output parsing handles SSIDs with colons, duplicate SSIDs, open networks, malformed rows, known-profile flags, cached-network flags, and last-connected cache updates.

### Connect, disconnect, and forget

- [x] Connect ignores duplicate requests while already connecting.
- [x] Connect sets busy state, target SSID, and clears stale errors.
- [x] Connect reuses existing or cached profiles without retaining typed passwords.
- [x] Connect creates new profiles with supplied passwords when no existing profile is known.
- [x] Disconnect tracks the target SSID and starts the disconnect process.
- [x] Forget tracks the target SSID, removes it from the known-network cache, preserves other cached networks, clears `lastConnected` when needed, persists cache changes, and starts the forget process.

### Status and icons

- [x] Connection status updates disconnect other active networks.
- [x] Existing connected targets become connected, existing, and cached.
- [x] Missing connected targets are synthesized with placeholder security and full signal.
- [x] Missing disconnected targets are not synthesized.
- [x] Status updates force a `networks` property-change notification.
- [x] Passive device status synthesizes connected Wi-Fi networks from `nmcli device` output so bar icons do not require a background scan.
- [x] Passive device status clears stale connected Wi-Fi state when no Wi-Fi device is connected.
- [x] Unknown or missing connectivity checks default connected Wi-Fi to the normal Wi-Fi icon instead of `world-off`.
- [x] Connected offline networks show the `world-off` icon only after a known offline/captive connectivity result.
- [x] Signal strength maps strong, medium, weak, and very weak/missing signal to the expected Wi-Fi icons.
- [x] Security helper rejects missing, placeholder, and blank security values.

## How it works

- [docs/wiki/systems/network.md](../wiki/systems/network.md)

## Implementation inventory

- `Services/Networking/NetworkService.qml` - Wi-Fi radio state, scanning, connection commands, cache state, status updates, and icon/security helpers.
- `Modules/Panels/WiFi/WiFiPanel.qml` - Wi-Fi panel shell.
- `Modules/Panels/WiFi/WiFiNetworksList.qml` - network list, connect/disconnect/forget UI.
- `Modules/Panels/Settings/Tabs/NetworkTab.qml` - settings toggles for network features.
- `Modules/Bar/Widgets/Network.qml` - bar network status widget.

## Tests asserting this spec

- `Tests/network-service-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add executable tests for connectivity check and ping fallback transitions.
- [ ] Add spec coverage for Wi-Fi panel connect/password/forget UI behavior.

## Out of scope

- Bluetooth and airplane-mode state belongs in a separate Bluetooth spec.
- System monitor network throughput belongs in a separate system monitor spec.
