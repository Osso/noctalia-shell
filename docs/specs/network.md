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
- [x] Scan queues a pending rescan and ignores superseded successful output instead of racing an active scan.
- [x] Scan resets stale errors and scan state before launching.
- [x] Scan refreshes known profiles before scanning networks.
- [x] nmcli scan output parsing handles SSIDs with colons, duplicate SSIDs, open networks, malformed rows, known-profile flags, cached-network flags, and last-connected cache updates.
- [x] Profile-query and Wi-Fi scan collectors buffer stdout/stderr and apply normal scan state from process-exit handlers after the exit status is known.
- [x] Nonzero exits from started profile-query or Wi-Fi scan processes clear busy state and publish a concrete error; queued rescans get a 100 ms follow-up, while delayed retry execution remains gated by an active Wi-Fi UI consumer.

### Connect, disconnect, and forget

- [x] Connect rejects empty or overlapping requests using both service and process state.
- [x] Connect sets busy state, target SSID, clears stale errors, resets process buffers, and advances operation identity.
- [x] Connect reuses existing or cached profiles without retaining typed passwords.
- [x] Connect creates new profiles with supplied passwords when no existing profile is known.
- [x] Disconnect rejects empty/overlapping requests, tracks the target SSID, resets process buffers, advances operation identity, and starts the disconnect process.
- [x] Connect/disconnect completion is exit-code-driven, identity-safe, and independent of localized stdout text.
- [x] Successful actions update status/cache as applicable, clear credentials/busy/error state, show notice, refresh status, and schedule scans only while polling.
- [x] Nonzero and failed-start actions preserve network/cache state, clear credentials/busy state, expose stderr/stdout diagnostics or a concrete fallback, and do not schedule scans that erase errors.
- [x] Forget rejects empty/overlapping requests, tracks the target SSID, resets buffered process state, and starts system profile deletion without mutating cache/UI state first.
- [x] The forget helper lists unescaped NetworkManager profile names, matches exact, `Auto `, and arbitrary numeric-suffix variants, and propagates list/delete failures.
- [x] Successful forget completion identity-checks the SSID, removes only that cached network, clears `lastConnected` when needed, updates known/existing UI state, persists cache changes, and schedules verification scan while polling.
- [x] Nonzero and failed-to-start forget operations preserve cache/UI state, clear busy state, expose a concrete error, and cannot let stale completion overwrite a newer request.

### Status and icons

- [x] Connection status updates disconnect other active networks.
- [x] Existing connected targets become connected, existing, and cached.
- [x] Missing connected targets are synthesized with placeholder security and full signal.
- [x] Missing disconnected targets are not synthesized.
- [x] Status updates force a `networks` property-change notification.
- [x] Passive device status synthesizes connected Wi-Fi networks from `nmcli device` output so bar icons do not require a background scan.
- [x] Passive device status clears stale connected Wi-Fi state when no Wi-Fi device is connected.
- [x] Ethernet and Wi-Fi radio status mutate state only after successful process exit; nonzero and failed-start checks preserve the last known state and log a concrete diagnostic.
- [x] Unknown or missing connectivity checks default connected Wi-Fi to the normal Wi-Fi icon instead of `world-off`.
- [x] Connected offline networks show the `world-off` icon only after a known offline/captive connectivity result.
- [x] `none` transitions immediately clear internet connectivity; `full` transitions restore it.
- [x] Repeated limited/portal results launch at most one fallback ping, expose offline state while validation is pending, and ignore ping completion superseded by a newer connectivity result.
- [x] Fallback ping failure remains offline, resets failure accumulation, reports the limitation, and scans only while active polling is retained.
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

- `Tests/network-forget-profiles.test.sh`
- `Tests/network-service-guards.test.js`
- `Tests/qml-runtime-guards.test.js`

## Known gaps (current cycle)

- [ ] Add spec coverage for Wi-Fi panel connect/password/forget UI behavior.

## Out of scope

- Bluetooth and airplane-mode state belongs in a separate Bluetooth spec.
- System monitor network throughput belongs in a separate system monitor spec.
